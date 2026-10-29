"""Compile and deploy only the read-only observer into the pinned XM data folder."""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
import pc_a_raw_archive as raw


def main():
    source=ROOT/'mt5/ProspectiveUtcObserver.mq5'
    text=source.read_text()
    if re.search(r'\b(OrderSend|OrderSendAsync|CTrade|PositionOpen|CopyTicks|CopyRates|WebRequest)\b|#import|#include',text):
        raise ValueError('OBSERVER_CAPABILITY_NOT_READ_ONLY_CALLBACK')
    data=Path.home()/'AppData/Roaming/MetaQuotes/Terminal'/raw.DATA_NAME
    if not (data/'MQL5').is_dir():raise ValueError('PINNED_XM_DATA_FOLDER_REQUIRED')
    destination=data/'MQL5/Experts/ResearchDiagnostics/ProspectiveUtcObserver.mq5'
    destination.parent.mkdir(parents=True,exist_ok=True)
    bundle=ROOT/'outputs/pc_a_prospective_utc/deployments'/uuid.uuid4().hex
    bundle.mkdir(parents=True)
    if destination.exists():shutil.copyfile(destination,bundle/'previous_source.mq5')
    if destination.with_suffix('.ex5').exists():shutil.copyfile(destination.with_suffix('.ex5'),bundle/'previous_binary.ex5')
    shutil.copyfile(source,destination)
    log=bundle/'compile.log'
    editor=Path(raw.TERMINAL).with_name('metaeditor64.exe')
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    subprocess.run(f'"{editor}" /compile:"{destination}" /log:"{log}"',startupinfo=startup,timeout=90)
    content=log.read_text(encoding='utf-16')
    binary=destination.with_suffix('.ex5')
    if not re.search(r'Result: 0 errors, 0 warnings',content) or not binary.is_file():
        raise RuntimeError('OBSERVER_COMPILE_FAILED')
    report=dict(source_sha256=raw.sha(source),deployed_source_sha256=raw.sha(destination),
        binary_sha256=raw.sha(binary),compile_log_sha256=raw.sha(log),compile='PASS_ZERO_ERRORS_ZERO_WARNINGS',
        attached=False,native_callbacks_observed=False,auto_trading_changed=False,dll_enabled=False,orders_sent=0)
    raw.atomic(bundle/'deployment.json',report)
    raw.atomic(ROOT/'outputs/pc_a_prospective_utc/deployment_latest.json',dict(folder=bundle.name,report=report))
    print(bundle)


if __name__=='__main__':main()
