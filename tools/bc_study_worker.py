"""Versioned operational wrapper: bounded IPC retry, no scientific changes."""
import argparse,json,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import bc_study_station as station
from controller.authorized_capture import sha,once
from controller.isolated_observation import host_clock,atomic
from tools.prospective_pipeline import NativeReference


class RecoveryReference(NativeReference):
    def connect(self):
        try:return super().connect()
        except ValueError as exc:
            if str(exc)!='XM_READ_ONLY_ATTACH_FAILED':raise
        import MetaTrader5 as api,psutil
        expected='C:/Program Files/XM Global SC MT5 Terminal/terminal64.exe'
        matches=[p.pid for p in psutil.process_iter(['exe']) if (p.info.get('exe') or '').replace('\\','/').lower()==expected.lower()]
        if len(matches)!=1:raise RuntimeError('BC_IPC_RECOVERY_AMBIGUOUS_TERMINAL')
        first=api.last_error();api.shutdown();before=host_clock()
        if not api.initialize(path=expected,timeout=20000):
            raise RuntimeError('BC_BOUNDED_IPC_RETRY_FAILED:'+str(api.last_error())+';first='+str(first))
        self.mt5=api;self.bound_pid=matches[0]
        try:
            checked=station.identity(self);self.step=str(checked['tick_size'])
            if not psutil.pid_exists(matches[0]):raise RuntimeError('BC_TERMINAL_CHANGED_DURING_ATTACH')
        except BaseException:self.close();raise
        once(station.BASE/'incidents'/('ipc_recovered_'+uuid.uuid4().hex+'.json'),dict(
            first_error=first,second_attach_timeout_ms=20000,before=before,after=host_clock(),
            original_terminal_pid=matches[0],terminal_restarted=False,
            root_cause='TRANSIENT_IPC_DELAY_CAUSE_UNPROVEN',no_scientific_tolerance_added=True))


def run(budget=6):
    record=station.PACKAGE/'operational_wrapper_v2.json'
    pin=json.loads(record.read_bytes())
    if (pin['activation_sha256']!=sha(station.PACKAGE/'activation.json')
            or pin['wrapper_sha256']!=sha(__file__)
            or pin['authorization_sha256']!=sha(station.PACKAGE/'authorization.json')
            or pin['scope']!='BOUNDED_IPC_ATTACH_ONLY_NO_SCIENTIFIC_CHANGE'):
        raise ValueError('BC_OPERATIONAL_WRAPPER_CHANGED')
    station.NativeReference=RecoveryReference
    return station.run(budget)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--budget',type=int,default=6);args=parser.parse_args()
    if not 1<=args.budget<=24:parser.error('budget must be 1..24')
    try:print(json.dumps(run(args.budget)))
    except Exception as exc:
        failure=dict(clock=host_clock(),error=type(exc).__name__+':'+str(exc),retry_safe=True,training_executed=False,LIVE_TRADING=False)
        once(station.BASE/'incidents'/('failure_'+uuid.uuid4().hex+'.json'),failure)
        atomic(station.BASE/'runtime_failure.json',failure)
        raise
