"""Read-only C+F checkpoint audit, with optional immutable prefix comparison."""
import argparse
import json
import sqlite3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from controller.authorized_capture import sha, once
from controller.pretrain_contracts import seal
from tools.audit_native_database_trial import audit
from controller.exclusive_roles import verify_roles
from controller.six_routes import aggregate_m1


def check_availability(feature, receipt, pair, poll):
    first = pair['first_observation']
    verified = pair['verification_observation']
    clocks = [poll['read_end'], first['read_start'], first['read_end'], verified['read_start'], verified['read_end'],
              feature['compute_clock'], receipt['offline_use_clock']]
    stamps = [clock['monotonic_ns'] for clock in clocks]
    if (len({clock['boot_id'] for clock in clocks}) != 1 or stamps != sorted(stamps)
            or feature['source_receipt'] != verified['read_end']
            or receipt['first_observation'] != first or receipt['ready_clock'] != feature['compute_clock']
            or receipt['physical_original_entry_availability_proven'] is not False):
        raise ValueError('CF_OFFLINE_AVAILABILITY_CHAIN_INVALID')
    cutoff = feature['feature_cutoff_native_msc']
    reference = feature['decision_input_ref']
    decision = reference['native_time_msc']
    source = {key:value for key,value in pair.items() if key not in ('quarantine','admitted')}
    if (cutoff != pair['end_native_exclusive_msc']-1 or decision <= cutoff
            or decision != poll['native_quote']['time_msc'] or reference['segment'] != pair['epoch']
            or reference['snapshot_hash'] != seal(source)):
        raise ValueError('CF_NATIVE_FEATURE_CUTOFF_INVALID')
    return dict(feature_max_native_msc=cutoff, decision_native_msc=decision,
                ready_clock=receipt['ready_clock'], offline_use_clock=receipt['offline_use_clock'])


