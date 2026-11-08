"""Streaming frozen baseline labels for an allowed TRAIN prefix only. No model."""
import math
from .pretrain_contracts import FEATURES,seal


def initial():return dict(pending=None,active=[],rows=[],last_quote=None,sequence=0,last_bar_index=None)


def consume(state,bar_index,ticks,signal=None):
    """Native ordered ticks; stop boundaries are supplied by the admitted caller.

    TP=240 at fixed level, gap SL at executable quote, TIME_EXIT at observed
    entry-index+100. Positions without that quote are censored, never invented.
    """
    if not ticks:raise ValueError('LABEL_BAR_WITHOUT_QUOTES')
    previous=state['last_bar_index']
    if type(bar_index) is not int or bar_index<0 or previous is not None and bar_index not in (previous,previous+1):
        raise ValueError('LABEL_OBSERVED_BAR_GAP')
    state['last_bar_index']=bar_index
    for tick in ticks:
        stamp=tick['time_msc'];bid=tick['bid'];ask=tick['ask'];state['sequence']+=1
        if not all(math.isfinite(v) for v in (bid,ask)) or not 0<bid<=ask:raise ValueError('INVALID_LABEL_BID_ASK')
        if state['last_quote'] is not None and stamp<state['last_quote']:raise ValueError('LABEL_QUOTE_ORDER_REGRESSION')
        state['last_quote']=stamp
        if state['pending']:
            pending=state.pop('pending');state['pending']=None
            if pending['bar_index']+1!=bar_index or pending['feature_max_native_msc']>=stamp:
                raise ValueError('NONCAUSAL_OR_MISSING_NEXT_ENTRY_BAR')
            side=1 if pending['side']=='BUY' else -1
            row=dict(signal_id=pending['signal_id'],side=pending['side'],decision=stamp,
                arrival_index=state['sequence'],features=pending['features'],observed_bar_index=pending['bar_index'],
                follow_exit=None,invert_exit=None,follow_pnl=None,invert_pnl=None)
            pair=dict(row=row,entry_bar=bar_index,legs={name:dict(side=direction,entry=ask if direction==1 else bid)
                for name,direction in (('follow',side),('invert',-side))})
            state['active'].append(pair)
        for pair in state['active'][:]:
            for name,leg in pair['legs'].items():
                if pair['row'][name+'_exit'] is not None:continue
                pnl=leg['side']*((bid if leg['side']==1 else ask)-leg['entry'])
                if pnl<=-180 or pnl>=240 or bar_index-pair['entry_bar']>=100:
                    pair['row'][name+'_exit']=stamp
                    pair['row'][name+'_pnl']=240. if pnl>=240 else pnl
            if all(pair['row'][name+'_exit'] is not None for name in ('follow','invert')):
                state['rows'].append(pair['row']);state['active'].remove(pair)
    if signal:
        if state['pending'] is not None or set(signal['features'])!=set(FEATURES):raise ValueError('INVALID_PENDING_SIGNAL')
        state['pending']=signal
    return state


def validate_rows(rows):
    previous=-1;ids=set()
    for row in rows:
        if row['signal_id'] in ids or row['observed_bar_index']<=previous:raise ValueError('DUPLICATE_OR_NONCHRONOLOGICAL_LABEL_ROWS')
        ids.add(row['signal_id']);previous=row['observed_bar_index']
        if set(row['features'])!=set(FEATURES) or any(v is None or not math.isfinite(v) for v in row['features'].values()):
            raise ValueError('MISSING_OR_NONFINITE_CAUSAL_FEATURE')
        if any(row[k] is None or row[k]<row['decision'] for k in ('follow_exit','invert_exit')):
            raise ValueError('INCOMPLETE_OR_NONCAUSAL_LABEL_HORIZON')
    return seal(rows)
