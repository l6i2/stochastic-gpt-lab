"""Diagnostic UTC cross-check, never adjusts a clock or authorizes a quote.

NTP is unauthenticated: corroborate its result with independent TLS Date responses.
Intervals include the entire network RTT, rather than accepting future quotes by
adding an arbitrary tolerance. An empty quorum intersection fails closed.
"""
from __future__ import annotations
from datetime import datetime, timezone
import secrets
import socket
import struct
import time
import urllib.request
from email.utils import parsedate_to_datetime

NTP_UNIX_OFFSET = 2208988800


def decode_response(packet: bytes, nonce: bytes) -> int:
    if (len(packet) < 48 or packet[0] & 7 != 4 or packet[0] >> 6 == 3
            or not 1 <= packet[1] <= 15 or packet[24:32] != nonce):
        raise ValueError('INVALID_NTP_RESPONSE')
    seconds, fraction = struct.unpack('!II', packet[40:48])
    return (seconds - NTP_UNIX_OFFSET) * 1_000_000_000 + fraction * 1_000_000_000 // 2**32


def reconcile(samples: list[dict], *, anchor_monotonic_ns: int, local_utc_ns: int) -> dict:
    if len(samples) < 3 or len({s['host'] for s in samples}) < 3:
        return {'status': 'UNVERIFIED', 'reason': 'THREE_INDEPENDENT_REFERENCES_REQUIRED'}
    lower = max(s['server_transmit_ns'] + anchor_monotonic_ns - s['received_monotonic_ns'] for s in samples)
    upper = min(s['server_transmit_ns'] + s['rtt_ns'] + anchor_monotonic_ns - s['received_monotonic_ns'] for s in samples)
    if lower > upper:
        return {'status': 'UNVERIFIED', 'reason': 'REFERENCE_INTERVALS_DISAGREE'}
    return {'status': 'REFERENCE_QUORUM', 'authority_scope': 'diagnostic only; unauthenticated NTP',
            'utc_lower_ns': lower, 'utc_upper_ns': upper,
            'local_clock_within_network_interval': lower <= local_utc_ns <= upper,
            'local_lag_lower_ns': lower - local_utc_ns, 'local_lag_upper_ns': upper - local_utc_ns}


def capture_reference() -> dict:
    samples, errors = [], []
    for host in ('time.windows.com', 'time.cloudflare.com', 'time.google.com'):
        nonce = secrets.token_bytes(8)
        request = b'\x23' + bytes(39) + nonce
        started = time.monotonic_ns()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
                client.settimeout(3)
                client.connect((host, 123))
                client.send(request)
                packet = client.recv(512)
            received = time.monotonic_ns()
            transmit = decode_response(packet, nonce)
            samples.append({'host': host, 'server_transmit_ns': transmit,
                            'server_transmit_utc': datetime.fromtimestamp(transmit / 1e9, timezone.utc).isoformat(),
                            'rtt_ns': received - started, 'received_monotonic_ns': received,
                            'stratum': packet[1], 'nonce_echo_verified': True,
                            'root_delay_ns': struct.unpack('!i',packet[4:8])[0]*1_000_000_000//65536,
                            'root_dispersion_ns': struct.unpack('!I',packet[8:12])[0]*1_000_000_000//65536,
                            'precision_log2_seconds': struct.unpack('!b',packet[3:4])[0],
                            'leap_indicator': packet[0]>>6,
                            'response_packet_hex': packet.hex(), 'request_nonce_hex': nonce.hex(),
                            'authenticated': False,
                            'uncertainty_scope': 'RTT and unauthenticated server-advertised errors; no calibrated oscillator bound'})
        except (OSError, ValueError) as exc:
            errors.append({'host': host, 'error': type(exc).__name__})
    kernel_interval = None
    if __import__('sys').platform == 'win32':
        import ctypes
        kernel = ctypes.windll.kernel32.GetTickCount64
        kernel.restype = ctypes.c_ulonglong
        kernel_before = kernel()
    anchor = time.monotonic_ns()
    local = time.time_ns()
    if __import__('sys').platform == 'win32':
        kernel_interval = [kernel_before, kernel()]
    comparison = reconcile(samples, anchor_monotonic_ns=anchor, local_utc_ns=local)
    tls = []
    for base in ('https://www.microsoft.com/', 'https://www.google.com/generate_204', 'https://www.bing.com/'):
        started = time.monotonic_ns()
        try:
            request = urllib.request.Request(base + '?clockaudit=' + secrets.token_hex(8),
                method='HEAD', headers={'Cache-Control': 'no-cache, no-store'})
            with urllib.request.urlopen(request, timeout=5) as response:
                value, age = response.headers.get('Date'), response.headers.get('Age')
            received = time.monotonic_ns()
            stamp = int(parsedate_to_datetime(value).timestamp()) * 1_000_000_000
            # HTTP Date is second resolution. Project its interval to the NTP anchor.
            lower = stamp + anchor - received
            upper = stamp + 1_000_000_000 + received - started + anchor - received
            agrees = (comparison.get('status') == 'REFERENCE_QUORUM' and age in (None, '0')
                      and lower <= comparison['utc_upper_ns'] and upper >= comparison['utc_lower_ns'])
            tls.append({'url': base, 'date': value, 'age': age, 'agrees_with_ntp_interval': agrees})
        except (OSError, ValueError, TypeError) as exc:
            tls.append({'url': base, 'error': type(exc).__name__, 'agrees_with_ntp_interval': False})
    return {'samples': samples, 'errors': errors, 'anchor_monotonic_ns': anchor,
            'anchor_kernel_uptime_ms_interval': kernel_interval,
            'projection_limits': 'No calibrated uptime quantization/drift or broker callback queue-delay bound',
            'local_utc_ns': local, 'local_utc': datetime.fromtimestamp(local / 1e9, timezone.utc).isoformat(),
            'comparison': comparison, 'tls_corroboration': tls,
            'tls_corroborated': sum(row['agrees_with_ntp_interval'] for row in tls) >= 2,
            'clock_changed': False, 'orders_sent': 0}
