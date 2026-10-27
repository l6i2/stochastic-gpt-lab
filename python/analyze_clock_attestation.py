"""Analyze one completed local capture; observations never certify broker offsets."""
import argparse
import csv
import hashlib
import math
import json
from pathlib import Path
from finalize_clock_capture import finalize


def analyze(folder: Path) -> dict:
    manifest = json.loads((folder / 'run.json').read_text(encoding='utf-8'))
    native, markers, script = (Path(manifest[k]) for k in ('native', 'markers', 'script'))
    marker_text = markers.read_text(encoding='utf-8-sig')
    run_id = manifest['run_id']
    for marker in ('CLOCK_ATTESTATION_BEGIN', 'CLOCK_ATTESTATION_END'):
        if f'{marker}|run={run_id}|' not in marker_text:
            raise ValueError('MISSING_OR_WRONG_RUN_MARKER')
    with native.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        stamps = [int(row[k]) for k in ('mono_start_ms', 'gmt_before_mono_ms', 'local_mono_ms',
                  'gmt_mono_ms', 'current_mono_ms', 'server_mono_ms', 'tick_mono_ms', 'mono_end_ms')]
        if stamps != sorted(stamps) or min(stamps) < 0:
            raise ValueError('NATIVE_INTERNAL_MONOTONIC_ORDER')
        bid, ask = float(row['bid']), float(row['ask'])
        if not math.isfinite(bid) or not math.isfinite(ask) or not 0 < bid <= ask:
            raise ValueError('INVALID_NATIVE_QUOTE')
    if (folder / 'audit.json').exists():
        hashes = json.loads((folder / 'hashes.json').read_text())
        for key, path in (('source_sha256', script), ('ex5_sha256', script.with_suffix('.ex5')),
                          ('capture_sha256', folder / 'capture.json'), ('native_csv_sha256', native),
                          ('markers_sha256', markers)):
            if hashlib.sha256(path.read_bytes()).hexdigest() != hashes[key]:
                raise ValueError('RESUME_EVIDENCE_HASH_MISMATCH')
        audit_raw = (folder / 'audit.json').read_bytes()
        if hashlib.sha256(audit_raw).hexdigest() != (folder / 'audit.json.sha256').read_text().strip():
            raise ValueError('RESUME_AUDIT_HASH_MISMATCH')
        result = json.loads(audit_raw)
    else:
        result = finalize(folder, native, markers, script, manifest['build'])
    # Separate capture/readiness from actual operational acceptance.
    result['clock_attestation'] = ('PASS' if result['windows_clock_sync'] == 'PASS'
                                  and result['simultaneous_overlap'] == 'PASS' else 'FAIL')
    result['native_to_utc_mapping'] = 'LOCAL_EXTERNAL_EVIDENCE_REQUIRED'
    result['causal_audit'] = 'LOCAL_REQUIRED'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.folder)
    with (args.folder / 'analysis.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
    print(json.dumps(result))
    return 0 if result['clock_attestation'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
