"""Native-clock technical parity; no dataset admission or hypothesis scoring."""
import csv
import gzip
import html
import json
from pathlib import Path
import re
import sys
from .native_diagnostic import BASE,SERVER,DATA_NAME
from .profiles import BASE_OUTPUTS
from .compile_runner import sha256
from .safety_gate import ROOT


def capture_rates(environment,folder):
    import MetaTrader5 as mt5
    if not mt5.initialize(path=environment['TERMINAL_PATH'],timeout=5000):raise ValueError('ORIGINAL_TERMINAL_ATTACH_FAILED')
    try:
        t=mt5.terminal_info();a=mt5.account_info()
        if not t or Path(t.data_path).name!=DATA_NAME or not a or a.trade_mode!=0 or a.server!=SERVER:raise ValueError('PINNED_ORIGINAL_DEMO_MISMATCH')
        result={}
        for label,tf in [('M1',mt5.TIMEFRAME_M1),('M5',mt5.TIMEFRAME_M5)]:
            path=folder/('native_'+label+'.csv')
            if path.exists():
                with path.open() as stream:
                    if any(not 1704153600<=int(r['time'])<1704240000 for r in csv.DictReader(stream)):raise ValueError('EXISTING_OUT_OF_RANGE_RESPONSE_RETAINED_NOT_ACCEPTED_'+label)
                continue
            from datetime import datetime,timezone
            rows=mt5.copy_rates_range('US30Cash',tf,datetime(2024,1,2,tzinfo=timezone.utc),datetime(2024,1,2,23,59,59,tzinfo=timezone.utc))
            if rows is None or not len(rows):raise ValueError('NATIVE_RATES_UNAVAILABLE_'+label)
            if any(not 1704153600<=int(r['time'])<1704240000 for r in rows):raise ValueError('OUT_OF_RANGE_API_RESPONSE_REJECTED_'+label)
            with path.open('x',newline='',encoding='utf-8') as stream:
                writer=csv.writer(stream);writer.writerow(rows.dtype.names)
                for row in rows:writer.writerow([row[n].item() for n in rows.dtype.names])
            result[label]=len(rows)
        info=mt5.symbol_info('US30Cash')
        result['symbol']={k:getattr(info,k,None) for k in ('name','digits','point','chart_mode','trade_tick_size','trade_calc_mode')}
        result['time_basis']='NATIVE_EPOCH_LABEL_RANGE_NOT_CERTIFIED_UTC'
        return result
    finally:mt5.shutdown()


def bars_from_tape(tape,seconds):
    result=[];bar=None
    for row in tape:
        start=int(row['time_msc'])//(seconds*1000)*seconds;price=float(row['bid'])
        if bar is None or bar['time']!=start:
            if bar:result.append(bar)
            bar=dict(time=start,open=price,high=price,low=price,close=price,observed_quotes=0)
        bar['high']=max(bar['high'],price);bar['low']=min(bar['low'],price);bar['close']=price;bar['observed_quotes']+=1
    if bar:result.append(bar)
    return result


