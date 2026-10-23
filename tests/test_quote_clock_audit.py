from datetime import datetime, timedelta, timezone
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from quote_clock_audit import validate_quote_clock
from temporal_causality import utc_milliseconds
from independent_clock_reference import decode_response, reconcile, NTP_UNIX_OFFSET


class QuoteClockAuditTests(unittest.TestCase):
    def check(self, decision, stamp):
        return validate_quote_clock(seconds=stamp // 1000, milliseconds=stamp, decision=decision)

    def test_correct_exact_and_one_millisecond_future(self):
        now = datetime(2026, 10, 23, tzinfo=timezone.utc)
        ms = utc_milliseconds(now)
        self.assertTrue(self.check(now, ms - 1)[0])
        self.assertTrue(self.check(now, ms)[0])
        self.assertEqual(self.check(now, ms + 1)[1], 'FUTURE_QUOTE')

    def test_stale_startup_tick_is_not_made_fresh_by_attach(self):
        now = datetime(2026, 10, 23, tzinfo=timezone.utc)
        old = utc_milliseconds(now) - 5001
        for attempt in range(3):
            self.assertEqual(self.check(now + timedelta(seconds=attempt), old)[1], 'STALE_QUOTE')

    def test_server_offset_and_dst_preserve_instant(self):
        for now in (datetime(2026, 3, 29, 1, tzinfo=timezone.utc), datetime(2026, 10, 25, 1, tzinfo=timezone.utc)):
            for offset in (-5, 2, 3):
                wall = now.astimezone(timezone(timedelta(hours=offset)))
                self.assertTrue(self.check(wall, utc_milliseconds(now))[0])

    def test_double_timezone_conversion_and_naive_time_rejected(self):
        now = datetime(2026, 10, 23, tzinfo=timezone.utc)
        shifted = utc_milliseconds(now + timedelta(hours=2))
        self.assertEqual(self.check(now, shifted)[1], 'FUTURE_QUOTE')
        with self.assertRaises(ValueError):
            self.check(now.replace(tzinfo=None), utc_milliseconds(now))

    def test_seconds_milliseconds_pair_must_agree(self):
        now = datetime(2026, 10, 23, tzinfo=timezone.utc)
        ms = utc_milliseconds(now)
        for seconds, milliseconds in ((ms, ms), (ms // 1000, ms // 1000), (ms // 1000 + 1, ms), (None, ms)):
            self.assertEqual(validate_quote_clock(seconds=seconds, milliseconds=milliseconds, decision=now)[1], 'SECONDS_MILLISECONDS_MISMATCH')

    def test_wrong_local_clock_does_not_justify_quote_offset(self):
        bad = datetime(2026, 10, 23, tzinfo=timezone.utc)
        tick = utc_milliseconds(bad + timedelta(days=1))
        self.assertEqual(self.check(bad, tick)[1], 'FUTURE_QUOTE')
        # Independent time can explain provenance; the stale quote is still rejected.
        self.assertEqual(self.check(bad + timedelta(days=2), tick)[1], 'STALE_QUOTE')

    def test_ntp_nonce_leap_and_stratum_validation(self):
        nonce = b'12345678'
        packet = bytearray(48); packet[0] = 0x24; packet[1] = 1
        packet[24:32] = nonce; packet[40:48] = struct.pack('!II', NTP_UNIX_OFFSET + 100, 0)
        self.assertEqual(decode_response(bytes(packet), nonce), 100_000_000_000)
        for index, value in ((0, 0xE4), (1, 0), (24, 0)):
            bad = bytearray(packet); bad[index] = value
            with self.assertRaises(ValueError): decode_response(bytes(bad), nonce)

    def test_reference_quorum_requires_overlap_and_independence(self):
        rows = [{'host': str(i), 'server_transmit_ns': 1000, 'received_monotonic_ns': 100, 'rtt_ns': 20} for i in range(3)]
        result = reconcile(rows, anchor_monotonic_ns=100, local_utc_ns=10)
        self.assertEqual(result['status'], 'REFERENCE_QUORUM')
        self.assertFalse(result['local_clock_within_network_interval'])
        self.assertEqual(reconcile(rows[:2], anchor_monotonic_ns=100, local_utc_ns=10)['status'], 'UNVERIFIED')
        rows[2]['server_transmit_ns'] = 2000
        self.assertEqual(reconcile(rows, anchor_monotonic_ns=100, local_utc_ns=10)['status'], 'UNVERIFIED')


if __name__ == '__main__':
    unittest.main()
