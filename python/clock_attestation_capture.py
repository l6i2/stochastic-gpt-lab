"""Pair 50 native MT5 frames with Windows clocks using shared GetTickCount64.

Observation is bounded, not atomic: retain every native read bracket and the
sidecar receipt bracket. Never infer simultaneous reads from wall-clock labels.
"""
from __future__ import annotations
import csv
import ctypes
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import time

from independent_clock_reference import capture_reference


def capture(native_file: Path, output: Path, *, wait_seconds: int = 600) -> dict:
    if output.exists() or native_file.exists():
        raise FileExistsError('Fresh native nonce/output required; preserve old evidence')
    get_tick = ctypes.WinDLL('kernel32').GetTickCount64
    get_tick.restype = ctypes.c_ulonglong
    tz_before = int(get_tick())
    zone = subprocess.check_output(['tzutil.exe', '/g'], text=True).strip()
    tz_after = int(get_tick())
    reference_before = capture_reference()
    anchors = {'shared_tick_ms': int(get_tick()), 'monotonic_ns': time.monotonic_ns()}
    frames = []
    started = time.monotonic()
    seen = set()
    print('WAITING_FOR_FRESH_NATIVE_FILE', flush=True)
    while time.monotonic() - started < wait_seconds and len(seen) < 50:
        if native_file.exists():
            try:
                content = native_file.read_text(encoding='utf-8-sig')
            except PermissionError:
                time.sleep(.02)
                continue
            # FileFlush occurs after each complete frame. Ignore partial trailing lines.
            if not content.endswith('\n'):
                content = content[:content.rfind('\n') + 1]
            rows = list(csv.DictReader(io.StringIO(content)))
            for frame in range(50):
                group = [r for r in rows if r.get('frame') == str(frame)]
                if frame in seen or len(group) != 3:
                    continue
                if {r['symbol'] for r in group} != {'US30Cash', 'EURUSD', 'USDCHF'}:
                    raise ValueError('NATIVE_FRAME_MEMBERSHIP')
                before = int(get_tick())
                utc = datetime.now(timezone.utc)
                utc_read = int(get_tick())
                local = datetime.now().astimezone()
                local_read = int(get_tick())
                after = int(get_tick())
                frame_data = {'frame': frame, 'system_utc': utc.isoformat(),
                              'system_local': local.isoformat(), 'windows_timezone': zone,
                              'windows_timezone_read_start_ms': tz_before,
                              'windows_timezone_read_end_ms': tz_after,
                              'system_read_start_ms': before, 'system_utc_read_ms': utc_read,
                              'system_local_read_ms': local_read, 'system_read_end_ms': after,
                              'native': group,
                              'pairing_delay_ms': before - max(int(r['mono_end_ms']) for r in group)}
                frames.append(frame_data)
                seen.add(frame)
        time.sleep(.02)
    reference_after = capture_reference()
    report = {'schema_version': 'clock-attestation-capture/1.0', 'frames': frames,
              'status': 'CAPTURE_COMPLETE' if len(seen) == 50 else 'INCOMPLETE',
              'reference_before': reference_before, 'reference_after': reference_after,
              'monotonic_anchor': anchors, 'orders_sent': 0, 'clock_changed': False,
              'simultaneity': 'bracketed native/sidecar observations, not atomic',
              'timezone_metadata': 'cached Windows timezone with read bracket; not a UTC attestation'}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'frames': len(frames), 'orders_sent': 0}), flush=True)
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    capture(args.native_file, args.output)
