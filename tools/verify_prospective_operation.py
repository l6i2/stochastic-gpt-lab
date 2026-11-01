"""Read-only operational evidence from real raw/derived artifacts, not fixtures."""
import argparse,json,sqlite3,sys,time
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from controller.authorized_capture import CaptureManager,sha
from controller.isolated_observation import host_clock,GENESIS
from controller.pretrain_contracts import seal
from tools.prospective_pipeline import BASE,NativeReference,verify_code_pin


def worker_processes(worker_pid):
    import psutil
    path=str(ROOT/'tools/prospective_pipeline.py');records=[]
    for p in psutil.process_iter(['name','cmdline','memory_info']):
        try:
            if p.info['name']!='pythonw.exe' or path not in (p.info['cmdline'] or []):continue
            mem=p.info['memory_info'];records.append(dict(pid=p.pid,parent_pid=p.ppid(),role='PROCESSING_WORKER' if p.pid==worker_pid else 'VENV_LAUNCHER_OR_UNEXPECTED',working_mb=round(mem.rss/1048576,2),private_mb=round(getattr(mem,'private',mem.vms)/1048576,2),cpu_seconds=p.cpu_times().user+p.cpu_times().system))
        except (psutil.NoSuchProcess,psutil.AccessDenied):continue
    owners=[r for r in records if r['pid']==worker_pid]
    expected={worker_pid}
    if owners:expected.add(owners[0]['parent_pid'])
    for record in records:
        if record['pid']!=worker_pid and record['pid'] in expected:record['role']='VENV_LAUNCHER'
    return dict(processes=records,processing_workers=len(owners),unexpected_processes=sum(r['pid'] not in expected for r in records))


def native_cache():
    ref=NativeReference()
    try:
        ref.connect();terminal=ref.mt5.terminal_info();tick=ref.mt5.symbol_info_tick('US30Cash')
        return dict(status='ATTACHED_PINNED_XM_INSTANCE_READ_ONLY',connected=bool(terminal.connected),cached_quote_native_msc=int(tick.time_msc) if tick else None,cached_quote_present=tick is not None,cached_quote_not_adopted_as_prospective=True,identity_verified=True)
    except (ValueError,OSError) as exc:return dict(status='UNAVAILABLE',reason=str(exc),connected=None,cached_quote_not_adopted_as_prospective=True)
    finally:ref.close()


def sample():
    manager=CaptureManager();manager.load();raw=json.loads((manager.root/'collector_status.json').read_text())
    derived=json.loads((BASE/manager.root.name/'maturity.json').read_text())
    clock=host_clock()
    return dict(clock=clock,capture_id=manager.root.name,raw=raw,derived=derived,worker=worker_processes(derived['process_id']),native_cache=native_cache())


def compare_samples(first,last):
    if first['capture_id']!=last['capture_id']:raise ValueError('CAPTURE_ID_CHANGED_DURING_AUDIT')
    same_boot=first['clock']['boot_id']==last['clock']['boot_id']
    elapsed=(last['clock']['monotonic_ns']-first['clock']['monotonic_ns'])/1e9 if same_boot else None
    callbacks=last['raw']['totals']['source_records']-first['raw']['totals']['source_records']
    ticks=last['raw']['totals']['tick_callbacks']-first['raw']['totals']['tick_callbacks']
    consumed=last['derived']['raw_records_processed']-first['derived']['raw_records_processed']
    if min(callbacks,ticks,consumed)<0:raise ValueError('REAL_COUNTER_REGRESSION')
    live=callbacks>0 and consumed>0 and last['worker']['processing_workers']==1 and last['worker']['unexpected_processes']==0
    connections=[s['native_cache']['connected'] for s in (first,last)]
    if ticks>0:reason='REAL_QUOTE_CALLBACKS_ADVANCED_CHECK_DERIVED_EVIDENCE'
    elif any(c is False for c in connections):reason='NO_NEW_TICKS_WITH_BROKER_DISCONNECTION_OBSERVED'
    else:reason='NO_NEW_TICKS_MARKET_OR_BROKER_FEED_AVAILABILITY_NOT_CERTIFIED'
    cpu=None
    a={p['pid']:p for p in first['worker']['processes']};b={p['pid']:p for p in last['worker']['processes']}
    pid=last['derived']['process_id']
    if elapsed and elapsed>0 and pid in a and pid in b:cpu=max(0,100*(b[pid]['cpu_seconds']-a[pid]['cpu_seconds'])/elapsed)
    return dict(sample_elapsed_monotonic_seconds=elapsed,real_callback_delta=callbacks,real_tick_delta=ticks,worker_consumed_delta=consumed,observed_heartbeat_ingestion='PASS_REAL_RECORD_PROGRESS' if live else 'NOT_DEMONSTRATED',end_to_end_market_pipeline='NOT_DEMONSTRATED_NO_MARKET_TICK_PROGRESS' if ticks==0 else 'REQUIRES_REAL_BAR_FEATURE_SIGNAL_EVIDENCE',immediate_cause=reason,terminal_connections=connections,worker_cpu_one_core_average_percent=cpu,cached_quote_unchanged=first['native_cache'].get('cached_quote_native_msc')==last['native_cache'].get('cached_quote_native_msc'),market_closed_certified=False,scientific_admission=False)


