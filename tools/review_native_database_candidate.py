"""One-shot readonly comparison for an inactive proposal. Never ingests capture data."""
import argparse,importlib.util,json,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.prospective_pipeline import NativeReference,BASE,read_collector_status
from controller.authorized_capture import CaptureManager,sha
from controller.isolated_observation import host_clock
from python.native_m5_rebuild import price_units


def run(out):
    out=Path(out).resolve()
    if not out.is_relative_to((ROOT/'outputs/producer_coverage_20261102').resolve()):raise ValueError('DIAGNOSTIC_OUTPUT_NAMESPACE_ONLY')
    if out.exists():raise ValueError('NO_OVERWRITE')
    manager=CaptureManager();manager.load()
    if read_collector_status(manager.root/'collector_status.json')['status']!='ACTIVE_QUARANTINED':raise ValueError('FRESH_SOURCE_REQUIRED')
    import sqlite3
    db=sqlite3.connect((BASE/manager.root.name/'quarantine.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
    state=json.loads(db.execute('select body from checkpoint').fetchone()[0]);db.close()
    end=state['last_tick'][0]//60000*60000;start=end-60000
    # Choose a recent reference interval from the active capture's native coordinate.
    # This does not prove that the whole interval belongs to its newest segment.
    anchor=json.loads((manager.root/'segments'/state['segment']/'manifest.json').read_text())['anchor']
    if state['cursors'][state['segment']]['native_sequence']<=anchor['source_sequence']:raise ValueError('POSTCUT_PREFIX_REQUIRED')
    spec=importlib.util.spec_from_file_location('candidate_review',ROOT/'research/proposals/native_database_capture_v1/review.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    oracle=NativeReference();oracle.connect();batches=[]
    try:
        for _ in range(2):
            before=host_clock();begin=time.perf_counter_ns()
            ticks=oracle.mt5.copy_ticks_range('US30Cash',datetime.fromtimestamp(start/1000,timezone.utc),datetime.fromtimestamp(end/1000,timezone.utc),oracle.mt5.COPY_TICKS_ALL)
            error=oracle.mt5.last_error();finish=time.perf_counter_ns()
            if ticks is None or ticks.nbytes>20000*80:raise ValueError('QUERY_FAILED_OR_RESOURCE_CAP_NO_TRUNCATION')
            rows=[dict(time=int(r['time']),time_msc=int(r['time_msc']),bid=float(r['bid']),ask=float(r['ask']),flags=int(r['flags']),last=float(r['last']),volume=int(r['volume']),volume_real=float(r['volume_real'])) for r in ticks if start<=int(r['time_msc'])<end]
            batches.append(dict(origin='TERMINAL_DATABASE_QUERY',rows=rows,start_msc=start,end_msc=end,
                query_start_ns=begin,query_end_ns=finish,boot_id=before['boot_id'],session_id=state['segment'],
                connected=bool(oracle.mt5.terminal_info().connected),error=None if error[0]==1 else str(error[0]),first_seen_host_label=before['host_utc_label']))
        result=module.review(*batches)
        rates=oracle.mt5.copy_rates_range('US30Cash',oracle.mt5.TIMEFRAME_M1,datetime.fromtimestamp(start/1000,timezone.utc),datetime.fromtimestamp((end-1000)/1000,timezone.utc))
        bid=[r for r in batches[0]['rows'] if r['flags']&2];differences=[]
        if rates is None or len(rates)!=1 or not bid:differences=['NATIVE_BAR_OR_BID_ROWS_UNAVAILABLE']
        else:
            native=rates[0];prices=[price_units(r['bid'],oracle.step) for r in bid];derived=dict(open=prices[0],high=max(prices),low=min(prices),close=prices[-1])
            differences=[k for k,v in derived.items() if price_units(float(native[k]),oracle.step)!=v]
            if len(bid)!=int(native['tick_volume']):differences.append('tick_volume')
        result.update(native_m1_differences=differences,native_m1_repeatable_reference_parity=not differences,
            capture_id=manager.root.name,segment=state['segment'],range_is_new_segment_membership_proven=False,start_native_msc=start,end_native_exclusive_msc=end,
            source='TWO_POSTCLOSE_DATABASE_REFERENCE_QUERIES_NOT_PROSPECTIVE_RECEIPTS',
            read_observations=[{k:b[k] for k in ('query_start_ns','query_end_ns','first_seen_host_label')} for b in batches],
            raw_originals_modified=False,raw_rows_published=0,reference_rows_adopted=0,
            review_source_sha256=sha(ROOT/'research/proposals/native_database_capture_v1/review.py'))
        out.mkdir(parents=True);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
        return result
    finally:oracle.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);a=p.parse_args();print(json.dumps(run(a.out),indent=2))
