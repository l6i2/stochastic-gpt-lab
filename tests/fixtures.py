"""Synthetic contract fixtures. These are NOT historical backtest results."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
import pandas as pd
from research import REQUIRED, FEATURE_COLUMNS, PROFILE_PREFIXES


def dataset(n=100):
    records=[]
    for i in range(n):
        bar=1704067200+i*600
        cutoff=(bar+300)*1000-1
        side=1 if i%2==0 else -1
        row={c:None for c in REQUIRED}
        row.update({c:float((i%10)+1) for c in FEATURE_COLUMNS})
        row.update(signal_id=f'SYNTHETIC_{i}',symbol='SYNTHETIC_US30',schema_version='1.0',trigger_line='MAIN_K',simulation_mode='TICK_QUOTES',signal_time_msc=cutoff,feature_max_time_msc=cutoff,signal_bar_open=bar,entry_bar_open=bar+300,entry_time_msc=cutoff+1,
                   stoch_k_period=5,stoch_d_period=3,stoch_slowing=3,tp_distance=240,sl_distance=180,time_exit_bars=100,zone_run_censored=0,history_bars_available=350,
                   stoch_k=21 if side==1 else 79,stoch_k_prev=20 if side==1 else 80,stoch_d=25,stoch_d_prev=25,
                   volume_feature_source='tick_volume',real_volume_status='zero_or_unavailable',real_volume=0,
                   server_time='2024.01.01 00:05:00',UTC_time='2023.12.31 22:05:00',NY_time='2023.12.31 17:05:00',signal_utc_epoch=bar+300-7200,NY_hour=i%24,NY_minute=5,weekday=6,session='Other',server_utc_offset_seconds=7200,
                   close=1000.,entry_bid=1000.,entry_ask=1002.,spread=2.,follow_side='BUY' if side==1 else 'SELL',invert_side='SELL' if side==1 else 'BUY',excursion_quality='observed_quotes',run_status='OK')
        for p in PROFILE_PREFIXES:
            row.update({p+'status':'available_coverage_unverified',p+'source':'tick_activity_bid',p+'window_start_msc':cutoff-60000,p+'window_end_msc':cutoff,p+'copy_error':0,p+'ticks_used':20,p+'first_tick_msc':cutoff-59000,p+'last_tick_msc':cutoff-1,p+'POC':1005.,p+'VAH':1020.,p+'VAL':980.,p+'distance_price_to_POC':-5.,p+'distance_price_to_VAH':-20.,p+'distance_price_to_VAL':20.})
        for name,direction in [('follow',side),('invert',-side)]:
            entry=1002. if direction==1 else 1000.
            pnl=(240. if i%3 else -180.) if name=='follow' else (-180. if i%3 else 240.)
            row.update({name+'_entry_price':entry,name+'_exit_time':cutoff+1000,name+'_exit_price':entry+direction*pnl,name+'_exit_reason':'TP' if pnl==240 else 'SL',name+'_PnL':pnl,name+'_MFE':max(pnl,0),name+'_MAE':max(-pnl,0),name+'_bars_in_trade':1})
        row['directional_advantage']=row['follow_PnL']-row['invert_PnL']
        records.append(row)
    return pd.DataFrame(records)


def audit(n): return {'schema_version':'1.0','signals':n,'rows_written':n,'aborted':False,'deinit_reason':1}
