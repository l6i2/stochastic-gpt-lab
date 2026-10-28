"""Read-only bounded M5/parity/time investigation. Never opens scientific gates."""
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'python'))
import pc_a_raw_archive as raw
from native_m5_rebuild import rebuild, compare
from native_metadata_v3 import main_k
from main_k_native_parity import fixtures


def stream_ticks(folder, manifest):
    for segment in manifest['segments']:
        with gzip.open(folder / segment['ticks']['file'], 'rt', newline='') as stream:
            yield from csv.DictReader(stream)


def native_bars(folder, manifest):
    result = []
    for segment in manifest['segments']:
        with gzip.open(folder / segment['bars']['file'], 'rt', newline='') as stream:
            result.extend(csv.DictReader(stream))
    return result


def metadata_audit():
    folder = ROOT / 'configs/main_k_native_evidence_20261023'
    audit = json.loads((folder / 'validated_audit.json').read_text())
    if raw.sha(folder / 'validated_audit.json') != (folder / 'validated_audit.sha256').read_text().strip():
        raise RuntimeError('NATIVE_AUDIT_SEAL_CHANGED')
    for name, digest in audit['artifacts_sha256'].items():
        if raw.sha(folder / name) != digest:
            raise RuntimeError('NATIVE_EVIDENCE_CHANGED')
    families = fixtures()
    values = {name: list(main_k(rows)) for name, rows in families.items()}
    ready = warm = 0
    max_error = 0.
    with (folder / 'pk_41a2e93f_native.csv').open(newline='') as stream:
        seen = set()
        for row in csv.DictReader(stream):
            name, index = row['fixture'], int(row['bar_index'])
            key = (name, index)
            if key in seen or int(row['bar_time']) != int(families[name][index]['bar_time']):
                raise RuntimeError('NATIVE_FIXTURE_MEMBERSHIP_INVALID')
            seen.add(key)
            value = values[name][index]
            if value is None:
                if row['readiness'] != 'WARMUP':
                    raise RuntimeError('NATIVE_WARMUP_DISAGREES')
                warm += 1
            else:
                error = abs(value - float(row['native_main']))
                if error > 1e-10 or row['readiness'] == 'WARMUP':
                    raise RuntimeError('METADATA_NATIVE_PARITY_FAILED')
                max_error = max(max_error, error)
                ready += 1
        wanted = {(name, i) for name, rows in families.items() for i in range(len(rows) - 1)}
        if seen != wanted:
            raise RuntimeError('NATIVE_FIXTURE_ROWS_MISSING')
    return dict(status='PASS_NATIVE_MAIN_K_V3', ready_rows=ready, warmup_rows=warm,
                families=sorted(families), max_absolute_error=max_error, absolute_tolerance=1e-10,
                legacy_metadata_status='FAIL_UNCHANGED', activation='BLOCKED_CLOCK_MAPPING_CALENDAR',
                audit_sha256=raw.sha(folder / 'validated_audit.json'), adapter_sha256=raw.sha(ROOT / 'python/native_metadata_v3.py'),
                scientific_acceptance=False, maturity_counts_derived=False)


def clock_investigation():
    pointer = json.loads((ROOT / 'outputs/pc_a/active_clock_capture.json').read_text())
    folder = Path(pointer['folder'])
    seals = json.loads((folder / 'hashes.json').read_text())
    if raw.sha(folder / 'capture.json') != seals['capture_sha256']:
        raise RuntimeError('CLOCK_CAPTURE_CHANGED')
    capture = json.loads((folder / 'capture.json').read_text())
    offsets, raw_future, candidate_future = set(), 0, 0
    for frame in capture['paired_frames']:
        after_ns = frame['windows_after']['precise_utc_ns']
        for row in frame['native']:
            offsets.add(int(row['time_trade_server']) - int(row['time_gmt']))
            raw_future += int(int(row['tick_time_msc']) * 1000000 > after_ns)
            # Candidate tested as a hypothesis only. It is never installed or
            # substituted for original timestamps in any archive or mapping.
            candidate_future += int((int(row['tick_time_msc']) - 7200000) * 1000000 > after_ns)
    return dict(native_to_utc_mapping='FAIL_INDEPENDENT_EVENT_TIME_PROVENANCE_UNRESOLVED',
                frames=len(capture['paired_frames']), observed_server_minus_gmt_seconds=sorted(offsets),
                raw_quotes_after_receipt_upper_bound=raw_future,
                candidate_7200_quotes_after_receipt_upper_bound=candidate_future,
                candidate_scope='DIAGNOSTIC_ONLY_NOT_AUTHORIZED_MAPPING', authorized_segments=[],
                raw_timestamps_changed=False, future_tolerance_ms=0,
                reason='Consistent observed wall-clock offset does not certify event UTC provenance, stale/replayed quotes, or historical DST transitions',
                capture_sha256=seals['capture_sha256'])


