import json
import subprocess
import sys
from pathlib import Path
from .compile_runner import sha256
from .artifact_collector import write_manifest
from .safety_gate import ROOT, assert_research_range_allowed
from .profiles import BASE_EA, profile


def validate_run(run_id, ea=BASE_EA):
    if not run_id.replace('_', '').isalnum():
        raise ValueError('Invalid run ID')
    selected = profile(ea)
    folder = ROOT / 'outputs' / selected['namespace'] / 'runs' / run_id
    manifest = json.loads((folder / 'run_manifest.json').read_text())
    assert_research_range_allowed(manifest['from'], manifest['to'])
    if manifest['tester_status'] != 'PASS':
        raise RuntimeError('VALIDATION: tester did not pass')
    for name, expected in manifest['artifact_hashes'].items():
        if Path(name).name != name or sha256(folder / name) != expected:
            raise RuntimeError('VALIDATION: artifact hash mismatch')
    prefix = folder / (run_id + '_stochastic_events.csv')
    snapshot = folder / (run_id + '_intratrade_snapshots.csv')
    targets = folder / (run_id + '_intratrade_snapshot_targets.csv')
    commands = {
        'DATASET_VALIDATOR': [str(ROOT / 'python/validate_dataset.py'), str(prefix)],
        'INTRATRADE_VALIDATOR': [str(ROOT / 'python/validate_intratrade_dataset.py'), str(snapshot),
            '--targets', str(targets), '--events', str(prefix),
            '--train', str(ROOT / 'outputs/splits/train.parquet'),
            '--validation', str(ROOT / 'outputs/splits/validation.parquet'),
            '--split-manifest', str(ROOT / 'outputs/splits/split_manifest.json')],
    }
    result = {}
    if selected['schema'] == '3.0':
        commands['INTRATRADE_VALIDATOR'].extend([
            '--execution-quotes', str(folder/(run_id+'_bar_execution_quotes.csv'))])
    for key, arguments in commands.items():
        process = subprocess.run([sys.executable, *arguments], cwd=ROOT, capture_output=True, text=True)
        (folder / (key.lower() + '.log')).write_text(process.stdout + process.stderr, encoding='utf-8')
        result[key] = 'PASS' if process.returncode == 0 else 'FAIL'
        if process.returncode:
            break
    result['CAUSALITY_STATUS'] = 'NOT_VERIFIED'
    proof_path = ROOT / 'outputs' / selected['namespace'] / 'checkpoints/causal_invariance.json'
    if proof_path.exists():
        proof = json.loads(proof_path.read_text())
        proof_folder = ROOT / 'outputs' / selected['namespace'] / 'causality' / proof['run_id']
        hashes_match = all((ROOT/'mt5'/name).is_file() and sha256(ROOT/'mt5'/name)==expected
                           for name,expected in proof.get('producer_hashes',{}).items())
        artifacts_match = all((proof_folder/name).is_file() and sha256(proof_folder/name)==expected
                              for name,expected in proof.get('artifact_hashes',{}).items())
        if (proof.get('CAUSAL_INVARIANCE') == 'PASS' and proof.get('compared_snapshots',0)>0
                and proof.get('compared_features',0)>0 and proof.get('ea_hash')==manifest['ea_hash']
                and hashes_match and artifacts_match):
            result['CAUSALITY_STATUS']='PASS'
            result['CAUSAL_PROOF_RUN_ID']=proof['run_id']
    result['VALIDATION_STATUS'] = 'PASS' if all(
        result.get(key) == 'PASS' for key in commands) and result['CAUSALITY_STATUS'] == 'PASS' else 'FAIL'
    manifest.update(result)
    write_manifest(folder, manifest)
    return result
