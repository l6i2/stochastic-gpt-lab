"""Oracle adapter for a specifically verified historical prefix across sessions."""
import csv,json,shutil,subprocess,uuid
from pathlib import Path
from controller.authorized_capture import sha,manager_lock
from controller.cf_atr_candidate import initial_state,advance
from controller.pretrain_contracts import seal
from python.native_metadata_v3 import main_k
from tools.cf_own_indicator_oracle import build_source
from tools.xm_recovered_context import ISOLATION


def verify_export(rows,bars):
    if len(rows)!=len(bars):raise ValueError('BC_NATIVE_EXPORT_INCOMPLETE')
    atr=initial_state();ha=None;history=[];maximum=0.;errors=[]
    for row,bar in zip(rows,bars):
        if int(row['time'])!=bar['time'] or any(float(row[k])!=bar[k] for k in ('open','high','low','close')):
            raise ValueError('BC_NATIVE_ORACLE_INPUT_CHANGED')
        atr=advance(atr,bar,seal(bar),(bar['time']+300)*1000)
        if atr['value'] is not None and atr['value']!=float(row['atr']):errors.append('ATR')
        hc=(bar['open']+bar['high']+bar['low']+bar['close'])/4
        ho=(bar['open']+bar['close'])/2 if ha is None else sum(ha)/2
        if any(float(row[k])!=v for k,v in dict(ha_open=ho,ha_close=hc,ha_high=max(bar['high'],ho,hc),ha_low=min(bar['low'],ho,hc)).items()):errors.append('HA')
        ha=(ho,hc);history.append(bar);k=list(main_k(history[-7:]))[-1]
        if k is not None:maximum=max(maximum,abs(k-float(row['main_k'])))
    # Retained MAIN_K tolerance from the existing approved native comparator.
    return dict(status='PASS_RETROSPECTIVE_CONTEXT_DIAGNOSTIC' if not errors and maximum<=1e-10 else 'FAILED_PARITY',
        bars=len(bars),atr_candidate_compared=max(0,len(bars)-13),ha_ohlc_compared=len(bars),
        ha_own_ready_276=len(bars)>=276,main_k_max_abs_error=maximum,failures=errors,
        start_native=bars[0]['time'],end_native_exclusive=bars[-1]['time']+300)


def compare(root,base,members,entries,milestone):
    import psutil
    if psutil.virtual_memory().available<512*1024**2:return dict(status='WAITING_FOR_RESOURCES')
    root=Path(root);base=Path(base);target=ISOLATION/'terminal';checkpoint=json.loads((ISOLATION/'isolation_checkpoint.json').read_bytes())
    for name,digest in checkpoint['program_hashes'].items():
        if sha(target/name)!=digest:raise ValueError('BC_ISOLATED_ORACLE_BINARY_CHANGED')
    if any((p.info.get('exe') or '').lower()==str(target/'terminal64.exe').lower() for p in psutil.process_iter(['exe'])):
        return dict(status='WAITING_FOR_ISOLATED_TERMINAL')
    bars=[];minutes=[];parents=[];bridges=[]
    for member in members:
        if member['role']=='VERIFIED_CLOSED_SESSION_BRIDGE':bridges.append(member['proof_sha256']);continue
        path=base/entries[str(member['native_start'])]['manifest']
        if sha(path)!=member['manifest_sha256']:raise ValueError('BC_PREFIX_INPUT_CHANGED')
        m=json.loads(path.read_bytes())
        for kind,destination in (('m1',minutes),('m5',bars)):
            file=path.parent/(kind+'.jsonl')
            if sha(file)!=m['files'][file.name]:raise ValueError('BC_PREFIX_PAYLOAD_CHANGED')
            destination.extend(json.loads(line) for line in file.read_bytes().splitlines())
        parents.append(member['manifest_sha256'])
        if len(bars)==milestone:break
    if len(bars)!=milestone or not bridges:raise ValueError('BC_VERIFIED_BRIDGE_PREFIX_REQUIRED')
    with manager_lock(root/'outputs/cf_own_indicator_oracle'):
        run='bcctx_'+uuid.uuid4().hex[:10];out=base/'context_trials'/run;out.mkdir(parents=True)
        scripts=target/'MQL5/Scripts/ResearchDiagnostics'/run;scripts.mkdir(parents=True)
        source=scripts/'Oracle.mq5';source.write_text(build_source(dict(native_m5=bars,native_m1=minutes),run),encoding='utf8')
        shutil.copyfile(root/'mt5/HeikinAshiCore.mqh',scripts/'HeikinAshiCore.mqh')
        startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        log=out/'compile.log';subprocess.run(f'"C:/Program Files/XM Global SC MT5 Terminal/metaeditor64.exe" /compile:"{source}" /log:"{log}"',startupinfo=startup,timeout=90)
        if '0 errors, 0 warnings' not in log.read_text(encoding='utf16'):raise RuntimeError('BC_PREFIX_COMPILE_FAILED')
        ini=out/'oracle.ini';ini.write_text('[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\n[StartUp]\nScript=ResearchDiagnostics\\'+run+'\\Oracle\nSymbol=US30Cash\nPeriod=M5\nShutdownTerminal=1\n',encoding='utf16')
        process=subprocess.Popen(f'"{target/"terminal64.exe"}" /portable /config:"{ini}"',startupinfo=startup)
        try:process.wait(timeout=90)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10);raise RuntimeError('BC_PREFIX_ISOLATED_TIMEOUT')
        export=target/'MQL5/Files'/(run+'_oracle.csv');shutil.copyfile(export,out/export.name)
        with export.open(encoding='utf-8-sig') as stream:rows=list(csv.DictReader(stream))
        return dict(verify_export(rows,bars),archive_parents=parents,calendar_bridge_hashes=bridges,
            source_sha256=sha(source),export_sha256=sha(export),original_live_receipt_proven=False,
            dataset_admitted=False,training_executed=False,BC_new_dataset_only=True)
