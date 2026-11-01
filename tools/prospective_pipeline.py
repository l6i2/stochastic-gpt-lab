"""Quarantined, low-memory derivative worker; original collector stays unchanged."""
import argparse,json,os,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from controller.authorized_capture import CaptureManager,sha,once
from controller.isolated_observation import atomic,host_clock,native_line,GENESIS
from controller.pretrain_contracts import seal
from controller.prospective_processor import Ledger,Processor

BASE=ROOT/'outputs/prospective_derivatives_v1'


def frozen_requirements():
    package=ROOT/'research/studies/us30cash_m5_native_pretrain_v1'
    auth=json.loads((package/'scientific_authorization_package.json').read_text())
    if sha(package/'PROTOCOL_ES.md')!=auth['PROTOCOL_HASH']:raise ValueError('FROZEN_PROTOCOL_CHANGED')
    import re
    plan=json.loads((package/'prospective_collection_plan.json').read_text());accept=auth['ACCEPTANCE_CRITERIA']
    return dict(warmup=int(re.search(r'MINIMUM_(\d+)_CLOSED',plan['warmup']).group(1)),signals=int(re.search(r'FIRST_(\d+)_',plan['acquisition_stop']).group(1)),post_bars=int(re.search(r'THEN_(\d+)_',plan['acquisition_stop']).group(1)),evaluable=accept['minimum_evaluation_signals'],each_side=accept['minimum_each_side'])


class NativeReference:
    def __init__(self):self.mt5=None;self.step=None
    def connect(self):
        if self.mt5:return
        import psutil,MetaTrader5 as mt5
        expected='C:/Program Files/XM Global SC MT5 Terminal/terminal64.exe'
        if not any((p.info.get('exe') or '').replace('\\','/').lower()==expected.lower() for p in psutil.process_iter(['exe'])):raise ValueError('XM_NOT_RUNNING_NO_AUTOMATIC_INITIALIZE_LAUNCH')
        if not mt5.initialize(path=expected,timeout=5000):raise ValueError('XM_READ_ONLY_ATTACH_FAILED')
        info=mt5.terminal_info();account=mt5.account_info();symbol=mt5.symbol_info('US30Cash')
        if not info or Path(info.data_path).name!='20C285FE08971A9A2E814AAC44AFC9D2' or not account or account.server!='XMGlobalSC-MT5 5' or account.trade_mode!=0 or not symbol or symbol.chart_mode!=0:
            mt5.shutdown();raise ValueError('PINNED_XM_DEMO_BID_CHART_IDENTITY_MISMATCH')
        self.mt5=mt5;self.step=str(symbol.trade_tick_size)
    def __call__(self,opening,seconds):
        try:
            self.connect();before=host_clock()
            account=self.mt5.account_info();terminal=self.mt5.terminal_info();symbol=self.mt5.symbol_info('US30Cash')
            if not account or account.server!='XMGlobalSC-MT5 5' or account.trade_mode!=0 or not terminal or Path(terminal.data_path).name!='20C285FE08971A9A2E814AAC44AFC9D2' or not symbol or symbol.chart_mode!=0 or str(symbol.trade_tick_size)!=self.step:raise ValueError('NATIVE_REFERENCE_IDENTITY_OR_GRID_CHANGED')
            rows=self.mt5.copy_rates_range('US30Cash',self.mt5.TIMEFRAME_M5 if seconds==300 else self.mt5.TIMEFRAME_M1,datetime.fromtimestamp(opening,timezone.utc),datetime.fromtimestamp(opening,timezone.utc))
            after=host_clock();bar=None
            if rows is not None:
                if any(int(r['time'])!=opening for r in rows) or len(rows)>1:raise ValueError('NATIVE_REFERENCE_OUT_OF_REQUESTED_BAR')
                if len(rows):bar={n:rows[0][n].item() for n in rows.dtype.names}
            evidence=dict(kind='COPY_RATES_COMPARISON_ONLY_NOT_PROSPECTIVE_INPUT',bar=bar,requested_native_open=opening,timeframe_seconds=seconds,request_before=before,request_after=after,time_semantics='NATIVE_LABEL_REQUEST_NO_UTC_MAPPING',not_used_to_fill_missing_raw=True)
            return dict(evidence,hash=seal(evidence))
        except (ValueError,OSError) as exc:return dict(bar=None,error=type(exc).__name__+':'+str(exc),comparison_only=True)
    def close(self):
        if self.mt5:self.mt5.shutdown();self.mt5=None


