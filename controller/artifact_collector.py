import json
import shutil
import time
from pathlib import Path
from .compile_runner import sha256

OUTPUTS = ('stochastic_events.csv', 'stochastic_events.csv.audit.json',
           'intratrade_snapshots.csv', 'intratrade_snapshot_targets.csv',
           'intratrade_snapshots.csv.audit.json')


def find_artifacts(environment, run_id, started):
    matches = []
    for folder in environment['TESTER_AGENT_FOLDERS']:
        files = Path(folder) / 'MQL5/Files'
        paths = [files / f'{run_id}_{name}' for name in OUTPUTS]
        if all(p.is_file() and p.stat().st_mtime >= started - 2 for p in paths):
            matches.append(paths)
    if len(matches) > 1:
        raise RuntimeError('OUTPUT_NOT_FOUND: ambiguous agent output')
    return matches[0] if matches else None


def collect(paths, run_dir):
    hashes = {}
    for source in paths:
        target = Path(run_dir) / source.name
        if target.exists():
            raise RuntimeError('OUTPUT_NOT_FOUND: destination already exists')
        shutil.copy2(source, target)
        hashes[target.name] = sha256(target)
    return hashes


def write_manifest(run_dir, manifest):
    atomic_json(Path(run_dir) / 'run_manifest.json',manifest)


def atomic_json(path, manifest):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    for attempt in range(20):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.1 * (attempt + 1))
