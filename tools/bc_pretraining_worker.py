"""Existing B+C acquisition plus change-driven pre-admission. No fits/scoring."""
import argparse,json,sqlite3,subprocess,sys,time
from contextlib import closing
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import bc_study_station as station
from tools import bc_study_worker as ipc
from controller.authorized_capture import sha,once,manager_lock
from controller.isolated_observation import atomic,host_clock
from controller.pretrain_contracts import seal,canonical
from controller.bc_study import initial,advance,assessment,check_request
from controller.bc_admission import GATES,MINIMUMS,VERIFIED_CALENDAR_RECEIPTS,review,package_template
from controller.bc_training_rows import initial as label_initial,consume,validate_rows
from controller.native_study_design import fold_plan
from controller.git_runtime import command as git_command


def checkpoint():
    path=station.BASE/'ledger.sqlite3'
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        db.execute('BEGIN')
        row=db.execute('SELECT body,digest FROM checkpoint WHERE id=1').fetchone()
        state=json.loads(row[0]);last=json.loads(db.execute('SELECT body FROM artifacts ORDER BY n DESC LIMIT 1').fetchone()[0])
        if seal(state)!=row[1] or last.get('state_hash')!=row[1]:raise ValueError('BC_ADMISSION_CHECKPOINT_CHANGED')
    return state['bc']


def calendar_sources():
    registry=station.PACKAGE/'admission_evidence_registry.json'
    if not registry.exists():return [],None
    rows=json.loads(registry.read_bytes());proofs=[]
    for item in rows.get('calendar',[]):
        if item['sha256'] not in VERIFIED_CALENDAR_RECEIPTS:
            raise ValueError('BC_CALENDAR_CERTIFICATE_NOT_INDEPENDENTLY_VERIFIED')
        file=(station.PACKAGE/item['path']).resolve()
        if not file.is_relative_to(station.PACKAGE.resolve()) or file.is_symlink() or sha(file)!=item['sha256']:
            raise ValueError('BC_CALENDAR_REGISTERED_RECEIPT_CHANGED')
        proof=json.loads(file.read_bytes())
        if (proof.get('kind')!='BC_REVIEWED_XM_SERVER_CALENDAR' or proof.get('server')!='XMGlobalSC-MT5 5'
                or proof.get('symbol')!='US30Cash' or not proof.get('source_attestation')
                or proof.get('source_scope')!='SERVER_SPECIFIC_SCHEDULE_AND_DATED_EXCEPTIONS'
                or not proof.get('inputs')):raise ValueError('BC_CALENDAR_SOURCE_NOT_CERTIFIED')
        for name,digest in proof['inputs'].items():
            source=(station.PACKAGE/name).resolve()
            if not source.is_relative_to(station.PACKAGE.resolve()) or sha(source)!=digest:
                raise ValueError('BC_CALENDAR_SOURCE_CHANGED')
        proofs.append(dict(proof,receipt_sha256=item['sha256']))
    return proofs,sha(registry)


def closed_gap(proofs,start,end):
    return next((p['receipt_sha256'] for p in proofs if any(
        interval['start']<=start<end<=interval['end'] for interval in p.get('closed_native_intervals',[]))),None)


