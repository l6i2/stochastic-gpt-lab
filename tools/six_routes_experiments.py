"""Execute permitted historical, aggregation, clock and membership experiments."""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from controller.authorized_capture import sha
from controller.pretrain_contracts import interval_disposition
from controller.six_routes import aggregate_m1
from tools.offline_study_receipt import build as offline, RUN
from tools.prospective_pipeline import NativeReference
from tools import authenticated_utc_station


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8-sig'))


def routes(out):
    out = Path(out)
    out.mkdir(exist_ok=False, parents=True)
    def write(name, value):
        (out / name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n', encoding='utf8',newline='\n')
    historical = offline()
    source = ROOT / 'outputs/historical_downloads_v1' / RUN
    extraction = ROOT / 'outputs/six_alternatives_experiment' / ('historical_' + uuid.uuid4().hex)
    extraction.mkdir(parents=True)
    for name, digest in historical['diagnostic']['files'].items():
        with (source / name).open('rb') as src, (extraction / name).open('xb') as dst:
            shutil.copyfileobj(src, dst, length=65536)
        if sha(extraction / name) != digest:
            raise ValueError('EXTRACTION_HASH_MISMATCH')
    a = dict(dataset_id=extraction.name, source_kind='HISTORICAL_DIAGNOSTIC_EXPOSED',
             extraction_utc=datetime.now(timezone.utc).isoformat(), source_files=historical['diagnostic']['files'],
             tick_count=historical['diagnostic']['ticks'], bars=historical['diagnostic']['bars'],
             replay=historical['replay'], independently_admitted=False, copying_block_bytes=65536)
    ref = NativeReference()
    try:
        ref.connect()
        api = ref.mt5
        terminal = api.terminal_info()
        if terminal.trade_allowed:
            raise ValueError('TERMINAL_TRADING_MUST_BE_DISABLED')
        a['terminal'] = dict(connected=terminal.connected, maxbars=terminal.maxbars, terminal_trade_allowed=False)
        opening, ending = 1704157200, 1704157500
        a['native_queries'] = []
        for kind, frame in [('M1',api.TIMEFRAME_M1),('M5',api.TIMEFRAME_M5),('TICKS',None)]:
            first = datetime.fromtimestamp(opening, timezone.utc)
            last = datetime.fromtimestamp(ending if frame is None else ending-1, timezone.utc)
            rows = api.copy_ticks_range('US30Cash',first,last,api.COPY_TICKS_ALL) if frame is None else api.copy_rates_range('US30Cash',frame,first,last)
            error = api.last_error()[0]
            coordinate = 'time_msc' if frame is None else 'time'
            scale = 1000 if frame is None else 1
            valid = rows is not None and len(rows)>0 and all(
                opening*scale <= int(row[coordinate]) and
                (int(row[coordinate]) <= ending*scale if frame is None else int(row[coordinate]) < ending*scale)
                for row in rows)
            interval_rows = [row for row in rows if int(row[coordinate]) < ending*scale] if valid else []
            payload_hash = None
            if valid and frame is None:
                payload=[{name:row[name].item() for name in rows.dtype.names} for row in interval_rows]
                payload_path=extraction/'native_api_ticks_sample.json'
                payload_path.write_text(json.dumps(payload,sort_keys=True)+'\n',encoding='utf8',newline='\n')
                payload_hash=sha(payload_path)
            a['native_queries'].append(dict(kind=kind,error=error,returned_rows=len(rows) if rows is not None else None,
                interval_rows=len(interval_rows),envelope_verified=valid,
                excluded_exact_end_rows=len(rows)-len(interval_rows) if valid else None,
                sample_payload_sha256=payload_hash,payload_adopted_as_prospective=False))
    except (ValueError,RuntimeError) as error:
        a['native_query_failure'] = str(error)
    finally:
        ref.close()
    write('A_history.json',a)
    def bars(frame):
        with (source/(RUN+'_stochastic_events.csv.native_'+frame+'.csv')).open() as stream:
            return list(csv.DictReader(stream))
    derived = aggregate_m1(bars('M1'))
    native = {int(row['time']): row for row in bars('M5')}
    comparisons = []
    for row in derived:
        expected = native.get(row['time'])
        differences = ['MISSING_NATIVE_M5'] if expected is None else [k for k in ('open','high','low','close','tick_volume') if float(expected[k]) != row[k]]
        comparisons.append(dict(native_open=row['time'],complete_five_minutes=row['complete_five_minutes'],differences=differences))
    write('B_aggregation.json',dict(m5_from_m1=len(derived),m5_native=len(native),
          full_five_minute_buckets=sum(r['complete_five_minutes'] for r in comparisons),
          exact_ohlc_volume_buckets=sum(not r['differences'] for r in comparisons),
          ticks_comparison=historical['diagnostic']['bars']['M5'],intervals=comparisons,
          session_status='NATIVE_LABELS_ONLY_CALENDAR_PARTIAL',original_receipt_coverage_proven=False))
    base = ROOT/'outputs/pc_a_prospective_utc/authenticated_utc'
    state = read('outputs/pc_a_prospective_utc/authenticated_utc/state.json')
    record = read('outputs/pc_a_prospective_utc/authenticated_utc/'+state['last_record'])
    measurements = [dict(status=r['status'], measurement=r.get('measurement')) for r in record['payload']['results']]
    write('D_temporal.json',dict(verified_nts_chain_records=authenticated_utc_station.verify_history(base,state),
          last_record_sha256=sha(base/state['last_record']), measurements=measurements,
          native_receipt_correlations=record['payload'].get('native_receipt_correlations'),
          native_generation_utc_certified=False, calendar=read('configs/xm_us30cash_sessions_utc.json'),
          strategy_time_domain='NATIVE_EVENT_ORDER', independent_clock='NTS_CONDITIONAL_BOUNDS',
          missing_guarantees=['BROKER_GENERATION_ATTESTATION','BOUNDED_EVENT_TO_RECEIPT_DELAY','DRIFT_AND_UPTIME_CALIBRATION']))
    ledger = read('research/studies/us30cash_m5_native_pretrain_v1/exposure_ledger.json')
    candidate = dict(instrument='US30Cash',domain_id='NEW_PC_A_NATIVE_UNRECONCILED',
          dependency_start=record['payload']['observed_host_utc'] and int(datetime.now(timezone.utc).timestamp()*1000),
          label_end=int(datetime.now(timezone.utc).timestamp()*1000),signal_ids=['FUTURE_METADATA_BOUNDARY_PREVIEW'],source_sha256='FUTURE_UNKNOWN')
    write('E_independence.json',dict(candidate_metadata_only=candidate,disposition=interval_disposition(candidate,ledger),
          missing=ledger['missing'],legacy_search_receipt_sha256=sha(ROOT/'research/studies/pc_a_independent_advance_20261101_v1/legacy_recovery.json'),
          missing_artifacts={p:dict(status='UNKNOWN',exists=(ROOT/p).exists()) for p in
              read('research/studies/us30cash_m5_native_pretrain_v1/dataset_inventory.json')['expected_original_manifests']},
          forward_boundary_test='HOST_UTC_IS_NOT_PROOF_OF_XM_NATIVE_NONOVERLAP',rows_protected_opened=0))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True)
    routes(parser.parse_args().out)