def verify_code_pin():
    pin=json.loads((BASE/'deployment_pin.json').read_text())
    for name,expected in pin['files'].items():
        path=(ROOT/name).resolve()
        if not path.is_relative_to(ROOT.resolve()) or sha(path)!=expected:raise ValueError('PIPELINE_PIN_CHANGED_'+name)


class Worker:
    def __init__(self):
        verify_code_pin();self.manager=CaptureManager();manifest=self.manager.load();self.folder=BASE/manifest['capture_id'];self.folder.mkdir(parents=True,exist_ok=True)
        import msvcrt
        self.lock=(self.folder/'worker.lock').open('a+b');self.lock.seek(0)
        try:msvcrt.locking(self.lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:self.lock.close();raise RuntimeError('DERIVED_WORKER_ALREADY_RUNNING')
        self.manifest=manifest;self.oracle=NativeReference();self.req=frozen_requirements()
        pin=json.loads((BASE/'deployment_pin.json').read_text());certificate=pin['native_indicator_oracle']
        if certificate['worker_source_sha256']!=sha(ROOT/'controller/prospective_processor.py') or certificate['ATR_PARITY']!='PASS_EXACT' or certificate['HA_PARITY']!='PASS_EXACT' or certificate['MAIN_K_PARITY']!='PASS_RETAINED_BOUND':raise ValueError('NATIVE_IMPLEMENTATION_ORACLE_NOT_BOUND')
        self.ledger=Ledger(self.folder/'quarantine.sqlite3')
        once(self.folder/'manifest.json',dict(capture_id=manifest['capture_id'],raw_manifest_sha256=sha(self.manager.root/'collection_manifest.json'),code_pin_sha256=sha(BASE/'deployment_pin.json'),requirements=frozen_requirements(),mode='DERIVED_QUARANTINE',raw_inputs='EXISTING_POST_ACTIVATION_DURABLE_JOURNAL_ONLY',native_reference='COPY_RATES_COMPARISON_ONLY',no_backfill=True,labels=False,scoring=False,training=False,admitted_dataset_hash=None,live_trading=False))
        self.verify_prefixes()
    def verify_prefixes(self):
        for segment,cursor in self.ledger.state['cursors'].items():
            if Path(segment).name!=segment:raise ValueError('INVALID_RAW_SEGMENT')
            folder=self.manager.root/'segments'/segment
            if sha(folder/'manifest.json')!=cursor['manifest_hash']:raise ValueError('RAW_SEGMENT_MANIFEST_CHANGED')
            head=GENESIS;count=0
            with (folder/'journal.jsonl').open('rb') as stream:
                while stream.tell()<cursor['offset']:
                    line=stream.readline();row=json.loads(line)
                    if not line.endswith(b'\n') or row['previous']!=head or row['sha256']!=seal(dict(previous=head,payload=row['payload'])):raise ValueError('RAW_PREFIX_CHANGED')
                    head=row['sha256'];count+=1
                if stream.tell()!=cursor['offset'] or head!=cursor['head'] or count!=cursor['rows']:raise ValueError('RAW_PREFIX_TRUNCATED')
    def pump(self):
        self.manager.load();runtime=json.loads((self.manager.root/'runtime_state.json').read_text());s=self.ledger.state;processed=0;started=time.monotonic()
        for segment in runtime['segments']:
            if Path(segment).name!=segment:raise ValueError('INVALID_RAW_SEGMENT')
            folder=self.manager.root/'segments'/segment;manifest=json.loads((folder/'manifest.json').read_text());cp=json.loads((folder/'checkpoint.json').read_text())
            cursor=s['cursors'].get(segment,dict(rows=0,offset=0,head=GENESIS,manifest_hash=sha(folder/'manifest.json'),native_head=manifest['anchor']['source_sha256'],native_sequence=manifest['anchor']['source_sequence']))
            if sha(folder/'manifest.json')!=cursor['manifest_hash'] or seal(manifest)!=cp['manifest_sha256']:raise ValueError('RAW_MANIFEST_CHANGED')
            if cp['rows']<cursor['rows']:raise ValueError('RAW_CHECKPOINT_REGRESSED')
            with (folder/'journal.jsonl').open('rb') as stream:
                if stream.seek(0,2)<cursor['offset']:raise ValueError('RAW_JOURNAL_TRUNCATED')
                stream.seek(cursor['offset'])
                while cursor['rows']<cp['rows'] and processed<1000:
                    line=stream.readline();record=json.loads(line);body=record['payload'];event=body['event']
                    if not line.endswith(b'\n') or record['previous']!=cursor['head'] or record['sha256']!=seal(dict(previous=cursor['head'],payload=body)) or body['index']!=cursor['rows'] or body['capture_id']!=segment:raise ValueError('RAW_JOURNAL_CHAIN_OR_ORDER_CHANGED')
                    if event['kind']=='SOURCE_OBSERVATION':
                        parent,digest,row=native_line(event['native_line'].encode())
                        if parent!=cursor['native_head'] or row['sequence']!=cursor['native_sequence']+1 or digest!=event['source_sha256'] or row['session_id']!=manifest['anchor']['source_session'] or row['callback_uptime_ms']<=manifest['actual_start_clock']['uptime_ms']:raise ValueError('NATIVE_REFERENCE_OR_BOUNDARY_CHANGED')
                        step=self.oracle.step
                        if row['kind']=='ONTICK_LATEST_QUOTE' and not step:self.oracle.connect();step=self.oracle.step
                        processor=Processor(s,self.ledger.emit,self.oracle,step or '1',self.req)
                        processor.segment(segment,cursor['manifest_hash'])
                        ref=dict(raw_journal_hash=record['sha256'],native_hash=digest,native_sequence=row['sequence'],native_time_msc=row['time_msc'],callback_uptime_ms=row['callback_uptime_ms'],segment=segment)
                        processor.event(row,ref,event['receipt_clock'])
                        cursor['native_head']=digest;cursor['native_sequence']=row['sequence']
                    elif event['kind']=='EXCLUDED_PRE_CUT_METADATA':
                        cursor['native_head']=event['source_sha256'];cursor['native_sequence']=event['source_sequence']
                    else:raise ValueError('UNEXPECTED_NON_NATIVE_INPUT')
                    cursor.update(rows=cursor['rows']+1,offset=stream.tell(),head=record['sha256']);s['cursors'][segment]=cursor;processed+=1
            if processed>=1000:break
        if processed:self.ledger.emit('MEMBERSHIP_EXPOSURE_PREFIX',dict(capture_id=self.manifest['capture_id'],raw_cursors=s['cursors'],labels_read=0,protected_rows_read=0,legacy_independence='PENDING'));self.ledger.commit()
        monitor=Processor(s,self.ledger.emit,self.oracle,self.oracle.step or '1',self.req).maturity()
        monitor.update(process_id=os.getpid(),observed_clock=host_clock(),raw_capture_id=self.manifest['capture_id'],source_cursors=s['cursors'],ledger_chain_head=self.ledger.head,ledger_artifacts=self.ledger.count,source_records_last_poll=processed,poll_elapsed_ms=round((time.monotonic()-started)*1000,2),status='ACTIVE_QUARANTINED_WAITING_NATIVE_TICKS' if not s['last_tick'] else 'ACTIVE_DERIVED_QUARANTINED',native_indicators_parity='PASS_SYNTHETIC_IMPLEMENTATION_LIVE_SEED_MEMBERSHIP_PENDING',m5_parity='NOT_OBSERVED_NO_CLOSED_BUCKETS' if not s['own_bars'] else 'EXACT_AGGREGATES_ONLY_NOT_EVENT_COMPLETENESS')
        atomic(self.folder/'maturity.json',monitor);return monitor
    def close(self):
        self.oracle.close();self.ledger.close();self.lock.close()


def main(serve=False):
    worker=Worker()
    try:
        while True:
            result=worker.pump()
            if not serve:return result
            enabled=BASE/'enabled.json'
            if enabled.exists() and json.loads(enabled.read_text(encoding='utf-8-sig')).get('enabled') is False:return result
            time.sleep(2)
    finally:worker.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--serve',action='store_true');args=parser.parse_args()
    try:print(json.dumps(main(args.serve),indent=2))
    except Exception as exc:
        BASE.mkdir(parents=True,exist_ok=True);atomic(BASE/'last_error.json',dict(error=type(exc).__name__,reason=str(exc),clock=host_clock(),admitted=False,live_trading=False));raise
