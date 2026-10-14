"""Bounded-memory schema 3 master builder; immutable inherited membership."""
import csv
import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from .membership_contract import digest
from .parquet_io import read_parquet
from .validate_intratrade_dataset import REQUIRED_TARGET_COLUMNS, validate

ROOT = Path(__file__).resolve().parents[1]
STRINGS = {'snapshot_id', 'signal_id', 'symbol', 'original_signal', 'virtual_mode',
           'virtual_side', 'stoch_zone', 'ha_status', 'server_time', 'UTC_time', 'NY_time'}


def feature_dtypes(columns):
    return {c: (str if c in STRINGS or c.endswith(('_status', '_source')) else
                'Int64' if c.endswith('_msc') else 'float64') for c in columns}


def append_frame(frame, path):
    frame.to_parquet(path, engine='fastparquet', index=False, append=path.exists(), compression='SNAPPY')


def copy_allowed_rows(paths, destination, allowed, empty_columns=()):
    count = 0
    fields = None
    with destination.open('w', encoding='utf-8', newline='') as target:
        writer = None
        for path in paths:
            with path.open(encoding='utf-8-sig', newline='') as stream:
                reader = csv.DictReader(stream)
                if not reader.fieldnames:
                    continue
                if fields is None:
                    fields = reader.fieldnames
                    writer = csv.DictWriter(target, fieldnames=fields)
                    writer.writeheader()
                elif fields != reader.fieldnames:
                    raise ValueError('Source table schemas differ')
                for row in reader:
                    if allowed is None or row['signal_id'] in allowed:
                        writer.writerow(row)
                        count += 1
        if fields is None and empty_columns:
            csv.DictWriter(target, fieldnames=list(empty_columns)).writeheader()
    return count


