"""Metadata-only C+F admission rehearsal. This module cannot admit or train.

An internally consistent rehearsal packet is not independent evidence: the caller
must supply verified receipts. No protected/data file reader is provided here.
"""
import copy
from .pretrain_contracts import seal, FEATURES
from .cf_study import admission
from .cf_session_calendar import transition_review
from .training_admission_gate import authorize_execution

SECTIONS=('identity','membership','coverage','features','seeds','maturity','calendar')


def bind_packet(artifacts):
    """Seal a rehearsal envelope; never signs a scientific admission receipt."""
    return dict(schema='cf-admission-rehearsal/1',artifacts=copy.deepcopy(artifacts),
                hashes={name:seal(artifacts[name]) for name in SECTIONS})


def review(packet):
    hard=[]; pending=[]
    try:
        if packet['schema']!='cf-admission-rehearsal/1':raise ValueError('SCHEMA')
        artifacts=packet['artifacts']
        for name in SECTIONS:
            if seal(artifacts[name])!=packet['hashes'][name]:hard.append('HASH_CHANGED:'+name)
        if hard:return result(hard,pending)
        identity=artifacts['identity'];membership=artifacts['membership']
        if identity.get('receipt_verified') is not True:pending.append('IDENTITY_RECEIPT_EVIDENCE')
        if identity.get('server')!='XMGlobalSC-MT5 5' or identity.get('symbol')!='US30Cash' or identity.get('terminal_trade_allowed') is not False:
            hard.append('UNSAFE_OR_UNKNOWN_IDENTITY')
        if membership.get('exclusive_verified') is not True:pending.append('EXCLUSIVE_MEMBERSHIP_EVIDENCE')
        cutoff=membership['minimum_native_open_msc'];intervals=membership['intervals']
        previous_end=None
        expected=(identity['study_id'],identity['dataset_id'],identity['producer_id'])
        for row in sorted(intervals,key=lambda row:row['start_native_msc']):
            if (row.get('study_id'),row.get('dataset_id'),row.get('producer_id'))!=expected:hard.append('MEMBERSHIP_IDENTITY_MISMATCH')
            start,end=row['start_native_msc'],row['end_native_exclusive_msc']
            if start<cutoff or end!=start+300000 or start%300000:hard.append('PRE_CUT_OR_INVALID_NATIVE_INTERVAL')
            if previous_end is not None and start<previous_end:hard.append('OVERLAPPING_INTERVALS')
            previous_end=end
            if row.get('origin')!='POST_CUTOFF_NATIVE_DATABASE_SNAPSHOT' or row.get('backfill') is not False:hard.append('INELIGIBLE_RETROSPECTIVE_IMPORT')
            if row.get('first_observation_post_cut_verified') is not True:pending.append('FIRST_OBSERVATION_EVIDENCE')
        coverage=artifacts['coverage']
        if coverage.get('complete') is not True:pending.append('COVERAGE_EVIDENCE')
        for key in ('five_own_m1','ohlc_exact','volume_exact','two_views_equal','bid_ask_preserved'):
            if coverage.get(key) is not True:pending.append('COVERAGE:'+key)
        if artifacts['features'].get('whitelist')!=list(FEATURES):hard.append('WHITELIST_CHANGED')
        features=artifacts['features']
        if features.get('complete') is not True:pending.append('FEATURE_EVIDENCE')
        if not features.get('availability'):pending.append('FEATURE_AVAILABILITY_EVIDENCE')
        for row in features.get('availability',[]):
            if row['feature_max_native_msc']>row['decision_native_msc']:hard.append('NATIVE_FEATURE_LEAKAGE')
            ready,used=row['ready_clock'],row['offline_use_clock']
            if ready['boot_id']!=used['boot_id'] or ready['monotonic_ns']>used['monotonic_ns']:hard.append('FEATURE_NOT_READY_BEFORE_OFFLINE_USE')
        seeds=artifacts['seeds']
        if not seeds.get('own_post_cut') or seeds.get('ha_count',0)<350 or seeds.get('atr_count',0)<350 or seeds.get('native_atr_parity') is not True:
            pending.append('OWN_SEEDS_AND_ATR_EVIDENCE')
        calendar=artifacts['calendar']
        for bridge in calendar.get('bridges',[]):
            if not transition_review(bridge.get('transition_request',{}))['bridge_allowed']:hard.append('UNCERTIFIED_SESSION_BRIDGE')
        if calendar.get('applicable_verified') is not True:pending.append('CALENDAR_EVIDENCE')
        counts=artifacts['maturity']
        facts=dict(contract_approved=True,independence=True,nonoverlap=True,calendar=True,coverage=True,causality=True,seeds=True,**counts)
        gate=admission(facts)
        if gate['NEW_STUDY_DATASET_ADMISSION']!='PASS':pending.append('FROZEN_MATURITY_OR_SEAL_REQUIREMENTS')
        return result(hard,pending)
    except (KeyError,TypeError,ValueError,OverflowError):
        return result(hard+['MALFORMED_OR_INCOMPLETE_METADATA'],pending)


