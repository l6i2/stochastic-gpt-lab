"""One historical reference comparison, never a prospective input or backfill."""
import json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from controller.authorized_capture import CaptureManager
from controller.isolated_observation import native_line
from controller.tick_discrepancy import reconcile
from tools.prospective_pipeline import NativeReference


def run(out):
    out=Path(out)
    if out.exists():raise ValueError('NEW_FORENSIC_VERSION_REQUIRED')
    m=CaptureManager();m.load();start=1793583600000;end=start+300000
    rows=[];refs=[];context=[]
    for segment in json.loads((m.root/'runtime_state.json').read_text())['segments']:
        p=m.root/'segments'/segment;checkpoint=json.loads((p/'checkpoint.json').read_text())
        with (p/'journal.jsonl').open('rb') as f:
            for _ in range(checkpoint['rows']):
                record=json.loads(f.readline());event=record['payload']['event']
                if not event.get('native_line'):continue
                _,digest,r=native_line(event['native_line'].encode())
                if r['kind']=='ONTICK_LATEST_QUOTE' and start<=r['time_msc']<end:
                    rows.append(r);refs.append(dict(native_hash=digest,journal_hash=record['sha256'],sequence=r['sequence']))
                if rows and rows[0]['callback_uptime_ms']<=r['callback_uptime_ms']:
                    context.append(dict(sequence=r['sequence'],kind=r['kind'],connected=r['connected'],session=r['session_id'],uptime=r['callback_uptime_ms']))
                if rows and r['kind']=='ONTICK_LATEST_QUOTE' and r['time_msc']>=end:break
    context=[r for r in context if r['uptime']<=rows[-1]['callback_uptime_ms']]
    oracle=NativeReference();oracle.connect()
    try:
        account=oracle.mt5.account_info();terminal=oracle.mt5.terminal_info()
        if account is None or account.trade_mode!=0:raise ValueError('REAL_OR_UNKNOWN_ACCOUNT_HARD_FAIL')
        a=datetime.fromtimestamp(start//1000,timezone.utc);b=datetime.fromtimestamp(end/1000-.001,timezone.utc)
        snapshots=[]
        for _ in range(2):
            native=oracle.mt5.copy_ticks_range('US30Cash',a,b,oracle.mt5.COPY_TICKS_ALL)
            if native is None:raise ValueError('REFERENCE_QUERY_FAILED')
            reference=[{k:r[k].item() for k in ('time','time_msc','bid','ask','flags')} for r in native]
            snapshots.append(dict(reconciliation=reconcile(rows,reference,start,end,oracle.step),query_record_count=len(reference)))
        result=dict(capture_id=m.root.name,start_native_msc=start,end_native_exclusive_msc=end,
            original_raw_refs=refs,raw_sequences_contiguous=all(y['sequence']==x['sequence']+1 for x,y in zip(context,context[1:])),
            sessions=sorted({r['session_id'] for r in rows}),disconnected_quote_callbacks=sum(not r['connected'] for r in rows),
            observed_heartbeat_and_quote_records=len(context),snapshots=snapshots,
            repeated_queries_payload_reconciliation_equal=snapshots[0]==snapshots[1],
            mechanism='ONTICK_LATEST_SNAPSHOT_NOT_EXHAUSTIVE_EVENT_FEED; SERIAL_HANDLER_AND_FILEFLUSH_CAN_COALESCE',
            exact_per_event_scheduler_cause='NOT_RECORDED_CANNOT_PROVE_FOR_EACH_MISSING_PAYLOAD',
            original_interval_modified=False,backfill=False,broker_demo_verified=True,
            documentation=['https://www.mql5.com/en/docs/event_handlers/ontick','https://www.mql5.com/en/docs/series/copyticksrange'])
    finally:oracle.close()
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf8',newline='\n')
    return {k:result[k] for k in ('capture_id','repeated_queries_payload_reconciliation_equal','sessions')}|dict(reconciliation=snapshots[0]['reconciliation'])


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);print(json.dumps(run(p.parse_args().out),indent=2))
