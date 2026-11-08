"""Approved B+C acquisition math. No training, labels, orders or admission."""
import copy
import math
from .pretrain_contracts import seal
from .cf_atr_candidate import initial_state as atr_initial, advance as atr_advance
from .xm_history_recovery import quality, validate_rows

STUDY='US30CASH_M5_XM_TRAIN_FUTURE_EVAL_PROPOSED_V1'
FRAME=300000


def initial():
    return dict(schema='bc-incremental/1',floor=None,cursor=None,completed={},epoch=1,
        last_bar=None,total_m5=0,rejected=0,history=[],atr=atr_initial(),ha=None,
        run_bars=0,previous_k=None,BUY=0,SELL=0,base_signals=0,post_bars=0,
        dependency=None,last_runtime=None,acquisition_complete=False)


def native_floor(anchor,new_quote):
    """A stale weekend quote cannot establish post-authorization native bounds."""
    old=anchor['time_msc'];new=new_quote['time_msc']
    if type(old) is not int or type(new) is not int or new<=old:return None
    # Always skip the observed forming interval, including exact boundary ticks.
    return (new//FRAME+1)*FRAME


def check_request(start,end,floor,observed_native_msc):
    if (type(floor) is not int or type(start) is not int or type(end) is not int
            or start%FRAME or end-start!=FRAME or start<floor
            or end>observed_native_msc//FRAME*FRAME):
        raise PermissionError('BC_UNRESERVED_OR_FORMING_OR_PRECUT_INTERVAL')


def assessment(rows,start,end):
    for kind in ('ticks','m1','m5'):validate_rows(rows[kind],kind,start,end)
    q=quality(rows['ticks'],rows['m1'],rows['m5'],start,end)
    complete=(len(rows['m1'])==5 and len(rows['m5'])==1
        and q['invalid_bid_ask_rows']==0 and bool(rows['ticks'])
        and all(x['status']=='EXACT' for x in q['m1_m5'])
        and all(x['ohlc']=='EXACT' and x['bid_flag_rows']==x['native_volume'] for x in q['tick_m1']))
    return dict(quality=q,native_archive_parity=complete,
        scientific_admission=False,live_receipt_proven=False,
        classification='VERIFIED_NATIVE_ARCHIVE_QUARANTINED' if complete else 'PARTIAL_QUARANTINED')


def reset(state):
    state.update(history=[],atr=atr_initial(),ha=None,run_bars=0,previous_k=None,
        base_signals=0,post_bars=0,BUY=0,SELL=0,dependency=None,acquisition_complete=False)
    state['epoch']+=1


def advance(state,bar,manifest_hash):
    """Prefix-only features. Historical context is not a claim of live receipt."""
    s=copy.deepcopy(state)
    if s['last_bar'] is not None and bar['time']<=s['last_bar']:
        raise ValueError('BC_DUPLICATE_OR_BACKWARD_BAR')
    boundary=s['last_bar'] is not None and bar['time']!=s['last_bar']+300
    if boundary:reset(s)  # No calendar bridge without a separately verified proof.
    previous_count=s['run_bars'];role='TRAIN_CONTEXT' if previous_count<350 else 'TRAIN_DEV'
    s['last_bar']=bar['time'];s['total_m5']+=1;s['run_bars']+=1
    bh=seal(bar);s['atr']=atr_advance(s['atr'],bar,bh,(bar['time']+300)*1000)
    hc=(bar['open']+bar['high']+bar['low']+bar['close'])/4
    ho=(bar['open']+bar['close'])/2 if s['ha'] is None else (s['ha']['open']+s['ha']['close'])/2
    s['ha']=dict(open=ho,close=hc,count=s['run_bars'],seed_bar_hash=s['ha']['seed_bar_hash'] if s['ha'] else bh)
    s['history']=(s['history']+[dict(bar,bar_hash=bh)])[-351:]
    from python.native_metadata_v3 import main_k
    k=list(main_k(s['history'][-7:]))[-1];previous=s['previous_k'];s['previous_k']=k
    volumes=[b['tick_volume'] for b in s['history'][-21:-1]] if len(s['history'])>=21 else []
    mean=sum(volumes)/20 if volumes else None;atr=s['atr']['value']
    values=dict(stoch_k=k,delta_k_1=k-previous if k is not None and previous is not None else None,
        ATR=atr,relative_volume_20=bar['tick_volume']/mean if mean else None,
        ha_direction=(1 if hc>ho else -1 if hc<ho else 0) if s['run_bars']>=276 else None,
        range_to_ATR=(bar['high']-bar['low'])/atr if atr else None)
    side='BUY' if previous is not None and k is not None and previous<=20<k else 'SELL' if previous is not None and k is not None and previous>=80>k else None
    was_complete=s['base_signals']==800
    if was_complete:s['post_bars']=min(100,s['post_bars']+1)
    elif side and role=='TRAIN_DEV':
        s[side]+=1;s['base_signals']+=1
    s['acquisition_complete']=s['base_signals']==800 and s['post_bars']==100
    s['dependency']=seal(dict(previous=s['dependency'],bar=bh))
    artifact=dict(native_bar=bar,bar_hash=bh,role=role,epoch=s['epoch'],manifest_hash=manifest_hash,
        values=values,feature_hash=seal(values),feature_max_native_msc=(bar['time']+300)*1000-1,
        earliest_decision_native_msc=(bar['time']+300)*1000,
        dependency_hash=s['dependency'],ATR_seed_hash=s['atr']['seed_bar_hash'],
        HA_seed_hash=s['ha']['seed_bar_hash'],signal_side=side if role=='TRAIN_DEV' and not was_complete else None,
        full_features=all(v is not None and math.isfinite(v) for v in values.values()),
        calendar_boundary_unverified=boundary,quarantine=True,scientific_admission=False,
        semantics='HISTORICAL_NATIVE_PREFIX_AVAILABILITY_NOT_ORIGINAL_RECEIPT_OR_UTC_GENERATION')
    return s,artifact


def evaluation_guard(freeze,train_last_label,purge_end,observation):
    """Planning check only; cannot assign EVAL or enable scoring."""
    if (not freeze or not freeze.get('model_hashes') or not freeze.get('authorized_evaluation_receipt')
            or not all(type(x) is int for x in (train_last_label,purge_end,observation.get('monotonic_ns')))
            or observation.get('boot_id')!=freeze.get('boot_id')
            or not train_last_label<=purge_end<freeze['monotonic_ns']<observation['monotonic_ns']):
        raise PermissionError('BC_EVALUATION_NOT_AUTHORIZED_OR_NOT_AFTER_FREEZE_AND_PURGE')
    return 'CONDITIONAL_ORDER_ONLY_NOT_ADMISSION'
