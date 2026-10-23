"""Finalize one observed capture automatically; never opens evaluation/trading gates."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import shutil
import time

from simultaneous_clock_audit import audit_overlap


def finalize(folder: Path, native: Path, markers: Path, script: Path, build: dict) -> dict:
    if (folder / 'audit.json').exists():
        raise FileExistsError('Preserve completed audit; no overwrite')
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    if sha(script) != build['source_sha256'] or sha(script.with_suffix('.ex5')) != build['ex5_sha256']:
        raise ValueError('NATIVE_SOURCE_OR_EXECUTABLE_CHANGED')
    capture = json.loads((folder / 'capture.json').read_text(encoding='utf-8'))
    with native.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 150 or rows != [r for p in capture['paired_frames'] for r in p['native']]:
        raise ValueError('NATIVE_CSV_AND_CAPTURE_MISMATCH')
    text = markers.read_text(encoding='utf-8-sig')
    end_ok = 'CLOCK_ATTESTATION_BEGIN' in text and 'CLOCK_ATTESTATION_END' in text
    audit = audit_overlap(capture, end_marker_present=end_ok)
    audit.update(manual_action_required='NONE', final_test='LOCKED', demo='DISABLED',
                 discovery_validation='BLOCKED', live_trading=False,
                 next_state='HARD_BLOCKER_CLOCK_ATTESTATION_AND_MAPPING',
                 historical_dataset_impact='NONE', scoring_performed=False)
    hashes = {'source_sha256': sha(script), 'ex5_sha256': sha(script.with_suffix('.ex5')),
              'capture_sha256': sha(folder / 'capture.json'),
              'native_csv_sha256': sha(native), 'markers_sha256': sha(markers)}
    shutil.copyfile(native, folder / 'native.csv')
    shutil.copyfile(markers, folder / 'markers.txt')
    for name, payload in (('audit.json', audit), ('hashes.json', hashes)):
        (folder / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    (folder / 'audit.json.sha256').write_text(sha(folder / 'audit.json') + '\n', encoding='ascii')
    return audit


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, required=True)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--markers', type=Path, required=True)
    parser.add_argument('--script', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    args = parser.parse_args()
    print('FINALIZER_ARMED_NO_EXPIRY', flush=True)
    while not (args.folder / 'capture.json').exists():
        time.sleep(.2)
    result = finalize(args.folder, args.native, args.markers, args.script,
                      json.loads(args.build.read_text(encoding='utf-8')))
    print(json.dumps(result), flush=True)
