"""Causal dataset contract and chronological partitions. No trade optimization."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from heikin_ashi import HA_COLUMNS, HA_METADATA, validate_ha

PROFILE_PREFIXES = [f"vp_{m}m_" for m in (30,60,120,240)] + ["vp_session_", "vp_previous_session_"]
PROFILE_VALUES = ["POC","VAH","VAL","distance_price_to_POC","distance_price_to_VAH","distance_price_to_VAL","inside_value_area","above_value_area","below_value_area","POC_position_in_range","high_volume_node_nearest","low_volume_node_nearest","distance_to_HVN","distance_to_LVN"]
FEATURE_COLUMNS = [
 "stoch_k","stoch_d","stoch_k_prev","stoch_d_prev","distance_to_20","distance_to_80",
 *[f"delta_{line}_{i}" for line in ('k','d') for i in (1,2,3)],
 "bars_in_oversold","bars_in_overbought","exit_speed_from_zone","tick_volume","real_volume",
 *[f"relative_volume_{w}" for w in (5,10,20,50,100)],
 *[f"volume_change_{w}" for w in (1,3,5)],
 *[f"volume_percentile_{w}" for w in (20,50,100)],
 "volume_zscore_20","volume_zscore_50","volume_expansion",
 "open","high","low","close","direction","body","range","body_percent","upper_wick","lower_wick","range_to_ATR",
 *[f"{side}_ratio_{w}" for side in ('bullish','bearish') for w in (5,10,20)],
 "ATR","ATR_normalized",*[f"ATR_percentile_{w}" for w in (20,50,100)],
 "rolling_std_20","rolling_std_50","range_expansion","range_compression",
 *[f"price_to_ema{w}" for w in (20,50,100,200)],
 *[f"ema{w}_slope" for w in (20,50,100,200)],
 "ema20_minus_50","ema50_minus_100","ema100_minus_200","bull_alignment","bear_alignment",
 *[f"{kind}_count_{w}" for kind in ('HH','HL','LH','LL') for w in (5,10,20)],
 "distance_to_recent_high","distance_to_recent_low","NY_hour","NY_minute","weekday",
 *[p+f for p in PROFILE_PREFIXES for f in PROFILE_VALUES],
]
METADATA = ['signal_id','symbol','schema_version','trigger_line','simulation_mode','signal_time_msc','feature_max_time_msc','signal_bar_open','entry_bar_open','entry_time_msc','stoch_k_period','stoch_d_period','stoch_slowing','tp_distance','sl_distance','time_exit_bars','zone_run_censored','history_bars_available','volume_feature_source','real_volume_status','server_time','UTC_time','NY_time','signal_utc_epoch','session','server_utc_offset_seconds','entry_bid','entry_ask','spread','follow_side','invert_side','excursion_quality','run_status']
PROFILE_META = ['status','source','window_start_msc','window_end_msc','copy_error','ticks_used','first_tick_msc','last_tick_msc']
OUTCOMES = [f'{side}_{field}' for side in ('follow','invert') for field in ('entry_price','exit_time','exit_price','exit_reason','PnL','MFE','MAE','bars_in_trade')] + ['directional_advantage']
REQUIRED = list(dict.fromkeys(METADATA+FEATURE_COLUMNS+[p+f for p in PROFILE_PREFIXES for f in PROFILE_META]+OUTCOMES))

REQUIRED_V1 = REQUIRED.copy()
FEATURE_COLUMNS_V1 = FEATURE_COLUMNS.copy()
FEATURE_COLUMNS += HA_COLUMNS
METADATA += HA_METADATA
REQUIRED += HA_COLUMNS + HA_METADATA


def read_dataset(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix == '.parquet':
        return pd.read_parquet(path)
    # Reject duplicate headers rather than accepting pandas' automatic renaming.
    import csv
    with path.open(encoding='utf-8-sig', newline='') as fh:
        header = next(csv.reader(fh), [])
    if len(header) != len(set(header)):
        raise ValueError('Duplicate CSV column names')
    if not header:
        raise ValueError('Empty run: no event header. Check the EA audit file.')
    return pd.read_csv(path)


def validate(df: pd.DataFrame, audit: dict | None = None) -> list[str]:
    errors: list[str] = []
    versions = set(df.schema_version.astype(str)) if 'schema_version' in df else set()
    if len(versions)!=1 or not versions.issubset({'1.0', '1.1'}):
        return ['Unsupported or mixed schema_version (expected 1.0 or 1.1)']
    has_ha = versions == {'1.1'}
    if not has_ha and any(c in df for c in HA_COLUMNS+HA_METADATA):
        return ['HEIKIN_ASHI columns require schema_version 1.1']
    missing = sorted(set(REQUIRED if has_ha else REQUIRED_V1)-set(df.columns))
    if missing:
        return ['Missing columns: '+', '.join(missing)]
    def check(ok, message):
        if not bool(ok): errors.append(message)
    def allclose(a, b):
        return np.allclose(a, b, atol=1e-7, rtol=1e-9, equal_nan=False)
    check(not df.empty, 'Dataset has no signals')
    if df.empty: return errors
    check(df.signal_id.notna().all() and df.signal_id.is_unique, 'Duplicate or missing signal_id')
    check(df.signal_time_msc.is_monotonic_increasing, 'Non-monotonic signal timestamps')
    check(not df.duplicated(['symbol','signal_time_msc']).any(), 'Multiple records for one symbol/signal time')
    check(df.symbol.nunique()==1, 'One symbol per dataset required')
    for c in ('trigger_line','simulation_mode','server_utc_offset_seconds'):
        if c!='server_utc_offset_seconds': check(df[c].nunique()==1, f'Mixed run configuration: {c}')
    for key, value in [('stoch_k_period',5),('stoch_d_period',3),('stoch_slowing',3),('tp_distance',240),('sl_distance',180),('time_exit_bars',100)]:
        check(df[key].eq(value).all(), f'Invalid strategy constant: {key}')
    check(df.run_status.eq('OK').all(), 'Aborted EA run')
    check(df.trigger_line.isin(['MAIN_K','SIGNAL_D']).all(), 'Invalid trigger line')
    check(df.simulation_mode.isin(['TICK_QUOTES','BAR_CONSERVATIVE']).all(), 'Invalid simulation mode')
    check((df.feature_max_time_msc<=df.signal_time_msc).all(), 'Future feature timestamp')
    check((df.signal_time_msc==(df.signal_bar_open+300)*1000-1).all(), 'Signal not at M5 close')
    check((df.entry_bar_open>=df.signal_bar_open+300).all(), 'Entry before following available bar')
    check(((df.entry_time_msc>=df.entry_bar_open*1000)&(df.entry_time_msc<(df.entry_bar_open+300)*1000)).all(), 'Entry outside next observed bar')
    check((df.entry_time_msc>df.signal_time_msc).all(), 'Entry not after signal')
    check(allclose(df.spread,df.entry_ask-df.entry_bid) and df.spread.ge(0).all(), 'Invalid entry spread')
    check((df.entry_bid>0).all(), 'Invalid entry quote')
    check(df.follow_side.isin(['BUY','SELL']).all(), 'Invalid FOLLOW side')
    check(df.invert_side.eq(df.follow_side.map({'BUY':'SELL','SELL':'BUY'})).all(), 'Invalid INVERT mapping')
    current=np.where(df.trigger_line.eq('MAIN_K'),df.stoch_k,df.stoch_d)
    previous=np.where(df.trigger_line.eq('MAIN_K'),df.stoch_k_prev,df.stoch_d_prev)
    valid_buy=(previous<=20)&(current>20); valid_sell=(previous>=80)&(current<80)
    check(np.where(df.follow_side.eq('BUY'),valid_buy,valid_sell).all(), 'Signal is not an exit from the specified zone')
    check(df.tick_volume.ge(0).all() and df.real_volume.ge(0).all(), 'Negative broker volume')
    check(df.volume_feature_source.eq('tick_volume').all(), 'Volume source mislabeled')
    check(df.NY_hour.between(0,23).all() and df.NY_minute.between(0,59).all(), 'Invalid NY time')
    for p in PROFILE_PREFIXES:
        check((df[p+'window_end_msc']<=df.signal_time_msc).all(), f'Future profile window: {p}')
        check(df[p+'source'].isin(['tick_activity_bid','real_trade_volume_last']).all(), f'Invalid profile source: {p}')
        check(df[p+'status'].isin(['available_coverage_unverified','empty_window','copy_error_or_limit','no_eligible_ticks','bin_limit']).all(), f'Invalid profile status: {p}')
        available=df[p+'status'].eq('available_coverage_unverified'); d=df[available]
        check(d[p+'ticks_used'].gt(0).all(), f'Profile has no ticks: {p}')
        check(((d[p+'first_tick_msc']>=d[p+'window_start_msc'])&(d[p+'last_tick_msc']<=d[p+'window_end_msc'])&(d[p+'last_tick_msc']>=d[p+'first_tick_msc'])).all(), f'Profile ticks outside causal window: {p}')
        check(((d[p+'VAL']<=d[p+'POC'])&(d[p+'POC']<=d[p+'VAH'])).all(), f'Invalid value area: {p}')
        check(df.loc[~available,[p+v for v in PROFILE_VALUES]].isna().all().all(), f'Unavailable profile has fabricated values: {p}')
        for level in ('POC','VAH','VAL'):
            check(allclose(d[p+'distance_price_to_'+level],d.close-d[p+level]), f'Profile distance mismatch: {p}{level}')
    for side in ('follow','invert'):
        direction=df[side+'_side'].map({'BUY':1,'SELL':-1})
        entry=df[side+'_entry_price']; expected=np.where(direction.eq(1),df.entry_ask,df.entry_bid)
        check(allclose(entry,expected),f'Wrong {side} entry bid/ask')
        reason=df[side+'_exit_reason']; done=reason.ne('END_OF_DATA')
        check(reason.isin(['SL','TP','TIME_EXIT','END_OF_DATA']).all(),f'Unknown {side} exit reason')
        check((df[side+'_exit_time']>=df.entry_time_msc).all(),f'{side} exit before entry')
        check(df[side+'_bars_in_trade'].between(1,100).all(),f'{side} invalid bar duration')
        check(df.loc[reason.eq('TIME_EXIT'),side+'_bars_in_trade'].eq(100).all(),f'{side} invalid TIME_EXIT')
        check(allclose(df.loc[done,side+'_PnL'],(direction*(df[side+'_exit_price']-entry))[done]),f'{side} PnL arithmetic')
        check(df.loc[~done,side+'_PnL'].isna().all(),f'{side} censored PnL must be missing')
        check(allclose(df.loc[reason.eq('TP'),side+'_PnL'],np.full(reason.eq('TP').sum(),240)),f'{side} TP must be 240')
        check(df.loc[reason.eq('SL'),side+'_PnL'].le(-180+1e-7).all(),f'{side} SL must be <= -180 (gaps)')
        check(df[side+'_MFE'].ge(0).all() and df[side+'_MAE'].ge(0).all(),f'{side} invalid excursions')
    complete=df.follow_exit_reason.ne('END_OF_DATA')&df.invert_exit_reason.ne('END_OF_DATA')
    check(allclose(df.loc[complete,'directional_advantage'],(df.follow_PnL-df.invert_PnL)[complete]),'Invalid directional advantage')
    check(df.loc[~complete,'directional_advantage'].isna().all(),'Censored advantage must be missing')
    numeric=df.select_dtypes(include='number')
    check(not np.isinf(numeric.to_numpy()).any(), 'Infinite numeric values')
    if audit is not None:
        check(not audit.get('aborted',True), 'Audit reports aborted run')
        check(audit.get('signals')==audit.get('rows_written')==len(df), 'Audit signal/row count mismatch')
    if has_ha:
        errors.extend(validate_ha(df))
    if audit is not None:
        check(str(audit.get('schema_version')) in versions, 'Audit schema version mismatch')
    return errors


def chronological_split(df: pd.DataFrame, train=.6, validation=.2):
    if not (0<train<1 and 0<validation<1 and train+validation<1):
        raise ValueError('Require positive TRAIN/VALIDATION/TEST fractions summing to 1')
    if not df.signal_time_msc.is_monotonic_increasing or not df.signal_time_msc.is_unique:
        raise ValueError('Chronological unique signal order required; no sorting/shuffling is performed')
    a,b=int(len(df)*train),int(len(df)*(train+validation))
    if not (0<a<b<len(df)):
        raise ValueError('Not enough signals for three nonempty partitions')
    return {'TRAIN':df.iloc[:a].copy(),'DISCOVERY_VALIDATION':df.iloc[a:b].copy(),'FINAL_TEST':df.iloc[b:].copy()}


def purge_at_boundary(df: pd.DataFrame, boundary: int | None):
    """Do not let labels use quotes from the next research partition."""
    if boundary is None: return df.copy(), 0
    label_end=df[['follow_exit_time','invert_exit_time']].max(axis=1)
    keep=label_end<boundary
    return df.loc[keep].copy(), int((~keep).sum())


def walk_forward(pool: pd.DataFrame, initial: int, step: int):
    if initial<1 or step<1: raise ValueError('Walk-forward sizes must be positive')
    for end in range(initial,len(pool),step):
        train=pool.iloc[:end].copy(); validation=pool.iloc[end:end+step].copy()
        train,purged=purge_at_boundary(train,int(validation.signal_time_msc.iloc[0]))
        following=end+step
        boundary=int(pool.signal_time_msc.iloc[following]) if following<len(pool) else None
        validation,val_purged=purge_at_boundary(validation,boundary)
        yield train,validation,{'train_purged':purged,'validation_purged':val_purged}


def causal_profile(ticks: pd.DataFrame, start: int, cutoff: int, bin_size=10., real=False):
    """Small reference oracle for tests, using only ticks in the requested interval.
    Production profiles are constructed in the EA with CopyTicksRange.
    """
    if bin_size<=0: raise ValueError('bin_size must be positive')
    t=ticks.loc[ticks.time_msc.between(start,cutoff)].copy()
    if real:
        t=t[(t['flags'].astype(int)&(8|16|32|64)!=0)&(t.volume_real>0)&(t['last']>0)]
        px=t['last']; weights=t.volume_real
    else:
        t=t[t.bid>0]; px=t.bid; weights=pd.Series(1.,index=t.index)
    if t.empty: return None
    bins=np.floor(px/bin_size).astype(int)
    mass=weights.groupby(bins).sum(); mass=mass.reindex(range(mass.index.min(),mass.index.max()+1),fill_value=0.)
    poc=int(np.argmax(mass.to_numpy())); left=right=poc; total=mass.iloc[poc]
    while total<.7*mass.sum():
        lw=mass.iloc[left-1] if left>0 else -1
        rw=mass.iloc[right+1] if right<len(mass)-1 else -1
        if lw>=rw: left-=1; total+=mass.iloc[left]
        else: right+=1; total+=mass.iloc[right]
    return {'POC':(mass.index[poc]+.5)*bin_size,'VAL':mass.index[left]*bin_size,'VAH':(mass.index[right]+1)*bin_size,'last_tick_msc':int(t.time_msc.max()),'ticks_used':len(t)}
