"""Consolidate existing evidence only. Never dispatch training or query history."""
import json,sys,hashlib,re
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from controller.isolated_observation import atomic
from controller.pretrain_contracts import seal,verify_chain
from controller.training_admission_gate import snapshot_gate

def code_head(root):
    # Scheduled GUI processes may have no git executable on PATH.
    git=root/'.git'
    if git.is_file():git=(root/git.read_text().strip().removeprefix('gitdir: ')).resolve()
    head=(git/'HEAD').read_text().strip()
    if head.startswith('ref: '):
        ref=head[5:]
        if not ref.startswith('refs/') or '..' in ref.split('/'):raise ValueError('INVALID_GIT_REF')
        common=(git/(git/'commondir').read_text().strip()).resolve() if (git/'commondir').exists() else git
        if (common/ref).exists():head=(common/ref).read_text().strip()
        else:
            matches=[line.split()[0] for line in (common/'packed-refs').read_text().splitlines() if line.endswith(' '+ref)]
            if len(matches)!=1:raise ValueError('UNRESOLVED_GIT_HEAD')
            head=matches[0]
    if not re.fullmatch('[0-9a-f]{40}',head):raise ValueError('INVALID_GIT_HEAD')
    return head

def review_state(gate,errors):
    # Presentation of the existing authority, never a second authorization path.
    if errors or 'REAL_OR_UNKNOWN_ACCOUNT_HARD_FAIL' in gate.get('reasons',[]):return 'FAIL'
    if gate.get('execution_permitted') and gate.get('package_complete'):return 'PASS'
    if gate.get('authorization_request_ready') and gate.get('package_complete'):return 'WAITING_FOR_AUTHORIZATION'
    return 'WAITING_FOR_DATA'

