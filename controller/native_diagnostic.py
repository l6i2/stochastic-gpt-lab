"""One fixed TRAIN-era technical replay in an isolated portable XM terminal.

No scientific admission, strategy selection, trading API or active-terminal stop.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import uuid
from .artifact_collector import atomic_json
from .cold_start import redact
from .compile_runner import sha256
from .profiles import BAR_EA
from .safety_gate import ROOT, assert_safe_source
from .tester_config import preset,write_preset,tester_end

BASE=ROOT/'outputs/pc_a_certification/native_tester'
DATA_NAME='20C285FE08971A9A2E814AAC44AFC9D2'
SERVER='XMGlobalSC-MT5 5'
DAY='2024-01-02'
DIAGNOSTIC_EA='NativeTesterDiagnosticEA'


def assert_diagnostic(start,end):
    # Explicit fixed smoke, documented inside historical TRAIN (not another
    # search on TRAIN). No missing split manifest is fabricated or unlocked.
    if start!=DAY or end!=DAY:raise ValueError('ONLY_FIXED_AUTHORIZED_TECHNICAL_SMOKE')


def configuration(run_id,start=DAY,end=DAY):
    assert_diagnostic(start,end)
    if not re.fullmatch(r'diag_[a-f0-9]{12}',run_id):raise ValueError('INVALID_DIAGNOSTIC_ID')
    values=dict(Expert='NativeDiagnostic\\'+DIAGNOSTIC_EA+'.ex5',ExpertParameters=run_id+'.set',Symbol='US30Cash',
        Period='M5',Model=4,FromDate=start.replace('-','.'),ToDate=tester_end(end),Optimization=0,ForwardMode=0,
        Deposit=10000,Currency='USD',Report='reports\\'+run_id+'.htm',ReplaceReport=0,ShutdownTerminal=1,
        Visual=0,UseLocal=1,UseRemote=0,UseCloud=0,ExecutionMode=0)
    return '[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\n[Tester]\n'+''.join(f'{k}={v}\n' for k,v in values.items())


def prepare(environment):
    if not environment.get('SAFE_FOR_RESEARCH') or environment.get('ACCOUNT_MODE')!='DEMO':raise ValueError('PINNED_XM_DEMO_REQUIRED')
    source=Path(environment['DATA_FOLDER']).resolve();install=Path(environment['TERMINAL_PATH']).parent.resolve()
    if source.name!=DATA_NAME or install.name!='XM Global SC MT5 Terminal':raise ValueError('ENVIRONMENT_IDENTITY_MISMATCH')
    target=BASE/'terminal';target.mkdir(parents=True,exist_ok=True)
    import psutil
    for p in psutil.process_iter(['name','exe']):
        if (p.info['name'] or '').lower()=='terminal64.exe' and Path(p.info['exe'] or '').resolve()==(target/'terminal64.exe').resolve():raise RuntimeError('ISOLATED_TERMINAL_ALREADY_RUNNING_USE_CHECKPOINT')
    copied={}
    def copy(a,b,mutable=False):
        b.parent.mkdir(parents=True,exist_ok=True)
        if b.exists() and mutable:return
        if not b.exists():shutil.copy2(a,b)
        if sha256(a)!=sha256(b):raise ValueError('ISOLATED_COPY_HASH_MISMATCH')
        copied[str(b.relative_to(target))]=sha256(b)
    for name in ('terminal64.exe','metatester64.exe'):
        copy(install/name,target/name)
    # Existing encrypted local account cache stays private under ignored outputs.
    # No passwords/tokens are read, printed, serialized or published by us.
    for name in ('accounts.dat','servers.dat','common.ini'):
        copy(source/'config'/name,target/'Config'/name,mutable=True)
    server=source/'bases'/SERVER
    for file in (server/'symbols').glob('*.dat'):copy(file,target/'Bases'/SERVER/'symbols'/file.name,mutable=True)
    for name in ('2023.hcc','2024.hcc'):
        copy(server/'history/US30Cash'/name,target/'Bases'/SERVER/'history/US30Cash'/name,mutable=True)
    copy(server/'ticks/US30Cash/202401.tkc',target/'Bases'/SERVER/'ticks/US30Cash/202401.tkc',mutable=True)
    expert=target/'MQL5/Experts/NativeDiagnostic';expert.mkdir(parents=True,exist_ok=True)
    for name in (BAR_EA+'.mq5','ResearchCore.mqh','HeikinAshiCore.mqh',DIAGNOSTIC_EA+'.mq5'):
        assert_safe_source(ROOT/'mt5'/name) if name==BAR_EA+'.mq5' else None
        text=(ROOT/'mt5'/name).read_text()
        if re.search(r'\b(OrderSend|OrderSendAsync|CTrade|PositionOpen)\b',text,re.I):raise ValueError('TRADING_API_FORBIDDEN')
        copy(ROOT/'mt5'/name,expert/name)
    (target/'reports').mkdir(exist_ok=True);(target/'MQL5/Profiles/Tester').mkdir(parents=True,exist_ok=True)
    atomic_json(BASE/'isolation_checkpoint.json',dict(program_hashes={n:copied[n] for n in ('terminal64.exe','metatester64.exe')},
        expert_source_sha256=sha256(expert/(BAR_EA+'.mq5')),private_local_cache_only=True,
        source_years=[2023,2024],tick_months=['202401'],active_terminal_untouched=True,orders_sent=0))
    return target


def compile_expert(environment,target):
    folder=BASE/('compile_'+uuid.uuid4().hex[:12]);folder.mkdir(parents=True)
    log=folder/'compile.log';source=target/'MQL5/Experts/NativeDiagnostic'/(DIAGNOSTIC_EA+'.mq5')
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    started=time.time_ns()
    subprocess.run(f'"{environment["METAEDITOR_PATH"]}" /compile:"{source}" /log:"{log}"',startupinfo=startup,timeout=90)
    text=log.read_text(encoding='utf-16')
    if '0 errors, 0 warnings' not in text or not source.with_suffix('.ex5').exists() or source.with_suffix('.ex5').stat().st_mtime_ns<started-2000000000:raise RuntimeError('NATIVE_DIAGNOSTIC_COMPILE_FAILED')
    return dict(expert_name=DIAGNOSTIC_EA,source_sha256=sha256(source),ex5_sha256=sha256(source.with_suffix('.ex5')),compile_log_sha256=sha256(log),errors=0,warnings=0)


def launch(target,compiled):
    expert=target/'MQL5/Experts/NativeDiagnostic'
    if sha256(expert/(DIAGNOSTIC_EA+'.ex5'))!=compiled['ex5_sha256'] or sha256(expert/(DIAGNOSTIC_EA+'.mq5'))!=compiled['source_sha256']:raise ValueError('DIAGNOSTIC_BINARY_OR_SOURCE_CHANGED')
    for name in (BAR_EA+'.mq5','ResearchCore.mqh','HeikinAshiCore.mqh',DIAGNOSTIC_EA+'.mq5'):
        if sha256(expert/name)!=sha256(ROOT/'mt5'/name):raise ValueError('FROZEN_STRATEGY_OR_WRAPPER_COPY_CHANGED')
    run_id='diag_'+uuid.uuid4().hex[:12];folder=BASE/'runs'/run_id;folder.mkdir(parents=True)
    inputs=preset(run_id,BAR_EA);write_preset(target/'MQL5/Profiles/Tester'/(run_id+'.set'),inputs)
    ini=folder/'tester.ini';ini.write_text(configuration(run_id),encoding='utf-16')
    command=f'"{target / "terminal64.exe"}" /portable /config:"{ini.resolve()}"'
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    logs_before={str(p.relative_to(target)):p.stat().st_size for p in diagnostic_logs(target)}
    started=time.time_ns();p=subprocess.Popen(command,startupinfo=startup)
    record=dict(run_id=run_id,pid=p.pid,started_host_ns=started,start=DAY,end=DAY,model=4,logs_before=logs_before,
        optimization=False,live_trading=False,orders_sent=0,inputs=inputs,compiled=compiled,
        ini_sha256=sha256(ini),preset_sha256=sha256(target/'MQL5/Profiles/Tester'/(run_id+'.set')),
        status='RUNNING',scientific_admission=False,command=command)
    atomic_json(folder/'run_manifest.json',record);return record


def diagnostic_logs(target):
    for directory in [target/'logs',target/'Tester/logs',target/'MQL5/Logs']+list((target/'Tester').glob('Agent-*/logs')):
        yield from directory.glob('*.log')


def inspect(run_id):
    if not re.fullmatch(r'diag_[a-f0-9]{12}',run_id):raise ValueError('INVALID_DIAGNOSTIC_ID')
    folder=BASE/'runs'/run_id;record=json.loads((folder/'run_manifest.json').read_text());target=BASE/'terminal'
    if record.get('status')=='COMPLETE' and record.get('artifacts'):
        for name,digest in record['artifacts'].items():
            if Path(name).name!=name or sha256(folder/name)!=digest:raise ValueError('DIAGNOSTIC_CHECKPOINT_ARTIFACT_CHANGED')
        return record
    logs=[]
    for path in diagnostic_logs(target):
        if path.stat().st_mtime_ns<record['started_host_ns'] or path.stat().st_size>20000000:continue
        data=path.read_bytes();offset=record.get('logs_before',{}).get(str(path.relative_to(target)),0)
        if offset>len(data):raise ValueError('DIAGNOSTIC_LOG_TRUNCATED')
        data=data[offset:];text=data.decode('utf-16' if data.startswith(b'\xff\xfe') else 'utf-16-le' if b'\0' in data[:80] else 'utf-8-sig',errors='replace')
        logs.append(text)
        safe_name='__'.join(path.relative_to(target).parts)
        (folder/safe_name).write_text(redact(text),encoding='utf-8')
    text='\n'.join(logs)
    artifacts={p.name:sha256(p) for p in folder.glob(run_id+'_*') if p.is_file()}
    for path in target.rglob(run_id+'_*'):
        if path.is_file():
            destination=folder/path.name
            if destination.exists() and sha256(destination)!=sha256(path):continue
            if not destination.exists():shutil.copy2(path,destination)
            artifacts[path.name]=sha256(destination)
    report=target/'reports'/(run_id+'.htm')
    if report.exists():
        destination=folder/report.name
        if not destination.exists():shutil.copy2(report,destination)
        artifacts[report.name]=sha256(destination)
    required=[run_id+'_'+s for s in ('bar_quote_path.bin','bar_trade_index.csv','intratrade_snapshots.csv','stochastic_events.csv')]
    if record['compiled'].get('expert_name')==DIAGNOSTIC_EA:
        required += [run_id+'_stochastic_events.csv.native_'+s+'.csv' for s in ('M1','M5','main')]
    complete=bool('test passed' in text.lower() and all(n in artifacts for n in required) and report.exists()
        and '2024.01.02' in text and SERVER in text and 'generating based on real ticks' in text.lower()
        and not re.search(r'FATAL RESEARCH RUN|initialization.*failed',text,re.I))
    record.update(status='COMPLETE' if complete else 'RUNNING_OR_BLOCKED',
        terminal_test_passed='test passed' in text.lower(),artifacts=artifacts,
        diagnostics=[redact(line) for line in text.splitlines() if re.search('generated|discard|real ticks|ticks generated|history|error|failed|no connection',line,re.I)][-70:])
    atomic_json(folder/'run_manifest.json',record);return record


def smoke(resume=False,timeout=180):
    """Single-command automation, with restartable checkpoints, never scheduled."""
    checkpoint=BASE/'smoke_checkpoint.json'
    if resume:
        state=json.loads(checkpoint.read_text())
    else:
        from .mt5_env import status
        environment=status();target=prepare(environment);compiled=compile_expert(environment,target)
        state=dict(compiled=compiled,runs=[],active=None,scientific_admission=False)
    while len(state['runs'])<2:
        if state['active'] is None:
            launched=launch(BASE/'terminal',state['compiled']);state['active']=launched['run_id'];atomic_json(checkpoint,state)
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            observed=inspect(state['active'])
            if observed['status']=='COMPLETE':break
            time.sleep(2)
        else:
            raise RuntimeError('DIAGNOSTIC_TIMEOUT_USE_RESUME_CHECKPOINT_PROCESS_NOT_TERMINATED')
        state['runs'].append(state['active']);state['active']=None;atomic_json(checkpoint,state)
    from .native_reconciliation import reconcile
    result=reconcile(*state['runs']);atomic_json(BASE/'reconciliation.json',result)
    return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--resume',action='store_true')
    args=parser.parse_args();print(json.dumps(smoke(args.resume),indent=2))
