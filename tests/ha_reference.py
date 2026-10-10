"""Independent batch oracle for the streaming native HA implementation; test only."""
import numpy as np
import pandas as pd
from heikin_ashi import HA_COLUMNS, HA_READY_BARS, HA_WARMUP


def reference(raw, cutoff):
    raw=raw.loc[(raw.time+300)*1000-1<=cutoff]
    history=[]; result=[]
    for row in raw.itertuples(index=False):
        close=(row.open+row.high+row.low+row.close)/4
        op=(row.open+row.close)/2 if not history else (history[-1]['o']+history[-1]['c'])/2
        high=max(row.high,op,close);low=min(row.low,op,close)
        direction=int(np.sign(close-op))
        prev=history[-1] if history else {'bull':0,'bear':0,'direction':0}
        b={'o':op,'h':high,'l':low,'c':close,'direction':direction,
           'body':abs(close-op),'range':high-low,'upper':high-max(op,close),'lower':min(op,close)-low,
           'bull_before':prev['bull'],'bear_before':prev['bear'],
           'bull':prev['bull']+1 if direction==1 else 0,'bear':prev['bear']+1 if direction==-1 else 0}
        history.append(b);n=len(history)
        f=dict.fromkeys(HA_COLUMNS,np.nan)
        f.update(ha_status='ready' if n>=HA_READY_BARS else 'warming_up',ha_seed_bar_open=int(raw.time.iloc[0]),ha_last_bar_open=row.time,ha_bars_processed=n,ha_warmup_bars=HA_WARMUP,
                 ha_streak_left_censored=int(b['bull']==n or b['bear']==n or (n>1 and (b['bull_before']==n-1 or b['bear_before']==n-1))))
        if n>=HA_READY_BARS:
            def ratio(a,d):return a/d if d else np.nan
            f.update(ha_open=op,ha_high=high,ha_low=low,ha_close=close,ha_direction=direction,ha_body=b['body'],ha_range=b['range'],ha_body_percent=ratio(100*b['body'],b['range']),ha_upper_wick=b['upper'],ha_lower_wick=b['lower'],ha_upper_wick_to_range=ratio(b['upper'],b['range']),ha_lower_wick_to_range=ratio(b['lower'],b['range']))
            for lag in (1,2,3):
                f[f'ha_delta_close_{lag}']=close-history[-1-lag]['c']
                f[f'ha_delta_body_{lag}']=b['body']-history[-1-lag]['body']
            f['ha_body_expansion']=ratio(b['body'],prev['body']);f['ha_range_expansion']=ratio(b['range'],prev['range'])
            f['ha_consecutive_bullish']=b['bull'];f['ha_consecutive_bearish']=b['bear']
            for w in (3,5,10,20):
                past=history[-w:]
                for side,d in [('bullish',1),('bearish',-1)]:f[f'ha_{side}_ratio_{w}']=sum(x['direction']==d for x in past)/w
                for kind in ('body','range'):f[f'ha_avg_{kind}_{w}']=sum(x[kind] for x in past)/w
            for w in (5,10):
                for kind in ('body','range'):f[f'ha_{kind}_vs_avg{w}']=ratio(b[kind],sum(x[kind] for x in history[-w-1:-1])/w)
            nl=b['lower']<=1e-10;nu=b['upper']<=1e-10;small=b['range']>0 and b['body']<=.25*b['range']
            f.update(ha_no_lower_wick=int(nl),ha_no_upper_wick=int(nu),ha_small_body=int(small),
                     ha_bullish_strong=int(direction==1 and nl and b['body']>=.5*b['range']),ha_bearish_strong=int(direction==-1 and nu and b['body']>=.5*b['range']),ha_indecision=int(small and not nl and not nu),
                     ha_changed_to_bullish=int(direction==1 and prev['direction']!=1),ha_changed_to_bearish=int(direction==-1 and prev['direction']!=-1),
                     ha_bullish_after_bearish_run=int(direction==1 and b['bear_before']>0),ha_bearish_after_bullish_run=int(direction==-1 and b['bull_before']>0),
                     ha_bullish_run_before_signal=b['bull_before'],ha_bearish_run_before_signal=b['bear_before'])
        result.append(f)
    return pd.DataFrame(result)


def candles(n=320):
    rng=np.random.default_rng(831)
    op=1000+rng.normal(0,20,n).cumsum();close=op+rng.normal(0,12,n)
    return pd.DataFrame({'time':1704067200+np.arange(n)*300,'open':op,'high':np.maximum(op,close)+rng.uniform(0,10,n),'low':np.minimum(op,close)-rng.uniform(0,10,n),'close':close})
