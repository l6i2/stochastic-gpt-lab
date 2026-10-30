"""PC A prospective callback monitor and external witness; never attaches/trades."""
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
import pc_a_raw_archive as raw
from independent_clock_reference import capture_reference
from prospective_utc import verify_callback,segment_verdict,GENESIS
from time_semantics import instant_display
from callback_continuity import analyze as analyze_continuity, receipt_projection

BASE=ROOT/'outputs/pc_a_prospective_utc'
NATIVE=Path.home()/'AppData/Roaming/MetaQuotes/Terminal'/raw.DATA_NAME/'MQL5/Files/ResearchDiagnostics/ProspectiveUTC'


def append_witness(value):
    path=BASE/'external_witness.jsonl'
    checkpoint_path=BASE/'witness_checkpoint.json'
    checkpoint=json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else None
    if checkpoint and not path.exists():raise ValueError('PREVIOUS_WITNESS_MISSING')
    previous=GENESIS
    rows=0;prefix_matched=not checkpoint
    if path.exists():
        with path.open('rb') as stream:
            for line in stream:
                item=json.loads(line)
                body=raw.canonical(item['payload'])
                digest=hashlib.sha256(previous.encode()+b'\n'+body).hexdigest()
                if item['previous']!=previous or item['sha256']!=digest:raise ValueError('WITNESS_CHAIN_BROKEN')
                previous=digest;rows+=1
                if checkpoint and rows==checkpoint['rows']:
                    if digest!=checkpoint['chain_head']:raise ValueError('WITNESS_PREFIX_CHANGED')
                    prefix_matched=True
    if not prefix_matched:raise ValueError('WITNESS_TRUNCATED')
    digest=hashlib.sha256(previous.encode()+b'\n'+raw.canonical(value)).hexdigest()
    with path.open('ab') as stream:
        stream.write(raw.canonical(dict(previous=previous,sha256=digest,payload=value))+b'\n')
        stream.flush();__import__('os').fsync(stream.fileno())
    raw.atomic(checkpoint_path,dict(rows=rows+1,chain_head=digest))
    return digest


def observe(network=True):
    # Pure witness validation is portable; real capture still requires Windows.
    if sys.platform != 'win32':
        raise OSError('LOCAL_REQUIRED_WINDOWS_CLOCK_AND_FILE_LOCK')
    import msvcrt
    BASE.mkdir(parents=True,exist_ok=True)
    with (BASE/'monitor.lock').open('a+b') as lock:
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        return locked_observe(network)


