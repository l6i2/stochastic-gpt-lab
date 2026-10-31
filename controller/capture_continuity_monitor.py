"""Passive, incremental continuity audit of the new capture only.

No broker queries, power changes, backfill, scoring or admission. Incident facts
are immutable; cursor/summary are derived checkpoints, separate from raw journals.
"""
import json
import os
from pathlib import Path

from .isolated_observation import atomic,host_clock,native_line,GENESIS
from .pretrain_contracts import canonical,seal


def record_incident(root,fact,clock):
    identity=seal(fact);path=root/'continuity_incidents'/(identity+'.json')
    path.parent.mkdir(exist_ok=True)
    if path.exists():
        row=json.loads(path.read_text())
        if row['incident_id']!=identity or seal(row['fact'])!=identity:
            raise ValueError('IMMUTABLE_CONTINUITY_INCIDENT_CHANGED')
        return identity
    value=dict(incident_id=identity,fact=fact,first_detected_host_clock=clock,
               dataset_admission=False,training_authorized=False,backfill_performed=False)
    try:
        with path.open('xb') as stream:stream.write(canonical(value)+b'\n');stream.flush();os.fsync(stream.fileno())
    except FileExistsError:return record_incident(root,fact,clock)
    return identity


def sparse(row):
    return {k:row.get(k) for k in ('kind','session_id','sequence','callback_uptime_ms',
        'callback_program_us','receipt_host_gmt_seconds','connected','time_msc')}


def audit(root,clock=host_clock):
    import msvcrt
    root=Path(root)
    with (root/'continuity_monitor.lock').open('a+b') as lock:
        if lock.seek(0,2)==0:lock.write(b'0');lock.flush()
        lock.seek(0)
        try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            path=root/'continuity_summary.json'
            return json.loads(path.read_text()) if path.exists() else {'status':'MONITOR_BUSY'}
        try:return locked_audit(root,clock)
        finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)