def run(out, previous=None):
    out = Path(out)
    base = ROOT/'outputs/us30cash_m5_native_observations'
    summary = audit(out, base)
    pointer = json.loads((base/'current.json').read_text())
    folder = base/pointer['capture_id']
    package = ROOT/'research/studies/us30cash_m5_native_observations'
    manifest = json.loads((folder/'manifest.json').read_text())
    contract = json.loads((package/'contract.json').read_text())
    assert sha(package/'contract.json') == manifest['contract_sha256']
    assert sha(package/'authorization.json') == contract['authority_sha256']
    assert sha(ROOT/manifest['authorization_path']) == manifest['authorization_sha256']
    roles=verify_roles(ROOT,manifest)
    index = json.loads((package/'contract_sources.json').read_text())
    assert all(sha(package/name)==digest for name,digest in index['files'].items())
    ref = json.loads((folder/'runtime_pin_current.json').read_text())
    pin = json.loads((folder/'source_versions'/ref['file']).read_text())
    assert sha(folder/'source_versions'/ref['file']) == ref['sha256']
    assert pin['origin_manifest_sha256'] == pointer['manifest_sha256']
    assert all(sha(ROOT/name)==digest for name,digest in pin['source_hashes'].items())
    checkpoint = json.loads((out/'checkpoint_receipt.json').read_text())
    state = checkpoint['state']
    db = sqlite3.connect((folder/'snapshots.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
    db.execute('BEGIN')
    kinds = {}; starts=[]; parity=[]; availability=[]
    minutes=[]; last_pair=None; feature=None; poll=None; active_evidence=[]
    for n,digest,body in db.execute('SELECT n,digest,body FROM records WHERE n < ? ORDER BY n',(summary['verified_records'],)):
        row = json.loads(body)
        kinds[row['kind']] = kinds.get(row['kind'],0)+1
        if row['kind']=='PROCESS_START': starts.append(dict(n=n,**row))
        if row['kind'] in ('NEW_OBSERVATION_EPOCH','OBSERVATION_INTERRUPTION'):
            minutes=[];active_evidence=[];feature=None;last_pair=None;poll=None
        if row['kind']=='LIVE_LATEST_STATE_POLL':poll=row
        if row['kind']=='CF_CONTEXT_EXCLUDED':active_evidence=[]
        if row['kind']=='DATABASE_SNAPSHOT_PAIR' and row['assessment']['status']=='VERIFIED_DATABASE_VIEW_ONLY':
            if row['frame_seconds']==60:
                minutes=(minutes+[dict(row['native_bar'],epoch=row['epoch'])])[-10:]
            elif row['frame_seconds']==300:last_pair=row
        if row['kind']=='CF_M1_M5_PARITY':
            if last_pair is None:raise ValueError('CF_M5_PARITY_SOURCE_MISSING')
            bar=last_pair['native_bar']
            matching=[minute for minute in minutes if minute['epoch']==last_pair['epoch'] and bar['time']<=minute['time']<bar['time']+300]
            aggregates=aggregate_m1(matching)
            matched=(len(aggregates)==1 and aggregates[0]['complete_five_minutes']
                     and all(aggregates[0][k]==bar[k] for k in ('open','high','low','close','tick_volume')))
            source={k:v for k,v in last_pair.items() if k not in ('quarantine','admitted')}
            bar_hash=seal(dict(bar,segment=last_pair['epoch'],evidence_hash=seal(source)))
            if (matched!=row['matched'] or row['native_open']!=bar['time'] or bar_hash!=row['native_m5_hash']
                    or row['minute_bar_hashes']!=[seal(minute) for minute in matching]):
                raise ValueError('CF_M1_M5_PARITY_NOT_REPRODUCIBLE')
            parity.append(dict(n=n,**row))
        if row['kind']=='CAUSAL_PREFIX_FEATURES':
            feature=row
            body={k:v for k,v in row.items() if k not in ('kind','feature_hash','quarantine','admitted')}
            if seal(body)!=row['feature_hash']:raise ValueError('CF_FEATURE_HASH_CHANGED')
        if row['kind']=='CF_OFFLINE_AVAILABILITY':
            if (feature is None or last_pair is None or poll is None or not parity or not parity[-1]['matched']
                    or row['feature_hash']!=feature['feature_hash']
                    or row['native_bar_hash']!=feature['bar_hash'] or feature['bar_hash']!=parity[-1]['native_m5_hash']):
                raise ValueError('CF_FEATURE_SOURCE_BINDING_MISSING')
            evidence=check_availability(feature,row,last_pair,poll)
            item=dict(n=n,feature_hash=row['feature_hash'],epoch=last_pair['epoch'],
                      start_native_msc=last_pair['start_native_msc'],**evidence)
            availability.append(item);active_evidence.append(item);feature=None
    prefix=None
    if previous:
        prior=json.loads((Path(previous)/'summary.json').read_text())
        assert prior['capture_id']==summary['capture_id']
        digest=db.execute('SELECT digest FROM records WHERE n=?',(prior['verified_records']-1,)).fetchone()[0]
        assert digest==prior['chain_head']
        prefix=dict(previous_receipt_sha256=sha(Path(previous)/'summary.json'),records=prior['verified_records'],
                    chain_head=digest,preserved=True,prior_m5=prior['accepted'].get('300',0),
                    new_m5=summary['accepted'].get('300',0)-prior['accepted'].get('300',0))
    db.close()
    first=state['cf_first_observation']
    if len(active_evidence)!=state.get('cf_features',{}).get('own_run_bars',0):
        raise ValueError('CF_ACTIVE_CAUSAL_CONTEXT_COUNT_MISMATCH')
    authority=json.loads((package/'authorization.json').read_text())
    # Host labels are only one recorded ordering aid, never physical-generation UTC certification.
    assert first['read_start']['monotonic_ns'] >= manifest['intent_clock']['monotonic_ns']
    receipt=dict(study_id=manifest['study_id'],producer_id=manifest['producer_id'],dataset_id=manifest['dataset_id'],
        capture_id=pointer['capture_id'],contract_id=contract['contract_id'],contract_sha256=sha(package/'contract.json'),
        authorization_sha256=manifest['authorization_sha256'],implementation_pin_sha256=ref['sha256'],
        origin_manifest_sha256=pointer['manifest_sha256'],checkpoint_state_hash=checkpoint['state_hash'],
        first_observation=first,activation=manifest['activation'],verified_records=summary['verified_records'],
        chain_head=summary['chain_head'],real_m1=summary['accepted'].get('60',0),real_m5=summary['accepted'].get('300',0),
        rejected=summary['rejected'],technical_consecutive_m5=state.get('cf_features',{}).get('own_run_bars',0),
        scientific_warmup=0,process_starts=starts,m1_m5_parity=parity,offline_availability=availability,
        active_context_availability=active_evidence,
        prefix_persistence=prefix,native_membership=[dict(epoch=p['epoch'],frame_seconds=p['frame_seconds'],
            start_native_msc=p['start_native_msc'],end_native_exclusive_msc=p['end_native_exclusive_msc'],
            status=p['status'],hash=p['first_sha256']) for p in json.loads((out/'pairs.json').read_text())],
        exclusive_roles=roles,
        membership_scope='EXCLUSIVE_FORWARD_SCOPE_BY_EXPLICIT_DECISION' if roles else 'OWN_ARTIFACTS_VERIFIED_EXCLUSIVE_ROLE_NONOVERLAP_NOT_DEMONSTRATED',
        dataset_hash=None,dataset_admitted=False,NEW_STUDY_DATASET_ADMISSION='WAITING_FOR_EVIDENCE',
        callback_receipt_proven=False,event_generation_utc_proven=False,
        TRAINING_EXECUTED=False,PROTECTED_SCORING=False,LIVE_TRADING=False)
    if roles:
        for member in receipt['native_membership']:
            minimum=roles['minimum_m1_open_msc'] if member['frame_seconds']==60 else roles['minimum_native_open_msc']
            assert member['start_native_msc']>=minimum
    once(out/'cf_receipt.json',receipt)
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',required=True);p.add_argument('--previous')
    args=p.parse_args();r=run(args.out,args.previous)
    print(json.dumps({k:r[k] for k in ('real_m1','real_m5','technical_consecutive_m5','verified_records','chain_head','prefix_persistence')},indent=2))
