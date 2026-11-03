"""Small read-only dashboard, supervised by the existing research guardian."""
import argparse,html,json,os,sqlite3,sys,time
from datetime import datetime,timezone,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from controller.training_admission_gate import snapshot_gate
from controller.isolated_observation import atomic
BASE=ROOT/'outputs/research_readiness'


def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))


def render():
    pointer=read(ROOT/'outputs/new_native_studies/us30cash_m5_native_20261030_01/current_capture.json')
    capture=pointer.get('capture_id') or pointer.get('id')
    if not capture or Path(capture).name!=capture:raise ValueError('UNSAFE_CAPTURE_POINTER')
    raw=ROOT/'outputs/new_native_studies/us30cash_m5_native_20261030_01'/capture
    derived=ROOT/'outputs/prospective_derivatives_v1'/capture
    m=read(derived/'maturity.json');r=read(raw/'collector_status.json')
    if (m['warmup_required'],m['signals_required'],m['post_signal_bars_required'],m['evaluable_required'],m['evaluable_required_each_side'])!=(350,800,100,200,80):raise ValueError('FROZEN_MATURITY_CHANGED')
    # No new MT5 DLL instance: the main audit records current DEMO identity;
    # a future admitted dispatch always rechecks actual account itself.
    broker=read(BASE/'broker_identity.json') if (BASE/'broker_identity.json').exists() else {}
    grant_path=ROOT/'configs/scientific_training_grant.json'
    grant=read(grant_path) if grant_path.exists() else None
    gate=snapshot_gate(m,broker,grant=grant,root=ROOT)
    now=datetime.now(timezone.utc)
    progress={k:dict(observed=n,required=d,percent=100*n/d) for k,n,d in (
        ('warmup_current_run',m['warmup_current_own_run'],350),('first_consecutive_signals',m['diagnostic_first_signals_progress'],800),
        ('post_signal_bars',m['diagnostic_post_signal_bars'],100),('evaluable_total',m['evaluable_total'],200),
        ('BUY',m['evaluable_buy'],80),('SELL',m['evaluable_sell'],80))}
    value=dict(ecuador=now.astimezone(ZoneInfo('America/Guayaquil')).isoformat(),
        new_york=now.astimezone(ZoneInfo('America/New_York')).isoformat(),host_utc_label=now.isoformat(),
        receipt_time_not_event_utc=True,capture_id=capture,worker_pid=m['process_id'],reporter_pid=os.getpid(),
        raw_ticks=r['totals']['tick_callbacks'],raw_heartbeats=r['totals']['heartbeat_records'],
        M1=m['m1_aggregate_bars'],M5=m['m5_aggregate_bars'],diagnostic_BUY=m['diagnostic_buy_signals'],diagnostic_SELL=m['diagnostic_sell_signals'],
        admissible_progress_percent=0,overall_dataset_percent=None,
        overall_reason='NO_SINGLE_PERCENT_FOR_UNCERTIFIED_COVERAGE_MEMBERSHIP_AND_INTEGRITY',
        progress=progress,scientific_admission=m['admitted_records'],dataset_hash=m['dataset_hash'],
        protocol_stream_unbroken=m['protocol_stream_unbroken'],rejected_buckets=m['rejected_buckets'],
        incidents=m['incident_count'],coverage_rule=m['coverage_rule'],causal_audit=m['causal_audit'],
        callback_gaps=r['continuity']['callback_gaps'],gap_coverage='UNKNOWN_NO_BACKFILL',
        broker_identity_observation=broker,gate=gate,training_execution=dict(training_executed=False),
        approval_conditions=['EXACT_COVERAGE','OWN_WARMUP_AND_SEEDS','FROZEN_SIGNAL_SUPPORT','COMPLETE_MEMBERSHIP',
            'APPLICABLE_CAUSAL_CONTRACT','SEALED_DATASET','EXPLICIT_HASH_BOUND_TRAINING_GRANT'],
        protected_sets=dict(DISCOVERY_VALIDATION='BLOCKED',HISTORICAL_HOLDOUT='LOCKED',FINAL_TEST='LOCKED'),DEMO='DISABLED',LIVE_TRADING=False)
    db=sqlite3.connect((derived/'quarantine.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
    state=json.loads(db.execute('SELECT body FROM checkpoint WHERE id=1').fetchone()[0]);db.close()
    last=state.get('last_tick')
    value['last_native_quote_coordinate']=last
    value['XM_native_civil_label']=(datetime(1970,1,1)+timedelta(milliseconds=last[0])).isoformat() if last else None
    value['XM_display_scope']='ORIGINAL_NATIVE_LABEL_NO_CALIBRATED_CORRESPONDENCE_TO_RECEIPT_CLOCKS'
    value['XM_to_UTC_mapping']='UNVERIFIED_NO_CONVERSION'
    if gate['execution_permitted']:
        from tools.admitted_training import dispatch
        value['training_execution']=dispatch(grant)
    if gate['authorization_request_ready']:
        from controller.training_admission_gate import prepare_authorization_request
        from controller.pretrain_contracts import seal
        request=prepare_authorization_request(grant,ROOT)
        target=BASE/('authorization_request_'+seal(request)+'.json')
        if not target.exists():
            with target.open('x',encoding='utf8') as f:json.dump(request,f,indent=2)
    BASE.mkdir(parents=True,exist_ok=True);atomic(BASE/'status.json',value)
    rows=''.join('<tr><td>'+html.escape(k)+'</td><td>'+html.escape(str(v))+'</td></tr>' for k,v in value.items() if k not in ('progress','broker_identity_observation'))
    bars=''.join('<tr><td>'+html.escape(k)+'</td><td>'+str(v['observed'])+'/'+str(v['required'])+'</td><td>'+f"{v['percent']:.2f}%"+'</td></tr>' for k,v in progress.items())
    page='<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="60"><title>PC A — PRE_TRAIN</title><style>body{font:16px system-ui;max-width:1100px;margin:30px auto;background:#101923;color:#e9f0f5}td{padding:8px;border-bottom:1px solid #345;overflow-wrap:anywhere}h1{color:#6edbd0}</style><h1>Stochastic — PC A — Ecuador</h1><p>CUARENTENA · Sin entrenamiento autorizado · No es scoring</p><p>Captura activa ≠ completa ≠ admitida. Las horas mostradas son de recepción local, no generación XM.</p><table>'+bars+'</table><h2>Estado y condiciones</h2><table>'+rows+'</table>'
    temp=BASE/'index.tmp';temp.write_text(page,encoding='utf8');os.replace(temp,BASE/'index.html')
    return value


def main(serve):
    import msvcrt
    BASE.mkdir(parents=True,exist_ok=True)
    with (BASE/'reporter.lock').open('a+b') as lock:
        if lock.seek(0,2)==0:lock.write(b'0');lock.flush()
        lock.seek(0)
        try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:return {'status':'ALREADY_RUNNING'}
        while True:
            try:value=render()
            except Exception as e:
                value=dict(status='REPORT_FAILED_FAIL_CLOSED',reason=type(e).__name__+': '+str(e),training_executed=False)
                atomic(BASE/'report_error.json',value)
                atomic(BASE/'status.json',value|dict(TRAINING_ADMISSION_GATE='BLOCKED_REPORT_FAILURE'))
                (BASE/'index.html').write_text('<meta charset="utf-8"><meta http-equiv="refresh" content="60"><h1>Reporte bloqueado</h1><p>'+html.escape(value['reason'])+'</p><p>Sin autorización ni ejecución de entrenamiento.</p>',encoding='utf8')
            if not serve:return value
            # Reuse the supervised reporter, rather than another process/task.
            # Separate failure receipt: a bad consolidated report never dispatches.
            try:
                from tools.autonomous_research_status import build
                atomic(ROOT/'outputs/status/AUTONOMOUS_RESEARCH_STATUS.json',build())
            except Exception as exc:
                atomic(ROOT/'outputs/status/AUTONOMOUS_RESEARCH_STATUS.json',dict(
                    TRAINING_ADMISSION_GATE='FAIL',TRAINING_READINESS='BLOCKED',TRAINING_EXECUTED=False,
                    error=type(exc).__name__+':'+str(exc),LIVE_TRADING=False))
            time.sleep(60)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--serve',action='store_true');a=p.parse_args();print(json.dumps(main(a.serve)))
