"""Bounded separate native-database trial using the existing read-only producer."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from controller.authorized_capture import sha, once
from controller.isolated_observation import host_clock, atomic
from tools import native_database_snapshots as native

BASE = ROOT / 'outputs/six_alternatives_experiment'
AUTHORIZATION = 'research/studies/six_alternatives_resolution/experimental_authorization.json'


def initialize():
    import psutil
    if psutil.virtual_memory().available < 768 * 1048576:
        raise RuntimeError('INSUFFICIENT_AVAILABLE_RAM_FOR_SEPARATE_TRIAL')
    BASE.mkdir(parents=True, exist_ok=True)
    if (BASE / 'current.json').exists():
        raise ValueError('TRIAL_ALREADY_INITIALIZED_USE_EXISTING_ID')
    original = ROOT / 'outputs/native_database_snapshots_v1'
    pointer = json.loads((original / 'current.json').read_text())
    folder = original / pointer['capture_id']
    manifest = json.loads((folder / 'manifest.json').read_text())
    files = set(manifest['source_hashes']) | {'tools/six_routes_capture.py'}
    capture_id = 'dbsnap_' + uuid.uuid4().hex
    target = BASE / capture_id
    target.mkdir()
    manifest.update(capture_id=capture_id, authorization_path=AUTHORIZATION,
                    authorization_sha256=sha(ROOT / AUTHORIZATION), intent_clock=host_clock(),
                    source_hashes={name: sha(ROOT / name) for name in sorted(files)},
                    source='EXPERIMENTAL_NATIVE_DATABASE_FIRST_OBSERVATION',
                    previous_capture_membership_adopted=False, scientific_warmup=0,
                    quarantine=True, maximum_trial_seconds=1200)
    once(target / 'manifest.json', manifest)
    once(BASE / 'current.json', dict(capture_id=capture_id, manifest_sha256=sha(target / 'manifest.json')))
    atomic(BASE / 'enabled.json', dict(enabled=True))
    return capture_id


def serve():
    native.BASE = BASE
    producer = native.Producer()
    started = time.monotonic()
    try:
        while time.monotonic() - started < 1200:
            producer.poll()
            if producer.store.state['consecutive_m5'] >= 2:
                break
            time.sleep(2)
        producer.store.commit([dict(kind='CONTROLLED_TRIAL_STOP', clock=host_clock(),
                                    producer_id=producer.folder.name, reason='BOUND_REACHED_OR_TWO_M5',
                                    gaps_not_backfilled=True)])
        producer.report('TRIAL_STOPPED_QUARANTINED')
        atomic(BASE / 'enabled.json', dict(enabled=False))
    finally:
        producer.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--init', action='store_true')
    parser.add_argument('--serve', action='store_true')
    args = parser.parse_args()
    if args.init:
        print(initialize())
    elif args.serve:
        serve()
