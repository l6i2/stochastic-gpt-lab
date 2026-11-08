"""Native indicator comparison on the first eligible recovered block only."""
import csv
import json
from pathlib import Path
import shutil
import subprocess
import uuid

from controller.authorized_capture import manager_lock,sha
from controller.native_diagnostic import BASE as ISOLATION
from controller.cf_atr_candidate import initial_state,advance
from python.native_metadata_v3 import main_k
from tools.cf_own_indicator_oracle import build_source


def compare(root,base,state,requests):
    import psutil
    root=Path(root);base=Path(base)
    if psutil.virtual_memory().available<512*1024**2:
        return dict(status='WAITING_FOR_RESOURCES',training_executed=False)
    minutes={};bars={};parents=[]
    for request in requests:
        item=state['completed'].get(request['key'])
        if not item:continue
        path=base/item['path'];manifest=json.loads(path.read_bytes())
        if manifest['failures']:continue
        for kind,destination in (('m1',minutes),('m5',bars)):
            file=path.parent/(kind+'.jsonl')
            if sha(file)!=manifest['files'][file.name]:raise ValueError('RECOVERED_CONTEXT_HASH_CHANGED')
            for raw in file.read_bytes().splitlines():
                row=json.loads(raw);destination[row['time']]=row
        parents.append(item['sha256'])
    chosen=[]
    for stamp,bar in sorted(bars.items()):
        if chosen and stamp!=chosen[-1]['time']+300:chosen=[]
        if not all(stamp+j*60 in minutes for j in range(5)):chosen=[];continue
        chosen.append(bar)
        if len(chosen)==30:break
    if len(chosen)<30:return dict(status='WAITING_FOR_30_CONTIGUOUS_RECOVERED_BARS',training_executed=False)
    own_minutes=[minutes[bar['time']+j*60] for bar in chosen for j in range(5)]
    target=ISOLATION/'terminal'
    checkpoint=json.loads((ISOLATION/'isolation_checkpoint.json').read_bytes())
    for name,digest in checkpoint['program_hashes'].items():
        if sha(target/name)!=digest:raise ValueError('CONTEXT_ISOLATION_CHANGED')
    if any((p.info.get('exe') or '').lower()==str(target/'terminal64.exe').lower() for p in psutil.process_iter(['exe'])):
        return dict(status='WAITING_FOR_ISOLATED_TERMINAL',training_executed=False)
    original={p.pid for p in psutil.process_iter(['name']) if p.info['name']=='terminal64.exe'}
    run='xmhctx_'+uuid.uuid4().hex[:8];out=base/'context_trials'/run;out.mkdir(parents=True)
    with manager_lock(root/'outputs/cf_own_indicator_oracle'):
        scripts=target/'MQL5/Scripts/ResearchDiagnostics'/run;scripts.mkdir(parents=True)
        source=scripts/'Oracle.mq5';source.write_text('// RETROSPECTIVE RECOVERED DATA DIAGNOSTIC\n'+build_source(dict(native_m5=chosen,native_m1=own_minutes),run),encoding='utf8')
        shutil.copyfile(root/'mt5/HeikinAshiCore.mqh',scripts/'HeikinAshiCore.mqh')
        startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        log=out/'compile.log'
        subprocess.run(f'"C:/Program Files/XM Global SC MT5 Terminal/metaeditor64.exe" /compile:"{source}" /log:"{log}"',startupinfo=startup,timeout=90)
        if '0 errors, 0 warnings' not in log.read_text(encoding='utf16'):raise RuntimeError('CONTEXT_COMPILE_FAILED')
        ini=out/'context.ini';ini.write_text('[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\n[StartUp]\nScript=ResearchDiagnostics\\'+run+'\\Oracle\nSymbol=US30Cash\nPeriod=M5\nShutdownTerminal=1\n',encoding='utf16')
        process=subprocess.Popen(f'"{target/"terminal64.exe"}" /portable /config:"{ini}"',startupinfo=startup)
        try:process.wait(timeout=90)
        except subprocess.TimeoutExpired:
            process.kill();process.wait(timeout=10);raise RuntimeError('CONTEXT_NATIVE_TIMEOUT')
        export=target/'MQL5/Files'/(run+'_oracle.csv');shutil.copyfile(export,out/export.name)
        with export.open(encoding='utf-8-sig') as stream:rows=list(csv.DictReader(stream))
        if len(rows)!=30:raise ValueError('CONTEXT_NATIVE_EXPORT_INCOMPLETE')
        atr=initial_state();ha=None;history=[];errors=[];max_k_error=0.;signals=dict(BUY=0,SELL=0);previous_k=None
        for index,(row,bar) in enumerate(zip(rows,chosen)):
            if int(row['time'])!=bar['time'] or any(float(row[k])!=bar[k] for k in ('open','high','low','close')):
                raise ValueError('CONTEXT_NATIVE_INPUT_CHANGED')
            atr=advance(atr,bar,str(index),(bar['time']+300)*1000)
            if atr['value'] is not None and atr['value']!=float(row['atr']):errors.append('ATR:'+str(index))
            hc=(bar['open']+bar['high']+bar['low']+bar['close'])/4
            ho=(bar['open']+bar['close'])/2 if ha is None else sum(ha)/2
            expected=dict(ha_open=ho,ha_close=hc,ha_high=max(bar['high'],ho,hc),ha_low=min(bar['low'],ho,hc))
            if any(float(row[k])!=v for k,v in expected.items()):errors.append('HA:'+str(index))
            ha=(ho,hc);history.append(bar);k=list(main_k(history[-7:]))[-1]
            if k is not None:max_k_error=max(max_k_error,abs(k-float(row['main_k'])))
            if k is not None and previous_k is not None:
                if previous_k<=20 and k>20:signals['BUY']+=1
                if previous_k>=80 and k<80:signals['SELL']+=1
            previous_k=k
        result=dict(status='PASS_RETROSPECTIVE_CONTEXT_DIAGNOSTIC' if not errors and max_k_error<=1e-10 else 'FAILED_PARITY',
            origin='RETROSPECTIVE_XM_ARCHIVE_NOT_PROSPECTIVE_RECEIPT',bars=30,atr_candidate_compared=17,
            ha_ohlc_compared=30,ha_own_ready_276=False,main_k_max_abs_error=max_k_error,diagnostic_base_signals=signals,
            failures=errors,source_sha256=sha(source),export_sha256=sha(export),archive_parents=parents,
            start_native=chosen[0]['time'],end_native_exclusive=chosen[-1]['time']+300,
            original_terminals_preserved=all(psutil.pid_exists(pid) for pid in original),
            prospective_warmup_contribution=0,dataset_admitted=False,training_executed=False,orders_sent=0)
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
        return result
