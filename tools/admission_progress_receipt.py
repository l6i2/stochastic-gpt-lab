"""Verify new quarantine ledger tails and report evidence still needed for admission."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from controller.pretrain_contracts import seal
from controller.scientific_authority import ADMITTED_PACKAGE_HASHES, AUTHORIZED_GRANT_HASHES
from tools.autonomous_research_status import build


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8-sig'))


def tail(database, table, first, first_hash, last, last_hash):
    if last < first or table not in ('records', 'artifacts'):
        raise ValueError('INVALID_LEDGER_RANGE')
    with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.execute('BEGIN')
        if db.execute(f'SELECT digest FROM {table} WHERE n=?', (first,)).fetchone() != (first_hash,):
            raise ValueError('PUBLISHED_PREFIX_CHANGED')
        expected, head = first + 1, first_hash
        for n, previous, digest, body in db.execute(
                f'SELECT n,previous,digest,body FROM {table} WHERE n>? AND n<=? ORDER BY n', (first,last)):
            if n != expected or previous != head or seal(dict(previous=previous,payload=json.loads(body))) != digest:
                raise ValueError('NEW_LEDGER_TAIL_CHANGED')
            expected, head = expected + 1, digest
        if expected != last + 1 or head != last_hash:
            raise ValueError('LATEST_LEDGER_ANCHOR_CHANGED')
    return dict(prefix_n=first, prefix_hash=first_hash, final_n=last, final_hash=head, appended_verified=last-first)


def receipt():
    status = build()
    snap = status['snapshot_trial']
    warmup = status['warmup_counter_receipt']
    old_snap = read('research/studies/final_mission_20261104_v1/snapshot_receipt.json')
    old_status = read('research/studies/warmup_resolution_20261103_v1/status.json')
    old_warmup = old_status['warmup_counter_receipt']
    if snap['capture_id'] != old_snap['capture_id'] or status['capture_id'] != old_status['capture_id']:
        raise ValueError('CAPTURE_IDENTITY_CHANGED')
    package = 'research/studies/us30cash_m5_native_pretrain_v1/'
    inventory = read(package + 'dataset_inventory.json')
    matrix = 'research/studies/final_mission_20261104_v1/offline_receipt.json'
    return dict(
        status=status,
        matrix_receipt_sha256=hashlib.sha256((ROOT/matrix).read_bytes()).hexdigest(),
        metadata_manifest_paths_present={p:(ROOT/p).is_file() for p in inventory['expected_original_manifests']},
        snapshot_tail=tail(ROOT/'outputs/native_database_snapshots_v1'/snap['capture_id']/'snapshots.sqlite3',
                           'records',old_snap['verified_records']-1,old_snap['chain_head'],snap['records']-1,snap['chain_head']),
        original_tail=tail(ROOT/'outputs/prospective_derivatives_v1'/status['capture_id']/'quarantine.sqlite3',
                           'artifacts',old_warmup['ledger_last_n'],old_warmup['ledger_head'],warmup['ledger_last_n'],warmup['ledger_head']),
        admitted_package_count=len(ADMITTED_PACKAGE_HASHES), authorized_grant_count=len(AUTHORIZED_GRANT_HASHES),
        independent_periods_demonstrated=[], protected_rows_read=0, training_executed=False,
        replay_rerun=False, scientific_contract_changed=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = receipt()
    with args.out.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, ensure_ascii=False)
        stream.write('\n')