def _review_current(force=False):
    m=station.load_manifest();state=checkpoint();base=station.BASE;out=base/'pretraining_quarantine';out.mkdir(exist_ok=True)
    contract=station.PACKAGE/'contract.json';whitelist=station.PACKAGE/'feature_whitelist.json'
    entries=state['completed'];proofs=list((out/'proofs').glob('*.json'))+list(base.glob('parity_*.json'))
    calendars,calendar_registry_hash=calendar_sources()
    import psutil
    from tools.xm_recovered_context import ISOLATION
    isolated_executable=str(ISOLATION/'terminal/terminal64.exe').replace('\\','/').lower()
    resources=dict(memory_ready=psutil.virtual_memory().available>=512*1024**2,
        isolated_pids=[p.pid for p in psutil.process_iter(['exe']) if (p.info.get('exe') or '').replace('\\','/').lower()==isolated_executable],
        oracle_code_sha256=sha(ROOT/'tools/bc_prefix_oracle.py'))
    marker=seal(dict(completed=entries,floor=state['floor'],contract=sha(contract),
        proofs={p.name:sha(p) for p in proofs},calendar_registry_hash=calendar_registry_hash,resources=resources,code_head=subprocess.check_output(git_command('rev-parse','HEAD'),cwd=ROOT,text=True).strip(),code=[sha(ROOT/p) for p in (
            'controller/bc_admission.py','controller/bc_training_rows.py','tools/bc_pretraining_worker.py')]))
    previous=out/'status.json'
    if previous.exists() and not force:
        saved=json.loads(previous.read_bytes())
        if saved['input_marker']==marker:
            if 'review_hash' in saved:
                extras={'review_hash','input_marker','reevaluated','clock','market_status','dataset_hash_admitted','candidate_package_sha256'}
                if seal({k:v for k,v in saved.items() if k not in extras})!=saved['review_hash']:
                    raise ValueError('BC_CACHED_REVIEW_CHANGED')
            elif saved.get('status') not in ('FAIL','WAITING_FOR_EVIDENCE'):
                raise ValueError('BC_UNSEALED_CACHED_REVIEW')
            if 'candidate_package_sha256' in saved:
                packet=out/'future_authorization_package.json'
                frozen_packet=out/'versions'/marker/'future_authorization_package.json'
                expected=saved['candidate_package_sha256']
                if (not packet.is_file() or not frozen_packet.is_file()
                        or sha(packet)!=expected or sha(frozen_packet)!=expected):
                    raise ValueError('BC_CACHED_CANDIDATE_PACKAGE_CHANGED')
            return dict(saved,reevaluated=False)
    counts={k:0 for k in MINIMUMS};gates={k:dict(status='WAITING_FOR_EVIDENCE',witness_hashes=[]) for k in GATES}
    projection_folder=out/'versions'/marker
    once(projection_folder/'input_snapshot.json',dict(study_id=m['study_id'],dataset_id=m['dataset_id'],
        native_floor=state['floor'],manifest_versions=entries,input_marker=marker,
        frozen_before_labels=True,scientific_admission=False))
    activation_hash=sha(station.PACKAGE/'activation.json')
    for name in ('independence','exclusivity','provenance'):
        gates[name]=dict(status='PASS',witness_hashes=[activation_hash,sha(station.PACKAGE/'role_decision.json')],
            scope='EXCLUSIVE_APPROVED_NATIVE_ORDER_NO_PHYSICAL_UTC_GENERATION_CLAIM')
    context=initial();labels=label_initial();members=[];valid=[];signal_count=0;post=0;native_hashes=[];deadline=time.monotonic()+150
    try:
        for key,item in entries.items():
            path=(base/item['manifest']).resolve()
            if not path.is_relative_to(base.resolve()) or path.is_symlink() or sha(path)!=item['sha256']:
                raise ValueError('BC_MANIFEST_MEMBERSHIP_OR_HASH_CHANGED')
            vintage=json.loads(path.read_bytes());start=vintage['start'];end=vintage['end']
            if str(start)!=key or vintage['dataset_id']!=m['dataset_id'] or vintage['study_id']!=m['study_id']:
                raise ValueError('BC_WRONG_DATASET_MEMBERSHIP')
            check_request(start,end,state['floor'],vintage['observation']['quote']['time_msc'])
            if set(vintage['files'])!={'ticks.jsonl','m1.jsonl','m5.jsonl'}:raise ValueError('BC_RAW_FILES_INDEX_CHANGED')
            rows={}
            for filename,digest in vintage['files'].items():
                file=path.parent/filename
                if file.is_symlink() or sha(file)!=digest:raise ValueError('BC_PAYLOAD_HASH_CHANGED')
                rows[filename.split('.')[0]]=[json.loads(line) for line in file.read_bytes().splitlines()]
            checked=assessment(rows,start,end)
            if not checked['native_archive_parity'] or vintage['failures']:
                if not vintage['failures'] and not any(rows.values()) and closed_gap(calendars,start,end):continue
                context=initial();labels=label_initial();members=[];valid=[];signal_count=0;post=0;native_hashes=[];continue
            bar=rows['m5'][0]
            if valid and bar['time']!=valid[-1]['time']+300:
                bridge=closed_gap(calendars,(valid[-1]['time']+300)*1000,bar['time']*1000)
                if bridge:
                    # This projection explicitly carries recursive context across
                    # a registered closed interval. No native bar is moved or
                    # invented; the original producer and its counters stay intact.
                    context['last_bar']=None
                    members.append(dict(role='VERIFIED_CLOSED_SESSION_BRIDGE',proof_sha256=bridge,
                        native_start=(valid[-1]['time']+300)*1000,native_end=bar['time']*1000))
                else:context=initial();labels=label_initial();members=[];valid=[];signal_count=0;post=0;native_hashes=[]
            context,features=advance(context,bar,item['sha256']);index=len(valid);valid.append(bar);native_hashes.append(item['sha256'])
            members.append(dict(native_start=start,native_end=end,manifest_sha256=item['sha256'],role=features['role'],bar_hash=features['bar_hash']))
            new_signal=None
            if signal_count==800:post+=1
            elif features['signal_side']:
                signal_count+=1
                new_signal=dict(signal_id=seal(dict(bar=features['bar_hash'],side=features['signal_side'],features=features['feature_hash'])),
                    side=features['signal_side'],bar_index=index,features=features['values'],feature_max_native_msc=features['feature_max_native_msc'])
            # Labels are frozen baseline diagnostics on this new allowed TRAIN,
            # never model scoring. No protected data reader is used.
            consume(labels,index,rows['ticks'],new_signal)
            if time.monotonic()>deadline:raise RuntimeError('WAITING_FOR_RESOURCES_REVIEW_TIME_BOUND')
            if signal_count==800 and post==100:break
        complete=sorted(labels['rows'],key=lambda r:r['observed_bar_index'])
        if complete:validate_rows(complete)
        counts.update(context=min(350,len(valid)),signals=signal_count,post_bars=post,evaluable=len(complete),
            BUY=sum(r['side']=='BUY' for r in complete),SELL=sum(r['side']=='SELL' for r in complete))
        plan=None
        if len(complete)>=8:
            plan=fold_plan([{k:r[k] for k in ('signal_id','side','decision','arrival_index','follow_exit','invert_exit')} for r in complete])
            evaluation_ids=set(i for f in plan['folds'] for i in f['evaluation_ids'])
            evaluable=[r for r in complete if r['signal_id'] in evaluation_ids]
            counts.update(evaluable=len(evaluable),BUY=sum(r['side']=='BUY' for r in evaluable),SELL=sum(r['side']=='SELL' for r in evaluable))
            for side in ('BUY','SELL'):counts[side+'_folds']=sum(f['evaluation_sides'][side]>0 for f in plan['folds'])
        # Reuse the native isolated oracle only when a new eligible own prefix
        # appears. Failed identical attempts are recorded, not repeated forever.
        for milestone in (15,30,276,350):
            if len(valid)<milestone:continue
            target=out/'proofs'/(str(valid[0]['time'])+'_'+str(milestone)+'_'+seal(native_hashes[:milestone])[:12]+'.json')
            attempt=target.with_suffix('.attempt_'+seal(resources)[:12]+'.json')
            if target.exists() or attempt.exists():continue
            native_members=[x for x in members if 'manifest_sha256' in x]
            selected={str(x['native_start']):dict(path=entries[str(x['native_start'])]['manifest'],sha256=x['manifest_sha256']) for x in native_members[:milestone]}
            try:
                if any(x['role']=='VERIFIED_CLOSED_SESSION_BRIDGE' for x in members[:milestone]):
                    from tools.bc_prefix_oracle import compare
                    result=compare(ROOT,base,members,entries,milestone)
                else:
                    from tools.xm_recovered_context import compare
                    result=compare(ROOT,base,dict(completed=selected),[dict(key=key) for key in selected],bar_count=milestone)
            except Exception as exc:
                result=dict(status='FAILED_NATIVE_PREFIX_PROBE',error=type(exc).__name__+':'+str(exc))
            result['BC_new_dataset_only']=True
            once(target if result['status']=='PASS_RETROSPECTIVE_CONTEXT_DIAGNOSTIC' else attempt,result)
            if target.exists():proofs.append(target)
            break
        if valid:
            witness=seal(members)
            for name in ('membership','tick_coverage','OHLC','BID_ASK','historical_continuity','causality','features','no_leakage','hashes'):
                gates[name]=dict(status='PASS',witness_hashes=[witness,*native_hashes],scope='SELECTED_CONTIGUOUS_NATIVE_TRAIN_PREFIX_ONLY_NOT_GLOBAL_UTC_CERTIFICATION')
            gates['calendar']=dict(status='WAITING_FOR_EVIDENCE',witness_hashes=[],reason='CURRENT_TRANSITION_EXCEPTION_PROOF_REQUIRED; NUMERIC_ADJACENCY_ALONE_IS_NOT_CALENDAR_CERTIFICATION')
            if any(p.get('valid_from_native_msc',10**30)<=members[0]['native_start'] and p.get('valid_to_native_msc',-1)>=members[-1]['native_end'] for p in calendars):
                gates['calendar']=dict(status='PASS',witness_hashes=[p['receipt_sha256'] for p in calendars])
            if complete:gates['exit_horizons']=dict(status='PASS',witness_hashes=[seal(complete)],censored=len(labels['active'])+int(labels['pending'] is not None))
            if plan:
                by_id={r['signal_id']:r for r in complete}
                classes=all(len({int(by_id[i]['follow_pnl']>by_id[i]['invert_pnl'])
                    for i in fold['train_ids'] if by_id[i]['side']==side})==2
                    for fold in plan['folds'] for side in ('BUY','SELL'))
                enough=counts['BUY_folds']>=3 and counts['SELL_folds']>=3
                status='PASS' if enough and classes else 'FAIL' if signal_count==800 and post==100 else 'WAITING_FOR_DATA'
                gates['folds']=dict(status=status,witness_hashes=[seal(plan),seal(complete)],
                    eight_train_positions_have_both_classes=classes,reason='FIXED_SAMPLE_NO_RETUNING_OR_EXTENSION')
        import platform
        from importlib.metadata import version
        environment=dict(python=platform.python_version(),numpy=version('numpy'),**{'scikit-learn':version('scikit-learn')})
        gates['reproducibility']=dict(status='PASS',witness_hashes=[seal(environment),marker])
        # Only prefix-matched native receipts from this new dataset can support
        # seeds. Missing receipts remain pending; old B/C+F results never count.
        for proof in proofs:
            value=json.loads(proof.read_bytes())
            if (valid and value.get('status')=='PASS_RETROSPECTIVE_CONTEXT_DIAGNOSTIC'
                    and value.get('start_native')==valid[0]['time'] and value.get('BC_new_dataset_only') is True
                    and set(value.get('archive_parents',[]))<=set(native_hashes)):
                if value.get('bars',0)>=30:gates['ATR_seed']=dict(status='PASS',witness_hashes=[sha(proof)],scope='MATCHED_NEW_PREFIX_NATIVE_ORACLE')
                if value.get('ha_own_ready_276'):gates['HA_seed']=dict(status='PASS',witness_hashes=[sha(proof)],scope='MATCHED_NEW_PREFIX_NATIVE_ORACLE')
        result=review(counts,gates)
        bindings=dict(protocol_hash=sha(contract),feature_whitelist_hash=sha(whitelist),
            acceptance_criteria=json.loads(contract.read_bytes())['approved_proposal']['statistics'],
            code_head=subprocess.check_output(git_command('rev-parse','HEAD'),cwd=ROOT,text=True).strip(),environment=environment,
            dataset_hash=seal(complete) if complete else None,native_bounds=[members[0]['native_start'],members[-1]['native_end']] if members else None,
            membership_hash=seal(members) if members else None,exposure_hash=seal(dict(source=members,usage='FIXED_TECHNICAL_LABELS_NO_MODEL_SCORING')) if members else None,
            code_hash=seal({file:sha(ROOT/file) for file in (
                'controller/bc_training_rows.py','controller/bc_admission.py','controller/bc_study.py',
                'controller/native_study_runner.py','controller/training_admission_gate.py','tools/bc_pretraining_worker.py')}),
            plan_hash=seal(plan) if plan else None)
        packet=package_template(m,bindings,result)
        once(projection_folder/'future_authorization_package.json',packet)
        once(projection_folder/'membership.json',dict(intervals=members,sha256=seal(members),quarantine=True))
        once(projection_folder/'review.json',result)
        atomic(out/'future_authorization_package.json',packet)
        atomic(out/'membership.json',dict(intervals=members,sha256=seal(members),quarantine=True))
        # Never create an admitted namespace, change an allowlist or submit a
        # training request automatically. Candidate rows are private quarantine.
        if signal_count==800 and post==100:
            once(projection_folder/'candidate_rows.json',complete)
            atomic(out/'candidate_rows.json',complete)
        result.update(input_marker=marker,reevaluated=True,clock=host_clock(),
            market_status='WAITING_FOR_MARKET' if state['floor'] is None else 'NEW_NATIVE_INTERVAL_BOUND',
            dataset_hash_admitted=None,candidate_package_sha256=sha(out/'future_authorization_package.json'))
        atomic(previous,result);return result
    except Exception as exc:
        result=dict(status='WAITING_FOR_EVIDENCE' if isinstance(exc,RuntimeError) else 'FAIL',
            error=type(exc).__name__+':'+str(exc),input_marker=marker,clock=host_clock(),
            dataset_admitted=False,training_executed=False)
        atomic(previous,result);return result


def review_current(force=False):
    with manager_lock(station.BASE/'pretraining_review_lock'):
        return _review_current(force)


def run(budget=6):
    runtime_error=None
    try:runtime=ipc.run(budget)
    except Exception as exc:runtime=None;runtime_error=type(exc).__name__+':'+str(exc)
    # An IPC failure cannot prevent independent review of committed artifacts.
    try:admission=review_current()
    except Exception as exc:admission=dict(status='FAIL',error=type(exc).__name__+':'+str(exc))
    result=dict(clock=host_clock(),runtime=runtime,runtime_error=runtime_error,
        admission_status=admission['status'],TRAINING_EXECUTED=False,PROTECTED_SCORING=False,orders=0)
    atomic(station.BASE/'pretraining_worker_status.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--budget',type=int,default=6);parser.add_argument('--review-only',action='store_true');args=parser.parse_args()
    if not 1<=args.budget<=24:parser.error('budget must be 1..24')
    if args.review_only:print(json.dumps(review_current()))
    else:
        result=run(args.budget);print(json.dumps(result))
        if result['runtime_error']:sys.exit(1)
