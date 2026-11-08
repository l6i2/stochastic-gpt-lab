"""Versioned native ATR arithmetic candidate. Diagnostic use only.

No producer import, dataset admission or frozen-feature replacement is provided.
The native seed is observable at bar 14; production readiness remains separately
governed by its existing contract and implementation pin.
"""
import math

from .pretrain_contracts import seal

SCHEMA = 'cf-native-atr14-candidate/1'


def initial_state():
    return dict(schema=SCHEMA,count=0,ranges=[],value=None,previous_close=None,
                last_time=None,seed_bar_hash=None,dependency_hash=None)


def advance(state, bar, bar_hash, decision_native_msc):
    """Return a new state after one closed bar, preserving operation order."""
    count = state['count']
    if (state['schema'] != SCHEMA or type(count) is not int or count < 0
            or len(state['ranges']) != min(14,count)
            or (state['value'] is not None) != (count >= 14)):
        raise ValueError('ATR_CANDIDATE_STATE_INVALID')
    if not bar_hash or (bar['time']+300)*1000 > decision_native_msc:
        raise ValueError('ATR_CANDIDATE_BAR_NOT_AVAILABLE')
    if count and bar['time'] <= state['last_time']:
        raise ValueError('ATR_CANDIDATE_DUPLICATE_OR_OUT_OF_ORDER')
    if not all(math.isfinite(bar[k]) for k in ('open','high','low','close')):
        raise ValueError('ATR_CANDIDATE_NONFINITE_BAR')
    if bar['low'] > min(bar['open'],bar['close']) or bar['high'] < max(bar['open'],bar['close']):
        raise ValueError('ATR_CANDIDATE_INVALID_OHLC')
    span = bar['high']-bar['low'] if count == 0 else (
        max(bar['high'],state['previous_close'])-min(bar['low'],state['previous_close']))
    ranges = (state['ranges']+[span])[-14:]
    value = state['value']
    if count == 13:
        value = 0.0
        for item in ranges:
            value += item
        value /= 14
    elif count >= 14:
        value += (span-state['ranges'][0])/14
    return dict(schema=SCHEMA,count=count+1,ranges=ranges,value=value,
                previous_close=bar['close'],last_time=bar['time'],
                seed_bar_hash=state['seed_bar_hash'] if count else bar_hash,
                dependency_hash=seal(dict(previous=state['dependency_hash'],bar_hash=bar_hash)))


def restore(snapshot):
    state = snapshot['state']
    if snapshot['state_sha256'] != seal(state) or state.get('schema') != SCHEMA:
        raise ValueError('ATR_CANDIDATE_CHECKPOINT_CHANGED')
    # Copy the range window so a caller cannot mutate the checkpoint in place.
    return dict(state,ranges=list(state['ranges']))