def locked_observe(network):
    checkpoint_path=BASE/'checkpoints.json'
    old=json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else {}
    sessions={};new_incidents=[]
    for name in old:
        if not (NATIVE/name).is_file():raise ValueError('PREVIOUS_CAPTURE_MISSING')
    for path in NATIVE.glob('pc_a_prospective_utc_v1_*.jsonl'):
        sessions[path.name]=verify_callback(path,old.get(path.name))
        # Append only complete verified lines to a project-owned local mirror.
        # This is the same disk/failure domain, not an independent backup.
        mirror=BASE/'native_mirror'/path.name;mirror.parent.mkdir(parents=True,exist_ok=True)
        copied=0
        if mirror.exists():
            prior=verify_callback(mirror)
            verify_callback(path,prior)
            copied=prior['bytes_verified']
        remaining=sessions[path.name]['bytes_verified']-copied
        if remaining<0:raise ValueError('NATIVE_SHORTER_THAN_MIRROR')
        with path.open('rb') as source,mirror.open('ab') as destination:
            source.seek(copied)
            while remaining:
                chunk=source.read(min(1048576,remaining))
                if not chunk:raise ValueError('NATIVE_CHANGED_DURING_MIRROR')
                destination.write(chunk);remaining-=len(chunk)
            destination.flush();__import__('os').fsync(destination.fileno())
        if verify_callback(mirror)['chain_head']!=sessions[path.name]['chain_head']:
            raise ValueError('MIRROR_PREFIX_MISMATCH')
        continuity=analyze_continuity(mirror)
        sessions[path.name]['continuity']=continuity
        for incident in continuity['incidents']:
            destination=BASE/'incidents'/(incident['incident_id']+'.json')
            destination.parent.mkdir(parents=True,exist_ok=True)
            if not destination.exists():
                new_incidents.append(incident)
                # Exclusive creation preserves the first observation forever.
                with destination.open('x',encoding='utf-8') as stream:
                    json.dump(dict(incident=incident,first_observed_host_utc=raw.utc(),
                        native_prefix_chain_head=sessions[path.name]['chain_head'],
                        causal_certification=False),stream,sort_keys=True)
    if new_incidents:
        start=min(i['before_host_gmt_seconds'] for i in new_incidents)-300
        end=max(i['after_host_gmt_seconds'] for i in new_incidents)+300
        # Host-domain event context, not independent UTC proof or a cause claim.
        script="$s=[DateTimeOffset]::FromUnixTimeSeconds("+str(start)+").LocalDateTime;$e=[DateTimeOffset]::FromUnixTimeSeconds("+str(end)+").LocalDateTime;try {$v=@(Get-WinEvent -FilterHashtable @{LogName='System';StartTime=$s;EndTime=$e;Id=1,12,13,41,42,107,506,507,6005,6006,6008} -MaxEvents 200 -ErrorAction Stop | Select-Object Id,ProviderName,RecordId,@{N='TimeUtc';E={$_.TimeCreated.ToUniversalTime().ToString('o')}});@{status='OK';events=$v}|ConvertTo-Json -Depth 4 -Compress}catch{if($_.FullyQualifiedErrorId -like '*NoMatchingEventsFound*'){@{status='NO_MATCHING_EVENTS';events=@()}|ConvertTo-Json -Compress}else{@{status='QUERY_FAILED';events=@()}|ConvertTo-Json -Compress}}"
        context=subprocess.run(['powershell.exe','-NoProfile','-Command',script],capture_output=True,text=True,timeout=20)
        raw.atomic(BASE/'incident_context'/(__import__('uuid').uuid4().hex+'.json'),dict(
            incident_ids=[i['incident_id'] for i in new_incidents],host_window_start_seconds=start,
            host_window_end_seconds=end,system_events=json.loads(context.stdout) if context.returncode==0 and context.stdout.strip() else {'status':'UNAVAILABLE'},
            cause='UNDETERMINED_EVENTS_ARE_CONTEXT_ONLY',context_may_be_capped_at=200))
    kernel=ctypes.windll.kernel32.GetTickCount64;kernel.restype=ctypes.c_ulonglong
    uptime=kernel()
    for value in sessions.values():
        last=value['last_callback_uptime_ms']
        value['observed_age_ms']=uptime-last if last is not None and uptime>=last else None
        value['liveness']='CLOSED' if value['last_kind']=='SESSION_END' else 'UPTIME_EPOCH_CHANGED_OR_EMPTY' if value['observed_age_ms'] is None else 'RECENT' if value['observed_age_ms']<=10000 else 'HEARTBEAT_OVERDUE'
    witness={}
    if network:
        before=dict(kernel_uptime_ms=kernel(),perf_counter_ns=time.perf_counter_ns(),host_utc_ns=time.time_ns())
        reference=capture_reference()
        after=dict(kernel_uptime_ms=kernel(),perf_counter_ns=time.perf_counter_ns(),host_utc_ns=time.time_ns())
        clock=subprocess.run(['w32tm','/query','/status'],capture_output=True,text=True,timeout=15)
        witness=dict(kind='EXTERNAL_REFERENCE_DIAGNOSTIC',before=before,after=after,reference=reference,
            windows_sync_status=clock.stdout,windows_sync_exit=clock.returncode,
            authenticated_utc_bound=False,uncertainty='NOT_CERTIFIED_NTP_UNAUTHENTICATED_NO_OSCILLATOR_BOUND',
            same_event_binding=False,clock_changed=False,orders_sent=0)
        witness['callback_receipt_models']={name:dict(native_observation=s['continuity']['last_tick_observation'],
            receipt_projection=receipt_projection(reference,s['continuity']['last_tick_observation']['callback_uptime_ms']))
            for name,s in sessions.items() if s['liveness']=='RECENT' and s['continuity'].get('last_tick_observation')}
        append_witness(witness)
        # Isolate cryptographic dependencies and failures from native ingestion.
        try:
            nts=subprocess.run([sys.executable,str(ROOT/'tools/authenticated_utc_station.py')],
                cwd=ROOT,capture_output=True,text=True,timeout=40)
            witness['nts_station_exit']=nts.returncode
            nts_status=json.loads(nts.stdout) if nts.returncode==0 and nts.stdout.strip() else dict(status='BLOCKED',error='ISOLATED_NTS_STATION_FAILED')
        except (subprocess.TimeoutExpired,ValueError,OSError) as exc:
            nts_status=dict(status='BLOCKED',error=type(exc).__name__)
        raw.atomic(BASE/'nts_station_status.json',nts_status)
    ticks=sum(s['tick_callbacks'] for s in sessions.values())
    active=any(s['tick_callbacks'] and s['last_connected'] and s['liveness']=='RECENT' for s in sessions.values())
    capture_status='ACTIVE_CALLBACKS_QUARANTINED' if active else 'INACTIVE_CALLBACKS_RETAINED' if ticks else 'STALLED_START_ONLY' if sessions else 'PREPARED_NOT_OBSERVED'
    status=dict(observed=instant_display(datetime.now(timezone.utc),basis='HOST_RECEIPT_UNATTESTED'),
        REALTIME_CAPTURE=capture_status,
        native_sessions=sessions,session_count=len(sessions),session_boundaries_observed=max(0,len(sessions)-1),
        restart_interpretation='NEW_SESSION_CAN_BE_REINIT_RESTART_OR_ANOTHER_CHART_NO_AUTOMATIC_EQUIVALENCE',
        total_tick_callbacks=ticks,EXTERNAL_UTC_SOURCE='NTP_AND_TLS_REFERENCES_DIAGNOSTIC_ONLY',
        CLOCK_UNCERTAINTY='UNVERIFIED_NO_AUTHENTICATED_PRECISION_BOUND',
        SEGMENT_CERTIFICATION=segment_verdict(dict(tick_callbacks=ticks),witness),
        XM_TIMESTAMP_MAPPING='UNVERIFIED',BROKER_CALENDAR='PARTIAL_NATIVE_OBSERVATIONS_RETAINED',
        CAUSAL_AUDIT='FAIL',TRAINING_READINESS='BLOCKED_BY_RESEARCH_GOVERNANCE',
        heartbeat_liveness='NOT_OBSERVED' if not sessions else 'COMPARE_LAST_CALLBACK_UPTIME_WITH_CURRENT_KERNEL_UPTIME',
        source_sha256=raw.sha(ROOT/'mt5/ProspectiveUtcObserver.mq5'),
        source_sha256_scope='REPOSITORY_SOURCE_NOT_RUNTIME_BINARY_ATTESTATION',
        DISCOVERY_VALIDATION='BLOCKED',FINAL_TEST='LOCKED',DEMO='DISABLED',LIVE_TRADING=False,orders_sent=0)
    if (BASE/'external_witness.jsonl').exists():status['external_witness_sha256']=raw.sha(BASE/'external_witness.jsonl')
    nts_state=BASE/'authenticated_utc/state.json'
    if nts_state.exists():
        pointer=json.loads(nts_state.read_text());record=json.loads((nts_state.parent/pointer['last_record']).read_text())
        valid=hashlib.sha256(raw.canonical(record['payload'])).hexdigest()==pointer['chain_head']==record['sha256']
        authenticated=valid and any(r.get('status')=='AUTHENTICATED_MEASUREMENT' for r in record['payload']['results'])
        status['EXTERNAL_UTC_AUTHENTICATION']='PASS_NTS_MEASUREMENT_ONLY' if authenticated else 'UNVERIFIED'
        status['authenticated_utc_record_sha256']=pointer['chain_head']
        status['authenticated_utc_record']=pointer['last_record']
        status['local_clock_continuous_authentication']='UNVERIFIED_BETWEEN_MEASUREMENTS'
    raw.atomic(checkpoint_path,sessions)
    raw.atomic(BASE/'status.json',status)
    # Derived diagnostics fail independently; capture and its status are durable.
    try:
        from correlate_nts_xm import run as correlate_nts
        raw.atomic(BASE/'correlation_monitor_status.json',correlate_nts())
    except Exception as exc:
        raw.atomic(BASE/'correlation_monitor_status.json',dict(status='QUARANTINED',error=type(exc).__name__,reason=str(exc),scientific_acceptance=False))
    return status


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--offline',action='store_true')
    args=parser.parse_args()
    try:print(json.dumps(observe(not args.offline),indent=2))
    except Exception as exc:
        raw.atomic(BASE/'last_failure.json',dict(observed_utc=raw.utc(),error=type(exc).__name__,reason=str(exc),scientific_acceptance=False))
        raise