def result(hard,pending):
    # Even all-synthetic success cannot mutate admission authority or dataset role.
    return dict(REHEARSAL_STATUS='REJECTED' if hard else 'NOT_READY' if pending else 'CHECKS_SATISFIED_DRY_RUN_ONLY',
        rejection_reasons=sorted(set(hard)),pending_evidence=sorted(set(pending)),
        dataset_admitted=False,TRAINING_EXECUTED=False,PROTECTED_SCORING=False,LIVE_TRADING=False,
        physical_generation_utc_certified=False)


def no_grant_rejection():
    """Exercise existing authority: an absent grant rejects before file access."""
    try:authorize_execution({},None)
    except PermissionError as exc:
        return dict(rejected=True,reason=str(exc),training_executed=False)
    raise AssertionError('UNEXPECTED_TRAINING_AUTHORITY_CHANGE')


def from_operational_receipt(receipt):
    """Conservative adapter: unknown real evidence stays unknown, never inferred."""
    roles=receipt.get('exclusive_roles') or {}
    identity={k:receipt[k] for k in ('study_id','dataset_id','producer_id')}
    identity.update(server='XMGlobalSC-MT5 5',symbol='US30Cash',terminal_trade_allowed=False,receipt_verified=False)
    intervals=[dict(row,**{k:identity[k] for k in ('study_id','dataset_id','producer_id')},
        origin='POST_CUTOFF_NATIVE_DATABASE_SNAPSHOT',backfill=False,
        first_observation_post_cut_verified=roles.get('exclusive') is True)
        for row in receipt.get('native_membership',[]) if row['frame_seconds']==300]
    availability=[]  # Actual full dependencies require their own hash-bound receipt.
    artifacts=dict(identity=identity,
        membership=dict(exclusive_verified=roles.get('exclusive') is True,
            minimum_native_open_msc=roles.get('minimum_native_open_msc',0),intervals=intervals),
        coverage=dict(complete=False,five_own_m1=False,ohlc_exact=False,volume_exact=False,two_views_equal=False,bid_ask_preserved=False),
        features=dict(whitelist=list(FEATURES),complete=False,availability=availability),
        seeds=dict(own_post_cut=False,ha_count=0,atr_count=0,native_atr_parity=False),
        calendar=dict(applicable_verified=False,bridges=[]),
        maturity=dict(warmup=receipt.get('technical_consecutive_m5',0),signals=0,post_bars=0,evaluable=0,BUY=0,SELL=0,BUY_folds=0,SELL_folds=0,dataset_hash=receipt.get('dataset_hash'),sealed_membership_hash=None))
    # Terminal identity is not contained in all operational receipt vintages;
    # the adapter's output is deliberately incomplete, not a fresh identity proof.
    packet=bind_packet(artifacts);packet['source_receipt_hash']=seal(receipt)
    return packet
