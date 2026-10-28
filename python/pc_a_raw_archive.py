"""Bounded raw broker-domain archival. No UTC normalization or scientific acceptance.

The prospective archive starts AFTER the quote observed at activation. It is
not the frozen future-validation collector and cannot supply maturity counts.
UTC fields describe receipt/query times only, never native event times.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'outputs/pc_a_raw_archive'
TERMINAL = r'C:\Program Files\XM Global SC MT5 Terminal\terminal64.exe'
DATA_NAME = '20C285FE08971A9A2E814AAC44AFC9D2'
SYMBOL = 'US30Cash'
VERSION = 'pc_a_native_quarantine_v1'
CHUNK_MS = 15 * 60 * 1000
MAX_ROWS = 200000
TICK_FIELDS = ('time', 'time_msc', 'bid', 'ask', 'last', 'volume', 'volume_real', 'flags')
BAR_FIELDS = ('time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume')


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_bytes(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b'\n')
    os.replace(temporary, path)


def transport(ms):
    # API transport encoding only. This is NOT a native-to-UTC conversion.
    return datetime.fromtimestamp(ms / 1000, timezone.utc)


def connect():
    import MetaTrader5 as mt5
    if not mt5.initialize(path=TERMINAL, timeout=60000):
        raise RuntimeError('PINNED_TERMINAL_CONNECTION_FAILED')
    account, terminal = mt5.account_info(), mt5.terminal_info()
    if not account or not terminal or account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
        raise RuntimeError('CONNECTED_DEMO_REQUIRED')
    if not terminal.connected or 'XM' not in account.company:
        raise RuntimeError('CONNECTED_XM_REQUIRED')
    if Path(terminal.data_path).name != DATA_NAME:
        raise RuntimeError('UNRELATED_DATA_FOLDER_REFUSED')
    if not mt5.symbol_select(SYMBOL, True):
        raise RuntimeError('SYMBOL_UNAVAILABLE')
    return mt5, account.server


def new_manifest(kind, server, start, end=None):
    if kind not in ('prospective', 'historical'):
        raise ValueError('Unknown archive kind')
    return dict(schema_version=1, archive_id=kind + '_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '_' + uuid.uuid4().hex[:8],
                kind=kind, collector_version=VERSION, collector_sha256=sha(__file__),
                created_utc=utc(), new_start_utc=utc() if kind == 'prospective' else None,
                server=server, symbol=SYMBOL, native_start_msc=start, next_native_msc=start,
                native_end_exclusive_msc=end, next_bar_native_msc=((start + 299999) // 300000) * 300000,
                segments=[], chain_head=None,
                previous_cohort_continuity='UNVERIFIED', native_to_utc_mapping='UNVERIFIED',
                status='RAW_QUARANTINE', scientific_acceptance=False,
                completeness='UNPROVEN_BROKER_QUERY_SEMANTICS_AND_LATE_ARRIVALS',
                train_access_allowed=False, evaluation_authorized=False,
                maturity_eligible=False, low_memory_mode=True, live_trading=False,
                orders_sent=0, gaps=[], last_attempt_utc=None, last_success_utc=None)


def verify(folder):
    folder = Path(folder)
    manifest = json.loads((folder / 'manifest.json').read_text())
    if manifest['collector_sha256'] != sha(__file__):
        raise RuntimeError('COLLECTOR_CODE_CHANGED_NEW_VERSION_REQUIRED')
    if any(manifest[key] is not False for key in ('scientific_acceptance', 'train_access_allowed', 'evaluation_authorized', 'maturity_eligible', 'live_trading')):
        raise RuntimeError('SCIENTIFIC_GATE_TAMPERED')
    previous = None
    cursor = manifest['native_start_msc']
    for index, entry in enumerate(manifest['segments']):
        item = dict(entry)
        entry_hash = item.pop('entry_sha256')
        if hashlib.sha256(canonical(item)).hexdigest() != entry_hash or item['previous'] != previous:
            raise RuntimeError('HASH_CHAIN_BROKEN')
        if item['start_native_msc'] != cursor or item['end_native_msc'] <= cursor:
            raise RuntimeError('NONCONTIGUOUS_NATIVE_WINDOWS')
        for kind in ('ticks', 'bars'):
            name = item[kind]['file']
            if Path(name).name != name or sha(folder / name) != item[kind]['sha256']:
                raise RuntimeError('RAW_FILE_TAMPERED')
        previous, cursor = entry_hash, item['end_native_msc']
    if cursor != manifest['next_native_msc'] or previous != manifest['chain_head']:
        raise RuntimeError('CHECKPOINT_MISMATCH')
    return manifest


def write_csv(path, rows, fields):
    # Unique files remain unreferenced if a process dies before manifest commit.
    with gzip.open(path, 'wt', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        for row in rows:
            writer.writerow([row[field].item() if hasattr(row[field], 'item') else row[field] for field in fields])
    return dict(file=path.name, rows=len(rows), sha256=sha(path))


def append_window(folder, manifest, start, end, ticks, bars, receipt_start):
    if len(ticks) >= MAX_ROWS or len(bars) >= MAX_ROWS:
        raise RuntimeError('QUERY_TOO_LARGE_REQUIRES_SMALLER_NEW_VERSION')
    last = start
    for row in ticks:
        ms = int(row['time_msc'])
        if not start <= ms < end or ms < last or int(row['time']) != ms // 1000:
            raise RuntimeError('NATIVE_TICK_QUERY_DOMAIN_OR_ORDER_UNPROVEN')
        last = ms
    # Separate bar cursor avoids losing bars when tick windows are fractional.
    bar_start = manifest['next_bar_native_msc']
    bar_end = max(bar_start, end // 300000 * 300000)
    bars = [row for row in bars if bar_start <= int(row['time']) * 1000 and (int(row['time']) + 300) * 1000 <= bar_end]
    nonce = uuid.uuid4().hex
    entry = dict(start_native_msc=start, end_native_msc=end,
                 bar_start_native_msc=bar_start, bar_end_native_msc=bar_end,
                 receipt_start_utc=receipt_start, receipt_end_utc=utc(), previous=manifest['chain_head'])
    entry['ticks'] = write_csv(folder / (nonce + '_ticks.csv.gz'), ticks, TICK_FIELDS)
    entry['bars'] = write_csv(folder / (nonce + '_m5.csv.gz'), bars, BAR_FIELDS)
    entry['entry_sha256'] = hashlib.sha256(canonical(entry)).hexdigest()
    manifest['segments'].append(entry)
    manifest['next_native_msc'] = end
    manifest['next_bar_native_msc'] = bar_end
    manifest['chain_head'] = entry['entry_sha256']
    manifest['last_success_utc'] = utc()
    atomic(folder / 'manifest.json', manifest)


def collect(folder, mt5, server, max_windows=16):
    manifest = verify(folder)
    if server != manifest['server']:
        raise RuntimeError('BROKER_SERVER_CHANGED')
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        raise RuntimeError('NO_LIVE_NATIVE_CURSOR')
    end = manifest['native_end_exclusive_msc']
    # Exclude the latest millisecond altogether so its multiplicity stays open.
    end = min(end, int(tick.time_msc)) if end is not None else int(tick.time_msc)
    if end < manifest['next_native_msc']:
        raise RuntimeError('NATIVE_CLOCK_REGRESSION_OR_STALE_QUOTE')
    for _ in range(max_windows):
        start = manifest['next_native_msc']
        if start >= end:
            break
        stop = min(start + CHUNK_MS, end)
        receipt = utc()
        # Some MT5 bridges serialize datetime only to seconds. Query enclosing
        # seconds and partition by unchanged native milliseconds afterwards.
        query_start = start // 1000 * 1000
        query_end = (stop + 999) // 1000 * 1000
        ticks = mt5.copy_ticks_range(SYMBOL, transport(query_start), transport(query_end), mt5.COPY_TICKS_ALL)
        # Query M5 once per window; retaining full bars prevents partial-bar use.
        bars = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M5, transport(manifest['next_bar_native_msc']), transport(max(manifest['next_bar_native_msc'], stop // 300000 * 300000 - 1)))
        if ticks is None or bars is None:
            raise RuntimeError('RAW_QUERY_FAILED_NO_CURSOR_ADVANCE')
        if len(ticks) >= MAX_ROWS or any(not query_start <= int(row['time_msc']) < query_end + 1000 for row in ticks):
            raise RuntimeError('NATIVE_QUERY_ROUNDTRIP_FAILED_OR_TOO_LARGE')
        ticks = [row for row in ticks if start <= int(row['time_msc']) < stop]
        append_window(folder, manifest, start, stop, ticks, bars, receipt)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('activate', 'collect', 'verify', 'historical'))
    args = parser.parse_args()
    BASE.mkdir(parents=True, exist_ok=True)
    # OS lock is released after crashes; never delete another process's lock.
    import msvcrt
    with (BASE / 'archive.lock').open('a+b') as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b'0'); lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        pointer = BASE / 'active.json'
        if args.action == 'verify':
            state = json.loads(pointer.read_text())
            result = verify(BASE / state['archive_id'])
        else:
            mt5, server = connect()
            try:
                if args.action == 'activate':
                    if pointer.exists():
                        raise RuntimeError('ALREADY_ACTIVATED_USE_COLLECT')
                    tick = mt5.symbol_info_tick(SYMBOL)
                    if tick is None:
                        raise RuntimeError('ACTIVATION_QUOTE_MISSING')
                    result = new_manifest('prospective', server, int(tick.time_msc) + 1)
                    # Receipt timestamp explicitly cannot prove event-time UTC.
                    result['activation_quote_native_msc'] = int(tick.time_msc)
                    folder = BASE / result['archive_id']
                    atomic(folder / 'manifest.json', result)
                    atomic(pointer, dict(archive_id=result['archive_id']))
                elif args.action == 'historical':
                    # Fixed documented TRAIN diagnostic scope, no split reconstruction.
                    # Not a replacement for missing frozen membership or UTC mapping.
                    start = int(datetime(2024, 1, 2, tzinfo=timezone.utc).timestamp() * 1000)
                    end = start + 86400000
                    hp = BASE / 'historical_active.json'
                    if hp.exists():
                        folder = BASE / json.loads(hp.read_text())['archive_id']
                    else:
                        result = new_manifest('historical', server, start, end)
                        result['scope'] = '2024-01-02_NATIVE_TRAIN_DIAGNOSTIC_ONLY'
                        result['independent_from_old_train'] = False
                        folder = BASE / result['archive_id']
                        atomic(folder / 'manifest.json', result)
                        atomic(hp, dict(archive_id=result['archive_id']))
                    result = collect(folder, mt5, server, max_windows=96)
                else:
                    folder = BASE / json.loads(pointer.read_text())['archive_id']
                    result = collect(folder, mt5, server)
            finally:
                mt5.shutdown()
        print(json.dumps({k: result[k] for k in ('archive_id', 'status', 'next_native_msc', 'chain_head', 'last_success_utc')}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
