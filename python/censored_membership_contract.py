"""Quarantine unresolved end-censored IDs without reading protected outcomes."""
import csv
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from .membership_contract import digest
    from .parquet_io import read_parquet
except ImportError:
    from membership_contract import digest
    from parquet_io import read_parquet

ROOT=Path(__file__).resolve().parents[1]


def candidates(rows, known_times, start_msc, end_day_msc, final_msc, maximum):
    by_id={row['signal_id']:row for row in rows}
    if len(by_id)!=len(rows):
        raise ValueError('Source identities are duplicated')
    expected={sid for sid,time in known_times.items() if start_msc<=time<end_day_msc+86400000}
    if not expected.issubset(by_id):
        raise ValueError('Frozen research observations are missing; quarantine forbidden')
    last=max(max(int(r['follow_exit_time']),int(r['invert_exit_time'])) for r in rows)
    if not end_day_msc<=last<end_day_msc+86400000 or last>=final_msc:
        raise ValueError('Censor endpoint is outside the permitted final source day')
    explained=[]
    for signal,row in by_id.items():
        if signal in known_times:
            continue
        stamp,entry=int(row['signal_time_msc']),int(row['entry_time_msc'])
        if not end_day_msc<=stamp<entry<=last:
            raise ValueError('Unassigned ID is outside the narrow source-end guard')
        for mode in ('follow','invert'):
            if (row[mode+'_exit_reason']!='END_OF_DATA' or int(row[mode+'_exit_time'])!=last
                    or not 1<=int(row[mode+'_bars_in_trade'])<=100):
                raise ValueError('Unassigned ID is not wholly censored at the permitted source end')
        explained.append(dict(signal_id=signal,signal_time_msc=stamp,entry_time_msc=entry,
                              censor_time_msc=last,reason='UNRESOLVED_CENSORED_NONMEMBER_EXCLUDED_FROM_RESEARCH'))
    if not explained or len(explained)>maximum:
        raise ValueError('Unresolved censor count exceeds frozen validation purge count')
    return sorted(explained,key=lambda r:r['signal_id']),len(expected)


def derive(run_id, root=ROOT):
    root=Path(root)
    if not run_id.replace('_','').isalnum():
        raise ValueError('Invalid evidence run ID')
    split_path=root/'outputs/splits/split_manifest.json'
    split=json.loads(split_path.read_text())
    final=int(split['boundaries']['final_test_start_signal_time_msc'])
    end_day=datetime.fromtimestamp(final/1000,timezone.utc).date()-timedelta(days=1)
    first=datetime(end_day.year,1,1,tzinfo=timezone.utc)
    end_clock=datetime.combine(end_day,datetime.min.time(),timezone.utc)
    folder=root/'outputs/controller/runs'/run_id
    record=json.loads((folder/'run_manifest.json').read_text())
    if (record.get('tester_status')!='PASS' or record.get('DATASET_VALIDATOR')!='PASS'
            or record.get('CAUSALITY_STATUS')!='PASS' or record.get('from')!=first.date().isoformat()
            or record.get('to')!=end_day.isoformat()):
        raise ValueError('Source-end evidence has not passed tester/source/causal gates')
    source=folder/(run_id+'_stochastic_events.csv')
    if digest(source)!=record['artifact_hashes'][source.name]:
        raise ValueError('Source-end evidence hash changed')
    known={}
    for field,name in (('train_parquet_sha256','train.parquet'),('validation_parquet_sha256','validation.parquet')):
        path=root/'outputs/splits'/name
        if digest(path)!=split[field]:
            raise ValueError('Frozen membership changed')
        frame=read_parquet(path,columns=['signal_id','signal_time_msc'])
        known.update(zip(frame.signal_id.astype(str),map(int,frame.signal_time_msc)))
    with source.open(encoding='utf-8-sig',newline='') as stream:
        rows=list(csv.DictReader(stream))
    ids,coverage=candidates(rows,known,int(first.timestamp()*1000),int(end_clock.timestamp()*1000),
                            final,int(split['purged']['DISCOVERY_VALIDATION']))
    identity={key:record[key] for key in ('run_id','from','to','ea_hash','ex5_hash')}
    return dict(contract_version=1,source_run_id=run_id,events_sha256=digest(source),
                run_identity_sha256=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest(),
                split_manifest_sha256=digest(split_path),expected_known_signals=coverage,
                frozen_membership_preserved=True,final_test_accessed=False,
                protected_outcomes_inferred=False,classification='QUARANTINE_NOT_CONFIRMED_PURGE',ids=ids)


def verified_ids(path,split_path,root=ROOT):
    if not Path(path).exists():
        return set()
    record=json.loads(Path(path).read_text())
    if record!=derive(record['source_run_id'],root) or record['split_manifest_sha256']!=digest(split_path):
        raise ValueError('Censored membership evidence changed')
    return {r['signal_id'] for r in record['ids']}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    args=parser.parse_args();result=derive(args.run_id)
    path=ROOT/'outputs/controller/checkpoints/censored_membership_quarantine_v1.json'
    if path.exists() and json.loads(path.read_text())!=result:
        raise ValueError('Refusing to overwrite another censored membership contract')
    path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
