"""Metadata/own-prefix checks; retained oracle parity never admits a dataset."""
import json
from pathlib import Path
import sqlite3
from .authorized_capture import sha
from .pretrain_contracts import seal


def retained_oracle(root):
    root=Path(root)
    from tools.prospective_pipeline import active_code_pin,feature_fragment_hash
    pin_path,pin=active_code_pin()
    certificate=pin['native_indicator_oracle'];binding=pin['unchanged_feature_fragment']
    if binding['approved_worker_source_sha256']!=certificate['worker_source_sha256']:
        raise ValueError('FEATURE_ORACLE_IMPLEMENTATION_BINDING_CHANGED')
    fragment=feature_fragment_hash((root/'controller/prospective_processor.py').read_text())
    if fragment!=binding['feature_fragment_sha256'] or sha(root/'mt5/HeikinAshiCore.mqh')!=certificate['ha_core_sha256']:
        raise ValueError('FEATURE_OR_HA_CORE_CHANGED')
    if sha(root/'python/native_metadata_v3.py')!=pin['files']['python/native_metadata_v3.py']:
        raise ValueError('FROZEN_MAIN_K_DEPENDENCY_CHANGED')
    published=root/'research/studies/us30cash_m5_prospective_pipeline_20261031_v1/native_oracle.json'
    if json.loads(published.read_text())!=certificate:
        raise ValueError('RETAINED_ORACLE_CERTIFICATE_CHANGED')
    if (certificate['ATR_PARITY']!='PASS_EXACT' or certificate['atr_max_abs_error']!=0
            or certificate['atr_tolerance']!=0 or certificate['HA_PARITY']!='PASS_EXACT'
            or certificate['MAIN_K_PARITY']!='PASS_RETAINED_BOUND' or certificate['native_execution'] is not True):
        raise ValueError('RETAINED_NATIVE_PARITY_FAILED')
    csv=root/'outputs/prospective_native_oracle'/certificate['run_id']/(certificate['run_id']+'_oracle.csv')
    if not csv.exists() or sha(csv)!=certificate['oracle_csv_sha256']:
        raise ValueError('NATIVE_EXPORT_NOT_AVAILABLE_OR_CHANGED')
    return dict(algorithmic_ATR_PARITY='PASS_EXACT_RETAINED_NATIVE_499_BAR_ORACLE',
        algorithmic_HA_PARITY='PASS_EXACT_RETAINED',algorithmic_MAIN_K_PARITY='PASS_RETAINED_BOUND',
        feature_fragment_sha256=fragment,ha_core_sha256=certificate['ha_core_sha256'],
        retained_receipt_sha256=sha(published),native_export_sha256=sha(csv),code_pin_sha256=sha(pin_path),
        rerun=False,own_dataset_native_iATR_parity=False,dataset_admitted=False)


def seed_check(context, first_own_bar_hash):
    n=context['own_run_bars'];ha=context.get('ha');atr=context.get('atr')
    if n==0:
        if ha is not None or atr is not None:raise ValueError('OLD_RECURSIVE_SEED_IN_EMPTY_EPOCH')
        return dict(own_bars=0,seeds_bound=False,ATR_INITIALIZED=False,HA_READY=False)
    if not first_own_bar_hash or not ha or not atr:
        raise ValueError('MISSING_OWN_SEED')
    if any(s['seed_bar_hash']!=first_own_bar_hash or s['count']!=n for s in (ha,atr)):
        raise ValueError('SEED_OUTSIDE_OWN_PREFIX_OR_COUNT_MISMATCH')
    if (atr['value'] is not None)!=(n>=15):raise ValueError('ATR_INITIALIZATION_BOUNDARY_CHANGED')
    if len(atr['tr'])!=min(14,n-1):raise ValueError('ATR_OWN_TR_WINDOW_CHANGED')
    return dict(own_bars=n,seeds_bound=True,seed_bar_hash=first_own_bar_hash,
        ATR_INITIALIZED=n>=15,ATR_required_own_bars=15,HA_READY=n>=276,HA_required_own_bars=276,
        warmup_ready=n>=350,warmup_required_own_bars=350,scientifically_admitted=False)


def own_prefix(root):
    root=Path(root);base=root/'outputs/us30cash_m5_native_observations'
    pointer=json.loads((base/'current.json').read_text());folder=base/pointer['capture_id']
    if sha(folder/'manifest.json')!=pointer['manifest_sha256']:raise ValueError('OWN_MANIFEST_CHANGED')
    db=sqlite3.connect((folder/'snapshots.sqlite3').resolve().as_uri()+'?mode=ro',uri=True);db.execute('BEGIN')
    try:
        body,digest=db.execute('SELECT body,digest FROM state WHERE id=1').fetchone();state=json.loads(body)
        if seal(state)!=digest:raise ValueError('OWN_FEATURE_CHECKPOINT_CHANGED')
        pairs=[];minutes=[];matched=[];availability=[]
        for _,row in db.execute('SELECT n,body FROM records ORDER BY n'):
            event=json.loads(row);kind=event['kind']
            if kind in ('NEW_OBSERVATION_EPOCH','OBSERVATION_INTERRUPTION','CF_CONTEXT_EXCLUDED'):
                pairs=[];minutes=[];matched=[];availability=[]
            if kind=='DATABASE_SNAPSHOT_PAIR' and event['assessment']['status']=='VERIFIED_DATABASE_VIEW_ONLY':
                (minutes if event['frame_seconds']==60 else pairs).append(event['native_bar'])
            if kind=='CF_M1_M5_PARITY' and event['matched']:matched.append(event)
            if kind=='CF_OFFLINE_AVAILABILITY':
                ready,used=event['ready_clock'],event['offline_use_clock']
                if ready['boot_id']!=used['boot_id'] or ready['monotonic_ns']>used['monotonic_ns']:
                    raise ValueError('FEATURE_NOT_PHYSICALLY_READY_BEFORE_OFFLINE_USE')
                availability.append(event)
        first=matched[0]['native_m5_hash'] if matched else None
        seeds=seed_check(state.get('cf_features',dict(own_run_bars=0)),first)
        if seeds['own_bars']!=len(matched) or len(availability)!=len(matched):raise ValueError('OWN_FEATURE_PREFIX_INCOMPLETE')
        starts={r['native_open'] for r in matched};bars=[row for row in pairs if row['time'] in starts]
        minutes=[row for row in minutes if row['time']//300*300 in starts]
        return dict(capture_id=folder.name,epoch=state['epoch'],state_hash=digest,seeds=seeds,
            native_m5=bars,native_m1=minutes,offline_availability_count=len(availability),
            physical_original_entry_availability_proven=False,generation_utc_certified=False)
    finally:db.close()
