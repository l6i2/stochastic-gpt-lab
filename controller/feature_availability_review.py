"""Metadata-only causality checks; not an independence or admission certificate."""
from .pretrain_contracts import FEATURES

GROUPS={
 'Stochastic':'CLOSED_M5_NATIVE_BUFFER_SHIFT_1_MAIN_K_5_3_3',
 'tick_volume':'CLOSED_M5_NATIVE_BID_UPDATE_VOLUME_PARITY_REQUIRED',
 'Volume_Profile':'TICK_WINDOW_END_AND_LAST_TICK_AT_OR_BEFORE_CUTOFF',
 'POC':'DETERMINISTIC_MAX_MASS_BIN_LOWER_PRICE_TIE',
 'VAH_VAL':'CONTIGUOUS_VALUE_AREA_70_PERCENT_NO_FUTURE_TICKS',
 'HVN_LVN':'LOCAL_BIN_NEIGHBORS_WITHIN_CLOSED_PROFILE_WINDOW',
 'Heikin_Ashi':'ENTIRE_RECURSION_FROM_OWN_SEED_READY_276',
 'ATR':'NATIVE_14_PERIOD_INITIALIZATION_BOUND_TO_OWN_HISTORY',
 'EMA':'RECURSIVE_NATIVE_SEED_PROVENANCE_NOT_JUST_LAST_350_BARS',
 'trend':'CLOSED_EMA_ALIGNMENT_AND_PAST_SLOPES',
 'structure':'CLOSED_ROLLING_HH_HL_LH_LL_NO_CENTERED_FUTURE_PIVOTS',
 'hours_sessions':'VERIFIED_EVENT_UTC_AND_IANA_MAPPING_NO_GUESSED_SERVER_OFFSET',
}


def review(metadata):
    required={'feature','source_max_native_msc','decision_native_msc','cutoff_native_msc','ready_order','decision_order','seed_required','seed_own','coverage_verified','utc_mapping_required','utc_mapping_verified'}
    if set(metadata)!=required:raise ValueError('UNKNOWN_OR_MISSING_CAUSAL_METADATA')
    m=metadata
    for k in ('source_max_native_msc','decision_native_msc','cutoff_native_msc','ready_order','decision_order'):
        if type(m[k]) is not int or m[k]<0:raise ValueError('INVALID_NATIVE_DEPENDENCY_POSITION')
    if m['source_max_native_msc']>m['cutoff_native_msc'] or m['cutoff_native_msc']>=m['decision_native_msc']:raise ValueError('FUTURE_OR_FORMING_BAR_DEPENDENCY')
    if m['ready_order']>=m['decision_order']:raise ValueError('FEATURE_NOT_READY_BEFORE_DECISION')
    if m['seed_required'] and not m['seed_own']:raise ValueError('UNBOUND_OR_PRE_START_RECURSIVE_SEED')
    if m['utc_mapping_required'] and not m['utc_mapping_verified']:raise ValueError('UNVERIFIED_SESSION_TIME_DOMAIN')
    return dict(structural_availability='PASS_DECLARED_METADATA_ONLY',coverage='VERIFIED_AS_DECLARED' if m['coverage_verified'] else 'PARTIAL_UNVERIFIED',real_feature_values_verified=False,admitted=False,whitelisted_for_current_study=m['feature'] in FEATURES)


def structure_break_observation(highs,lows):
    """Reproduce the frozen producer's inclusive-window flags; do not repair it."""
    if len(highs)!=20 or len(lows)!=20:raise ValueError('FROZEN_STRUCTURE_WINDOW_REQUIRES_20_CLOSED_BARS')
    import math
    if any(not math.isfinite(v) for v in highs+lows) or any(h<l for h,l in zip(highs,lows)):raise ValueError('INVALID_STRUCTURE_FIXTURE')
    return dict(recent_high_break=highs[0]>max(highs),recent_low_break=lows[0]<min(lows),interpretation='INCLUSIVE_CURRENT_BAR_EXTREME_MAKES_BOTH_FLAGS_FALSE_FOR_FINITE_VALID_INPUTS',strategy_changed=False)
