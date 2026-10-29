"""PC A prospective callback monitor and external witness; never attaches/trades."""
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import msvcrt
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
    BASE.mkdir(parents=True,exist_ok=True)
    with (BASE/'monitor.lock').open('a+b') as lock:
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        return locked_observe(network)


def locked_observe(network):
    checkpoint_path=BASE/'checkpoints.json'
    old=json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else {}
    sessions={}
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
        append_witness(witness)
    ticks=sum(s['tick_callbacks'] for s in sessions.values())
    status=dict(observed=instant_display(datetime.now(timezone.utc),basis='HOST_RECEIPT_UNATTESTED'),
        REALTIME_CAPTURE='CALLBACKS_OBSERVED' if ticks else 'PREPARED_NOT_OBSERVED',
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
    raw.atomic(checkpoint_path,sessions)
    raw.atomic(BASE/'status.json',status)
    return status


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--offline',action='store_true')
    args=parser.parse_args()
    try:print(json.dumps(observe(not args.offline),indent=2))
    except Exception as exc:
        raw.atomic(BASE/'last_failure.json',dict(observed_utc=raw.utc(),error=type(exc).__name__,reason=str(exc),scientific_acceptance=False))
        raise
