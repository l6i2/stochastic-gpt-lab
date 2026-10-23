"""Observe precise Windows clocks continuously around the existing native probe.

No orders, terminal restart, time adjustment or broker timestamp correction.
The pending watcher has no expiry; it exits after one complete native capture.
"""
from __future__ import annotations
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import csv
import ctypes
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import time
try:
    import winreg
except ImportError:
    winreg = None

from independent_clock_reference import capture_reference

FILETIME_UNIX_OFFSET = 116444736000000000


class SystemTime(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ushort) for name in
                ('year', 'month', 'weekday', 'day', 'hour', 'minute', 'second', 'millisecond')]


class WindowsClocks:
    def __init__(self):
        if winreg is None:
            raise OSError('WINDOWS_CLOCK_API_REQUIRED')
        self.kernel = ctypes.WinDLL('kernel32')
        self.kernel.GetTickCount64.restype = ctypes.c_ulonglong
        self.kernel.GetSystemTimePreciseAsFileTime.argtypes = [ctypes.POINTER(ctypes.c_ulonglong)]
        self.kernel.GetSystemTimeAsFileTime.argtypes = [ctypes.POINTER(ctypes.c_ulonglong)]

    def read(self) -> dict:
        k = self.kernel
        start = int(k.GetTickCount64())
        qpc_start = time.perf_counter_ns()
        precise, standard = ctypes.c_ulonglong(), ctypes.c_ulonglong()
        k.GetSystemTimePreciseAsFileTime(ctypes.byref(precise))
        precise_read = int(k.GetTickCount64())
        k.GetSystemTimeAsFileTime(ctypes.byref(standard))
        standard_read = int(k.GetTickCount64())
        local = SystemTime()
        k.GetLocalTime(ctypes.byref(local))
        local_read = int(k.GetTickCount64())
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                r'SYSTEM\CurrentControlSet\Control\TimeZoneInformation') as key:
            zone = winreg.QueryValueEx(key, 'TimeZoneKeyName')[0]
        zone_read = int(k.GetTickCount64())
        return {'start_tick_ms': start, 'qpc_start_ns': qpc_start,
                'precise_utc_ns': (precise.value - FILETIME_UNIX_OFFSET) * 100,
                'precise_read_tick_ms': precise_read,
                'standard_utc_ns': (standard.value - FILETIME_UNIX_OFFSET) * 100,
                'standard_read_tick_ms': standard_read,
                'local_time_fields': {name: getattr(local, name) for name, _ in local._fields_},
                'local_read_tick_ms': local_read, 'windows_timezone': zone,
                'timezone_read_tick_ms': zone_read, 'python_time_ns': time.time_ns(),
                'python_local': datetime.now().astimezone().isoformat(),
                'qpc_end_ns': time.perf_counter_ns(), 'end_tick_ms': int(k.GetTickCount64())}


def native_frames(content: str) -> list[list[dict]]:
    if not content.endswith('\n'):
        content = content[:content.rfind('\n') + 1]
    rows = list(csv.DictReader(io.StringIO(content)))
    result = []
    for frame in range(50):
        group = [row for row in rows if row.get('frame') == str(frame)]
        if len(group) == 3 and {r['symbol'] for r in group} == {'US30Cash', 'EURUSD', 'USDCHF'}:
            result.append(group)
    return result


def bracket(group: list[dict], windows: list[dict]) -> dict | None:
    start = min(int(r['mono_start_ms']) for r in group)
    end = max(int(r['mono_end_ms']) for r in group)
    before = [row for row in windows if row['end_tick_ms'] <= start]
    after = [row for row in windows if row['start_tick_ms'] >= end]
    if not before or not after:
        return None
    return {'frame': int(group[0]['frame']), 'native': group,
            'windows_before': before[-1], 'windows_after': after[0],
            'native_start_ms': start, 'native_end_ms': end,
            'bracket_width_ms': after[0]['end_tick_ms'] - before[-1]['start_tick_ms']}


def w32_snapshot() -> dict:
    result = {}
    for name, args in (('source', ['/query', '/source']), ('status', ['/query', '/status']),
                       ('offset', ['/stripchart', '/computer:time.windows.com', '/dataonly', '/samples:3'])):
        start = time.perf_counter_ns()
        try:
            run = subprocess.run(['w32tm.exe', *args], capture_output=True, timeout=15,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
            result[name] = {'returncode': run.returncode,
                            'stdout': run.stdout.decode('utf-8', errors='replace'),
                            'stderr': run.stderr.decode('utf-8', errors='replace')}
        except (OSError, subprocess.TimeoutExpired) as exc:
            result[name] = {'error': type(exc).__name__}
        result[name].update(qpc_start_ns=start, qpc_end_ns=time.perf_counter_ns())
    return result


def reference_snapshot() -> dict:
    start = time.perf_counter_ns()
    return {'qpc_start_ns': start, 'reference': capture_reference(), 'qpc_end_ns': time.perf_counter_ns()}


def atomic_json(path: Path, value: dict):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    temp.replace(path)


def watch(native: Path, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'capture.json').exists() or native.exists():
        raise FileExistsError('Existing evidence must be archived and hashed before arming')
    clocks = WindowsClocks()
    ring = deque(maxlen=15000)
    paired, seen, references = [], set(), []
    start = clocks.read()
    ring.append(start)
    with ThreadPoolExecutor(max_workers=2) as pool:
        reference_job = pool.submit(reference_snapshot)
        w32_job = pool.submit(w32_snapshot)
        next_reference_frame = 10
        atomic_json(output / 'ready.json', {'state': 'ARMED_NO_EXPIRY', 'start': start,
                    'native_filename': native.name, 'orders_sent': 0, 'clock_changed': False})
        print('ARMED_NO_EXPIRY', flush=True)
        while len(seen) < 50:
            ring.append(clocks.read())
            if reference_job is not None and reference_job.done():
                references.append(reference_job.result())
                reference_job = None
            if native.exists():
                try:
                    groups = native_frames(native.read_text(encoding='utf-8-sig'))
                except PermissionError:
                    groups = []
                for group in groups:
                    frame = int(group[0]['frame'])
                    if frame in seen:
                        continue
                    pair = bracket(group, list(ring))
                    if pair:
                        paired.append(pair)
                        seen.add(frame)
                if reference_job is None and len(seen) >= next_reference_frame:
                    reference_job = pool.submit(reference_snapshot)
                    next_reference_frame += 10
            time.sleep(.02)
        if reference_job is not None:
            references.append(reference_job.result())
        references.append(reference_snapshot())
        report = {'status': 'CAPTURE_COMPLETE', 'paired_frames': paired, 'references': references,
                  'w32_before': w32_job.result(), 'w32_after': w32_snapshot(),
                  'start': start, 'end': clocks.read(), 'clock_changed': False, 'orders_sent': 0,
                  'quote_tolerance_added': False,
                  'simultaneity': 'continuous Windows capture brackets native readings; no atomicity claim'}
        atomic_json(output / 'capture.json', report)
        atomic_json(output / 'ready.json', {'state': 'CAPTURE_COMPLETE', 'frames': len(paired),
                    'orders_sent': 0})
        print('CAPTURE_COMPLETE frames=50 orders_sent=0', flush=True)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    watch(args.native, args.output)
