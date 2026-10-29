"""Offline versioned audit of volume coverage, clock scope and calendar scope."""
import csv
from datetime import datetime, timedelta, timezone
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'python'))
import pc_a_raw_archive as raw
from volume_forensics import compare_quotes
from native_m5_rebuild import rebuild, compare
from native_time_mapping import _frozen_zone


def transitions(year, zone):
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    before = start.astimezone(zone).utcoffset()
    result = []
    while start < end:
        current = start.astimezone(zone).utcoffset()
        if current != before:
            result.append(dict(utc=start.isoformat(), offset_before_seconds=int(before.total_seconds()), offset_after_seconds=int(current.total_seconds())))
        before = current
        start += timedelta(hours=1)
    return result


def main():
    base = ROOT / 'outputs/pc_a_remaining_blockers'
    pointer = json.loads((base / 'latest.json').read_text())
    folder = base / pointer['folder']
    seals = json.loads((folder / 'hashes.json').read_text())
    for name, digest in seals.items():
        if Path(name).name != name or raw.sha(folder / name) != digest:
            raise RuntimeError('MEASUREMENT_HASH_CHANGED')
    manifest = json.loads((folder / 'original_source_manifest.json').read_text())
    windows = (1793217000, 1793218200, 1793219100, 1793220300)
    original = {start: [] for start in windows}
    for segment in manifest['segments']:
        path = raw.BASE / manifest['archive_id'] / segment['ticks']['file']
        if raw.sha(path) != segment['ticks']['sha256']:
            raise RuntimeError('ARCHIVE_SEGMENT_CHANGED')
        with gzip.open(path, 'rt', newline='') as stream:
            for row in csv.DictReader(stream):
                opening = int(row['time_msc']) // 300000 * 300
                if opening in original:
                    original[opening].append(row)
    result = []
    for iteration in range(3):
        for start in windows[:3]:
            query = json.loads((folder / f'window_{start}_query_{iteration}.json').read_text())
            item = compare_quotes(original[start], query['ticks'], query['native_bar']['tick_volume'])
            rebuilt = rebuild(original[start], start_msc=start*1000, end_msc=(start+300)*1000, tick_size='.01')
            contrast = compare(rebuilt['bars'], [query['native_bar']], '.01')
            item.update(iteration=iteration, native_bar_time=start,
                        ohlc_affected=any(field != 'tick_volume' for difference in contrast['differences'] for field in difference['fields']),
                        interval_scope='THIS_NATIVE_FIVE_MINUTE_BUCKET_ONLY_UTC_UNVERIFIED')
            result.append(item)
    supplement_pointer = json.loads((base / 'supplement_latest.json').read_text())
    supplement = base / supplement_pointer['folder']
    for name, digest in json.loads((supplement / 'hashes.json').read_text()).items():
        if Path(name).name != name or raw.sha(supplement / name) != digest:
            raise RuntimeError('SUPPLEMENT_HASH_CHANGED')
    for iteration in range(3):
        query = json.loads((supplement / f'query_{iteration}.json').read_text())
        item = compare_quotes(original[windows[3]], query['ticks'], query['native_tick_volume'])
        item.update(iteration=iteration, native_bar_time=windows[3],
                    interval_scope='ADDITIONAL_NATIVE_BUCKET_UTC_UNVERIFIED', ohlc_evidence='SEPARATE_NATIVE_M5_RECHECK')
        result.append(item)
    clock = json.loads((folder / 'additional_clock_measurement.json').read_text())
    reference = clock['independent_reference']
    approved_pointer = json.loads((ROOT / 'outputs/pc_a/active_clock_capture.json').read_text())
    approved_folder = Path(approved_pointer['folder'])
    approved_seals = json.loads((approved_folder / 'hashes.json').read_text())
    if raw.sha(approved_folder / 'native.csv') != approved_seals['native_csv_sha256']:
        raise RuntimeError('APPROVED_NATIVE_CLOCK_EVIDENCE_CHANGED')
    with (approved_folder / 'native.csv').open(newline='') as stream:
        approved_rows = list(csv.DictReader(stream))
    summary = dict(observed_utc=raw.utc(), M5_DATA_INTEGRITY='PASS_HISTORICAL_276_NATIVE_CONTRAST_RAW_STAGING_PARTIAL',
        VOLUME_DISCREPANCIES='THREE_REQUESTED_PLUS_ONE_ADDITIONAL_UNDERCOVERAGE_WINDOWS_ONE_REFERENCE_INCONSISTENCY',
        CLOCK_ATTESTATION='PASS_RETAINED_SEALED_INTERVAL_ONLY', NATIVE_TO_UTC_MAPPING='FAIL_EVENT_PROVENANCE_NOT_DEMONSTRATED',
        BROKER_CALENDAR='PARTIAL_NATIVE_WEEKLY_OBSERVATION_UTC_DST_AND_EXCEPTIONS_UNVERIFIED',
        MAIN_K_PARITY='PASS_RETAINED_NATIVE_EVIDENCE', METADATA_V3_PARITY='PASS_NATIVE_ADAPTER_NOT_ACTIVE',
        CAUSAL_AUDIT='FAIL_TIME_PROVENANCE_CALENDAR_AND_STAGING_COMPLETENESS',
        COLLECTOR_HEALTH='READ_ONLY_CAPTURE_ACTIVE_HASH_CHAIN_VERIFIED_NO_RETROACTIVE_REPAIR',
        PROSPECTIVE_COHORT_READINESS='BLOCKED_NEW_COHORT_PLAN_NOT_ACTIVE_NO_STAGING_ADOPTION',
        TRAINING_READINESS='BLOCKED_BY_RESEARCH_GOVERNANCE', PUSH_STATUS='PENDING_PUBLICATION',
        HARD_BLOCKER=['Independent broker-event UTC provenance and bounded mapping intervals',
                      'Exact-server authoritative historical session and holiday exceptions',
                      'Raw staging undercoverage cannot be repaired as original prospective receipt evidence'],
        NEXT_STATE='CONTINUE_NATIVE_QUARANTINE_CAPTURE_AWAIT_INDEPENDENT_TIME_AND_CALENDAR_EVIDENCE',
        volume=result, measurement_folder=folder.name, measurement_hashes_sha256=raw.sha(folder / 'hashes.json'),
        supplementary_measurement_folder=supplement.name, supplementary_hashes_sha256=raw.sha(supplement / 'hashes.json'),
        current_clock_diagnostic=dict(quorum=reference['comparison']['status'], tls_corroborated=reference['tls_corroborated'],
                    local_inside_quorum_interval=reference['comparison'].get('local_clock_within_network_interval'),
                    local_lag_lower_ns=reference['comparison'].get('local_lag_lower_ns'),
                    local_lag_upper_ns=reference['comparison'].get('local_lag_upper_ns'),
                    authority='DIAGNOSTIC_ONLY_NO_CURRENT_ATTESTATION_OR_EVENT_MAPPING'),
        calendar=dict(active_server='XMGlobalSC-MT5 5', legacy_policy_server='XMGlobal-MT5 10',
                      legacy_policy_reusable=False, native_session_clock_basis='OBSERVED_NATIVE_LABELS',
                      historical_exceptions='UNKNOWN', approved_utc_sessions=[],
                      iana_diagnostic_only={str(year):{key:transitions(year, _frozen_zone(key)) for key in ('Europe/Nicosia','America/New_York')} for year in (2024,2026)},
                      broker_dst_rule_certified=False, tzdata='2026.5',
                      public_source='https://www.xm.com/equity-indices', public_source_scope='Directs account login for exact hours; no usable historical server calendar'),
        native_mapping_evidence=dict(approved_probe_frames=50, approved_probe_rows=150,
                    observed_server_gmt_relationship_seconds=sorted({int(row['time_trade_server'])-int(row['time_gmt']) for row in approved_rows}),
                    observed_gmt_minus_local_seconds=sorted({int(row['time_gmt'])-int(row['time_local']) for row in approved_rows}),
                    approved_native_units_consistent=all(int(row['tick_time_msc'])//1000==int(row['tick_time']) for row in approved_rows),
                    additional_native_units_consistent=all(row['native_time_msc']//1000==row['native_time'] for row in clock['samples']),
                    approved_native_csv_sha256=approved_seals['native_csv_sha256'], event_utc_identity_proven=False,
                    historical_dst_offsets_proven=False, authorized_mapping_segments=[], fixed_offset_installed=False,
                    additional_receipt_samples=len(clock['samples']), raw_timestamps_changed=False, future_tolerance_ms=0),
        scientific_acceptance=False, DISCOVERY_VALIDATION='BLOCKED', FINAL_TEST='LOCKED', DEMO='DISABLED', LIVE_TRADING=False, ORDERS_SENT=0)
    target = ROOT / 'outputs/pc_a_remaining_blockers/final_scope_audit.json'
    raw.atomic(target, summary)
    print(json.dumps({key:value for key,value in summary.items() if key.isupper()}, indent=2))


if __name__ == '__main__': main()