def build(root=ROOT):
    root=Path(root);now=datetime.now(timezone.utc);receipts={};errors=[]
    def read(relative):
        p=root/relative;b=p.read_bytes();v=json.loads(b.decode('utf-8-sig'))
        receipts[relative]=hashlib.sha256(b).hexdigest();return v
    def fresh(label,clock,limit):
        age=(now-datetime.fromisoformat(clock)).total_seconds()
        if age<0 or age>limit:errors.append(label+'_STALE_OR_FUTURE')
        return age
    package='research/studies/us30cash_m5_native_pretrain_v1/'
    index=read(package+'package_hashes.json')
    if seal(index['files'])!=index['root_sha256']:raise ValueError('PACKAGE_INDEX_CHANGED')
    for name,digest in index['files'].items():
        if Path(name).name!=name or hashlib.sha256((root/package/name).read_bytes()).hexdigest()!=digest:raise ValueError('FROZEN_PACKAGE_CHANGED')
    exposure=read(package+'exposure_ledger.json');verify_chain(exposure['entries'],exposure['chain_head'])
    pointer=read('outputs/new_native_studies/us30cash_m5_native_20261030_01/current_capture.json')
    capture=pointer.get('capture_id') or pointer.get('id')
    if not capture or Path(capture).name!=capture:raise ValueError('UNSAFE_CAPTURE_ID')
    rawbase='outputs/new_native_studies/us30cash_m5_native_20261030_01/'+capture+'/'
    raw=read(rawbase+'collector_status.json');manifest=read(rawbase+'collection_manifest.json')
    m=read('outputs/prospective_derivatives_v1/'+capture+'/maturity.json')
    if [m[k] for k in ('warmup_required','signals_required','post_signal_bars_required','evaluable_required','evaluable_required_each_side')]!=[350,800,100,200,80]:raise ValueError('FROZEN_THRESHOLDS_CHANGED')
    fresh('WORKER',m['observed_clock']['host_utc_label'],120)
    recovery=read('outputs/pc_a_stability/recovery_status.json');fresh('GUARDIAN',recovery['host_utc'],120)
    broker=read('outputs/research_readiness/broker_identity.json')
    gate=snapshot_gate(m,broker,root=root)
    if 'REAL_OR_UNKNOWN_ACCOUNT_HARD_FAIL' in gate['reasons']:errors.append('IDENTITY_UNVERIFIED')
    # This reporting command cannot dispatch even a future valid grant.
    if (root/'configs/scientific_training_grant.json').exists():
        gate=snapshot_gate(m,broker,grant=read('configs/scientific_training_grant.json'),root=root)
    nbase='outputs/native_database_snapshots_v1/'
    n=read(nbase+'current.json');sid=n.get('capture_id') or n.get('id')
    if not sid or Path(sid).name!=sid:raise ValueError('UNSAFE_SNAPSHOT_ID')
    snapshot=read(nbase+sid+'/status.json');fresh('SNAPSHOT',snapshot['clock']['host_utc_label'],120)
    ntsbase='outputs/pc_a_prospective_utc/authenticated_utc/'
    nts=read(ntsbase+'state.json');record=nts['last_record']
    if Path(record).name!=record:raise ValueError('UNSAFE_NTS_RECORD')
    read(ntsbase+record)
    from controller.isolated_observation import host_clock
    clock=host_clock()
    if nts.get('failures',0):errors.append('NTS_SERVICE_FAILURES')
    # Scheduling health only: this 120s grace is not a temporal-certification tolerance.
    if nts['boot_identity']!='WINDOWS_PREFETCH_BOOT_ID:'+clock['boot_id'] or clock['uptime_ms']>nts['next_due_uptime_ms']+120000:errors.append('NTS_MEASUREMENT_OVERDUE_OR_BOOT_CHANGED')
    if raw['status']!='ACTIVE_QUARANTINED':errors.append('RAW_SOURCE_NOT_ACTIVE')
    if snapshot['status']!='ACTIVE_QUARANTINED':errors.append('SNAPSHOT_NOT_ACTIVE')
    historical=read('research/studies/maxbars_history_20261102_v1/summary.json')
    from controller.warmup_diagnostics import inspect
    warmup_receipt=inspect(root/'outputs/prospective_derivatives_v1'/capture/'quarantine.sqlite3')
    result=dict(schema='autonomous-research-status/1',observed_ecuador=now.astimezone(ZoneInfo('America/Guayaquil')).isoformat(),
        code_head=code_head(root),
        historical_diagnostic=historical['HISTORICAL_COVERAGE'],historical_parity=historical['MT5_BACKTEST_PARITY'],
        demonstrated_independent_admitted_periods=[],dataset_id='us30cash_m5_native_new_01_reserved',dataset_id_is_reservation=True,dataset_hash=m['dataset_hash'],
        capture_id=capture,capture_activation=manifest['activation_utc'],raw_ticks=raw['totals']['tick_callbacks'],
        raw_heartbeats=raw['totals']['heartbeat_records'],raw_status=raw['status'],
        observed_m1=m['m1_aggregate_bars'],observed_m5=m['m5_aggregate_bars'],warmup_current=m['warmup_current_own_run'],warmup_required=350,
        BUY_SIGNALS=m['diagnostic_buy_signals'],SELL_SIGNALS=m['diagnostic_sell_signals'],consecutive_signals=m['diagnostic_first_signals_progress'],signals_required=800,
        post_signal_bars=m['diagnostic_post_signal_bars'],post_required=100,evaluable_total=m['evaluable_total'],evaluable_required=200,
        evaluable_BUY=m['evaluable_buy'],evaluable_SELL=m['evaluable_sell'],required_each_side=80,
        admitted_records=m['admitted_records'],coverage=m['coverage_rule'],rejected_buckets_all_timeframes=m['rejected_buckets'],
        membership=m['membership'],exposure_missing=exposure['missing'],exposure_chain_verified=True,
        feature_status=m['native_indicators_parity'],causal_audit=m['causal_audit'],dataset_maturity=m['dataset_maturity'],
        warmup_counter_receipt=warmup_receipt,
        warmup_producer_authority='ORIGINAL_POST_ACTIVATION_CALLBACKS_ONLY_SUBJECT_TO_FROZEN_COVERAGE; SNAPSHOT_TRIAL_NOT_ADMITTED',
        snapshot_trial=snapshot,nts_state=nts,nts_latest_record_hash=receipts[ntsbase+record],
        nts_scope='AUTHENTICATION_VERIFIED_BY_EXISTING_NTS_SERVICE_NOT_RECHECKED_BY_THIS_METADATA_REPORT',
        gate_authority=gate,TRAINING_ADMISSION_GATE=review_state(gate,errors),TRAINING_READINESS='BLOCKED' if not gate['execution_permitted'] or errors else 'AUTHORIZED_NOT_EXECUTED_BY_REPORTER',
        TRAINING_EXECUTED=False,report_health_errors=errors,
        remaining_blockers=['EXACT_CALLBACK_COVERAGE_AND_OWN_RECURSIVE_SEEDS','350_OWN_M5_THEN_800_SIGNALS_AND_100_POST_BARS','200_EVALUABLE_80_EACH_SIDE_3_FOLDS_EACH',
            'COMPLETE_COMPARABLE_MEMBERSHIP_AND_APPLICABLE_CAUSALITY','NO_AUTHORIZATION_TO_ADMIT_DATABASE_SNAPSHOT_TRIAL','SEALED_DATASET_AND_SPECIFIC_TRAINING_GRANT'],
        non_data_blockers=['SNAPSHOT_METHOD_ADMISSION_NOT_AUTHORIZED','UNKNOWN_LEGACY_MEMBERSHIP_NOT_RESOLVED_BY_MORE_TICKS','EXPLICIT_SCIENTIFIC_GRANT_REQUIRED'],
        next_automatic_action='EXISTING_CAPTURE_WORKER_NTS_SNAPSHOT_MONITOR_CONTINUE_NO_BACKFILL',manual_action_required=False,
        protected_sets=dict(DISCOVERY_VALIDATION='BLOCKED',HISTORICAL_HOLDOUT='LOCKED',FINAL_TEST='LOCKED'),DEMO='DISABLED',LIVE_TRADING=False,
        receipts=receipts,report_does_not_train=True,old_window_queries=0)
    return result

def main():
    target=ROOT/'outputs/status/AUTONOMOUS_RESEARCH_STATUS.json'
    try:value=build()
    except Exception as e:
        value=dict(TRAINING_ADMISSION_GATE='FAIL',TRAINING_READINESS='BLOCKED',TRAINING_EXECUTED=False,error=type(e).__name__+':'+str(e),LIVE_TRADING=False)
    atomic(target,value);print(json.dumps(value,ensure_ascii=False,indent=2))
    return int(value['TRAINING_ADMISSION_GATE']=='FAIL')

if __name__=='__main__':raise SystemExit(main())
