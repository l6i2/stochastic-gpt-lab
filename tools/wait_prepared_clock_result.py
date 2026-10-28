"""Finalize a prepared read-only capture once its Windows watcher completes."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'python'))
from local_finalize import verify_source_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, required=True)
    parser.add_argument('--source-manifest', type=Path, required=True)
    parser.add_argument('--watcher-pid', type=int, required=True)
    args = parser.parse_args()
    folder = args.folder.resolve()
    if not folder.is_relative_to(ROOT / 'outputs/local_clock_attestation'):
        raise ValueError('CAPTURE_OUTSIDE_PROJECT')
    verify_source_manifest(args.source_manifest)
    watcher = psutil.Process(args.watcher_pid)
    identity = watcher.create_time()
    while not (folder / 'capture.json').exists():
        if not watcher.is_running() or watcher.create_time() != identity:
            raise RuntimeError('WATCHER_EXITED_WITHOUT_COMPLETE_CAPTURE')
        time.sleep(1)
    verify_source_manifest(args.source_manifest)
    with (folder / 'completion_console.log').open('x', encoding='utf-8') as log:
        result = subprocess.run([sys.executable, str(ROOT / 'python/local_finalize.py'),
                                 '--resume-folder', str(folder), '--source-manifest',
                                 str(args.source_manifest.resolve())], cwd=ROOT, stdout=log, stderr=log)
    report_exists = (folder / 'final_report.json').is_file()
    (folder / 'completion_status.json').write_text(json.dumps(dict(
        analysis_exit=result.returncode, report_available=report_exists,
        operational_gates='UNCHANGED', orders_sent=0), indent=2) + '\n', encoding='utf-8')
    return 0 if report_exists else 1


if __name__ == '__main__':
    raise SystemExit(main())
