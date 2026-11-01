"""Run new indicator implementation against native handles on SYNTHETIC bars only."""
import csv,json,shutil,subprocess,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from controller.native_diagnostic import BASE,diagnostic_logs
from controller.authorized_capture import sha
from controller.prospective_processor import Processor,initial_state


def run():
    import psutil
    target=BASE/'terminal';programs=json.loads((BASE/'isolation_checkpoint.json').read_text())['program_hashes']
    for name,expected in programs.items():
        if sha(target/name)!=expected:raise ValueError('ISOLATED_PROGRAM_CHANGED')
    for p in psutil.process_iter(['exe']):
        if (p.info.get('exe') or '').lower()==str(target/'terminal64.exe').lower():raise RuntimeError('ISOLATED_TERMINAL_BUSY')
    original={p.pid for p in psutil.process_iter(['name']) if p.info['name']=='terminal64.exe'}
    nonce='pipe_'+uuid.uuid4().hex[:8];folder=ROOT/'outputs/prospective_native_oracle'/nonce;folder.mkdir(parents=True)
    scripts=target/'MQL5/Scripts/ProspectivePipeline'/nonce;scripts.mkdir(parents=True)
    source=scripts/'ProspectiveIndicatorOracle.mq5';source.write_text((ROOT/'tests/mql5/ProspectiveIndicatorOracle.mq5').read_text().replace('__RUN__',nonce),encoding='utf8')
    shutil.copyfile(ROOT/'mt5/HeikinAshiCore.mqh',scripts/'HeikinAshiCore.mqh')
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    log=folder/'compile.log';editor=Path('C:/Program Files/XM Global SC MT5 Terminal/metaeditor64.exe')
    subprocess.run(f'"{editor}" /compile:"{source}" /log:"{log}"',startupinfo=startup,timeout=90)
    if '0 errors, 0 warnings' not in log.read_text(encoding='utf16') or not source.with_suffix('.ex5').exists():raise ValueError('NATIVE_ORACLE_COMPILE_FAILED')
    ini=folder/'synthetic.ini';ini.write_text('[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\n[StartUp]\nScript=ProspectivePipeline\\'+nonce+'\\ProspectiveIndicatorOracle\nSymbol=US30Cash\nPeriod=M5\nShutdownTerminal=1\n',encoding='utf16')
    process=subprocess.Popen(f'"{target/"terminal64.exe"}" /portable /config:"{ini}"',startupinfo=startup)
    (folder/'process.json').write_text(json.dumps(dict(pid=process.pid,isolated_path=str(target/'terminal64.exe'),no_orders=True)))
    process.wait(timeout=120)
    output=target/'MQL5/Files'/(nonce+'_oracle.csv');shutil.copyfile(output,folder/output.name)
    with output.open(encoding='utf-8-sig') as stream:rows=list(csv.DictReader(stream))
    if len(rows)!=499:raise ValueError('NATIVE_ORACLE_INCOMPLETE')
    state=initial_state();emitted=[];processor=Processor(state,lambda kind,body:emitted.append(dict(kind=kind,**body)),lambda *_:None,'1',dict(warmup=350,signals=800,post_bars=100,evaluable=200,each_side=80))
    processor.segment('SYNTHETIC_ONLY','synthetic')
    main_error=0;atr_error=0;ha_mismatches=0
    for row in rows:
        bar={k:float(row[k]) for k in ('open','high','low','close')};bar.update(time=int(row['time']),tick_volume=5,segment='SYNTHETIC_ONLY')
        state['own_run_bars']+=1;processor.features(bar,sha(output),dict(native_time_msc=(bar['time']+300)*1000),dict(boot_id='synthetic',uptime_ms=0,monotonic_ns=0,host_utc_label='2000-01-03T00:00:00+00:00'))
        feature=next(e for e in reversed(emitted) if e['kind']=='CAUSAL_PREFIX_FEATURES');v=feature['values']
        if v['stoch_k'] is not None:main_error=max(main_error,abs(v['stoch_k']-float(row['main_k'])))
        if v['ATR'] is not None:atr_error=max(atr_error,abs(v['ATR']-float(row['atr'])))
        if int(row['ha_ready'])!=(v['ha_direction'] is not None) or v['ha_direction'] is not None and v['ha_direction']!=int(row['ha_direction']):ha_mismatches+=1
    result=dict(run_id=nonce,native_execution=True,synthetic_bars=499,MAIN_K_PARITY='PASS_RETAINED_BOUND' if main_error<=1e-10 else 'FAIL',main_max_abs_error=main_error,main_bound_existing=1e-10,ATR_PARITY='PASS_EXACT' if atr_error==0 else 'FAIL_EXACT',atr_max_abs_error=atr_error,atr_tolerance=0,HA_PARITY='PASS_EXACT' if ha_mismatches==0 else 'FAIL',ha_mismatches=ha_mismatches,compile_errors=0,compile_warnings=0,original_terminals_preserved=all(psutil.pid_exists(p) for p in original),source_sha256=sha(source),ex5_sha256=sha(source.with_suffix('.ex5')),ha_core_sha256=sha(ROOT/'mt5/HeikinAshiCore.mqh'),oracle_csv_sha256=sha(output),worker_source_sha256=sha(ROOT/'controller/prospective_processor.py'),dataset_admitted=False,labels_read=0,orders_sent=0,protected_rows_read=0)
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(dict(folder=str(folder),**result)))


if __name__=='__main__':run()