def build(blocks, out, train_path, validation_path, split_manifest, chunksize=5000):
    blocks = list(map(Path, blocks))
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError('Refusing to overwrite an existing streaming build')
    out.mkdir(parents=True, exist_ok=True)
    split = json.loads(Path(split_manifest).read_text())
    final = int(split['boundaries']['final_test_start_signal_time_msc'])
    for field, path in (('train_parquet_sha256', train_path), ('validation_parquet_sha256', validation_path)):
        if digest(path) != split[field]:
            raise ValueError('Frozen partition hash changed')
    train_ids = set(read_parquet(train_path, columns=['signal_id']).signal_id.astype(str))
    validation_ids = set(read_parquet(validation_path, columns=['signal_id']).signal_id.astype(str))
    if train_ids & validation_ids:
        raise ValueError('Inherited memberships overlap')
    allowed = train_ids | validation_ids
    index_path = ROOT/'work'/('bar_master_index_'+uuid.uuid4().hex+'.sqlite')
    index_path.parent.mkdir(parents=True, exist_ok=True)
    database = sqlite3.connect(index_path)
    database.execute('PRAGMA cache_size=-8192')
    database.execute('CREATE TABLE ids (id TEXT PRIMARY KEY)')
    counts = dict(TRAIN=0, DISCOVERY_VALIDATION=0, master=0, quarantined=0, purged=0)
    schemas = None
    sources = []
    seen_signals = {'TRAIN': set(), 'DISCOVERY_VALIDATION': set()}
    last_cutoff = -1
    try:
        for block in blocks:
            metadata = json.loads((block/'manifest.json').read_text())
            end = datetime.fromisoformat(metadata['period'][1]).replace(tzinfo=timezone.utc)+timedelta(days=1)
            if (metadata.get('producer_schema') != '3.0' or int(metadata['max_signal_time_msc']) >= final
                    or int(end.timestamp()*1000) > final or metadata.get('LIVE_TRADING') is not False
                    or metadata.get('optimization') != 'OFF' or metadata.get('symbol') != 'US30Cash'
                    or metadata.get('timeframe') != 'M5'):
                raise ValueError('Unaccepted producer version or protected range')
            for name in ('stochastic_events.csv', 'stochastic_events.csv.audit.json',
                         'intratrade_snapshots.csv', 'intratrade_snapshots.csv.audit.json',
                         'intratrade_snapshot_targets.csv', 'bar_execution_quotes.csv'):
                expected = metadata['source_artifact_hashes'][metadata['run_id']+'_'+name]
                if digest(block/name) != expected:
                    raise ValueError('Accepted source hash changed')
            snapshot = block/'intratrade_snapshots.csv'
            audit = validate(snapshot, targets_csv=block/'intratrade_snapshot_targets.csv',
                             train_parquet=Path(train_path), validation_parquet=Path(validation_path),
                             events_csv=block/'stochastic_events.csv', split_manifest=Path(split_manifest),
                             execution_quotes_csv=block/'bar_execution_quotes.csv')
            quarantine = set(audit['quarantined_signal_ids'])
            with snapshot.open(encoding='utf-8-sig', newline='') as stream:
                columns = next(csv.reader(stream))
            if schemas is not None and schemas != columns:
                raise ValueError('Snapshot schema differs across blocks')
            schemas = columns
            for frame in pd.read_csv(snapshot, dtype=feature_dtypes(columns), float_precision='round_trip',
                                     keep_default_na=False, na_values=[''], chunksize=chunksize):
                membership = frame.signal_id.astype(str)
                unknown = ~membership.isin(allowed)
                counts['quarantined'] += int(membership.isin(quarantine).sum())
                counts['purged'] += int((unknown & ~membership.isin(quarantine)).sum())
                frame = frame.loc[~unknown].copy()
                if frame.empty:
                    continue
                cutoffs = frame.snapshot_time_msc.astype('int64')
                if not cutoffs.is_monotonic_increasing or int(cutoffs.min()) < last_cutoff:
                    raise ValueError('Producer decision-time chronology is not monotone')
                last_cutoff = int(cutoffs.max())
                try:
                    database.executemany('INSERT INTO ids VALUES (?)', [(v,) for v in frame.snapshot_id])
                    database.commit()
                except sqlite3.IntegrityError as exc:
                    raise ValueError('Duplicate snapshot ID across source blocks') from exc
                csv_path = out/'intratrade_master.csv'
                frame.to_csv(csv_path, mode='a', header=not csv_path.exists(), index=False, float_format='%.17g')
                append_frame(frame, out/'intratrade_master.parquet')
                for label, ids, filename in (('TRAIN',train_ids,'train.parquet'),
                                              ('DISCOVERY_VALIDATION',validation_ids,'validation.parquet')):
                    partition = frame.loc[frame.signal_id.isin(ids)]
                    if len(partition):
                        append_frame(partition, out/filename)
                        counts[label] += len(partition)
                        seen_signals[label].update(partition.signal_id)
                counts['master'] += len(frame)
            sources.append(dict(manifest_sha256=digest(block/'manifest.json'), validation=audit))
        if not counts['TRAIN'] or not counts['DISCOVERY_VALIDATION']:
            raise ValueError('Both inherited research partitions require observations')
        targets = copy_allowed_rows([Path(b)/'intratrade_snapshot_targets.csv' for b in blocks],
                                    out/'intratrade_targets.csv', allowed, sorted(REQUIRED_TARGET_COLUMNS))
        fills = copy_allowed_rows([Path(b)/'bar_execution_quotes.csv' for b in blocks],
                                  out/'bar_execution_quotes.csv', allowed)
        if fills != counts['master']:
            raise ValueError('Execution coverage changed while building')
        event_count = copy_allowed_rows([Path(b)/'stochastic_events.csv' for b in blocks],
                                        out/'all_allowed_events.csv', None)
        manifest = dict(schema_version='3.0', dataset_version='bar_decision_master_v1',
                        status='BUILT_NOT_PROMOTED', FINAL_TEST='LOCKED', LIVE_TRADING=False,
                        final_test_accessed=False, split_membership_changed=False,
                        split_manifest_sha256=digest(split_manifest), rows=counts,
                        signals={key:len(value) for key,value in seen_signals.items()},
                        targets=targets, execution_quotes=fills, source_events=event_count,
                        row_order='producer decision-time chronology', chunksize=chunksize,
                        sources=sources, legacy_future_excursions='EXCLUDED_FROM_PROMOTION',
                        sha256={p.name:digest(p) for p in out.iterdir() if p.is_file()})
        (out/'intratrade_master_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        return manifest
    finally:
        database.close()
