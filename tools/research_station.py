"""Manage PC A raw quarantine collection; all scientific gates stay closed."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'python'))
import pc_a_raw_archive as raw

TASK = 'StochasticGPTLab_PC_A_RawQuarantine_v1'
REPORT = ROOT / 'outputs/pc_a/raw_station_status.json'
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def archive(action):
    result = subprocess.run([str(ROOT / '.venv/Scripts/python.exe'), str(ROOT / 'python/pc_a_raw_archive.py'), action],
                            cwd=ROOT, capture_output=True, text=True, timeout=600, creationflags=NO_WINDOW)
    if result.returncode:
        # Exception names/reasons only, not broker/account objects.
        reason = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else 'ARCHIVE_FAILED'
        raise RuntimeError(reason)
    return json.loads(result.stdout)


def scheduler(action):
    script = ROOT / 'tools/pc_a_archive_schedule.ps1'
    result = subprocess.run(['powershell.exe', '-NoProfile', '-File', str(script), '-Action', action],
                            cwd=ROOT, capture_output=True, text=True, timeout=45, creationflags=NO_WINDOW)
    if result.returncode:
        raise RuntimeError('TASK_SCHEDULER_' + action.upper() + '_FAILED')
    return result.stdout.strip()


def backup():
    destination = ROOT / 'outputs/pc_a_raw_backup'
    count = 0
    for pointer in ('active.json', 'historical_active.json'):
        path = raw.BASE / pointer
        if not path.exists():
            continue
        archive_id = json.loads(path.read_text())['archive_id']
        if Path(archive_id).name != archive_id:
            raise RuntimeError('INVALID_ARCHIVE_POINTER')
        folder = raw.BASE / archive_id
        state = raw.verify(folder)
        target = destination / archive_id
        target.mkdir(parents=True, exist_ok=True)
        for segment in state['segments']:
            for kind in ('ticks', 'bars'):
                item = segment[kind]
                copy = target / item['file']
                if not copy.exists():
                    shutil.copyfile(folder / item['file'], copy)
                if raw.sha(copy) != item['sha256']:
                    raise RuntimeError('BACKUP_HASH_MISMATCH')
                count += 1
        raw.atomic(target / 'manifest.json', state)
        raw.atomic(destination / pointer, dict(archive_id=archive_id))
    return dict(status='VERIFIED_LOCAL_COPY', files=count, independent_failure_domain=False)


def report(error=None, scheduling=None):
    state = None
    pointer = raw.BASE / 'active.json'
    if pointer.exists():
        state = raw.verify(raw.BASE / json.loads(pointer.read_text())['archive_id'])
    task = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
                           "$t=Get-ScheduledTask -TaskName '" + TASK + "' -ErrorAction SilentlyContinue; if($t){$i=Get-ScheduledTaskInfo -TaskName $t.TaskName; @{state=[string]$t.State;enabled=[bool]$t.Settings.Enabled;last_result=$i.LastTaskResult;last_run=$i.LastRunTime.ToUniversalTime().ToString('o')}|ConvertTo-Json -Compress}"],
                          capture_output=True, text=True, timeout=30, creationflags=NO_WINDOW)
    task_status = json.loads(task.stdout) if task.returncode == 0 and task.stdout.strip() else {'state': 'UNKNOWN'}
    capture = 'BLOCKED' if error or not state else 'ACTIVE' if state['last_success_utc'] else 'READY'
    if task_status.get('enabled') is False or task_status['state'] == 'Disabled':
        capture = 'PAUSED'
    result = dict(observed_utc=datetime.now(timezone.utc).isoformat(),
                  raw_capture=capture,
                  new_cohort='BLOCKED_SCIENTIFIC_ACCEPTANCE',
                  archive_id=state['archive_id'] if state else None,
                  new_start_utc=state['new_start_utc'] if state else None,
                  segments=len(state['segments']) if state else 0,
                  last_success_utc=state['last_success_utc'] if state else None,
                  previous_cohort_continuity='UNVERIFIED', native_to_utc_mapping='FAIL_UNVERIFIED',
                  training_readiness='BLOCKED_BY_RESEARCH_GOVERNANCE',
                  low_memory_mode=True, best_candidate='NONE', discovery_validation='BLOCKED',
                  final_test='LOCKED', demo='DISABLED', live_trading=False,
                  orders_sent=0, error=error, scheduler_action=scheduling, scheduler=task_status)
    raw.atomic(REPORT, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('start', 'stop', 'resume', 'verify', 'collect', 'validate', 'reports', 'historical'))
    args = parser.parse_args()
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[key] = '1'
    os.environ['LOW_MEMORY_MODE'] = 'true'
    scheduling = None
    try:
        if args.action in ('start', 'resume'):
            if not (raw.BASE / 'active.json').exists():
                archive('activate')
            else:
                archive('verify')
            scheduling = scheduler('start')
            archive('collect')
        elif args.action == 'stop':
            scheduling = scheduler('stop')
        elif args.action in ('collect', 'historical'):
            archive(args.action)
        else:
            archive('verify')
        result = report(scheduling=scheduling)
        result['backup'] = backup()
        if args.action in ('start', 'resume', 'collect'):
            retry = subprocess.run([str(ROOT / '.venv/Scripts/python.exe'), str(ROOT / 'tools/retry_m5_repair.py')],
                                   cwd=ROOT, capture_output=True, text=True, timeout=330, creationflags=NO_WINDOW)
            result['m5_repair_retry_exit_code'] = retry.returncode
        raw.atomic(REPORT, result)
    except Exception as exc:
        result = report(error=str(exc), scheduling=scheduling)
        print(json.dumps(result, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
