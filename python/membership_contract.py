"""Explain frozen-universe endpoint gaps without adding research observations."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def derive(root=ROOT):
    """Read only original pre-FINAL_TEST 2024/2025 source identity metadata."""
    root = Path(root)
    master = root/'outputs/master/master_manifest.json'
    frozen = json.loads(master.read_text())
    pinned = set(frozen['source_block_manifest_hashes'])
    split = root/'outputs/splits/split_manifest.json'
    final = json.loads(split.read_text())['boundaries']['final_test_start_signal_time_msc']
    days = []
    for year in (2024, 2025):
        folder = root/'outputs/history/raw'/str(year)
        manifest_path = folder/'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        source = folder/'stochastic_events.csv'
        canonical_hash = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
        if canonical_hash not in pinned or digest(source) != manifest['csv_sha256']:
            raise ValueError('Frozen endpoint evidence hash mismatch')
        start = int(datetime(year, 12, 31, tzinfo=timezone.utc).timestamp()*1000)
        end = int(datetime(year+1, 1, 1, tzinfo=timezone.utc).timestamp()*1000)
        if end > final or manifest['period'] != f'{year}-01-01..{year}-12-31':
            raise ValueError('Endpoint quarantine is outside the allowed frozen evidence contract')
        count = 0
        latest = 0
        with source.open(encoding='utf-8-sig', newline='') as stream:
            for row in csv.DictReader(stream):
                stamp = int(row['signal_time_msc'])
                if stamp >= start:
                    raise ValueError('Frozen source already contains endpoint day; quarantine forbidden')
                latest = max(latest, stamp)
                count += 1
        if count != manifest['signals'] or count == 0:
            raise ValueError('Frozen source signal count differs')
        days.append(dict(date=f'{year}-12-31', start_msc=start, end_exclusive_msc=end,
                         canonical_manifest=str(manifest_path.relative_to(root)),
                         canonical_manifest_sha256=digest(manifest_path),
                         canonical_csv_sha256=digest(source), canonical_signals=count,
                         last_canonical_signal_msc=latest))
    return dict(action='EXCLUDE_FROM_RESEARCH_PRESERVE_FROZEN_SIGNAL_UNIVERSE',
                split_manifest_sha256=digest(split), master_manifest_sha256=digest(master),
                final_test_accessed=False, split_boundaries_changed=False,
                selection_uses_outcomes=False, days=days)


def quarantine_windows(path, split_path, root=ROOT):
    if not Path(path).exists():
        return []
    recorded = json.loads(Path(path).read_text())
    if recorded != derive(root) or recorded['split_manifest_sha256'] != digest(split_path):
        raise ValueError('Frozen membership quarantine evidence changed')
    return [(d['start_msc'], d['end_exclusive_msc']) for d in recorded['days']]


if __name__ == '__main__':
    result = derive()
    target = ROOT/'outputs/controller/checkpoints/membership_quarantine.json'
    if target.exists() and json.loads(target.read_text()) != result:
        raise ValueError('Refusing to replace a different frozen-universe contract')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
