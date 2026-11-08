"""Separate, bounded retrospective XM archive. No prospective writer or tester."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'python'))
from time_semantics import instant_display
from controller.authorized_capture import manager_lock,sha
from controller.isolated_observation import atomic,host_clock
from controller.pretrain_contracts import seal
from controller.exclusive_roles import verify_roles
from controller.cf_recovery import classify
from controller.xm_history_recovery import (SERVER,SYMBOL,missing_intervals,next_chunks,
    permitted,retrieve,archive_chunk,verify_manifest,retry_ready)
from tools.prospective_pipeline import NativeReference

BASE=ROOT/'outputs/xm_historical_recovery_v1'
AUTH=ROOT/'research/studies/xm_historical_recovery_20261108/authorization.json'


def inventory():
    original=ROOT/'outputs/us30cash_m5_native_observations'
    pointer=json.loads((original/'current.json').read_bytes())
    folder=original/pointer['capture_id']
    if folder.parent!=original or sha(folder/'manifest.json')!=pointer['manifest_sha256']:
        raise ValueError('PROSPECTIVE_MANIFEST_CHANGED')
    manifest=json.loads((folder/'manifest.json').read_bytes())
    roles=verify_roles(ROOT,manifest)
    if not roles or not roles.get('exclusive'):raise PermissionError('EXCLUSIVE_CUT_NOT_VERIFIED')
    authorization=json.loads(AUTH.read_bytes())
    if (authorization['diagnostic_recovery_only'] is not True
            or authorization['prospective_import_allowed'] is not False
            or any(authorization[k] is not False for k in ('training_authorized','scoring_authorized','dataset_admission_authorized','orders_authorized','live_trading'))
            or authorization['role_assignment_sha256']!=manifest['exclusive_role_assignment']['sha256']):
        raise PermissionError('DIAGNOSTIC_AUTHORIZATION_SCOPE_CHANGED')
    quality=json.loads((original/'quality_status.json').read_bytes())
    if quality.get('status')!='PASS_INCREMENTAL_QUARANTINED':
        raise RuntimeError('WAITING_FOR_VERIFIED_PROSPECTIVE_INDEX')
    end=quality['records_verified']
    events=[]
    with sqlite3.connect((folder/'snapshots.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:
        db.execute('BEGIN')
        if db.execute('SELECT digest FROM records WHERE n=?',(end-1,)).fetchone()!=(quality['chain_head'],):
            raise ValueError('PROSPECTIVE_INDEX_HEAD_CHANGED')
        interruptions=db.execute("SELECT n,body FROM records WHERE n<? AND json_extract(body,'$.kind') IN ('OBSERVATION_INTERRUPTION','NEW_OBSERVATION_EPOCH') ORDER BY n",(end,)).fetchall()
        for number,raw in interruptions:
            event=json.loads(raw)
            event['classification']={'SLEEP':'WINDOWS_SUSPENDED','XM_DISCONNECT':'XM_DISCONNECTED',
                'MARKET_CLOSED':'MARKET_CLOSED_VERIFIED'}.get(classify(event),'UNKNOWN_GAP')
            if not event.get('previous_observation'):
                prior=db.execute("SELECT n,body FROM records WHERE n<? AND json_extract(body,'$.kind')='LIVE_LATEST_STATE_POLL' ORDER BY n DESC LIMIT 1",(number,)).fetchone()
                if prior:
                    poll=json.loads(prior[1])
                    event=dict(event,previous_observation=dict(native_msc=poll['native_quote']['time_msc'],
                        record=prior[0],clock=poll['read_end']),prior_observation_derived_from_verified_ledger=True)
            events.append((number,event))
            before=(event.get('previous_observation') or {}).get('native_msc')
            if before is None:continue
            following=db.execute("SELECT n,body FROM records WHERE n>? AND n<? AND json_extract(body,'$.kind')='LIVE_LATEST_STATE_POLL' AND json_extract(body,'$.native_quote.time_msc')>? ORDER BY n LIMIT 1",(number,end,before)).fetchone()
            if following:events.append((following[0],json.loads(following[1])))
        last=db.execute("SELECT body FROM records WHERE n<? AND json_extract(body,'$.kind')='LIVE_LATEST_STATE_POLL' ORDER BY n DESC LIMIT 1",(end,)).fetchone()
    unique={number:event for number,event in events}
    result=missing_intervals(sorted(unique.items()),roles['minimum_native_open_msc'])
    maximum=json.loads(last[0])['native_quote']['time_msc']
    policy=dict(server=SERVER,symbol=SYMBOL,minimum_native_msc=roles['minimum_native_open_msc'],
                maximum_native_msc=maximum,gaps=result['gaps'],protected_intervals=[],
                authority_sha256=sha(AUTH),scope='POST_EXCLUSIVE_CUT_GAPS_DIAGNOSTIC_COPY_ONLY',
                source_index=dict(capture_id=folder.name,records=end,head=quality['chain_head'],
                    origin_manifest_sha256=pointer['manifest_sha256']),
                legacy_unknown_bounds_recovered=False,independence_certified=False)
    policy['archive_id']='XM_HISTORY_PC_A_DIAGNOSTIC_V1'
    policy['producer_id']='XM_RETROSPECTIVE_RECOVERY_V1'
    policy['source_hashes_at_request']={name:sha(ROOT/name) for name in (
        'tools/xm_historical_recovery.py','controller/xm_history_recovery.py','tools/xm_history_native.py')}
    return policy,dict(result,source_capture_id=folder.name,source_head=quality['chain_head'],
                       source_records=end,policy=policy,exclusive_role_unchanged=True)


def load_checkpoint():
    path=BASE/'checkpoint.json'
    state=dict(head=None,receipts=[],completed={})
    if path.exists():
        saved=json.loads(path.read_bytes())
        if seal(saved['state'])!=saved['sha256']:raise ValueError('HISTORICAL_CHECKPOINT_CHANGED')
        state=saved['state']
    parent=None
    for entry in state['receipts']:
        path=(BASE/entry['path']).resolve()
        if not path.is_relative_to(BASE.resolve()) or sha(path)!=entry['sha256']:
            raise ValueError('HISTORICAL_RECEIPT_CHANGED')
        manifest=json.loads(path.read_bytes())
        if manifest['previous']!=parent:raise ValueError('HISTORICAL_RECEIPT_CHAIN_CHANGED')
        parent=entry['sha256']
    if parent!=state['head']:raise ValueError('HISTORICAL_HEAD_CHANGED')
    known={entry['sha256'] for entry in state['receipts']}
    # A payload+manifest may have committed just before a checkpoint failure.
    while True:
        orphans=[]
        for path in (BASE/'requests').glob('*/attempt_*/manifest.json'):
            digest=sha(path)
            if digest in known:continue
            manifest=json.loads(path.read_bytes())
            if manifest['previous']==state['head']:orphans.append((path,manifest,digest))
        if not orphans:break
        if len(orphans)!=1:raise ValueError('HISTORICAL_RECEIPT_CHAIN_FORK')
        path,manifest,digest=orphans[0];verify_manifest(path.parent)
        adopt(state,path,manifest,digest);known.add(digest)
    return state


def adopt(state,path,manifest,digest):
    if manifest['previous']!=state['head']:raise ValueError('HISTORICAL_PARENT_CHANGED')
    entry=dict(path=path.relative_to(BASE).as_posix(),sha256=digest)
    state['receipts'].append(entry);state['head']=digest
    old=state['completed'].get(manifest['key'],{})
    marker=dict(boot_id=(manifest['recovery_clock'] or {}).get('boot_id'),native_max=manifest['policy']['maximum_native_msc'])
    count=old.get('attempts_for_source',old.get('attempts',0))+1 if old.get('source_marker')==marker else 1
    state['completed'][manifest['key']]=dict(entry,status=manifest['status'],
        attempts=old.get('attempts',0)+1,clock=manifest['recovery_clock'],source_marker=marker,attempts_for_source=count)


def run(budget=6,native_compare=False):
    import psutil
    BASE.mkdir(parents=True,exist_ok=True)
    with manager_lock(BASE):
        policy,gaps=inventory();atomic(BASE/'gap_inventory.json',gaps)
        state=load_checkpoint();clock=host_clock()
        atomic(BASE/'checkpoint.json',dict(state=state,sha256=seal(state)))
        completed=set()
        for key,item in state['completed'].items():
            marker=dict(boot_id=clock['boot_id'],native_max=policy['maximum_native_msc'])
            if not retry_ready(item,clock,marker):completed.add(key)
        requests=next_chunks(policy,completed,budget)
        reference=NativeReference();processed=[];native_launches=0
        try:
            if requests:reference.connect()
            if requests:
                account=reference.mt5.account_info();terminal=reference.mt5.terminal_info()
                if (not account or account.trade_mode!=0 or account.server!=SERVER
                        or not terminal.connected or terminal.trade_allowed):
                    raise RuntimeError('WAITING_FOR_SAFE_CONNECTED_XM')
                symbol=reference.mt5.symbol_info(SYMBOL)
                if not symbol or getattr(symbol,'custom',True):raise RuntimeError('NON_NATIVE_SYMBOL_REJECTED')
            expected_login=account.login if requests else None
            if psutil.disk_usage(str(BASE)).free<2*1024**3:raise RuntimeError('HISTORICAL_FREE_DISK_BOUND')
            for request in requests:
                if psutil.disk_usage(str(BASE)).free<2*1024**3:raise RuntimeError('HISTORICAL_FREE_DISK_BOUND')
                permitted(request['start'],request['end'],policy)
                native={}
                native_failure=None
                def fallback(kind,start,end):
                    nonlocal native_failure,native_launches
                    if native_failure:raise RuntimeError(native_failure)
                    if not native:
                        if native_launches>=1:raise RuntimeError('NATIVE_FALLBACK_DEFERRED_PER_RUN_BOUND')
                        native_launches+=1
                        from tools.xm_history_native import recover
                        try:native.update(recover(ROOT,policy,start,end,BASE/'native_trials'/request['key']))
                        except (RuntimeError,ValueError) as exc:
                            native_failure=str(exc);raise
                    completion=native['evidence']['completion']
                    count=completion['ticks' if kind=='ticks' else kind+'_count']
                    if int(count)<0:raise RuntimeError('MQL5_NATIVE_HISTORY_UNAVAILABLE_'+kind)
                    return native[kind],native['evidence']
                def reader(kind,start,end):
                    account_now=reference.mt5.account_info();terminal_now=reference.mt5.terminal_info()
                    if (not account_now or account_now.login!=expected_login or account_now.trade_mode!=0
                            or account_now.server!=SERVER or not terminal_now or not terminal_now.connected
                            or terminal_now.trade_allowed):raise RuntimeError('HISTORICAL_IDENTITY_CHANGED')
                    before=host_clock()
                    rows,source=retrieve(reference.mt5,kind,start,end,fallback)
                    after=host_clock();account_after=reference.mt5.account_info()
                    if not account_after or account_after.login!=expected_login:raise RuntimeError('HISTORICAL_IDENTITY_CHANGED_DURING_QUERY')
                    return rows,dict(source,retrieval_start=before,retrieval_end=after)
                folder,manifest=archive_chunk(BASE,policy,request,reader,state['head'],host_clock(),
                    retry_failed=request['key'] in state['completed'])
                if native_compare:
                    comparisons={}
                    for kind in ('m1','m5','ticks'):
                        try:
                            rows,evidence=fallback(kind,request['start'],request['end'])
                            archived=[json.loads(line) for line in (folder/(kind+'.jsonl')).read_bytes().splitlines()]
                            comparisons[kind]=dict(native_rows=len(rows),python_rows=len(archived),
                                exact=rows==archived,evidence=evidence)
                        except (RuntimeError,ValueError) as exc:comparisons[kind]=dict(error=str(exc))
                    atomic(BASE/'native_comparison.json',comparisons)
                    native_compare=False
                path=folder/'manifest.json';adopt(state,path,manifest,sha(path))
                atomic(BASE/'checkpoint.json',dict(state=state,sha256=seal(state)))
                processed.append(dict(key=request['key'],quality=manifest['quality'],status=manifest['status']))
        finally:reference.close()
        remaining=next_chunks(policy,set(state['completed']),1)
        result=dict(status='ACTIVE_RETROSPECTIVE_DIAGNOSTIC',observed_clock=host_clock(),
            archive_head=state['head'],archived_chunks=len(state['completed']),
            processed=processed,additional_unattempted_intervals=bool(remaining),
            prospective_import=False,dataset_admitted=False,training_executed=False,orders_sent=0)
        current=[]
        for request in next_chunks(policy,set(),10000):
            item=state['completed'].get(request['key'])
            if not item:continue
            path=BASE/item['path']
            if sha(path)!=item['sha256']:raise ValueError('HISTORICAL_MANIFEST_CHANGED')
            current.append(json.loads(path.read_bytes()))
        result['current_version_totals']=dict(intervals=len(current),
            ticks=sum(m['quality']['ticks'] for m in current),m1=sum(m['quality']['m1'] for m in current),
            m5=sum(m['quality']['m5'] for m in current),missing_m1=sum(len(m['quality']['missing_m1_opens']) for m in current),
            superseded_attempts_not_counted=len(state['receipts'])-len(current))
        result['recovery_time_display']=instant_display(datetime.fromisoformat(result['observed_clock']['host_utc_label']),basis='HOST_RECEIPT_UNATTESTED')
        context_path=BASE/'context_result.json'
        context=json.loads(context_path.read_bytes()) if context_path.exists() else None
        if not remaining and (context is None or context.get('status') in ('WAITING_FOR_RESOURCES','WAITING_FOR_ISOLATED_TERMINAL')):
            from tools.xm_recovered_context import compare
            try:context=compare(ROOT,BASE,state,next_chunks(policy,set(),10000))
            except Exception as exc:context=dict(status='FAILED_DIAGNOSTIC',error=type(exc).__name__+':'+str(exc),training_executed=False)
            atomic(context_path,context)
        result['context_diagnostic']=context
        atomic(BASE/'status.json',result)
        return result


def audit_archive():
    """Verify all local B payloads without contacting MT5 or a prospective writer."""
    with manager_lock(BASE):
        state=load_checkpoint()
        for entry in state['receipts']:
            path=BASE/entry['path']
            manifest=verify_manifest(path.parent)
            permitted(manifest['start'],manifest['end'],manifest['policy'])
        policy=json.loads((BASE/'gap_inventory.json').read_bytes())['policy']
        current=[]
        for request in next_chunks(policy,set(),10000):
            item=state['completed'].get(request['key'])
            if not item:continue
            manifest=json.loads((BASE/item['path']).read_bytes())
            current.append(dict(key=request['key'],start=request['start'],end=request['end'],
                manifest_sha256=item['sha256'],files=manifest['files'],quality=manifest['quality']))
        result=dict(status='PASS_LOCAL_RETROSPECTIVE_HASH_AUDIT',archive_head=state['head'],
            all_receipts_verified=len(state['receipts']),current_intervals=current,
            missing_requests=len(next_chunks(policy,set(state['completed']),10000)),
            prospective_import=False,dataset_admitted=False,training_executed=False)
        atomic(BASE/'audit_result.json',result)
        return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--budget',type=int,default=6)
    parser.add_argument('--native-compare',action='store_true')
    parser.add_argument('--audit',action='store_true')
    args=parser.parse_args()
    if not 1<=args.budget<=160:parser.error('budget must be 1..160 bounded chunks')
    try:
        result=audit_archive() if args.audit else run(args.budget,args.native_compare)
        if args.audit:result={k:v for k,v in result.items() if k!='current_intervals'}
        print(json.dumps(result,indent=2))
    except Exception as exc:
        if str(exc)=='CAPTURE_MANAGER_ALREADY_RUNNING':
            print(json.dumps(dict(status='EXISTING_HISTORICAL_WORKER_ACTIVE')));sys.exit(0)
        atomic(BASE/'status.json',dict(status='RETRY_REQUIRED',error=type(exc).__name__+':'+str(exc),
            observed_clock=host_clock(),prospective_import=False,training_executed=False))
        raise
