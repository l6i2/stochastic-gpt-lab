"""Verify native callback chains. Integrity alone never certifies broker event UTC."""
import hashlib
import json
from pathlib import Path
import re

GENESIS='0'*64
LINE=re.compile(r'^\{"previous":"([0-9a-f]{64})","sha256":"([0-9a-f]{64})","payload":(.*)\}$')


def verify_callback(path, checkpoint=None):
    previous=GENESIS; sequence=0; ticks=duplicates=regressions=disconnects=0;bytes_verified=0
    last_tick=None; last_payload=None; last_uptime=None; last_heartbeat=None
    largest_interval=0; session=None; capture=None; partial=False
    last_host=None; host_delta_envelope=[]
    prefix_matched=not checkpoint or (checkpoint['rows']==0 and checkpoint['chain_head']==GENESIS)
    with Path(path).open('rb') as stream:
        for line in stream:
            if not line.endswith(b'\n'):
                partial=True;break
            match=LINE.fullmatch(line.decode('utf-8').rstrip('\r\n'))
            if not match:raise ValueError('INVALID_NATIVE_CHAIN_LINE')
            parent,digest,body=match.groups()
            if parent!=previous or hashlib.sha256((parent+'\n'+body).encode()).hexdigest()!=digest:
                raise ValueError('CALLBACK_HASH_CHAIN_BROKEN')
            row=json.loads(body)
            if row['sequence']!=sequence:raise ValueError('SEQUENCE_GAP_OR_DUPLICATE')
            if row['server']!='XMGlobalSC-MT5 5' or row['symbol']!='US30Cash':raise ValueError('CALLBACK_IDENTITY_MISMATCH')
            if sequence==0:
                if row['kind']!='SESSION_START':raise ValueError('SESSION_START_REQUIRED')
                session,capture=row['session_id'],row['capture_id']
            if row['session_id']!=session or row['capture_id']!=capture:raise ValueError('SESSION_ID_CHANGED')
            uptime=row['callback_uptime_ms']
            if last_uptime is not None and uptime<last_uptime:raise ValueError('UPTIME_REGRESSION_RESTART_NOT_SEGMENTED')
            if row['read_uptime_ms']<uptime:raise ValueError('RECEIPT_ORDER_INVALID')
            if 'receipt_host_gmt_seconds' in row and last_host is not None:
                host_delta_envelope.append((row['receipt_host_gmt_seconds']-last_host)*1000-(uptime-last_uptime))
                if len(host_delta_envelope)>2:host_delta_envelope=[min(host_delta_envelope),max(host_delta_envelope)]
            last_host=row.get('receipt_host_gmt_seconds')
            if row['kind']=='HEARTBEAT':
                if last_heartbeat is not None:largest_interval=max(largest_interval,uptime-last_heartbeat)
                last_heartbeat=uptime
            if row['connected'] is False:disconnects+=1
            if row['kind']=='ONTICK_LATEST_QUOTE':
                stamp=row['time_msc']
                if stamp//1000!=row['time']:raise ValueError('NATIVE_TIMESTAMP_UNITS')
                key=(stamp,row['bid'],row['ask'],row['flags'])
                duplicates+=int(key==last_payload)
                regressions+=int(last_tick is not None and stamp<last_tick)
                last_tick,last_payload=stamp,key;ticks+=1
            previous=digest;sequence+=1;last_uptime=uptime;bytes_verified+=len(line)
            if checkpoint and sequence==checkpoint['rows']:
                if previous!=checkpoint['chain_head']:raise ValueError('PREVIOUS_PREFIX_CHANGED')
                prefix_matched=True
    if not prefix_matched:raise ValueError('CALLBACK_TRUNCATED_OR_DELETED')
    return dict(rows=sequence,chain_head=previous,tick_callbacks=ticks,bytes_verified=bytes_verified,
        adjacent_duplicate_quotes=duplicates,native_timestamp_regressions=regressions,
        disconnected_records=disconnects,largest_heartbeat_interval_ms=largest_interval,
        partial_tail=partial,session_id=session,capture_id=capture,last_callback_uptime_ms=last_uptime,
        completeness='UNPROVEN_ONTICK_CAN_COALESCE',future_event_timestamps='NOT_EVALUABLE_WITHOUT_MAPPING',
        last_connected=row['connected'] if sequence else None,last_kind=row['kind'] if sequence else None,
        host_clock_vs_uptime_delta_ms_envelope=[min(host_delta_envelope),max(host_delta_envelope)] if host_delta_envelope else None,
        host_clock_delta_scope='DIAGNOSTIC_SECOND_RESOLUTION_NOT_CERTIFIED_CLOCK_STEP',
        scientific_acceptance=False)


def segment_verdict(capture, witness):
    """Deliberately no authorizing mapping API; all required evidence is separate."""
    missing=['INDEPENDENT_SAME_EVENT_UTC_BINDING','BOUNDED_BROKER_EVENT_MAPPING',
             'DATED_EXACT_SERVER_CALENDAR','CALLBACK_COVERAGE_AND_QUEUE_DELAY_BOUND']
    if not capture.get('tick_callbacks'):missing.append('REAL_NATIVE_CALLBACKS_NOT_OBSERVED')
    if not witness.get('authenticated_utc_bound'):missing.append('AUTHENTICATED_UTC_WITH_DEFENSIBLE_UNCERTAINTY')
    # A caller-provided boolean is not evidence of authentication or authorization.
    return dict(status='QUARANTINED',certified_intervals=[],missing=missing,
                causal_audit='FAIL',training_readiness='BLOCKED_BY_RESEARCH_GOVERNANCE')
