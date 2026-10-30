"""Isolated, hash-pinned NTS measurements; never changes Windows clock or MT5."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'outputs/pc_a_prospective_utc'
sys.path.insert(0,str(ROOT/'python'))
import pc_a_raw_archive as raw


def verify_history(folder,state):
    records={}
    for path in folder.glob('*.json'):
        if len(path.stem)!=32:continue
        record=json.loads(path.read_text());digest=hashlib.sha256(raw.canonical(record['payload'])).hexdigest()
        if digest!=record['sha256']:raise ValueError('NTS_RECORD_HASH_MISMATCH')
        if digest in records:raise ValueError('NTS_DUPLICATE_RECORD')
        records[digest]=record['payload']
    head=state.get('chain_head','0'*64);seen=set()
    while head!='0'*64:
        if head in seen or head not in records:raise ValueError('NTS_CHAIN_MISSING_OR_CYCLE')
        seen.add(head);head=records[head]['previous']
    if len(seen)!=len(records):raise ValueError('NTS_ORPHAN_RECORD_REVIEW_REQUIRED')
    return len(seen)


def run(force=False):
    import ctypes,msvcrt
    folder=BASE/'authenticated_utc';folder.mkdir(parents=True,exist_ok=True)
    with (folder/'station.lock').open('a+b') as lock:
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        return locked_run(folder,force)


def locked_run(folder,force):
    import ctypes
    kernel=ctypes.windll.kernel32.GetTickCount64;kernel.restype=ctypes.c_ulonglong
    state_path=folder/'state.json'
    state=json.loads(state_path.read_text()) if state_path.exists() else {}
    verify_history(folder,state)
    now=kernel();previous=state.get('chain_head','0'*64)
    if not force and state.get('last_uptime_ms',0)<=now<state.get('next_due_uptime_ms',0):return {'status':'NOT_DUE','last_record':state.get('last_record')}
    if state.get('last_record'):
        old=json.loads((folder/state['last_record']).read_text())
        if old['sha256']!=previous or hashlib.sha256(raw.canonical(old['payload'])).hexdigest()!=previous:raise ValueError('NTS_PREVIOUS_RECORD_CHANGED')
    manifest_path=ROOT/'configs/nts_runtime_dependencies_20261029.json'
    manifest=json.loads(manifest_path.read_text());dependencies=BASE/'nts_dependencies';runtime=dependencies/'runtime'
    for name,digest in manifest['runtime_files'].items():
        path=(runtime/name).resolve()
        if not path.is_relative_to(runtime.resolve()) or raw.sha(path)!=digest:raise ValueError('NTS_RUNTIME_HASH_MISMATCH')
    ca=dependencies/'mozilla_cacert.pem'
    if raw.sha(ca)!=manifest['ca_sha256']:raise ValueError('NTS_CA_HASH_MISMATCH')
    sys.path.insert(0,str(runtime))
    from nts_external import measure
    results=[]
    # Fresh sessions: no cookies, exporter keys or access credentials persisted.
    for host in ('time.cloudflare.com','ntppool2.time.nl'):
        try:results.append(dict(status='AUTHENTICATED_MEASUREMENT',measurement=measure(host,ca)))
        except Exception as exc:results.append(dict(status='UNAVAILABLE',origin=host,error=type(exc).__name__))
    native_status_path=BASE/'status.json';models={}
    native=json.loads(native_status_path.read_text()) if native_status_path.exists() else {}
    for name,session in native.get('native_sessions',{}).items():
        tick=session.get('continuity',{}).get('last_tick_observation')
        if session.get('liveness')!='RECENT' or not tick:continue
        values=[]
        for result in results:
            if result['status']!='AUTHENTICATED_MEASUREMENT':continue
            measurement=result['measurement'];anchor=measurement['receive_kernel_uptime_ms_interval']
            if not anchor:continue
            bounds=measurement['utc_receive_interval_model_ns'];uptime=tick['callback_uptime_ms']
            values.append(dict(capture_id=measurement['capture_id'],
                receipt_model_ns=[bounds[0]+(uptime-anchor[1])*1000000,bounds[1]+(uptime-anchor[0])*1000000],
                unbounded_components=['UPTIME_QUANTIZATION','OSCILLATOR_DRIFT','BROKER_GENERATION_TO_CALLBACK_DELAY'],
                event_utc_inferred=False,certified=False))
        models[name]=dict(native_tick=tick,native_chain_head=session['chain_head'],models=values)
    payload=dict(record_id=uuid.uuid4().hex,observed_host_utc=raw.utc(),previous=previous,
        dependency_manifest_sha256=raw.sha(manifest_path),source_sha256=raw.sha(ROOT/'python/nts_external.py'),
        results=results,native_receipt_correlations=models,
        NATIVE_TO_UTC_MAPPING='UNVERIFIED',certified_segments=[],clock_adjusted=False,orders_sent=0)
    digest=hashlib.sha256(raw.canonical(payload)).hexdigest();name=payload['record_id']+'.json'
    with (folder/name).open('x',encoding='utf-8') as stream:json.dump(dict(payload=payload,sha256=digest),stream,sort_keys=True)
    success=any(r['status']=='AUTHENTICATED_MEASUREMENT' for r in results)
    failures=0 if success else state.get('failures',0)+1
    interval=300 if success else min(432000,max(300,10*1.5**min(failures-1,26)))
    raw.atomic(state_path,dict(chain_head=digest,last_record=name,last_uptime_ms=now,next_due_uptime_ms=now+int(interval*1000),failures=failures))
    return dict(status='AUTHENTICATED_MEASUREMENTS_ONLY' if success else 'BLOCKED_NO_AUTHENTICATED_MEASUREMENT',
        record=name,sha256=digest,results=results,certified_segments=[],clock_adjusted=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--force',action='store_true');a=p.parse_args()
    print(json.dumps(run(a.force),indent=2))