def reconcile(first,second):
    import numpy as np
    sys.path.insert(0,str(ROOT/'python'))
    from validate_bar_path import validate as baseline,QUOTE_DTYPE
    from validate_intratrade_dataset import validate as causal
    from research import read_dataset,validate as events_validate
    from causal_metadata_audit import main_values
    import pc_a_raw_archive as raw
    folders=[BASE/'runs'/r for r in (first,second)];folder=folders[0]
    p=lambda suffix:folder/(first+'_'+suffix)
    suffixes=BASE_OUTPUTS+('bar_execution_quotes.csv','bar_quote_path.bin','bar_trade_index.csv')
    deterministic={s:sha256(folders[0]/(first+'_'+s))==sha256(folders[1]/(second+'_'+s)) for s in suffixes}
    replay=baseline(p('bar_quote_path.bin'),p('bar_trade_index.csv'),p('stochastic_events.csv'),p('bar_execution_quotes.csv'),1704240000000)
    features=causal(p('intratrade_snapshots.csv'),targets_csv=p('intratrade_snapshot_targets.csv'),events_csv=p('stochastic_events.csv'),execution_quotes_csv=p('bar_execution_quotes.csv'))
    errors=events_validate(read_dataset(p('stochastic_events.csv')),json.loads(p('stochastic_events.csv.audit.json').read_text()))
    tape=np.memmap(p('bar_quote_path.bin'),dtype=QUOTE_DTYPE,mode='r');ohlc={};bars=None
    if int(tape['time_msc'].min())<1704153600000 or int(tape['time_msc'].max())>=1704240000000:raise ValueError('TESTER_TAPE_OUT_OF_FIXED_DIAGNOSTIC_RANGE')
    for label,seconds in [('M1',60),('M5',300)]:
        calculated=bars_from_tape(tape,seconds)
        native_path=p('stochastic_events.csv.native_'+label+'.csv')
        if not native_path.exists():native_path=folder/('native_'+label+'.csv')
        with native_path.open() as stream:native=list(csv.DictReader(stream))
        if any(not 1704153600<=int(n['time'])<1704240000 for n in native):raise ValueError('NATIVE_RATE_OUT_OF_DIAGNOSTIC_RANGE')
        indexed={int(r['time']):r for r in native};mismatch=[]
        for b in calculated:
            n=indexed.get(b['time'])
            if n is None or any(b[k]!=float(n[k]) for k in ('open','high','low','close')):mismatch.append(b['time'])
        ohlc[label]=dict(tape_bars=len(calculated),native_bars=len(native),ohlc_exact_matches=len(calculated)-len(mismatch),mismatched_native_bar_times=mismatch,missing_tape_bars=sorted(set(indexed)-{b['time'] for b in calculated}))
        if label=='M5':bars=calculated
    values=main_values(bars,native_reference=True);value_by_cutoff={(b['time']+300)*1000-1:(i,b) for i,b in enumerate(bars)}
    with p('stochastic_events.csv').open(encoding='utf-8-sig') as stream:events=list(csv.DictReader(stream))
    actual={int(e['signal_time_msc']):e for e in events};maximum_error=0.;compared=0;signals={}
    for i in range(7,len(bars)):
        previous,current=values[i-1:i+1];side=1 if previous<=20 and current>20 else -1 if previous>=80 and current<80 else 0
        cutoff=(bars[i]['time']+300)*1000-1
        if side and i+1<len(bars):signals[cutoff]=side
    for cutoff,event in actual.items():
        i,_=value_by_cutoff[cutoff]
        if i<7:continue
        maximum_error=max(maximum_error,abs(float(event['stoch_k'])-values[i]),abs(float(event['stoch_k_prev'])-values[i-1]));compared+=1
    native_main=p('stochastic_events.csv.native_main.csv');all_bar_comparisons=0;all_bar_error=0.
    if native_main.exists():
        by_open={b['time']:i for i,b in enumerate(bars)}
        with native_main.open() as stream:
            for row in csv.DictReader(stream):
                i=by_open[int(row['bar_open_native'])]
                if i<7:continue
                all_bar_comparisons+=1
                all_bar_error=max(all_bar_error,abs(float(row['main_k'])-values[i]),abs(float(row['previous_main_k'])-values[i-1]))
    eligible={c:1 if e['follow_side']=='BUY' else -1 for c,e in actual.items() if value_by_cutoff[c][0]>=7}
    # Existing native MAIN_K oracle's frozen 1e-10 numeric bound; no new tolerance.
    main=dict(status='PASS' if max(maximum_error,all_bar_error)<=1e-10 and signals==eligible and compared else 'FAIL',compared_signals=compared,max_error=maximum_error,
        all_native_closed_bars_compared=all_bar_comparisons,all_bar_max_error=all_bar_error,
        inherited_oracle_absolute_tolerance=1e-10,early_warmup_rows_not_compared=sum(value_by_cutoff[c][0]<7 for c in actual),missing_signal_cutoffs=sorted(set(signals)-set(eligible)))
    historical=raw.BASE/json.loads((raw.BASE/'historical_active.json').read_text())['archive_id'];manifest=raw.verify(historical);index=0;different=0
    from collections import Counter
    bid_updates={60:Counter(),300:Counter()}
    for segment in manifest['segments']:
        with gzip.open(historical/segment['ticks']['file'],'rt',newline='') as stream:
            for row in csv.DictReader(stream):
                if index>=len(tape) or any(float(row[k])!=float(tape[index][k]) for k in ('time_msc','bid','ask')):different+=1
                index+=1
                if int(row['flags'])&2:
                    for sec,counts in bid_updates.items():counts[int(row['time_msc'])//(sec*1000)*sec]+=1
    historical_parity=dict(original_archive_id=manifest['archive_id'],original_chain_head=manifest['chain_head'],original_ticks=index,tester_ticks=len(tape),different_time_bid_ask_rows=different,
        exact_ordered_quote_equivalence=(index==len(tape) and different==0),flags_not_exported_by_tester_tape=True)
    volume={}
    for label,sec in [('M1',60),('M5',300)]:
        with p('stochastic_events.csv.native_'+label+'.csv').open() as stream:
            rows=list(csv.DictReader(stream))
        volume[label]=dict(native_bars=len(rows),bid_update_volume_mismatches=[int(row['time']) for row in rows if int(row['tick_volume'])!=bid_updates[sec][int(row['time'])]],scope='ORIGINAL_BID_FLAG_UPDATES_VS_TESTER_NATIVE_VOLUME_THIS_DAY_ONLY')
    reports=[]
    for run,run_folder in zip((first,second),folders):
        data=(run_folder/(run+'.htm')).read_bytes();text=data.decode('utf-16' if data.startswith(b'\xff\xfe') else 'utf-8',errors='replace');flat=html.unescape(re.sub('<[^>]*>',' ',text));flat=' '.join(flat.split())
        quality=re.search(r'History Quality:\s*(.*?)(?:Bars:)',flat)
        reports.append(dict(run_id=run,history_quality=quality.group(1).strip() if quality else 'UNDETERMINED',report_sha256=sha256(run_folder/(run+'.htm'))))
    result=dict(native_clock_only=True,scientific_admission=False,native_backtest_parity_scope='FROZEN_NATIVE_VIRTUAL_EXPORTER_VS_PYTHON_NOT_MT5_ORDER_FILL_ENGINE',reproducibility=dict(status='PASS' if all(deterministic.values()) else 'FAIL',byte_identical_outputs=deterministic),
        baseline_replay=replay,causal_feature_checks=features,event_errors=errors,MAIN_K_PARITY=main,ohlc=ohlc,volume=volume,historical_quote_comparison=historical_parity,reports=reports,
        quote_order='NONDECREASING_DUPLICATE_TIMESTAMPS_PRESERVED',spread=dict(min=float(np.min(tape['ask']-tape['bid'])),max=float(np.max(tape['ask']-tape['bid']))),
        UTC_NY_SESSION_FIELDS='FROZEN_OFFSET_INPUTS_NOT_INDEPENDENTLY_CERTIFIED',EXTERNAL_UTC_CERTIFICATION='BLOCKED',DISCOVERY_VALIDATION='BLOCKED',FINAL_TEST='LOCKED',DEMO='DISABLED',LIVE_TRADING=False)
    return result
