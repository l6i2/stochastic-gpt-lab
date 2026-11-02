"""Versioned diagnostic replay of recorded prospective bytes, never raw backfill.

Uses a corrected comparison adapter, leaves live worker/checkpoints untouched.
Features are recomputed now; they are not live feature snapshots or admitted data.
"""
import argparse,json,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from controller.authorized_capture import CaptureManager,sha,NATIVE
from controller.isolated_observation import native_line,GENESIS
from controller.pretrain_contracts import chain,verify_chain
from controller.prospective_processor import Processor,initial_state
from tools.prospective_pipeline import NativeReference,frozen_requirements,verify_code_pin


def run(segment,out,cache=None):
    out=Path(out)
    if out.exists() or Path(segment).name!=segment:raise ValueError('NEW_RECHECK_VERSION_AND_SAFE_SEGMENT_REQUIRED')
    verify_code_pin();manager=CaptureManager();manager.load()
    folder=manager.root/'segments'/segment;manifest=json.loads((folder/'manifest.json').read_text());cp=json.loads((folder/'checkpoint.json').read_text())
    if manifest['dataset_admitted'] is not False or manifest['historical_backfill_allowed'] is not False:raise ValueError('ONLY_EXISTING_QUARANTINED_POST_CUT_CAPTURE_ALLOWED')
    source=Path(manifest['source_path'])
    if source.is_symlink() or not source.resolve().is_relative_to(NATIVE.resolve()):raise ValueError('SOURCE_OUTSIDE_PINNED_NATIVE_FOLDER')
    state=initial_state();events=[]
    oracle=NativeReference();oracle.connect();cached={};cache_hash=None
    if cache:
        cache=Path(cache);meta=json.loads((cache/'summary.json').read_text());old=json.loads((cache/'events.json').read_text())
        verify_chain(old,meta['recheck_ledger_head'])
        if meta['capture_id']!=manager.root.name or meta['segment']!=segment or meta['source_manifest_sha256']!=sha(folder/'manifest.json'):
            raise ValueError('REFERENCE_CACHE_FROM_DIFFERENT_CAPTURE')
        for e in old:
            if e['kind']=='BAR_COMPARISON' and e['body'].get('native_reference'):
                b=e['body'];cached[(b['bucket']['open_msc']//1000,b['bucket']['timeframe_seconds'])]=b['native_reference']
        cache_hash=sha(cache/'events.json')
    cache_hits=0;new_queries=0
    def reference(opening,seconds):
        nonlocal cache_hits,new_queries
        if (opening,seconds) in cached:
            cache_hits+=1;return cached[(opening,seconds)]
        new_queries+=1;return oracle(opening,seconds)
    def emit(kind,body):events.append(dict(kind=kind,body=body,recheck_only=True,admitted=False))
    processor=Processor(state,emit,reference,oracle.step,frozen_requirements());processor.segment(segment,sha(folder/'manifest.json'))
    head=GENESIS;native_head=manifest['anchor']['source_sha256'];sequence=manifest['anchor']['source_sequence'];count=0;quotes=0
    try:
        with (folder/'journal.jsonl').open('rb') as stream,source.open('rb') as native:
            native.seek(manifest['anchor']['source_offset'])
            for i in range(cp['rows']):
                line=stream.readline();record=json.loads(line);body=record['payload'];event=body['event']
                from controller.pretrain_contracts import seal
                if record['previous']!=head or record['sha256']!=seal(dict(previous=head,payload=body)) or body['index']!=i:raise ValueError('RAW_RECHECK_PREFIX_CHANGED')
                raw=native.readline(32768);parent,digest,row=native_line(raw)
                if parent!=native_head or row['sequence']!=sequence+1 or digest!=event['source_sha256']:raise ValueError('NATIVE_RECHECK_SOURCE_CHANGED')
                if row['session_id']!=manifest['anchor']['source_session'] or row['capture_id']!=manifest['anchor']['source_capture']:raise ValueError('SOURCE_IDENTITY_CHANGED')
                if event['kind']=='SOURCE_OBSERVATION':
                    receipt=event['receipt_clock']
                    if raw!=event['native_line'].encode() or row['callback_uptime_ms']<=manifest['actual_start_clock']['uptime_ms'] or receipt['boot_id']!=manifest['actual_start_clock']['boot_id']:
                        raise ValueError('PRE_CUT_OR_CHANGED_OBSERVATION')
                    if not row['callback_uptime_ms']<=row['read_uptime_ms']<=receipt['uptime_ms']:raise ValueError('RECEIPT_COUNTER_ORDER_CHANGED')
                    ref=dict(segment=segment,raw_journal_hash=record['sha256'],native_hash=digest,native_sequence=row['sequence'],native_time_msc=row['time_msc'],callback_uptime_ms=row['callback_uptime_ms'])
                    processor.event(row,ref,receipt);count+=1;quotes+=row['kind']=='ONTICK_LATEST_QUOTE'
                elif event['kind']!='EXCLUDED_PRE_CUT_METADATA':raise ValueError('NON_NATIVE_INPUT_REFUSED')
                head=record['sha256'];native_head=digest;sequence=row['sequence']
            source_end_offset=native.tell()
        if head!=cp['chain_head'] or native_head!=cp['source_sha256'] or sequence!=cp['source_sequence'] or source_end_offset!=cp['source_offset']:raise ValueError('SOURCE_CHECKPOINT_CHANGED')
    finally:oracle.close()
    records=chain(events);ledger_head=verify_chain(records)
    summary=dict(mode='VERSIONED_DIAGNOSTIC_RECHECK_NOT_LIVE_CAPTURE_OR_SCIENTIFIC_ADMISSION',
        capture_id=manager.root.name,segment=segment,source_manifest_sha256=sha(folder/'manifest.json'),source_rows=cp['rows'],
        source_chain_head=head,native_chain_head=native_head,last_source_sequence=sequence,
        first_source_sequence=manifest['anchor']['source_sequence']+1,own_post_cut_only=True,
        raw_quote_callbacks=quotes,source_observations=count,M5_valid=state['own_bars'],M1_valid=state['m1_bars'],
        rejected_total=state['rejected_buckets'],contiguous_diagnostic_bars=state['own_run_bars'],
        diagnostic_BUY=state['signals_buy'],diagnostic_SELL=state['signals_sell'],
        feature_records=sum(r['kind']=='CAUSAL_PREFIX_FEATURES' for r in events),
        code_sha256=sha(Path(__file__)),processor_sha256=sha(ROOT/'controller/prospective_processor.py'),
        reference_cache_sha256=cache_hash,cached_reference_comparisons=cache_hits,new_reference_queries=new_queries,
        recheck_ledger_head=ledger_head,recomputed_now_not_claimed_live_availability=True,
        live_worker_state_modified=False,old_rejections_replaced=False,reference_rows_used_as_inputs=0,
        admitted_records=0,training_calls=0,scoring_calls=0,
        old_259_284_queried=any(e['kind']=='BAR_COMPARISON' and e['body']['bucket']['timeframe_seconds']==300 and e['body']['bucket']['open_msc']==1793583600000 for e in events))
    out.mkdir(parents=True)
    for name,value in [('summary',summary),('events',records)]:
        (out/(name+'.json')).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n',encoding='utf8',newline='\n')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--segment',required=True);p.add_argument('--out',required=True);p.add_argument('--cache');a=p.parse_args();print(json.dumps(run(a.segment,a.out,a.cache),indent=2))
