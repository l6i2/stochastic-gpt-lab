"""Install an actual Script launcher, keeping the OnTick EA in Experts."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
import pc_a_raw_archive as raw


def main():
    api,server=raw.connect()
    try:
        info=api.terminal_info()
        data=Path(info.data_path).resolve();installation=Path(info.path).resolve()
        if server!='XMGlobalSC-MT5 5' or info.trade_allowed:
            raise ValueError('EXACT_SERVER_AND_ALGO_DISABLED_REQUIRED')
    finally:api.shutdown()
    if installation!=Path(raw.TERMINAL).parent.resolve():raise ValueError('WRONG_XM_INSTALLATION')
    target=data/'MQL5/Scripts/ResearchDiagnostics/PC_A';target.mkdir(parents=True,exist_ok=True)
    baseline={p.name:raw.sha(p) for p in target.iterdir() if p.is_file() and not p.name.startswith('StartProspectiveUtcObserver.')}
    source=ROOT/'mt5/StartProspectiveUtcObserver.mq5'
    if re.search(r'\b(OrderSend|OrderSendAsync|CTrade|PositionOpen|CopyTicks|CopyRates|WebRequest)\b|#import|#include',source.read_text()):
        raise ValueError('UNSAFE_LAUNCHER_SOURCE')
    ea=data/'MQL5/Experts/ResearchDiagnostics/ProspectiveUtcObserver.mq5'
    if not ea.with_suffix('.ex5').is_file() or raw.sha(ea)!=raw.sha(ROOT/'mt5/ProspectiveUtcObserver.mq5'):
        raise ValueError('EXISTING_CALLBACK_EA_MISSING_OR_CHANGED')
    bundle=ROOT/'outputs/pc_a_prospective_utc/launcher_installs'/uuid.uuid4().hex;bundle.mkdir(parents=True)
    destination=target/source.name
    for old in (destination,destination.with_suffix('.ex5')):
        if old.exists():shutil.copyfile(old,bundle/('previous_'+old.name))
    shutil.copyfile(source,destination)
    template=data/'MQL5/Profiles/Templates/PC_A_ProspectiveUtcObserver.tpl'
    if template.exists():shutil.copyfile(template,bundle/'previous_template.tpl')
    shutil.copyfile(ROOT/'mt5/PC_A_ProspectiveUtcObserver.tpl',template)
    log=bundle/'compile.log';started=time.time()
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    subprocess.run(f'"{installation / "metaeditor64.exe"}" /compile:"{destination}" /log:"{log}"',startupinfo=startup,timeout=90)
    text=log.read_text(encoding='utf-16');binary=destination.with_suffix('.ex5')
    if not re.search(r'Result: 0 errors, 0 warnings',text) or not binary.is_file() or binary.stat().st_mtime<started-2:
        raise ValueError('FRESH_SCRIPT_COMPILE_REQUIRED_ZERO_ERRORS_WARNINGS')
    for name,digest in baseline.items():
        if raw.sha(target/name)!=digest:raise ValueError('PREVIOUS_SCRIPT_CHANGED')
    report=dict(SCRIPT_NAME='StartProspectiveUtcObserver',SCRIPT_MQ5_PATH=str(destination),SCRIPT_EX5_PATH=str(binary),
        COMPILE_STATUS='PASS_ZERO_ERRORS_ZERO_WARNINGS',MT5_DATA_FOLDER=str(data),INSTALL_STATUS='VERIFIED_FILES_AND_HASHES',
        MANUAL_ACTION_REQUIRED='Right-click Scripts -> Refresh',navigator_refreshed=False,
        source_sha256=raw.sha(source),installed_source_sha256=raw.sha(destination),binary_sha256=raw.sha(binary),
        template_path=str(template),template_sha256=raw.sha(template),compile_log_sha256=raw.sha(log),
        existing_ea_source_sha256=raw.sha(ea),existing_ea_binary_sha256=raw.sha(ea.with_suffix('.ex5')),
        previous_scripts_verified=baseline,script_executed=False,template_runtime_verified=False,
        independent_utc_authorized=False,orders_sent=0,live_trading=False)
    raw.atomic(bundle/'installation.json',report)
    raw.atomic(ROOT/'outputs/pc_a_prospective_utc/launcher_latest.json',dict(folder=bundle.name,report=report))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
