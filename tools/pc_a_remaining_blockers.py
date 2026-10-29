"""Additional bounded evidence: three volume windows and independent clock reads."""
import csv
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
from pathlib import Path
import sys
import time
from datetime import datetime, timezone
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'python'))
import pc_a_raw_archive as raw
from volume_forensics import compare_quotes
from independent_clock_reference import capture_reference

WINDOWS = (1793217000, 1793218200, 1793219100)


def main():
    folder = ROOT / 'outputs/pc_a_remaining_blockers' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '_' + uuid.uuid4().hex[:8])
    folder.mkdir(parents=True)
    # Freeze the original snapshot used to identify the three discrepancies.
    pointer = json.loads((raw.BASE / 'active.json').read_text())
    manifest = raw.verify(raw.BASE / pointer['archive_id'])
    if manifest['native_start_msc'] > min(WINDOWS) * 1000 or manifest['next_native_msc'] < (max(WINDOWS) + 300) * 1000:
        raise RuntimeError('ORIGINAL_SNAPSHOT_DOES_NOT_COVER_WINDOWS')
    raw.atomic(folder / 'original_source_manifest.json', manifest)
    source = raw.BASE / manifest['archive_id']
    originals = {start: [] for start in WINDOWS}
    for segment in manifest['segments']:
        path = source / segment['ticks']['file']
        if raw.sha(path) != segment['ticks']['sha256']:
            raise RuntimeError('ORIGINAL_RAW_HASH_CHANGED')
        with gzip.open(path, 'rt', newline='') as stream:
            for row in csv.DictReader(stream):
                opening = int(row['time_msc']) // 300000 * 300
                if opening in originals:
                    originals[opening].append(row)
    if [len(originals[start]) for start in WINDOWS] != [696, 1131, 1223]:
        raise RuntimeError('ORIGINAL_WINDOW_MEMBERSHIP_CHANGED')
    api, server = raw.connect()
    results = []
    try:
        for iteration in range(3):
            for start in WINDOWS:
                ticks = api.copy_ticks_range(raw.SYMBOL, raw.transport(start * 1000), raw.transport((start + 300) * 1000), api.COPY_TICKS_ALL)
                bars = api.copy_rates_range(raw.SYMBOL, api.TIMEFRAME_M5, raw.transport(start * 1000), raw.transport(start * 1000))
                if ticks is None or bars is None or len(bars) != 1 or int(bars[0]['time']) != start:
                    raise RuntimeError('REFERENCE_QUERY_FAILED')
                rows = [dict((k, row[k].item()) for k in row.dtype.names) for row in ticks if start * 1000 <= int(row['time_msc']) < (start + 300) * 1000]
                if len(rows) >= raw.MAX_ROWS:
                    raise RuntimeError('QUERY_CAP')
                payload = dict(iteration=iteration, receipt_utc=raw.utc(), start_native=start, ticks=rows,
                               native_bar={k: bars[0][k].item() for k in bars.dtype.names})
                path = folder / f'window_{start}_query_{iteration}.json'
                raw.atomic(path, payload)
                report = compare_quotes(originals[start], rows, int(bars[0]['tick_volume']))
                report.update(iteration=iteration, start_native=start, raw_query_sha256=raw.sha(path),
                              native_interval='[start,start+300 seconds)', utc_interval='UNVERIFIED',
                              original_snapshot_sha256=raw.sha(folder / 'original_source_manifest.json'))
                results.append(report)
        # This measures receipt clocks again because event provenance remains
        # unresolved; it does not rerun or replace the approved native probe.
        with ThreadPoolExecutor(max_workers=1) as pool:
            reference = pool.submit(capture_reference)
            samples = []
            for _ in range(50):
                before = dict(utc_ns=time.time_ns(), monotonic_ns=time.monotonic_ns())
                tick = api.symbol_info_tick(raw.SYMBOL)
                after = dict(utc_ns=time.time_ns(), monotonic_ns=time.monotonic_ns())
                if tick is None:
                    raise RuntimeError('LIVE_QUOTE_MISSING')
                samples.append(dict(before=before, after=after, native_time=int(tick.time), native_time_msc=int(tick.time_msc), flags=int(tick.flags)))
                time.sleep(.1)
            independent = reference.result()
        raw.atomic(folder / 'additional_clock_measurement.json', dict(server=server, samples=samples, independent_reference=independent,
                   authority='DIAGNOSTIC_RECEIPT_UTC_ONLY_NOT_EVENT_MAPPING', raw_timestamps_changed=False))
        summary = dict(observed_utc=raw.utc(), server=server, volume_windows=results,
                       clock=dict(samples=len(samples), independent_quorum=independent['comparison']['status'],
                                  tls_corroborated=independent['tls_corroborated'],
                                  observed_native_minus_receipt_ms=[min((r['native_time_msc'] * 1000000-r['after']['utc_ns'])/1000000 for r in samples), max((r['native_time_msc'] * 1000000-r['before']['utc_ns'])/1000000 for r in samples)],
                                  event_mapping_authorized=False, authorized_segments=[]),
                       implementation_sha256=raw.sha(__file__), scientific_acceptance=False, orders_sent=0, live_trading=False)
        raw.atomic(folder / 'audit.json', summary)
        raw.atomic(folder / 'hashes.json', {p.name:raw.sha(p) for p in folder.glob('*.json') if p.name != 'hashes.json'})
        raw.atomic(ROOT / 'outputs/pc_a_remaining_blockers/latest.json', dict(folder=folder.name, audit_sha256=raw.sha(folder / 'audit.json')))
        print(json.dumps(summary, indent=2))
    finally:
        api.shutdown()


if __name__ == '__main__':
    main()
