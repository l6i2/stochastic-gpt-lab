"""Authorized separate B+C historical TRAIN acquisition. No fit/scoring/orders."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from controller.authorized_capture import sha,once,manager_lock,fresh_nts,bracket
from controller.isolated_observation import atomic,host_clock
from controller.pretrain_contracts import seal,canonical
from controller.prospective_processor import Ledger
from controller.bc_study import STUDY,FRAME,initial,native_floor,check_request,assessment,advance
from controller.xm_history_recovery import SERVER,SYMBOL,fetch,write_payload,verify_manifest
from tools.prospective_pipeline import NativeReference

BASE=ROOT/'outputs/bc_train_future_eval_v1'
PACKAGE=ROOT/'research/studies/bc_train_future_eval_v1'
OLD=ROOT/'outputs/us30cash_m5_native_observations'
PROPOSAL=ROOT/'research/studies/first_training_five_paths_20261108/proposal.json'
AUTH_SOURCE=Path('C:/Users/DELL 2022/.codex/attachments/6c2f2b0c-3d83-42f0-91b0-f8c60da4513b/Texto pegado.txt')
SOURCE_NAMES=('controller/bc_study.py','tools/bc_study_station.py','controller/cf_atr_candidate.py',
    'controller/xm_history_recovery.py','controller/prospective_processor.py','python/native_metadata_v3.py',
    'tools/xm_recovered_context.py','tools/cf_own_indicator_oracle.py')


def identity(ref):
    a=ref.mt5.account_info();t=ref.mt5.terminal_info();s=ref.mt5.symbol_info(SYMBOL)
    if (not a or a.trade_mode!=0 or a.server!=SERVER or not t or not t.connected
            or t.trade_allowed or Path(t.data_path).name!='20C285FE08971A9A2E814AAC44AFC9D2'
            or not s or s.custom or s.chart_mode!=0):
        raise RuntimeError('BC_WAITING_FOR_EXACT_CONNECTED_READONLY_XM')
    tick=ref.mt5.symbol_info_tick(SYMBOL)
    if not tick or not 0<tick.bid<=tick.ask:raise RuntimeError('BC_NATIVE_QUOTE_UNAVAILABLE')
    return dict(server=a.server,symbol=SYMBOL,terminal_data_folder_id=Path(t.data_path).name,
        tick_size=s.trade_tick_size,terminal_trade_allowed=False,account_mode='DEMO',
        quote={k:getattr(tick,k) for k in ('time','time_msc','bid','ask','flags')})


def load_manifest():
    pointer=json.loads((BASE/'current.json').read_bytes())
    path=PACKAGE/'activation.json'
    if sha(path)!=pointer['manifest_sha256']:raise ValueError('BC_ACTIVATION_CHANGED')
    m=json.loads(path.read_bytes())
    for p,h in m['source_hashes'].items():
        if sha(ROOT/p)!=h:raise ValueError('BC_SOURCE_PIN_CHANGED:'+p)
    if sha(PACKAGE/'authorization.json')!=m['authorization_sha256']:
        raise ValueError('BC_AUTHORIZATION_CHANGED')
    if sha(PACKAGE/'contract.json')!=m['contract_sha256']:
        raise ValueError('BC_APPROVED_CONTRACT_CHANGED')
    if json.loads((OLD/'enabled.json').read_bytes()).get('enabled') is not False:
        raise ValueError('BC_OLD_CF_INGRESS_NOT_CLOSED')
    return m


def activate():
    BASE.mkdir(parents=True,exist_ok=True);PACKAGE.mkdir(parents=True,exist_ok=True)
    with manager_lock(BASE):
        if (BASE/'current.json').exists():return load_manifest()
        source=AUTH_SOURCE.read_bytes();proposal=json.loads(PROPOSAL.read_bytes())
        if sha(ROOT/'controller/cf_atr_candidate.py')!=proposal['proposed_ATR_candidate_source_sha256']:
            raise ValueError('BC_APPROVED_ATR_VERSION_CHANGED')
        authorization=dict(schema='bc-authorization/1',study_id=STUDY,source_sha256=sha(AUTH_SOURCE),
            approved_proposal_sha256=sha(PROPOSAL),method_authorized=True,reservation_authorized=True,
            ATR_version_approved_subject_to_parity=True,training_authorized=False,evaluation_authorized=False,
            scoring_authorized=False,orders_authorized=False,live_trading=False,
            source_text=source.decode('utf-8-sig'))
        once(PACKAGE/'authorization.json',authorization)
        once(PACKAGE/'contract.json',dict(schema='bc-approved-method/1',approved_proposal=proposal,
            approved_proposal_sha256=sha(PROPOSAL),authority_sha256=sha(PACKAGE/'authorization.json'),
            method_active=True,ATR_candidate_approved_subject_to_tests=True,
            acquisition_roles_active=['TRAIN_CONTEXT','TRAIN_DEV'],evaluation_active=False,
            training_authorized=False,protected_scoring=False,
            acceptance_of_proposal_does_not_admit_data=True))
        # An immutable intent makes a crash during closure resumable, never a
        # reason to create a second cutoff or reopen old ingress.
        intent=PACKAGE/'closure_intent.json'
        if not intent.exists():
            once(intent,dict(authorization_sha256=sha(PACKAGE/'authorization.json'),clock=host_clock(),
                old_enabled_sha256=sha(OLD/'enabled.json'),scope='CLOSE_FUTURE_CF_US30CASH_PC_A_INGRESS_ONLY'))
        atomic(OLD/'enabled.json',dict(enabled=False,reason='AUTHORIZED_BC_FUTURE_SCOPE_CLOSURE',
            authority_sha256=sha(PACKAGE/'authorization.json')))
        # Acquire the existing producer lock only after its current poll has
        # committed and exited. Do not kill XM, the collector or Windows.
        import msvcrt
        lock=(OLD/'producer.lock').open('r+b');held=False
        try:
            for _ in range(45):
                lock.seek(0)
                try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);held=True;break
                except OSError:time.sleep(1)
            if not held:raise RuntimeError('BC_WAITING_FOR_OLD_CF_DURABLE_STOP')
            old_status=json.loads((OLD/'status.json').read_bytes())
            pointer=json.loads((OLD/'current.json').read_bytes())
            old_folder=OLD/pointer['capture_id']
            preserved={p.relative_to(ROOT).as_posix():sha(p) for p in [OLD/'current.json',old_folder/'manifest.json',old_folder/'checkpoint.json'] if p.exists()}
            ref=NativeReference()
            try:
                ref.connect();before_identity=identity(ref)
                before=fresh_nts();cut=host_clock();after=fresh_nts();utc=bracket(before,after,cut)
                after_identity=identity(ref)
                if before_identity['server']!=after_identity['server']:raise RuntimeError('BC_IDENTITY_CHANGED_DURING_CUT')
            finally:ref.close()
            epoch='bc_epoch_'+uuid.uuid4().hex
            m=dict(schema='bc-activation/1',study_id=STUDY,dataset_id='bc_train_'+uuid.uuid4().hex,
                producer_id='bc_history_'+uuid.uuid4().hex,epoch=epoch,clock=cut,activation_utc=utc,
                native_floor=None,native_floor_rule='FIRST_NEW_NATIVE_QUOTE_AFTER_CUT_THEN_NEXT_M5_OPEN',
                cut_anchor=after_identity,old_cf_last_status=old_status,old_immutable_hashes=preserved,
                authorization_sha256=sha(PACKAGE/'authorization.json'),proposal_sha256=sha(PROPOSAL),
                contract_sha256=sha(PACKAGE/'contract.json'),
                source_hashes={p:sha(ROOT/p) for p in SOURCE_NAMES},
                roles=['TRAIN_CONTEXT','TRAIN_DEV'],eval_roles='INACTIVE_UNTIL_MODEL_FREEZE_AND_SEPARATE_AUTHORIZATION',
                old_B_reassigned=False,old_CF_contract_modified=False,old_datasets_modified=False,
                training_authorized=False,scoring_authorized=False,LIVE_TRADING=False,terminal_trade_allowed=False)
            once(PACKAGE/'activation_clock_evidence.json',dict(before=before,cut=cut,after=after,utc=utc))
            once(PACKAGE/'activation.json',m)
            decision=dict(schema='bc-forward-role-decision/1',study_id=STUDY,epoch=epoch,clock=cut,utc=utc,
                previous_roles='CF_NEW_INGRESS_CLOSED_OLD_DATA_RIGHTS_PRESERVED',
                future_roles='BC_EXCLUSIVE_TRAIN_CONTEXT_THEN_TRAIN_DEV',
                native_floor_pending=True,retroactive_reassignment=False,activation_sha256=sha(PACKAGE/'activation.json'))
            once(PACKAGE/'role_decision.json',dict(payload=decision,sha256=seal(decision)))
            once(OLD/'bc_ingress_closed.json',dict(activation_sha256=sha(PACKAGE/'activation.json'),
                clock=cut,old_chain_head=old_status['chain_head'],old_records=old_status['ledger_records'],
                data_preserved=True,new_ingress_only=True))
            once(BASE/'current.json',dict(manifest_sha256=sha(PACKAGE/'activation.json'),epoch=epoch))
            atomic(BASE/'enabled.json',dict(enabled=True))
            return m
        finally:
            if held:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
            lock.close()


def archive(ref,folder,start,end,previous,manifest,observation):
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/'manifest.json'
    if path.exists():return verify_manifest(folder)
    once(folder/'intent.json',dict(start=start,end=end,previous=previous,activation_sha256=sha(PACKAGE/'activation.json')))
    rows={};sources={};failures={};clock=host_clock()
    for kind in ('m1','m5','ticks'):
        identity(ref)
        try:rows[kind],sources[kind]=fetch(ref.mt5,kind,start,end)
        except (RuntimeError,ValueError) as exc:rows[kind]=[];failures[kind]=str(exc)
    assessed=assessment(rows,start,end)
    files={}
    for kind,items in rows.items():
        file=folder/(kind+'.jsonl')
        # A crashed partial attempt is never overwritten. Its caller will choose
        # a new attempt folder; only a complete manifest is adoptable.
        files[file.name]=write_payload(file,items)
    body=dict(schema='bc-native-history-vintage/1',start=start,end=end,previous=previous,
        study_id=STUDY,dataset_id=manifest['dataset_id'],producer_id=manifest['producer_id'],
        server=SERVER,symbol=SYMBOL,origin='NATIVE_XM_RETROSPECTIVE_TRAIN_CANDIDATE',
        first_retrieval_clock=clock,completed_clock=host_clock(),observation=observation,
        original_live_receipt_proven=False,files=files,sources=sources,failures=failures,
        assessment=assessed,quarantine=True,scientific_admission=False)
    once(path,body);return body


def run(budget=6):
    import psutil
    with manager_lock(BASE):
        m=load_manifest();ledger=Ledger(BASE/'ledger.sqlite3');ref=NativeReference()
        try:
            s=ledger.state.setdefault('bc',initial());now=host_clock()
            previous=s['last_runtime']
            if previous and (previous['boot_id']!=now['boot_id'] or now['monotonic_ns']<previous['monotonic_ns'] or now['host_utc_label']<previous['host_utc_label']):
                ledger.emit('BC_CLOCK_OR_RESTART_INCIDENT',dict(previous=previous,current=now,
                    cause='BOOT_CHANGED' if previous['boot_id']!=now['boot_id'] else 'CLOCK_DISCONTINUITY',
                    historical_native_continuity_not_assumed=True,context_not_reset_solely_for_process_restart=True))
            ledger.emit('BC_EXECUTION',dict(clock=now,previous=s['last_runtime'],
                historical_recovery_allowed=True,live_receipt_claimed=False))
            s['last_runtime']=now
            ref.connect();ident=identity(ref);quote=ident['quote']
            if s['floor'] is None:
                floor=native_floor(m['cut_anchor']['quote'],quote)
                if floor is not None:
                    s['floor']=s['cursor']=floor
                    ledger.emit('BC_NATIVE_FLOOR_BOUND',dict(floor=floor,first_fresh_quote=quote,
                        observation_clock=host_clock(),scope='AFTER_NEW_OBSERVATION_NEXT_NATIVE_M5_NOT_UTC_GENERATION'))
            processed=0
            maximum=quote['time_msc']//FRAME*FRAME
            # Retry at most one failed historical vintage per invocation, after
            # 15 minutes or a reboot. Never rewrite its files. A repaired older
            # interval requires a new derived revision, not a silent splice.
            for stamp,item in list(s['completed'].items()):
                if not item.get('partial'):continue
                old=item['retry_clock']
                if old['boot_id']==now['boot_id'] and now['uptime_ms']-old['uptime_ms']<900000:continue
                if item.get('attempts',1)>=3 and item.get('native_marker')==maximum:continue
                start=int(stamp);check_request(start,start+FRAME,s['floor'],quote['time_msc'])
                directory=BASE/'raw'/stamp;attempts=list(directory.glob('attempt_*'))
                folder=directory/('attempt_'+str(len(attempts)+1).zfill(4))
                revised=archive(ref,folder,start,start+FRAME,ledger.head,m,dict(clock=now,quote=quote))
                new_hash=sha(folder/'manifest.json')
                ledger.emit('BC_NEW_RETRIEVAL_VINTAGE',dict(start=start,old_manifest_sha256=item['sha256'],new_manifest_sha256=new_hash))
                good=not revised['failures'] and revised['assessment']['native_archive_parity']
                item.update(manifest=folder.relative_to(BASE).as_posix()+'/manifest.json',sha256=new_hash,
                    partial=not good,retry_clock=now,attempts=item.get('attempts',1)+1,native_marker=maximum)
                if good:
                    preserved=dict(floor=s['floor'],completed=s['completed'],last_runtime=now,epoch=s['epoch']+1)
                    s.clear();s.update(initial());s.update(preserved);s['cursor']=s['floor']
                    ledger.emit('BC_DERIVED_REVISION_REPLAY',dict(reason='AUTHORIZED_HISTORICAL_VINTAGE_REPAIR',
                        original_artifacts_preserved=True,epoch=s['epoch'],prospective_backfill=False))
                ledger.commit();break
            while s['floor'] is not None and s['cursor']+FRAME<=maximum and processed<budget and not s['acquisition_complete']:
                if psutil.virtual_memory().available<384*1024**2 or psutil.disk_usage(str(BASE)).free<2*1024**3:
                    raise RuntimeError('BC_WAITING_FOR_RESOURCE_MARGIN')
                start=s['cursor'];end=start+FRAME;check_request(start,end,s['floor'],quote['time_msc'])
                directory=BASE/'raw'/str(start)
                # A full orphan manifest is adopted at the same cursor after a
                # crash. Incomplete attempts remain intact and get a new vintage.
                attempts=sorted(directory.glob('attempt_*')) if directory.exists() else []
                complete=[p for p in attempts if (p/'manifest.json').exists()]
                saved=s['completed'].get(str(start))
                folder=BASE/saved['manifest'] if saved else None
                folder=folder.parent if folder else complete[-1] if complete else directory/('attempt_'+str(len(attempts)+1).zfill(4))
                if saved and sha(folder/'manifest.json')!=saved['sha256']:raise ValueError('BC_COMMITTED_VINTAGE_CHANGED')
                vintage=archive(ref,folder,start,end,ledger.head,m,dict(clock=host_clock(),quote=quote))
                if (vintage['start']!=start or vintage['end']!=end or vintage['dataset_id']!=m['dataset_id']
                        or vintage['study_id']!=STUDY or vintage['server']!=SERVER or vintage['symbol']!=SYMBOL):
                    raise ValueError('BC_ARCHIVE_IDENTITY_OR_INTERVAL_CHANGED')
                mh=sha(folder/'manifest.json');s['completed'][str(start)]=saved or dict(
                    manifest=folder.relative_to(BASE).as_posix()+'/manifest.json',sha256=mh,
                    partial=bool(vintage['failures']) or not vintage['assessment']['native_archive_parity'],
                    retry_clock=now,attempts=1,native_marker=maximum)
                ledger.emit('BC_ARCHIVE_MEMBERSHIP',dict(start=start,end=end,manifest_sha256=mh,
                    role='TRAIN_CONTEXT' if s['run_bars']<350 else 'TRAIN_DEV',origin=vintage['origin'],
                    exposure='ACQUISITION_AND_TECHNICAL_VALIDATION_ONLY_NO_LABELS_NO_SCORING'))
                if not vintage['failures'] and vintage['assessment']['native_archive_parity']:
                    bar=json.loads((folder/'m5.jsonl').read_bytes().splitlines()[0])
                    new,artifact=advance(s,bar,mh);s.clear();s.update(new)
                    ledger.emit('BC_CAUSAL_NATIVE_FEATURES',{k:v for k,v in artifact.items() if k!='quarantine'})
                else:
                    s['rejected']+=1
                    ledger.emit('BC_UNVERIFIED_INTERVAL',dict(start=start,end=end,manifest_sha256=mh,
                        causes=vintage['failures'],quality=vintage['assessment'],calendar='PARTIAL_NO_ASSUMED_EXCEPTION'))
                s['cursor']=end;processed+=1;ledger.commit()
            ledger.commit()
            for milestone in (15,30,276,350):
                receipt=BASE/('parity_'+str(milestone)+'.json')
                if s['run_bars']<milestone or receipt.exists():continue
                from tools.xm_recovered_context import compare
                selected={key:dict(path=item['manifest'],sha256=item['sha256']) for key,item in s['completed'].items()}
                result=compare(ROOT,BASE,dict(completed=selected),[dict(key=key) for key in selected],bar_count=milestone)
                result['BC_new_dataset_only']=True
                if result['status']=='PASS_RETROSPECTIVE_CONTEXT_DIAGNOSTIC':once(receipt,result)
                else:atomic(BASE/'parity_pending.json',dict(milestone=milestone,result=result))
                break  # One native oracle per invocation; no repeated PASS probes.
            report=dict(schema='bc-runtime-status/1',study_id=STUDY,dataset_id=m['dataset_id'],epoch=m['epoch'],
                status='WAITING_FIRST_NEW_NATIVE_QUOTE' if s['floor'] is None else 'ACQUISITION_COMPLETE_QUARANTINED' if s['acquisition_complete'] else 'ACTIVE_HISTORICAL_TRAIN_QUARANTINED',
                clock=host_clock(),identity=ident,native_floor=s['floor'],next_interval=s['cursor'],
                processed_this_run=processed,intervals=len(s['completed']),M5_verified=s['total_m5'],
                M5_current_consecutive=s['run_bars'],M5_rejected=s['rejected'],
                warmup=min(350,s['run_bars']),BUY=s['BUY'],SELL=s['SELL'],signals=s['base_signals'],post_bars=s['post_bars'],
                evaluable=0,fold_support='PENDING_COMPLETE_LABEL_HORIZONS_AND_ADMISSION',
                seeds='APPROVED_VARIANT_PARITY_ON_NEW_CONTEXT_PENDING',calendar='PARTIAL_NO_UNPROVEN_BRIDGE',
                causal_audit='NOT_ADMITTED_GLOBAL_FAIL_UNCHANGED',dataset_admitted=False,dataset_hash=None,
                training_readiness='BLOCKED_NO_ADMITTED_DATASET_OR_SPECIFIC_GRANT',training_executed=False,
                scoring_executed=False,orders_sent=0,DEMO='DISABLED',LIVE_TRADING=False,terminal_trade_allowed=False,
                chain_head=ledger.head,ledger_records=ledger.count,old_ingress_closed=True,
                process_rss_bytes=psutil.Process().memory_info().rss)
            atomic(BASE/'status.json',report);return report
        finally:
            ref.close();ledger.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--activate',action='store_true');parser.add_argument('--budget',type=int,default=6)
    args=parser.parse_args()
    if not 1<=args.budget<=24:parser.error('budget must be 1..24')
    try:
        result=activate() if args.activate else run(args.budget)
        print(json.dumps(result,indent=2))
    except Exception as exc:
        failure=dict(clock=host_clock(),error=type(exc).__name__+':'+str(exc),
            retry_safe=True,training_executed=False,LIVE_TRADING=False)
        once(BASE/'incidents'/('failure_'+uuid.uuid4().hex+'.json'),failure)
        atomic(BASE/'runtime_failure.json',failure)
        raise