def main():
    destination = ROOT / 'outputs/pc_a_data_repair' / ('repair_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '_' + uuid.uuid4().hex[:8])
    destination.mkdir(parents=True)
    api, server = raw.connect()
    try:
        info = api.symbol_info(raw.SYMBOL)
        if info.chart_mode != 0:
            raise RuntimeError('NATIVE_CHART_IS_NOT_BID')
        grid = info.trade_tick_size
        summary = dict(observed_utc=raw.utc(), server=server, chart_mode='BID', tick_size=grid,
                       maxbars=api.terminal_info().maxbars, archives={},
                       producer_sha256={str(path.relative_to(ROOT)): raw.sha(path) for path in (
                           Path(__file__).resolve(), ROOT / 'python/native_m5_rebuild.py',
                           ROOT / 'python/native_metadata_v3.py', ROOT / 'python/pc_a_raw_archive.py')})
        for kind, pointer_name in (('historical', 'historical_active.json'), ('prospective', 'active.json')):
            pointer = json.loads((raw.BASE / pointer_name).read_text())
            folder = raw.BASE / pointer['archive_id']
            manifest = raw.verify(folder)
            if manifest['server'] != server:
                raise RuntimeError('BROKER_IDENTITY_CHANGED')
            # Snapshots bind exactly the immutable segments read, not later appends.
            raw.atomic(destination / (kind + '_source_manifest.json'), manifest)
            start, end = manifest['native_start_msc'], manifest['next_native_msc']
            derived = rebuild(stream_ticks(folder, manifest), start_msc=start, end_msc=end, tick_size=grid)
            raw.atomic(destination / (kind + '_derived_native_m5.json'), derived)
            request_start = (start + 299999) // 300000 * 300000
            request_end = end // 300000 * 300000
            native = api.copy_rates_range(raw.SYMBOL, api.TIMEFRAME_M5, raw.transport(request_start), raw.transport(request_end - 1))
            error = api.last_error()
            returned = [] if native is None else [dict((key, row[key].item()) for key in row.dtype.names) for row in native]
            outside = [int(row['time']) for row in returned if not request_start <= int(row['time']) * 1000 < request_end]
            valid = [row for row in returned if request_start <= int(row['time']) * 1000 < request_end]
            raw.atomic(destination / (kind + '_native_m5_query.json'), dict(native_query_start_msc=request_start,
                       native_query_end_exclusive_msc=request_end, raw_rows=returned, outside_requested_range=outside, api_error=error))
            result = compare(derived['bars'], valid, grid)
            # Save the diagnostic even if historical MT5 output is clamped.
            result.update(archive_id=manifest['archive_id'], derived_bars=len(derived['bars']), native_bars_in_range=len(valid),
                          native_bars_outside_range=len(outside), ticks_read=derived['ticks_read'],
                          source_chain_head=manifest['chain_head'], scientific_acceptance=False)
            summary['archives'][kind] = result
        summary['metadata'] = metadata_audit()
        summary['clock_mapping'] = clock_investigation()
        summary.update(causal_audit='FAIL_MAPPING_AND_CALENDAR_UNVERIFIED', training_readiness='BLOCKED_BY_RESEARCH_GOVERNANCE',
                       discovery_validation='BLOCKED', final_test='LOCKED', demo='DISABLED', live_trading=False, orders_sent=0)
        raw.atomic(destination / 'repair_audit.json', summary)
        raw.atomic(destination / 'hashes.json', {p.name: raw.sha(p) for p in destination.glob('*.json') if p.name != 'hashes.json'})
        raw.atomic(ROOT / 'outputs/pc_a_data_repair/latest.json', dict(folder=destination.name, audit_sha256=raw.sha(destination / 'repair_audit.json')))
        print(json.dumps(summary, indent=2))
    finally:
        api.shutdown()


if __name__ == '__main__':
    main()
