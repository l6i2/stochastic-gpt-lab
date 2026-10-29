"""Offline exact-server time evidence partition. Never authorizes an offset."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'python'))
import pc_a_raw_archive as raw
from local_finalize import verify_source_manifest
from time_semantics import instant_display
from native_time_mapping import load_mapping

SERVER = 'XMGlobalSC-MT5 5'


def correlation_audit(measurement):
    if measurement['server'] != SERVER or measurement['symbol'] != 'US30Cash':
        raise ValueError('EXACT_SERVER_SYMBOL_REQUIRED')
    reference = measurement['reference']
    differences, durations, payloads = [], [], set()
    zero_durations = 0
    comparison = reference['comparison']
    for sample in measurement['samples']:
        payload = sample['tick']
        digest = hashlib.sha256(raw.canonical(payload)).hexdigest()
        if digest != sample['payload_sha256']:
            raise ValueError('NATIVE_PAYLOAD_HASH_MISMATCH')
        if payload['time_msc'] // 1000 != payload['time']:
            raise ValueError('NATIVE_UNITS_INVALID')
        before, after = sample['before'], sample['after']
        duration = after['monotonic_ns'] - before['monotonic_ns']
        if duration < 0:
            raise ValueError('MONOTONIC_REGRESSION')
        durations.append(duration)
        zero_durations += duration == 0
        payloads.add(digest)
        if comparison.get('status') == 'REFERENCE_QUORUM':
            delta = after['monotonic_ns'] - reference['anchor_monotonic_ns']
            lower, upper = comparison['utc_lower_ns'] + delta, comparison['utc_upper_ns'] + delta
            if lower > upper:
                raise ValueError('INVALID_REFERENCE_INTERVAL')
            differences.append([payload['time_msc'] * 1000000 - upper,
                                payload['time_msc'] * 1000000 - lower])
    return dict(samples=len(durations), distinct_payloads=len(payloads),
        observed_api_duration_ns=dict(min=min(durations), max=max(durations)),
        indistinguishable_monotonic_readings=zero_durations,
        zero_duration_interpretation='COUNTER_CANNOT_RESOLVE_CALL_NOT_ZERO_LATENCY',
        native_minus_external_receipt_ns_envelope=[min(x[0] for x in differences),max(x[1] for x in differences)] if differences else None,
        native_after_external_receipt_if_direct_utc=sum(x[0] > 0 for x in differences),
        diagnostic_only=True, independently_identified_same_event=False,
        event_latency='UNVERIFIED', offsets_authorized=[], certified_intervals=[],
        limitations=['NTP unauthenticated; TLS Date corroboration is not an event record',
                    'Projection has no calibrated oscillator drift bound',
                    'Latest-quote polling is not a broker arrival callback',
                    'Payload differences do not guarantee global event uniqueness'])


def quarantine_partition(manifest):
    if manifest['server'] != SERVER or manifest['symbol'] != 'US30Cash':
        raise ValueError('EXACT_SERVER_SYMBOL_REQUIRED')
    return dict(archive_id=manifest['archive_id'], kind=manifest['kind'],
        status='QUARANTINED', native_start_msc=manifest['native_start_msc'],
        native_end_exclusive_msc=manifest['next_native_msc'], interval_basis='ORIGINAL_NATIVE_QUERY_DOMAIN_NOT_UTC',
        segments=len(manifest['segments']), ticks=sum(s['ticks']['rows'] for s in manifest['segments']),
        stored_m5_bars=sum(s['bars']['rows'] for s in manifest['segments']),
        chain_head=manifest['chain_head'], canonical_manifest_sha256=hashlib.sha256(raw.canonical(manifest)).hexdigest(),
        reason='NO_INDEPENDENT_EVENT_UTC_BINDING_NO_AUTHORIZED_BOUNDED_MAPPING',
        scientific_acceptance=False, original_modified=False)


def main():
    verify_source_manifest(ROOT / 'configs/pc_a_source_hashes_20261029_v11.json')
    folder=ROOT/'outputs/pc_a_temporal_intake/xm_interval_audits'/uuid.uuid4().hex
    folder.mkdir(parents=True)
    pointer=json.loads((ROOT/'outputs/pc_a_certification/latest.json').read_text())
    source=ROOT/'outputs/pc_a_certification'/pointer['folder']
    if raw.sha(source/'audit.json') != pointer['audit_sha256']:
        raise ValueError('CORRELATION_AUDIT_HASH_MISMATCH')
    seals=json.loads((source/'hashes.json').read_text())
    for name,digest in seals.items():
        if Path(name).name != name or raw.sha(source/name) != digest:
            raise ValueError('CORRELATION_SOURCE_HASH_MISMATCH')
    correlation=correlation_audit(json.loads((source/'correlation.json').read_text()))
    correlation['source_sha256']=raw.sha(source/'correlation.json')
    retained=[]
    base=ROOT/'outputs/pc_a_remaining_blockers'
    for pointer_name in ('latest.json','supplement_latest.json'):
        earlier=base/json.loads((base/pointer_name).read_text())['folder']
        earlier_seals=json.loads((earlier/'hashes.json').read_text())
        for name,digest in earlier_seals.items():
            if Path(name).name != name or raw.sha(earlier/name) != digest:
                raise ValueError('RETAINED_MEASUREMENT_HASH_MISMATCH')
        retained.append(dict(pointer=pointer_name,files_verified=len(earlier_seals),
                             seals_sha256=raw.sha(earlier/'hashes.json'),authority='RETAINED_DIAGNOSTIC_NOT_EVENT_PROOF'))
    approved=Path(json.loads((ROOT/'outputs/pc_a/active_clock_capture.json').read_text())['folder'])
    approved_seals=json.loads((approved/'hashes.json').read_text())
    if raw.sha(approved/'native.csv') != approved_seals['native_csv_sha256']:
        raise ValueError('APPROVED_NATIVE_PROBE_HASH_MISMATCH')
    retained.append(dict(native_probe_sha256=raw.sha(approved/'native.csv'),
                         authority='CLOCK_ATTESTATION_SEALED_INTERVAL_ONLY_NOT_EVENT_MAPPING'))
    partitions=[]
    for name in ('historical_active.json','active.json'):
        archive_id=json.loads((raw.BASE/name).read_text())['archive_id']
        if Path(archive_id).name != archive_id: raise ValueError('INVALID_ARCHIVE_POINTER')
        manifest=raw.verify(raw.BASE/archive_id)
        raw.atomic(folder/(manifest['kind']+'_manifest.snapshot.json'),manifest)
        item=quarantine_partition(manifest)
        item['snapshot_file_sha256']=raw.sha(folder/(manifest['kind']+'_manifest.snapshot.json'))
        partitions.append(item)
    sessions_path=ROOT/'configs/pc_a_remaining_blockers_evidence_20261028/current_server_native_sessions.json'
    sessions=json.loads(sessions_path.read_text())['canonical_observation']
    if sessions['server'] != SERVER or sessions['symbol'] != 'US30Cash': raise ValueError('SESSION_IDENTITY_MISMATCH')
    now=datetime.now(timezone.utc)
    try:
        candidate=load_mapping(ROOT/'configs/native_time_mapping_v1.prepared.json')
    except ValueError as exc:
        normalization_reason=str(exc)
    else:
        # A changed authorizing mapping requires explicit evidence review rather
        # than silently reclassifying archived data with this diagnostic tool.
        raise RuntimeError('MAPPING_STATE_CHANGED_REVIEW_REQUIRED')
    report=dict(observed=instant_display(now,basis='HOST_RECEIPT_UNATTESTED'),
        XM_UTC_EVENT_PROVENANCE='PARTIAL_RECEIPT_CORRELATION_NOT_SAME_EVENT_UTC_PROOF',
        XM_NATIVE_TIMESTAMP_SEMANTICS='DOCUMENTED_UNITS_AND_FIELDS_EXACT_SERVER_UTC_UNVERIFIED',
        XM_HISTORICAL_MAPPING='UNVERIFIED_NO_AUTHORIZED_INTERVALS',
        US30CASH_SESSION_CALENDAR='PARTIAL_NATIVE_WEEKLY_OBSERVATIONS_EXCEPTIONS_UNVERIFIED',
        CERTIFIED_INTERVALS=[],QUARANTINED_INTERVALS=partitions,
        correlation=correlation, retained_evidence=retained,
        sessions=dict(source_sha256=raw.sha(sessions_path),native_records=sessions['records'],
            clock_line_scope='HOST_DEPENDENT_NOT_INDEPENDENT_UTC',dated_exceptions=[],
            dated_exception_coverage='UNKNOWN_NOT_AN_EMPTY_HOLIDAY_CALENDAR',new_probe_run=False),
        CAUSAL_AUDIT=dict(status='FAIL',prerequisite='EXACT_SERVER_EVENT_NORMALIZATION_UNVERIFIED',guard_reason=normalization_reason,
            admitted_normalized_rows=0,feature_max_time_le_decision_time='NOT_EVALUABLE',quote_time_le_decision_time='NOT_EVALUABLE'),
        TRAINING_READINESS='BLOCKED_BY_RESEARCH_GOVERNANCE',
        HARD_BLOCKER=['Independent exact-server same-event UTC binding','Historical bounded mapping evidence','Dated exact-server sessions and exceptions'],
        MANUAL_ACTION_REQUIRED='NONE_FOR_CAPTURE_EXTERNAL_BROKER_EVIDENCE_REQUIRED_FOR_CERTIFICATION',
        NEXT_STATE='KEEP_QUARANTINE_COLLECTOR_ACTIVE_ACCEPT_EVIDENCE_WITHOUT_AUTOMATIC_AUTHORIZATION',
        clock_counter_metadata_now=dict(resolution=time.get_clock_info('monotonic').resolution,
            implementation=time.get_clock_info('monotonic').implementation,scope='CURRENT_RUNTIME_NOT_RETROACTIVE_CALIBRATION'),
        DISCOVERY_VALIDATION='BLOCKED',FINAL_TEST='LOCKED',DEMO='DISABLED',LIVE_TRADING=False,orders_sent=0,
        mapping_installed=False, probes_repeated=False)
    raw.atomic(folder/'audit.json',report)
    raw.atomic(folder/'hashes.json',{p.name:raw.sha(p) for p in folder.iterdir() if p.is_file()})
    raw.atomic(ROOT/'outputs/pc_a_temporal_intake/xm_interval_audits/latest.json',dict(folder=folder.name,audit_sha256=raw.sha(folder/'audit.json')))
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
