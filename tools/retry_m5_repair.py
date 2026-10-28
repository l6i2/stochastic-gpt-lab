"""One-shot automatic M5 retry after the terminal chart limit is repaired."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'python'))
import pc_a_raw_archive as raw


def main():
    checkpoint = ROOT / 'outputs/pc_a_data_repair/chart_limit_retry.json'
    previous = json.loads(checkpoint.read_text()) if checkpoint.exists() else {}
    if previous.get('completed') is True:
        return 0
    api, server = raw.connect()
    try:
        maximum = api.terminal_info().maxbars
    finally:
        api.shutdown()
    if maximum < 500000:
        raw.atomic(checkpoint, dict(observed_utc=raw.utc(), completed=False,
                   status='WAITING_CHART_LIMIT_AND_TERMINAL_RESTART', observed_maxbars=maximum))
        return 0
    attempts = previous.get('attempts', 0) + 1
    try:
        result = subprocess.run([str(ROOT / '.venv/Scripts/python.exe'), str(ROOT / 'tools/pc_a_data_repair.py')],
                                cwd=ROOT, capture_output=True, text=True, timeout=240,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except subprocess.TimeoutExpired:
        raw.atomic(checkpoint, dict(observed_utc=raw.utc(), completed=attempts >= 3, attempts=attempts,
                                   status='DIAGNOSTIC_TIMEOUT_NO_SCIENTIFIC_ACCEPTANCE'))
        return 1
    if result.returncode:
        raw.atomic(checkpoint, dict(observed_utc=raw.utc(), completed=attempts >= 3, attempts=attempts,
                                   status='DIAGNOSTIC_FAILED', exit_code=result.returncode))
        return 1
    # Completion means the retry ran, never that its scientific audit passed.
    audit = json.loads(result.stdout)
    complete = audit['archives']['historical']['native_bars_in_range'] > 0 or attempts >= 3
    raw.atomic(checkpoint, dict(observed_utc=raw.utc(), completed=complete, attempts=attempts,
                               status='DIAGNOSTIC_COMPLETED_REVIEW_AUDIT' if complete else 'WAITING_HISTORY_SYNCHRONIZATION_RETRY',
                               observed_maxbars=maximum, historical_result=audit['archives']['historical'],
                               causal_audit=audit['causal_audit'], scientific_acceptance=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
