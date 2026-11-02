"""Audit only new durable tails; no historical requests, second worker or fits."""
import argparse,hashlib,json,math,sqlite3,sys
from collections import Counter
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tools'),str(ROOT/'python')]
from controller.authorized_capture import CaptureManager,NATIVE
from controller.isolated_observation import native_line,GENESIS
from controller.pretrain_contracts import seal
from controller.prospective_progress import classify_tail
from controller.training_admission_gate import snapshot_gate
from controller.scientific_authority import AUTHORIZED_GRANT_HASHES,ADMITTED_PACKAGE_HASHES
from tools.verify_prospective_operation import sample,compare_samples
from tools.prospective_pipeline import verify_code_pin
from tools.new_capture_station import verify_deployment
from authenticated_utc_station import verify_history


def last_record(path,end):
    with path.open('rb') as f:
        f.seek(max(0,end-131072));raw=f.read(min(end,131072))
    if not raw.endswith(b'\n'):raise ValueError('ANCHOR_NOT_ON_COMPLETE_RECORD')
    return json.loads(raw.rstrip(b'\r\n').split(b'\n')[-1])


def build(base_path,out,first_path=None):
    out=Path(out);base_path=Path(base_path)
    if out.exists():raise ValueError('NEW_IMMUTABLE_REPORT_DIRECTORY_REQUIRED')
    base_raw=base_path.read_bytes();base=json.loads(base_raw)
    manager=CaptureManager();manager.load();verify_code_pin();verify_deployment()
    if base['capture_id']!=manager.root.name:raise ValueError('CAPTURE_MIXING_REFUSED')
    folder=ROOT/'outputs/prospective_derivatives_v1'/manager.root.name
    db=sqlite3.connect((folder/'quarantine.sqlite3').resolve().as_uri()+'?mode=ro',uri=True);db.execute('BEGIN')
    n0=base['derived_rows']
    if db.execute('SELECT digest FROM artifacts WHERE n=?',(n0-1,)).fetchone()[0]!=base['derived_head']:
        raise ValueError('PREVIOUS_PUBLISHED_ANCHOR_CHANGED')
    text,state_hash=db.execute('SELECT body,digest FROM checkpoint WHERE id=1').fetchone();state=json.loads(text)
    if seal(state)!=state_hash:raise ValueError('CURRENT_STATE_HASH_CHANGED')
    records=[(n,p,d,json.loads(b)) for n,p,d,b in db.execute('SELECT n,previous,digest,body FROM artifacts WHERE n>=? ORDER BY n',(n0,))]
    delta=classify_tail(records,n0,base['derived_head'])
    if records:
        if records[-1][3].get('kind')!='CHECKPOINT' or records[-1][3]['state_hash']!=state_hash:raise ValueError('STATE_NOT_BOUND_TO_LAST_ARTIFACT')
    elif state!=base['state']:raise ValueError('STATE_CHANGED_WITHOUT_NEW_ARTIFACT')
    db.close()
    ticks=0;heartbeats=0;source_records=0;membership=[];raw_segments=[]
    runtime=json.loads((manager.root/'runtime_state.json').read_text())
    for segment in runtime['segments']:
        if Path(segment).name!=segment:raise ValueError('UNSAFE_SEGMENT_ID')
        p=manager.root/'segments'/segment;manifest_bytes=(p/'manifest.json').read_bytes();manifest=json.loads(manifest_bytes)
        manifest_hash=hashlib.sha256(manifest_bytes).hexdigest();cp=json.loads((p/'checkpoint.json').read_text())
        if seal(manifest)!=cp['manifest_sha256'] or manifest['historical_backfill_allowed'] is not False or manifest['dataset_admitted'] is not False:
            raise ValueError('RAW_SEGMENT_CONTRACT_CHANGED')
        source=Path(manifest['source_path'])
        if not source.resolve().is_relative_to(NATIVE.resolve()) or source.is_symlink():raise ValueError('SOURCE_OUTSIDE_PINNED_NATIVE_FOLDER')
        target=state['cursors'].get(segment)
        if target is None:
            membership.append(dict(segment=segment,manifest_sha256=manifest_hash,rows_processed=0,raw_rows_waiting=cp['rows'],status='EMPTY_OR_NOT_YET_CONSUMED_QUARANTINED',certified=False))
            raw_segments.append(dict(segment=segment,manifest_file_sha256=manifest_hash,rows_processed=0))
            continue
        if target['manifest_hash']!=manifest_hash or cp['rows']<target['rows']:raise ValueError('RAW_MANIFEST_OR_CURSOR_REGRESSION')
        old=base['state']['cursors'].get(segment)
        if old:
            if old['manifest_hash']!=manifest_hash or target['rows']<old['rows']:raise ValueError('BASE_SEGMENT_CHANGED')
            previous=last_record(p/'journal.jsonl',old['offset'])
            if previous['sha256']!=old['head'] or previous['payload']['index']!=old['rows']-1:raise ValueError('RAW_BASE_ANCHOR_CHANGED')
            start_offset=previous['payload']['resulting_state']['source_offset']
            head=old['head'];native_head=old['native_head'];sequence=old['native_sequence'];start_n=old['rows'];journal_offset=old['offset']
        else:
            start_offset=manifest['anchor']['source_offset'];head=GENESIS;native_head=manifest['anchor']['source_sha256'];sequence=manifest['anchor']['source_sequence'];start_n=0;journal_offset=0
        counts=Counter();flags=Counter();start_sequence=sequence;source_offset=start_offset
        with (p/'journal.jsonl').open('rb') as f,source.open('rb') as original:
            f.seek(journal_offset);original.seek(start_offset)
            for i in range(start_n,target['rows']):
                line=f.readline();record=json.loads(line);body=record['payload'];event=body['event']
                if not line.endswith(b'\n') or record['previous']!=head or record['sha256']!=seal(dict(previous=head,payload=body)) or body['index']!=i or body['capture_id']!=segment:
                    raise ValueError('RAW_NEW_TAIL_CHANGED')
                raw=original.readline(32768);parent,digest,row=native_line(raw)
                if parent!=native_head or row['sequence']!=sequence+1 or digest!=event['source_sha256'] or row['sequence']!=event['source_sequence']:
                    raise ValueError('NATIVE_NEW_TAIL_CHAIN_CHANGED')
                if row['session_id']!=manifest['anchor']['source_session'] or row['capture_id']!=manifest['anchor']['source_capture']:raise ValueError('NATIVE_IDENTITY_CHANGED')
                if event['kind']=='SOURCE_OBSERVATION':
                    if raw!=event['native_line'].encode() or row['callback_uptime_ms']<=manifest['actual_start_clock']['uptime_ms']:raise ValueError('PRE_CUT_OR_REPLACED_NATIVE_BYTES')
                    receipt=event['receipt_clock']
                    if receipt['boot_id']!=manifest['actual_start_clock']['boot_id'] or not row['callback_uptime_ms']<=row['read_uptime_ms']<=receipt['uptime_ms']:raise ValueError('RECEIPT_ORDER_OR_BOOT_CHANGED')
                    if row['kind']=='ONTICK_LATEST_QUOTE':
                        if row['time_msc']//1000!=row['time'] or not all(math.isfinite(row[k]) for k in ('bid','ask')) or not 0<row['bid']<=row['ask']:raise ValueError('INVALID_QUOTE')
                        ticks+=1
                    heartbeats+=row['kind']=='HEARTBEAT';source_records+=1;counts[row['kind']]+=1;flags.update(event['quarantine_flags'])
                elif event['kind']!='EXCLUDED_PRE_CUT_METADATA':raise ValueError('UNSUPPORTED_RAW_INPUT')
                head=record['sha256'];native_head=digest;sequence=row['sequence'];source_offset+=len(raw)
            if f.tell()!=target['offset'] or head!=target['head'] or native_head!=target['native_head'] or sequence!=target['native_sequence']:
                raise ValueError('DERIVED_CURSOR_NOT_BOUND_TO_VERIFIED_RAW_BYTES')
        membership.append(dict(segment=segment,manifest_sha256=manifest_hash,source_session=manifest['anchor']['source_session'],boot_id=manifest['actual_start_clock']['boot_id'],
            previous_rows=start_n,rows_processed=target['rows'],new_rows=target['rows']-start_n,
            first_new_sequence=start_sequence+1 if sequence>start_sequence else None,last_sequence=sequence,
            source_new_byte_range=[start_offset,source_offset],journal_new_byte_range=[journal_offset,target['offset']],
            new_source_kinds=dict(counts),new_quarantine_flags=dict(flags),raw_rows_waiting=cp['rows']-target['rows'],
            own_post_cut_source_only=True,reference_rows_adopted=0,status='VERIFIED_NATIVE_TAIL_QUARANTINED',certified=False))
        raw_segments.append(dict(segment=segment,manifest_file_sha256=manifest_hash,rows_processed=target['rows']))
    if state['source_records']-base['state']['source_records']!=source_records:raise ValueError('SOURCE_COUNTER_DISAGREEMENT')
    completed=dict(base['completed_bars']);rejected=dict(base['rejected_bars'])
    for frame,counts in delta['classification_counts'].items():
        completed[frame]=completed.get(frame,0)+counts.get('VALID_REFERENCE_PARITY_QUARANTINED',0)
        rejected[frame]=rejected.get(frame,0)+counts.get('PARTIAL_REJECTED',0)+counts.get('REJECTED',0)
    if completed.get('300',0)!=state['own_bars'] or completed.get('60',0)!=state['m1_bars']:raise ValueError('BAR_COUNTS_DISAGREE_WITH_WORKER_STATE')
    checkpoint=dict(schema='incremental-prospective-progress/1',capture_id=manager.root.name,derived_head=delta['new_head'],derived_rows=delta['end_exclusive'],
        state=state,processed_real_ticks_in_quarantine=base['processed_real_ticks_in_quarantine']+ticks,
        processed_real_heartbeats=base['processed_real_heartbeats']+heartbeats,completed_bars=completed,rejected_bars=rejected,
        real_feature_causal_checks=base['real_feature_causal_checks']+len(delta['features']),raw_segments=raw_segments,
        prior_receipt_path=str(base_path),prior_receipt_sha256=hashlib.sha256(base_raw).hexdigest(),
        integrity_scope='PREVIOUS_PUBLISHED_ANCHORS_PRESERVED_NEW_TAIL_AND_ORIGINAL_NATIVE_BYTES_VERIFIED_NOT_FULL_REHASH')
    last=sample();first=json.loads(Path(first_path).read_text()) if first_path else last;live=compare_samples(first,last)
    if not last['native_cache'].get('identity_verified'):raise ValueError('BROKER_DEMO_IDENTITY_NOT_CURRENTLY_VERIFIED')
    gate=snapshot_gate(last['derived'],dict(identity_verified=True,demo=True))
    assert not AUTHORIZED_GRANT_HASHES and not ADMITTED_PACKAGE_HASHES
    nts_folder=ROOT/'outputs/pc_a_prospective_utc/authenticated_utc';nts_state=json.loads((nts_folder/'state.json').read_text());nts_count=verify_history(nts_folder,nts_state)
    m5=delta['classification_counts']['300'];total_m5_rejected=rejected.get('300',0)
    summary=dict(REAL_TICKS_NEW=ticks,REAL_TICKS_TOTAL=checkpoint['processed_real_ticks_in_quarantine'],
        REAL_M5_COMPLETED=dict(new=m5.get('VALID_REFERENCE_PARITY_QUARANTINED',0),total=completed.get('300',0)),
        REAL_M5_REJECTED=dict(new=m5.get('PARTIAL_REJECTED',0)+m5.get('REJECTED',0),total=total_m5_rejected,
            new_partial=m5.get('PARTIAL_REJECTED',0),new_other_rejected=m5.get('REJECTED',0),new_aborted=m5.get('PARTIAL_ABORTED_AT_SEGMENT_BOUNDARY',0)),
        WARMUP_VALID_BARS=state['own_run_bars'],WARMUP_SCIENTIFICALLY_ADMITTED=0,CONSECUTIVE_SIGNALS=state['after_warmup_signals'],
        BUY_SIGNALS=state['signals_buy'],SELL_SIGNALS=state['signals_sell'],POST_SIGNAL_BARS=state['post_signal_bars'],
        FEATURES_NEW=len(delta['features']),FEATURES_TOTAL=checkpoint['real_feature_causal_checks'],
        CERTIFIED_SEGMENTS=0,QUARANTINED_SEGMENTS=len(membership),
        MEMBERSHIP='NEW_NATIVE_TAIL_IDENTIFIERS_BYTES_HASHES_AND_PREFIX_VERIFIED_ADMITTED_DATASET_STILL_EMPTY',
        TEMPORAL_PROVENANCE='NATIVE_TIME_UNIT_AND_RECEIPT_ORDER_VERIFIED_SAME_BOOT; GENERATION_UTC_AND_ABSOLUTE_BOUNDS_UNVERIFIED',
        DATASET_MATURITY=dict(status='NOT_READY_QUARANTINED',warmup=f"{state['own_run_bars']}/350",signals=f"{state['after_warmup_signals']}/800",post_bars=f"{state['post_signal_bars']}/100",evaluable='0/200',BUY='0/80',SELL='0/80',admitted_percent=0,protocol_stream_unbroken=state['protocol_stream_unbroken']),
        TRAINING_ADMISSION_GATE=gate,TRAINING_READINESS='BLOCKED',TRAINING_EXECUTED=False,
        HARD_BLOCKER=['EXACT_NATIVE_BID_SEQUENCE_AND_OHLC_VOLUME_COVERAGE','CONTIGUOUS_OWN_WARMUP_AND_SEEDS','800_CONSECUTIVE_SIGNALS_PLUS_100_POST_BARS','200_EVALUABLE_80_BUY_80_SELL_AND_FOLD_SUPPORT','COMPLETE_SCIENTIFIC_MEMBERSHIP_AND_APPLICABLE_CAUSAL_PROVENANCE','EXPLICIT_HASH_BOUND_TRAINING_GRANT'],
        MANUAL_ACTION_REQUIRED='NONE_NOW',NEXT_STATE='EXISTING_WORKER_PROCESSES_NEW_NATIVE_INTERVALS_MONITOR_TRACKS_PROGRESS_QUARANTINE_REMAINS',
        snapshot_ecuador=datetime.now(timezone.utc).astimezone(ZoneInfo('America/Guayaquil')).isoformat(),
        historical_protected_rows_opened=0,old_259_284_queries=0,new_regression_of_old_window=0,scoring_calls=0,
        DISCOVERY_VALIDATION='BLOCKED',HISTORICAL_HOLDOUT='LOCKED',FINAL_TEST='LOCKED',DEMO='DISABLED',LIVE_TRADING=False)
    out.mkdir(parents=True)
    def write(name,value):(out/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf8',newline='\n')
    write('summary.json',summary);write('new_derived_tail.json',delta);write('membership.json',membership);write('prefix_checkpoint.json',checkpoint)
    write('health.json',dict(first=first,last=last,live_delta=live,nts_records=nts_count,nts_chain_head=nts_state['chain_head'],
        frozen_requirements=dict(warmup=350,signals=800,post_bars=100,evaluable=200,each_side=80),
        forming_intervals=state['buckets'],source_to_worker_rows_waiting=sum(r['raw_rows_waiting'] for r in membership)))
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',required=True);p.add_argument('--out',required=True);p.add_argument('--first-sample');a=p.parse_args()
    print(json.dumps(build(a.base,a.out,a.first_sample),ensure_ascii=False,indent=2))
