"""Supervise only the newly authorized quarantine capture. No trading APIs."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from controller.authorized_capture import CaptureManager,STATION,NATIVE,manager_lock,sha
from controller.isolated_observation import atomic,host_clock


def verify_deployment():
    current=STATION/'deployment_pin_current.json'
    if current.exists():
        ref=json.loads(current.read_text());path=STATION/'deployment_pins'/ref['file']
        if Path(ref['file']).name!=ref['file'] or sha(path)!=ref['sha256']:raise ValueError('DEPLOYMENT_PIN_POINTER_CHANGED')
    else:path=STATION/'deployment_pin.json'
    pin=json.loads(path.read_text())
    for relative,expected in pin['files'].items():
        path=(ROOT/relative).resolve()
        if not path.is_relative_to(ROOT.resolve()) or sha(path)!=expected:
            raise ValueError('DEPLOYED_CAPTURE_CODE_CHANGED_'+relative)
    observer=NATIVE.parents[2]/'Experts/ResearchDiagnostics/ProspectiveUtcObserver.mq5'
    if sha(observer)!=pin['native_observer_source_sha256'] or sha(observer.with_suffix('.ex5'))!=pin['native_observer_ex5_sha256']:
        raise ValueError('PINNED_NATIVE_OBSERVER_CHANGED')


def main(serve=False,status_only=False):
    verify_deployment()
    manager=CaptureManager()
    if status_only:
        manager.load()
        return json.loads((manager.root/'collector_status.json').read_text())
    with manager_lock(STATION):
        manager.activate()
        failures=0
        try:
            while True:
                try:
                    status=manager.poll();failures=0
                    atomic(STATION/'supervisor_status.json',dict(status='RUNNING',capture_id=status['capture_id'],
                        process_id=__import__('os').getpid(),clock=host_clock(),collector_status=status['status'],
                        active_segment=status['active_segment'],training_authorized=False,scoring_authorized=False))
                    if not serve:return status
                    time.sleep(1)
                except (ValueError,OSError,RuntimeError) as exc:
                    manager.close();failures+=1
                    atomic(STATION/'supervisor_status.json',dict(status='RETRYING_QUARANTINED',
                        error=type(exc).__name__+':'+str(exc),clock=host_clock(),failures=failures,
                        process_id=__import__('os').getpid(),training_authorized=False,scoring_authorized=False))
                    if not serve:raise
                    time.sleep(min(30,2**min(failures,4)))
        finally:manager.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serve',action='store_true')
    parser.add_argument('--status',action='store_true')
    args=parser.parse_args()
    result=main(args.serve,args.status)
    if not args.serve:print(json.dumps(result,indent=2))
