"""Bounded incremental read-only C+F validation in the existing reporter process."""
import json
from pathlib import Path
import sqlite3
import sys
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from controller.authorized_capture import sha,once,manager_lock
from controller.isolated_observation import GENESIS,atomic
from controller.pretrain_contracts import seal
from controller.exclusive_roles import verify_roles
from controller.cf_maturity import maturity,session_feasibility
from controller.native_database_snapshots import assess
from controller.cf_feature_review import seed_check,retained_oracle
from controller.prospective_processor import initial_state


def oracle_job_status(folder,expected,process_running):
    """A dead/failed oracle must never be presented indefinitely as running."""
    folder=Path(folder)
    try:result=json.loads((folder/'stdout.json').read_text())
    except (ValueError,FileNotFoundError):
        return dict(status='RUNNING' if process_running else 'FAILED_NO_VALID_RESULT',
                    native_parity_verified=False,training_executed=False)
    if result.get('status')=='PASS_OWN_PREFIX_NATIVE_DIAGNOSTIC_ONLY':
        valid=(all(result.get(k)==expected[k] for k in ('capture_id','epoch','own_seed_bar_hash'))
               and result.get('native_m5',0)>=expected['milestone']
               and result.get('ATR_PARITY')=='PASS_EXACT' and result.get('MAIN_K_PARITY')=='PASS_RETAINED_BOUND'
               and (expected['milestone']<276 or result.get('HA_PARITY')=='PASS_EXACT')
               and result.get('original_terminals_preserved') is True and result.get('orders_sent')==0
               and result.get('training_executed') is False and result.get('dataset_admitted') is False)
        return dict(status='PASS_OWN_PREFIX_NATIVE_DIAGNOSTIC_ONLY' if valid else 'FAILED_RESULT_SCOPE',
                    native_parity_verified=valid,result=result,training_executed=False)
    retryable=result.get('status') in ('WAITING_FOR_RESOURCES','WAITING_FOR_DATA')
    return dict(status=result.get('status','FAILED_RESULT_SCHEMA'),native_parity_verified=False,
                retryable_on_new_data=retryable,result=result,training_executed=False)


def oracle_process_running(pid,script):
    import psutil
    if not pid:return False
    try:return str(script).lower() in ' '.join(psutil.Process(pid).cmdline()).lower()
    except psutil.NoSuchProcess:return False
    except psutil.AccessDenied:return True  # Do not create a duplicate on uncertainty.