def verify_ledgers():
    from controller.dataset_maturity import audit_segment
    manager=CaptureManager();manager.load();folder=BASE/manager.root.name
    db=sqlite3.connect('file:'+str((folder/'quarantine.sqlite3').as_posix())+'?mode=ro',uri=True);db.execute('BEGIN')
    head=GENESIS;rows=0;counts=Counter();comparisons={};bar_counts=Counter();rejected=Counter();old_head=json.loads((BASE/'upgrade_latest.json').read_text())['before']['derived_head'];old_prefix=False
    native_feature_checks=0
    for n,previous,digest,text in db.execute('SELECT n,previous,digest,body FROM artifacts ORDER BY n'):
        body=json.loads(text)
        if n!=rows or previous!=head or seal(dict(previous=previous,payload=body))!=digest:raise ValueError('DERIVED_LEDGER_INTEGRITY_FAILED')
        head=digest;rows+=1;counts[body['kind']]+=1;old_prefix|=head==old_head
        if body['kind']=='BAR_COMPARISON':comparisons[body['evidence_hash']]=body['bucket']['timeframe_seconds']
        if body['kind']=='CLOSED_AGGREGATE_BAR':bar_counts[str(comparisons[body['bar']['evidence_hash']])]+=1
        if body['kind']=='INCOMPLETE_BUCKET':rejected[str(body['observed_bucket']['timeframe_seconds'])]+=1
        if body['kind']=='CAUSAL_PREFIX_FEATURES':
            if body['feature_cutoff_native_msc']>=body['decision_input_ref']['native_time_msc'] or body['ready_stage']>=body['decision_stage']:raise ValueError('DERIVED_FEATURE_FUTURE_OR_STAGE_VIOLATION')
            native_feature_checks+=1
    text,digest=db.execute('SELECT body,digest FROM checkpoint WHERE id=1').fetchone();state=json.loads(text)
    last=json.loads(db.execute('SELECT body FROM artifacts ORDER BY n DESC LIMIT 1').fetchone()[0])
    if seal(state)!=digest or last['state_hash']!=digest:raise ValueError('DERIVED_CHECKPOINT_NOT_BOUND')
    db.close()
    if bar_counts['300']!=state['own_bars'] or bar_counts['60']!=state['m1_bars']:raise ValueError('DERIVED_BAR_COUNTER_MISMATCH')
    runtime=json.loads((manager.root/'runtime_state.json').read_text());raw=[];processed_ticks=0;processed_heartbeats=0;processed_source_records=0
    recovery=json.loads((BASE/'upgrade_latest.json').read_text());old_cursors=recovery['before']['raw_cursors'];old_raw_prefixes_verified=0
    for name in runtime['segments']:
        segment=manager.root/'segments'/name;raw.append(audit_segment(segment))
        cursor=state['cursors'].get(name)
        if not cursor:continue
        head_at_cursor=GENESIS
        with (segment/'journal.jsonl').open('rb') as stream:
            for index in range(cursor['rows']):
                record=json.loads(stream.readline());event=record['payload']['event'];head_at_cursor=record['sha256']
                old_cursor=old_cursors.get(name)
                if old_cursor and index+1==old_cursor['rows']:
                    if stream.tell()!=old_cursor['offset'] or head_at_cursor!=old_cursor['head']:raise ValueError('PRE_RESTART_RAW_PREFIX_CHANGED')
                    old_raw_prefixes_verified+=1
                if event['kind']=='SOURCE_OBSERVATION':
                    processed_source_records+=1
                    row=json.loads(event['native_line'])['payload'];processed_ticks+=row['kind']=='ONTICK_LATEST_QUOTE';processed_heartbeats+=row['kind']=='HEARTBEAT'
            if stream.tell()!=cursor['offset'] or head_at_cursor!=cursor['head']:raise ValueError('DERIVED_CURSOR_DOES_NOT_MATCH_REAL_RAW_PREFIX')
    if processed_source_records!=state['source_records']:raise ValueError('PROCESSED_REAL_PREFIX_COUNT_MISMATCH')
    if old_raw_prefixes_verified!=sum(c['rows']>0 for c in old_cursors.values()):raise ValueError('PRE_RESTART_CURSOR_MISSING')
    return dict(capture_id=manager.root.name,derived_head=head,derived_rows=rows,artifact_counts=dict(counts),completed_bars=dict(bar_counts),rejected_bars=dict(rejected),state=state,raw_segments=raw,old_version_prefix_retained=old_prefix,old_raw_prefixes_verified=old_raw_prefixes_verified,processed_source_records=processed_source_records,processed_real_ticks_in_quarantine=processed_ticks,processed_real_heartbeats=processed_heartbeats,raw_and_derived_integrity='VERIFIED_AT_DURABLE_PREFIXES',real_feature_causal_checks=native_feature_checks,real_feature_causal_status='NOT_OBSERVED_NO_FEATURE_ARTIFACTS' if not native_feature_checks else 'NATIVE_PREFIX_CHECKS_ONLY_GLOBAL_FAIL_UNCHANGED',restart_idempotence_prior_receipt=recovery,physical_restart_performed=False,admitted_records=0)


def main(out,seconds):
    if not 10<=seconds<=60:raise ValueError('SAMPLING_INTERVAL_MUST_BE_10_TO_60_SECONDS')
    verify_code_pin();first=sample();time.sleep(seconds);last=sample();delta=compare_samples(first,last);proof=verify_ledgers()
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    for name,value in dict(first=first,last=last,progress=delta,ledger_verification=proof).items():(out/(name+'.json')).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(dict(progress=delta,raw_callbacks=last['raw']['totals']['source_records'],raw_ticks=last['raw']['totals']['tick_callbacks'],processed_ticks=proof['processed_real_ticks_in_quarantine'],M5=proof['completed_bars'].get('300',0))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);p.add_argument('--seconds',type=int,default=20);args=p.parse_args();main(args.out,args.seconds)
