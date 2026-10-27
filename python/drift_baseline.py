"""Seal an approved TRAIN-only feature matrix summary; never accesses cohort raw."""
import argparse
import hashlib
import json
from pathlib import Path
from drift_feature_stream import FEATURES, BINS
from drift_monitor import summarize_feature_csv

ROOT = Path(__file__).resolve().parents[1]


def build(matrix: Path, provenance: Path, output: Path):
    source = matrix.resolve()
    if any(word in str(source).casefold() for word in ('validation', 'final_test', 'future_cohort')):
        raise ValueError('TRAIN_ONLY_BASELINE_REQUIRED')
    proof = json.loads(provenance.read_text())
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    producer = ROOT / 'python/drift_feature_stream.py'
    contract = ROOT / 'configs/drift_feature_whitelist.json'
    if (proof.get('split') != 'TRAIN' or proof.get('feature_only') is not True
            or proof.get('producer_sha256') != digest(producer)
            or proof.get('matrix_sha256') != digest(source)
            or proof.get('normalized_utc_verified') is not True):
        raise ValueError('HASH_BOUND_NORMALIZED_TRAIN_PROVENANCE_REQUIRED')
    report = summarize_feature_csv(source, whitelist=set(FEATURES), bins=BINS,
                                  feature_definition_sha256=digest(contract), feature_producer_sha256=digest(producer))
    report['baseline_provenance_sha256'] = digest(provenance)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, sort_keys=True, indent=2)
    with output.with_name(output.name+'.sha256').open('x') as stream:
        stream.write(digest(output)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matrix', type=Path, required=True)
    parser.add_argument('--provenance', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.matrix, args.provenance, args.output)