def native_oracle_milestone(root,base,status):
    """Dispatch bounded work only on new seed milestones; never retry same input."""
    import psutil,subprocess,os
    n=status['technical_warmup']
    milestone=next((limit for limit in (350,276,30,15) if n>=limit),None)
    if milestone is None:return dict(status='WAITING_FOR_15_OWN_M5',own_bars=n,native_terminal_launched=False)
    if not status.get('own_seed_bar_hash'):raise ValueError('ORACLE_OWN_SEED_NOT_BOUND')
    script=root/'tools/cf_own_indicator_oracle.py'
    key=seal([status['capture_id'],status['epoch'],status['own_seed_bar_hash'],milestone,sha(script),sha(root/'controller/cf_feature_review.py'),sha(root/'controller/cf_atr_candidate.py')])
    stage=base/'native_oracle_jobs'/key;folder=stage;request=folder/'request.json'
    if (stage/'verified_result.json').exists():return json.loads((stage/'verified_result.json').read_text())
    if (stage/'last_attempt.json').exists():
        name=json.loads((stage/'last_attempt.json').read_text())['folder']
        if Path(name).name!=name:raise ValueError('ORACLE_ATTEMPT_PATH_CHANGED')
        folder=stage/name;request=folder/'request.json'
    if request.exists():
        pid=json.loads((folder/'process.json').read_text())['pid'] if (folder/'process.json').exists() else None
        running=oracle_process_running(pid,script)
        expected=dict(capture_id=status['capture_id'],epoch=status['epoch'],own_seed_bar_hash=status['own_seed_bar_hash'],milestone=milestone)
        result=oracle_job_status(folder,expected,running)
        if result['native_parity_verified']:
            once(stage/'verified_result.json',result);return result
        if not result.get('retryable_on_new_data') or n<=json.loads(request.read_text()).get('own_bars_at_dispatch',milestone):
            return dict(job_key=key,repeated=False,**result)
        # No repeated attempt on unchanged observations. Resource/data deferrals
        # can use a new own prefix; genuine parity/compile failures stay closed.
        folder=stage/('deferred_prefix_'+str(n));request=folder/'request.json'
        if request.exists():
            pid=json.loads((folder/'process.json').read_text())['pid'] if (folder/'process.json').exists() else None
            running=oracle_process_running(pid,script)
            result=oracle_job_status(folder,expected,running)
            if result['native_parity_verified']:once(stage/'verified_result.json',result)
            return dict(job_key=key,repeated=False,**result)
    if psutil.virtual_memory().available<512*1024*1024:return dict(status='WAITING_FOR_RESOURCES',job_key=key)
    for p in psutil.process_iter(['name','cmdline']):
        if p.info['name'] in ('pythonw.exe','python.exe') and str(script).lower() in ' '.join(p.info['cmdline'] or []).lower():
            return dict(status='EXISTING_OWN_ORACLE_JOB_ACTIVE')
    folder.mkdir(parents=True,exist_ok=True)
    once(request,dict(capture_id=status['capture_id'],epoch=status['epoch'],milestone=milestone,
                      own_seed_bar_hash=status['own_seed_bar_hash'],own_bars_at_dispatch=n,source_sha256=sha(script),training_executed=False))
    if folder!=stage:atomic(stage/'last_attempt.json',dict(folder=folder.name))
    with (folder/'stdout.json').open('w') as out,(folder/'stderr.log').open('w') as err:
        process=subprocess.Popen([str(root/'.venv/Scripts/pythonw.exe'),str(script)],cwd=root,
            stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    atomic(folder/'process.json',dict(pid=process.pid))
    return dict(status='STARTED_EXISTING_ISOLATED_NATIVE_ORACLE',job_key=key,milestone=milestone)


def _run_once(root=ROOT):
    root=Path(root);base=root/'outputs/us30cash_m5_native_observations'
    if not (base/'current.json').exists():return None
    pointer=json.loads((base/'current.json').read_text());folder=base/pointer['capture_id']
    calendar_path=root/'research/studies/us30cash_m5_native_observations/exclusive_cut_v1/native_calendar_observation.json'
    capacity=dict(status='MISSING_NATIVE_WEEKLY_METADATA',dataset_admitted=False)
    if calendar_path.exists():
        from controller.cf_session_calendar import parse_probe
        schedule=parse_probe(json.loads(calendar_path.read_text())['records'])
        capacity=dict(session_feasibility(schedule),source_sha256=sha(calendar_path))
    if folder.parent!=base or sha(folder/'manifest.json')!=pointer['manifest_sha256']:raise ValueError('MONITOR_MANIFEST_CHANGED')
    manifest=json.loads((folder/'manifest.json').read_text());roles=verify_roles(root,manifest)
    checkpoint=base/'quality_checkpoint.json'
    old=json.loads(checkpoint.read_text()) if checkpoint.exists() else {}
    monitor_source=sha(Path(__file__))
    if old.get('capture_id')!=pointer['capture_id'] or old.get('monitor_source_sha256')!=monitor_source:
        old=dict(capture_id=pointer['capture_id'],n=0,head=GENESIS)
    db=sqlite3.connect((folder/'snapshots.sqlite3').resolve().as_uri()+'?mode=ro',uri=True);db.execute('BEGIN')
    try:
        body,digest=db.execute('SELECT body,digest FROM state WHERE id=1').fetchone();state=json.loads(body)
        if seal(state)!=digest:raise ValueError('MONITOR_STATE_CHANGED')
        if old['n']:
            row=db.execute('SELECT digest FROM records WHERE n=?',(old['n']-1,)).fetchone()
            if not row or row[0]!=old['head']:raise ValueError('MONITOR_PREFIX_CHANGED')
        n=old['n'];head=old['head'];pending={};last=None;new_m5=0;excluded_queries=0
        seed_hash=old.get('epoch_seed_hash')
        parity_pass=old.get('m1_m5_pass',0);parity_fail=old.get('m1_m5_fail',0)
        for index,previous,current,body in db.execute('SELECT * FROM records WHERE n>=? ORDER BY n',(n,)):
            row=json.loads(body)
            if index!=n or previous!=head or seal(dict(previous=previous,payload=row))!=current:raise ValueError('MONITOR_CHAIN_CHANGED')
            if row.get('quarantine') is not True or row.get('admitted') is not False:raise ValueError('MONITOR_ADMISSION_SCOPE_CHANGED')
            n+=1;head=current;last=row
            if row['kind'] in ('NEW_OBSERVATION_EPOCH','OBSERVATION_INTERRUPTION'):
                excluded_queries+=sum(len(items) for items in pending.values());pending={}
                seed_hash=None
            if row['kind']=='CF_CONTEXT_EXCLUDED':seed_hash=None
            if row['kind']=='CF_M1_M5_PARITY':
                if row['matched']:parity_pass+=1
                else:parity_fail+=1
            if row['kind']=='DATABASE_QUERY_OBSERVATION':
                observation=row['observation'];key=(row['epoch'],row['frame_seconds'],observation['start_native_msc'],observation['end_native_exclusive_msc'])
                pending.setdefault(key,[]).append(row)
            if row['kind']=='DATABASE_SNAPSHOT_PAIR':
                key=(row['epoch'],row['frame_seconds'],row['start_native_msc'],row['end_native_exclusive_msc'])
                reads=pending.pop(key,[])
                if len(reads)!=2:raise ValueError('MONITOR_MISSING_DOUBLE_READ')
                one,two=[e['observation'] for e in reads]
                if one['tick_size']!=two['tick_size']:raise ValueError('MONITOR_GRID_CHANGED')
                error=one['query_error'] or two['query_error'] or ('ERROR' if 'QUERY_ERROR_OR_PARTIAL_READ' in row['assessment']['reasons'] else None)
                if assess(reads[0]['rows'],reads[1]['rows'],row['native_bar'],key[2],key[3],one['tick_size'],error)!=row['assessment']:raise ValueError('MONITOR_COVERAGE_CHANGED')
                if roles and key[2]<(roles['minimum_m1_open_msc'] if key[1]==60 else roles['minimum_native_open_msc']):raise ValueError('MONITOR_PRECUT_IMPORT')
                if key[1]==300:new_m5+=1
            if row['kind']=='CAUSAL_PREFIX_FEATURES':
                context={k:v for k,v in row.items() if k not in ('kind','feature_hash','quarantine','admitted')}
                if seal(context)!=row['feature_hash']:raise ValueError('MONITOR_FEATURE_HASH_CHANGED')
                if row['feature_cutoff_native_msc']>=row['decision_input_ref']['native_time_msc']:raise ValueError('MONITOR_NATIVE_LEAKAGE')
            if row['kind']=='CF_OFFLINE_AVAILABILITY':
                if seed_hash is None:seed_hash=row['native_bar_hash']
                ready,used=row['ready_clock'],row['offline_use_clock']
                if ready['boot_id']!=used['boot_id'] or ready['monotonic_ns']>used['monotonic_ns']:raise ValueError('MONITOR_PHYSICAL_OFFLINE_LEAKAGE')
        if last and (last['kind']!='CHECKPOINT' or last['state_hash']!=digest):raise ValueError('MONITOR_UNBOUND_CHECKPOINT')
        if pending:raise ValueError('MONITOR_UNPAIRED_READS')
    finally:db.close()
    status=json.loads((base/'status.json').read_text())
    if status['capture_id']!=pointer['capture_id']:raise ValueError('MONITOR_STATUS_CAPTURE_CHANGED')
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(status['clock']['host_utc_label'])).total_seconds()
    if age<0 or age>120:raise ValueError('MONITOR_STATUS_STALE_OR_FUTURE')
    context=state.get('cf_features',initial_state())
    seeds=seed_check(context,seed_hash)
    own_status=dict(status,technical_warmup=context.get('own_run_bars',0),BUY=context.get('signals_buy',0),
        SELL=context.get('signals_sell',0),consecutive_signals=context.get('after_warmup_signals',0),
        post_bars=context.get('post_signal_bars',0))
    value=dict(schema='cf-quality-monitor/1',observed_host_utc=datetime.now(timezone.utc).isoformat(),
        capture_id=pointer['capture_id'],records_verified=n,new_records_verified=n-old['n'],
        chain_head=head,checkpoint_hash=digest,epoch=state['epoch'],new_m5_pairs_checked=new_m5,
        status='PASS_INCREMENTAL_QUARANTINED',runtime_status=status['status'],
        real_m1=state['accepted']['60'],real_m5=state['accepted']['300'],rejected=state['rejected'],
        m5_with_five_m1_parity=parity_pass,m5_m1_m5_parity_exclusions=parity_fail,
        orphan_queries_excluded_on_explicit_interruption=excluded_queries,
        roles_verified=bool(roles),recursive_seeds=seeds,maturity=maturity(own_status),
        session_feasibility=capacity,
        retained_indicator_parity=retained_oracle(root) if (root/'research/studies/us30cash_m5_prospective_pipeline_20261031_v1/native_oracle.json').exists() else None,
        native_own_prefix_oracle=native_oracle_milestone(root,base,dict(own_status,epoch=state['epoch'],own_seed_bar_hash=seed_hash)),
        scientific_admission=False,physical_generation_utc_certified=False,training_executed=False)
    atomic(checkpoint,dict(capture_id=pointer['capture_id'],n=n,head=head,epoch_seed_hash=seed_hash,
        monitor_source_sha256=monitor_source,m1_m5_pass=parity_pass,m1_m5_fail=parity_fail))
    atomic(base/'quality_status.json',value)
    milestone=(pointer['capture_id'],state['epoch'],status['status'],
        next((x for x in (350,276,100,50,10,5,1) if status['technical_warmup']>=x),0),status['consecutive_signals']//100)
    milestone_path=base/'quality_milestones'/(seal(milestone)+'.json')
    if not milestone_path.exists():once(milestone_path,dict(milestone=milestone,evidence=value))
    return value


def run_once(root=ROOT):
    base=Path(root)/'outputs/us30cash_m5_native_observations'
    if not (base/'current.json').exists():return None
    try:
        with manager_lock(base/'quality_monitor_lock'):return _run_once(root)
    except RuntimeError as exc:
        if str(exc)!='CAPTURE_MANAGER_ALREADY_RUNNING':raise
        return dict(status='EXISTING_QUALITY_MONITOR_ACTIVE',training_executed=False)
    except Exception as exc:
        atomic(base/'quality_status.json',dict(status='FAIL_QUARANTINED',error=type(exc).__name__+':'+str(exc),
            observed_host_utc=datetime.now(timezone.utc).isoformat(),scientific_admission=False,training_executed=False))
        raise


if __name__=='__main__':print(json.dumps(run_once(),indent=2))
