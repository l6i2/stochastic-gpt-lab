"""Bounded CopyRates/CopyTicksRange fallback in the existing isolated terminal."""
import csv
import json
from pathlib import Path
import shutil
import subprocess
import uuid

from controller.authorized_capture import manager_lock,sha
from controller.native_diagnostic import BASE
from controller.xm_history_recovery import permitted,validate_rows


def source(start,end,run):
    return r'''#property strict
const string RUN="__RUN__";
const ulong FIRST=__FIRST__, LAST=__LAST__;
int R1=0,E1=0,R5=0,E5=0;
void Rates(ENUM_TIMEFRAMES frame,string name,int seconds){
 int file=FileOpen(RUN+"_"+name+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',',CP_UTF8);
 FileWrite(file,"time","open","high","low","close","tick_volume","spread","real_volume");
 long first=((long)FIRST+seconds*1000-1)/(seconds*1000)*seconds;
 long last=((long)LAST+1)/1000-seconds;
 MqlRates rows[];ResetLastError();int n=0;
 if(first<=last)n=CopyRates("US30Cash",frame,(datetime)first,(datetime)last,rows);
 int error=GetLastError();if(seconds==60){R1=n;E1=error;}else{R5=n;E5=error;}
 for(int i=0;i<n;i++)FileWrite(file,(long)rows[i].time,DoubleToString(rows[i].open,16),DoubleToString(rows[i].high,16),DoubleToString(rows[i].low,16),DoubleToString(rows[i].close,16),rows[i].tick_volume,rows[i].spread,rows[i].real_volume);
 FileFlush(file);FileClose(file);
 Print("HISTORY_RESULT ",name," ",n," ",error);
}
void OnStart(){
 if(AccountInfoInteger(ACCOUNT_TRADE_MODE)!=ACCOUNT_TRADE_MODE_DEMO||AccountInfoString(ACCOUNT_SERVER)!="XMGlobalSC-MT5 5"||TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)||MQLInfoInteger(MQL_TESTER)||SymbolInfoInteger("US30Cash",SYMBOL_CUSTOM))return;
 Rates(PERIOD_M1,"m1",60);Rates(PERIOD_M5,"m5",300);
 int file=FileOpen(RUN+"_ticks.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',',CP_UTF8);
 FileWrite(file,"time","bid","ask","last","volume","time_msc","flags","volume_real");
 MqlTick ticks[];ResetLastError();int n=CopyTicksRange("US30Cash",ticks,COPY_TICKS_ALL,FIRST,LAST);
 int tickerror=GetLastError();
 if(n>250000){FileClose(file);return;}
 for(int i=0;i<n;i++)FileWrite(file,(long)ticks[i].time,DoubleToString(ticks[i].bid,16),DoubleToString(ticks[i].ask,16),DoubleToString(ticks[i].last,16),ticks[i].volume,ticks[i].time_msc,ticks[i].flags,DoubleToString(ticks[i].volume_real,16));
 FileFlush(file);FileClose(file);
 int done=FileOpen(RUN+"_done.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',',CP_UTF8);
 FileWrite(done,"connected","server","tester","ticks","error","m1_count","m1_error","m5_count","m5_error");
 FileWrite(done,TerminalInfoInteger(TERMINAL_CONNECTED),AccountInfoString(ACCOUNT_SERVER),MQLInfoInteger(MQL_TESTER),n,tickerror,R1,E1,R5,E5);
 FileFlush(done);FileClose(done);
}
'''.replace('__RUN__',run).replace('__FIRST__',str(start)).replace('__LAST__',str(end-1))


def recover(root,policy,start,end,out):
    permitted(start,end,policy)
    import psutil
    if psutil.virtual_memory().available<768*1024*1024:
        raise RuntimeError('NATIVE_FALLBACK_MEMORY_BOUND')
    root=Path(root);out=Path(out);target=BASE/'terminal'
    programs=json.loads((BASE/'isolation_checkpoint.json').read_text())['program_hashes']
    for name,digest in programs.items():
        if sha(target/name)!=digest:raise ValueError('ISOLATED_TERMINAL_CHANGED')
    for p in psutil.process_iter(['exe']):
        if (p.info.get('exe') or '').lower()==str(target/'terminal64.exe').lower():
            raise RuntimeError('ISOLATED_TERMINAL_BUSY')
    originals={p.pid for p in psutil.process_iter(['name']) if p.info['name']=='terminal64.exe'}
    run='xmhist_'+uuid.uuid4().hex[:8]
    out=out/run
    with manager_lock(root/'outputs/cf_own_indicator_oracle'):
        scripts=target/'MQL5/Scripts/ResearchDiagnostics'/run;scripts.mkdir(parents=True)
        program=scripts/'HistoryRecovery.mq5';program.write_text(source(start,end,run),encoding='utf8')
        out.mkdir(parents=True,exist_ok=True)
        startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        log=out/'compile.log'
        subprocess.run(f'"C:/Program Files/XM Global SC MT5 Terminal/metaeditor64.exe" /compile:"{program}" /log:"{log}"',startupinfo=startup,timeout=90)
        if '0 errors, 0 warnings' not in log.read_text(encoding='utf16'):
            raise RuntimeError('HISTORICAL_NATIVE_COMPILE_FAILED')
        ini=out/'native.ini';ini.write_text('[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\n[StartUp]\nScript=ResearchDiagnostics\\'+run+'\\HistoryRecovery\nSymbol=US30Cash\nPeriod=M5\nShutdownTerminal=1\n',encoding='utf16')
        process=subprocess.Popen(f'"{target/"terminal64.exe"}" /portable /config:"{ini}"',startupinfo=startup)
        try:process.wait(timeout=90)
        except subprocess.TimeoutExpired:
            process.kill();process.wait(timeout=10);raise RuntimeError('ISOLATED_HISTORY_TIMEOUT')
        if not all(psutil.pid_exists(pid) for pid in originals):raise RuntimeError('ORIGINAL_TERMINAL_NOT_PRESERVED')
        done=target/'MQL5/Files'/(run+'_done.csv')
        if not done.exists():raise RuntimeError('NATIVE_HISTORY_IDENTITY_OR_COMPLETION_MISSING')
        shutil.copyfile(done,out/'completion.csv')
        with done.open(encoding='utf-8-sig') as stream:completion=list(csv.DictReader(stream))[0]
        if completion['server']!='XMGlobalSC-MT5 5' or completion['tester']!='0':raise ValueError('NATIVE_HISTORY_SOURCE_CHANGED')
        if completion['connected']!='1':raise RuntimeError('ISOLATED_NATIVE_HISTORY_DISCONNECTED')
        result={}
        for kind in ('m1','m5','ticks'):
            file=target/'MQL5/Files'/(run+'_'+kind+'.csv');shutil.copyfile(file,out/file.name)
            with file.open(encoding='utf-8-sig') as stream:rows=list(csv.DictReader(stream))
            integer={'time','time_msc','flags','volume','tick_volume','spread','real_volume'}
            rows=[{k:int(v) if k in integer else float(v) for k,v in row.items()} for row in rows]
            validate_rows(rows,kind,start,end)
            result[kind]=rows
        result['evidence']=dict(api='MQL5_COPYRATES_COPYTICKSRANGE',source_sha256=sha(program),
            ex5_sha256=sha(program.with_suffix('.ex5')),completion=completion,
            original_terminals_preserved=True,orders_sent=0,tester_used=False)
        return result
