"""Explicitly authorized bounded awake request; no Windows power profile changes."""
import argparse,ctypes,json,time
from pathlib import Path
from datetime import datetime,timezone


def run(folder):
    folder=Path(folder).resolve();auth=json.loads((folder/'authorization.json').read_text())
    if auth.get('temporary_awake_authorized') is not True or auth.get('maximum_seconds')!=1200:raise PermissionError('BOUNDED_AWAKE_AUTHORIZATION_REQUIRED')
    kernel=ctypes.windll.kernel32;kernel.SetThreadExecutionState.argtypes=[ctypes.c_uint];kernel.SetThreadExecutionState.restype=ctypes.c_uint
    started=time.monotonic();held=False
    def record(state):
        (folder/'status.json').write_text(json.dumps(dict(state=state,observed_host_utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-started,maximum_seconds=1200,power_profile_changed=False),indent=2),encoding='utf8')
    try:
        if not kernel.SetThreadExecutionState(0x80000003):raise OSError('WINDOWS_AWAKE_REQUEST_REFUSED')
        held=True;record('TEMPORARY_AWAKE_REQUEST_ACTIVE')
        while time.monotonic()-started<1200 and not (folder/'stop').exists():time.sleep(.5)
    finally:
        if held:
            released=bool(kernel.SetThreadExecutionState(0x80000000));record('RELEASED' if released else 'THREAD_EXIT_RELEASE_PENDING')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',required=True);run(p.parse_args().folder)
