"""Audit Git seals or local manifest ancestry only; never open segment data."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_git(root=ROOT):
    tracked = subprocess.check_output(['git', 'ls-files', 'configs', 'docs'], cwd=root, text=True).splitlines()
    rows = []
    for name in tracked:
        if not name.endswith('.sha256'):
            continue
        seal = root / name
        target = seal.with_name(seal.name[:-7])
        # Some older seals use a different basename; do not guess the target.
        if not target.is_file():
            rows.append({'seal': name, 'classification': 'PARTIAL', 'reason': 'NONSTANDARD_OR_MISSING_TARGET'})
            continue
        expected = seal.read_text(encoding='ascii').split()[0]
        valid = digest(target) == expected
        rows.append({'seal': name, 'classification': 'VERIFIED' if valid else 'PARTIAL',
                     'reason': 'GIT_BYTES_MATCH' if valid else 'SEAL_MISMATCH'})
    return {'scope': 'GIT_ARTIFACT_BYTES_ONLY', 'artifacts': rows,
            'pre_anchor': 'UNVERIFIABLE_PRE_ANCHOR', 'history_reconstructed': False,
            'labels_read': False, 'pnl_read': False}


def incorporate_local(cohort_root, evidence_dir=None):
    """Follow actual hash-linked bytes in published and supplied snapshot archives.

    Supplemental files never overwrite the original ledger or cohort manifests.
    """
    root = Path(cohort_root)
    current = root / 'cohort_manifest.json'
    expected = (root / 'cohort_manifest.sha256').read_text().strip()
    if digest(current) != expected:
        raise ValueError('CURRENT_MANIFEST_HASH_MISMATCH')
    directories = [root / 'manifest_history']
    if evidence_dir is not None:
        directories.append(Path(evidence_dir))
    chain, seen = [], set()
    path = current
    while expected:
        if expected in seen or digest(path) != expected:
            raise ValueError('BROKEN_OR_CYCLIC_MANIFEST_CHAIN')
        seen.add(expected)
        item = json.loads(path.read_text())
        chain.append((expected, item))
        expected = item.get('previous_manifest_sha256')
        if not expected:
            break
        if len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
            raise ValueError('INVALID_PARENT_HASH')
        matches = [d / (expected+'.json') for d in directories if (d / (expected+'.json')).is_file()]
        if not matches:
            break
        path = matches[0]
    for (_, new), (_, old) in zip(chain, chain[1:]):
        if new.get('segments', [])[:len(old.get('segments', []))] != old.get('segments', []):
            raise ValueError('SEGMENT_HISTORY_REWRITTEN')
        for key in ('cohort_id', 'cohort_start_utc', 'symbol', 'timeframe', 'collector_code_sha256',
                    'cohort_template_sha256', 'evaluation_authorized', 'live_trading', 'train_access_allowed'):
            if new.get(key) != old.get(key):
                raise ValueError('IMMUTABLE_IDENTITY_CHANGED')
        if new.get('next_cursor_utc', '') < old.get('next_cursor_utc', ''):
            raise ValueError('CURSOR_ROLLBACK')
    return {'classification': 'VERIFIED' if expected is None else 'PARTIAL',
            'pre_anchor': 'VERIFIED' if expected is None else 'UNVERIFIABLE_PRE_ANCHOR',
            'missing_parent_sha256': expected, 'verified_manifest_hashes': [sha for sha, _ in chain],
            'scope': 'MANIFEST_BYTES_ONLY_NOT_RAW_SEGMENTS_OR_EXTERNAL_HISTORY',
            'pnl_read': False, 'labels_read': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort-root', type=Path)
    parser.add_argument('--evidence-dir', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = incorporate_local(args.cohort_root, args.evidence_dir) if args.cohort_root else audit_git()
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