def locked_audit(root,clock):
    manifest=json.loads((root/'collection_manifest.json').read_text())
    runtime=json.loads((root/'runtime_state.json').read_text())
    state_path=root/'continuity_monitor_cursor.json'
    state=json.loads(state_path.read_text()) if state_path.exists() else dict(segments={})
    prior_state_hash=seal(state)
    for segment in runtime['segments']:
        folder=root/'segments'/segment
        meta=json.loads((folder/'manifest.json').read_text())
        checkpoint=json.loads((folder/'checkpoint.json').read_text())
        saved=state['segments'].get(segment,dict(rows=0,bytes_verified=0,chain_head=GENESIS,
            last_native=None,last_source_sha=meta['anchor']['source_sha256'],last_source_sequence=meta['anchor']['source_sequence']))
        if checkpoint['rows']<saved['rows']:raise ValueError('MONITORED_CAPTURE_TRUNCATED')
        if checkpoint['rows']==saved['rows'] and checkpoint['chain_head']!=saved['chain_head']:
            raise ValueError('MONITORED_PREFIX_CHANGED')
        if (folder/'journal.jsonl').stat().st_size<saved['bytes_verified']:
            raise ValueError('MONITORED_JOURNAL_TRUNCATED')
        with (folder/'journal.jsonl').open('rb') as stream:
            stream.seek(saved['bytes_verified'])
            while saved['rows']<checkpoint['rows']:
                raw=stream.readline()
                if not raw.endswith(b'\n'):raise ValueError('MONITORED_JOURNAL_INCOMPLETE')
                record=json.loads(raw);body=record['payload']
                if record['previous']!=saved['chain_head'] or record['sha256']!=seal(dict(previous=saved['chain_head'],payload=body)) or body['index']!=saved['rows']:
                    raise ValueError('MONITORED_JOURNAL_HASH_OR_ORDER_CHANGED')
                event=body['event']
                if event.get('source_sequence') is not None:
                    if event['source_sequence']!=saved['last_source_sequence']+1:raise ValueError('MONITORED_SOURCE_SEQUENCE_GAP')
                    native=None
                    if event['native_line'] is not None:
                        parent,digest,native=native_line(event['native_line'].encode())
                        if parent!=saved['last_source_sha'] or digest!=event['source_sha256']:
                            raise ValueError('MONITORED_NATIVE_BYTES_CHANGED')
                    if native is not None:
                        previous=saved['last_native']
                        common=dict(capture_id=manifest['capture_id'],segment=segment,
                            before=previous,after=sparse(native),source_record_hash=event['source_sha256'],
                            timestamps_are_host_labels_not_independent_event_UTC=True,
                            real_broker_event_loss='UNVERIFIED',scientific_disposition='QUARANTINED')
                        if event['callback_gap_ms']>10000:
                            record_incident(root,common|dict(kind='CALLBACK_TIMER_GAP',elapsed_ms=event['callback_gap_ms'],
                                detection='TWO_NOMINAL_5S_TIMER_PERIODS_NOT_DATA_ACCEPTANCE_TOLERANCE'),clock())
                        if native['connected'] is False and (previous is None or previous['connected'] is not False):
                            record_incident(root,common|dict(kind='DISCONNECTION_OBSERVED_START',
                                exact_disconnect_start='UNKNOWN_BETWEEN_OBSERVATIONS'),clock())
                        if native['connected'] is True and previous is not None and previous['connected'] is False:
                            record_incident(root,common|dict(kind='RECONNECTION_OBSERVED',
                                exact_reconnect_time='UNKNOWN_BETWEEN_OBSERVATIONS'),clock())
                        if 'NATIVE_TIMESTAMP_REGRESSION_UNMAPPED' in event['quarantine_flags']:
                            record_incident(root,common|dict(kind='NATIVE_TIME_REGRESSION'),clock())
                        saved['last_native']=sparse(native)
                    saved['last_source_sequence']=event['source_sequence'];saved['last_source_sha']=event['source_sha256']
                saved['chain_head']=record['sha256'];saved['rows']+=1;saved['bytes_verified']=stream.tell()
        if saved['chain_head']!=checkpoint['chain_head']:raise ValueError('MONITORED_CHECKPOINT_HEAD_MISMATCH')
        state['segments'][segment]=saved
    if not state_path.exists() or seal(state)!=prior_state_hash:atomic(state_path,state)
    incidents=[]
    for path in sorted((root/'continuity_incidents').glob('*.json')):
        value=json.loads(path.read_text())
        if seal(value['fact'])!=value['incident_id']:raise ValueError('CONTINUITY_INCIDENT_TAMPERED')
        incidents.append(value)
    gaps=[r for r in incidents if r['fact']['kind']=='CALLBACK_TIMER_GAP']
    last=state['segments'][runtime['active_segment']]['last_native']
    result=dict(status='ACTIVE_MONITOR_WITH_QUARANTINED_INTERRUPTION' if gaps else 'ACTIVE_MONITOR_NO_GAP_DETECTED_IN_VERIFIED_PREFIX',
        capture_id=manifest['capture_id'],verified_rows=sum(s['rows'] for s in state['segments'].values()),
        callback_gaps=len(gaps),maximum_callback_gap_ms=max([r['fact']['elapsed_ms'] for r in gaps],default=0),
        disconnection_starts=sum(r['fact']['kind']=='DISCONNECTION_OBSERVED_START' for r in incidents),
        reconnection_observations=sum(r['fact']['kind']=='RECONNECTION_OBSERVED' for r in incidents),
        last_connected=last['connected'] if last else None,incident_ids=[r['incident_id'] for r in incidents],
        source_sequence_integrity='PASS_AT_VERIFIED_PREFIX_NOT_PROOF_OF_MISSING_BROKER_EVENTS',
        capture_completeness='UNPROVEN_ONTICK_COALESCENCE_AND_INTERRUPTION',
        no_backfill=True,power_settings_changed=False,dataset_admission=False,training_authorized=False,scoring_authorized=False)
    summary_path=root/'continuity_summary.json'
    if not summary_path.exists() or seal(json.loads(summary_path.read_text()))!=seal(result):atomic(summary_path,result)
    return result
