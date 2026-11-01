"""Descriptive frozen-baseline diagnostics, restricted to one already authorized day."""
import csv,json,math,statistics
from collections import Counter
from pathlib import Path
from .authorized_capture import sha
from .safety_gate import ROOT

EVIDENCE=ROOT/'configs/pc_a_native_tester_evidence_20261030'
RUN_IDS=('diag_fd4e5bf3d468','diag_abedbf590923')
START=1704153600000
END=1704240000000


def authorized_inputs():
    if sha(EVIDENCE/'native_runs.json')!='4bade6e18468ac4434abd3a7e57774706594142267ce63352b31f3808bd99eac':raise ValueError('APPROVED_DIAGNOSTIC_INVENTORY_CHANGED')
    records=json.loads((EVIDENCE/'native_runs.json').read_text())['runs']
    selected=[]
    for run_id in RUN_IDS:
        record=next(r for r in records if r['run_id']==run_id)
        if record['start']!='2024-01-02' or record['end']!='2024-01-02' or record['optimization'] is not False or record['orders_sent']!=0:raise ValueError('NOT_THE_AUTHORIZED_FIXED_DIAGNOSTIC')
        folder=ROOT/'outputs/pc_a_certification/native_tester/runs'/run_id
        for name,expected in record['artifact_sha256'].items():
            if Path(name).name!=name or not name.startswith(run_id+'_') and name!=run_id+'.htm':raise ValueError('DIAGNOSTIC_PATH_ESCAPE')
            if sha(folder/name)!=expected:raise ValueError('DIAGNOSTIC_ARTIFACT_HASH_CHANGED_'+name)
        selected.append((folder,record))
    return selected


def finite(value):
    if value in ('',None):return None
    number=float(value)
    if not math.isfinite(number):raise ValueError('NONFINITE_DIAGNOSTIC_VALUE')
    return number


def distribution(values):
    values=[v for v in values if v is not None]
    return dict(n=len(values),mean=statistics.mean(values) if values else None,median=statistics.median(values) if values else None,min=min(values) if values else None,max=max(values) if values else None)


def summarize(rows,mode,side=None):
    rows=[r for r in rows if side is None or r['follow_side']==side];p=mode.lower()+'_'
    complete=[r for r in rows if r[p+'exit_reason']!='END_OF_DATA'];pnl=[finite(r[p+'PnL']) for r in complete]
    if any(v is None for v in pnl):raise ValueError('MISSING_COMPLETED_DIAGNOSTIC_OUTCOME')
    positive=sum(v for v in pnl if v>0);loss=-sum(v for v in pnl if v<0)
    equity=peak=0.;drawdown=0.
    ordered=sorted(enumerate(complete),key=lambda x:(int(x[1][p+'exit_time']),x[0]))
    for _,r in ordered:
        equity+=finite(r[p+'PnL']);peak=max(peak,equity);drawdown=min(drawdown,equity-peak)
    return dict(original_signal_side=side or 'ALL',mode=mode,signals=len(rows),completed=len(complete),censored=len(rows)-len(complete),exit_reasons=dict(Counter(r[p+'exit_reason'] for r in rows)),
        completed_pnl=distribution(pnl),completed_pnl_sum=sum(pnl),profit_factor=positive/loss if loss else None,
        completed_win_rate=sum(v>0 for v in pnl)/len(pnl) if pnl else None,
        closed_pnl_exit_order_drawdown_proxy=drawdown,drawdown_scope='CLOSED_VIRTUAL_PNL_EXIT_ORDER_NOT_MARK_TO_MARKET_OR_ACCOUNT_EQUITY',
        observed_mfe_all=distribution([finite(r[p+'MFE']) for r in rows]),observed_mae_all=distribution([finite(r[p+'MAE']) for r in rows]),
        completed_duration_observed_m5_bars=distribution([int(r[p+'bars_in_trade']) for r in complete]),
        units='US30CASH_PRICE_UNITS_NOT_CURRENCY',censoring='NO_ZERO_IMPUTATION_MFE_MAE_OF_CENSORED_PATHS_ARE_OBSERVED_LOWER_BOUNDS',scientific_inference=False)


def run():
    import numpy as np
    from python.validate_bar_path import validate,QUOTE_DTYPE
    from controller.native_reconciliation import bars_from_tape
    from python.causal_metadata_audit import main_values
    from python.native_m5_rebuild import price_units
    sources=authorized_inputs();folder,record=sources[0];run_id=record['run_id']
    path=lambda suffix:folder/(run_id+'_'+suffix)
    with path('stochastic_events.csv').open(encoding='utf-8-sig') as stream:rows=list(csv.DictReader(stream))
    if len(rows)!=28 or any(not START<=int(r['signal_time_msc'])<END or not START<=int(r['entry_time_msc'])<END for r in rows):raise ValueError('OUTSIDE_FIXED_DAY_OR_SIGNAL_COUNT_CHANGED')
    if len({r['signal_id'] for r in rows})!=len(rows):raise ValueError('DUPLICATE_DIAGNOSTIC_SIGNAL')
    if any(r['follow_side'] not in ('BUY','SELL') or r['invert_side']==r['follow_side'] or int(r['feature_max_time_msc'])>int(r['signal_time_msc']) for r in rows):raise ValueError('SIGNAL_OR_CAUSAL_CONTRACT_CHANGED')
    replay=validate(path('bar_quote_path.bin'),path('bar_trade_index.csv'),path('stochastic_events.csv'),path('bar_execution_quotes.csv'),END)
    tape=np.memmap(path('bar_quote_path.bin'),dtype=QUOTE_DTYPE,mode='r')
    if int(tape['time_msc'].min())<START or int(tape['time_msc'].max())>=END:raise ValueError('QUOTE_TAPE_OUTSIDE_FIXED_DIAGNOSTIC_DAY')
    ohlc={};m5=None
    for name,seconds in (('M1',60),('M5',300)):
        derived=bars_from_tape(tape,seconds)
        with path('stochastic_events.csv.native_'+name+'.csv').open() as stream:native=list(csv.DictReader(stream))
        expected={int(r['time']):r for r in native}
        mismatches=[b['time'] for b in derived if b['time'] not in expected or any(b[k]!=float(expected[b['time']][k]) for k in ('open','high','low','close'))]
        ohlc[name]=dict(derived_bars=len(derived),native_bars=len(native),mismatches=mismatches,missing=sorted(set(expected)-{b['time'] for b in derived}))
        if name=='M5':m5=derived
    del tape
    values=main_values(m5,native_reference=True);index={b['time']:i for i,b in enumerate(m5)};error=0.;comparisons=0
    with path('stochastic_events.csv.native_main.csv').open() as stream:
        for row in csv.DictReader(stream):
            i=index[int(row['bar_open_native'])]
            if i<7:continue
            comparisons+=1;error=max(error,abs(float(row['main_k'])-values[i]),abs(float(row['previous_main_k'])-values[i-1]))
    deterministic={}
    for suffix in ('bar_execution_quotes.csv','bar_quote_path.bin','bar_trade_index.csv','intratrade_snapshot_targets.csv','intratrade_snapshots.csv','intratrade_snapshots.csv.audit.json','stochastic_events.csv','stochastic_events.csv.audit.json'):
        deterministic[suffix]=sha(sources[0][0]/(RUN_IDS[0]+'_'+suffix))==sha(sources[1][0]/(RUN_IDS[1]+'_'+suffix))
    summaries=[summarize(rows,mode,side) for side in (None,'BUY','SELL') for mode in ('FOLLOW','INVERT')]
    paired=[r for r in rows if r['follow_exit_reason']!='END_OF_DATA' and r['invert_exit_reason']!='END_OF_DATA']
    difference={side:distribution([finite(r['follow_PnL'])-finite(r['invert_PnL']) for r in paired if side=='ALL' or r['follow_side']==side]) for side in ('ALL','BUY','SELL')}
    return dict(scope='FIXED_AUTHORIZED_2024_01_02_DIAGNOSTIC_ONLY_PREVIOUSLY_EXPOSED_NOT_INDEPENDENT',source_run_ids=list(RUN_IDS),source_file_sha256=sha(path('stochastic_events.csv')),baseline_replay=replay,
        reproducibility=dict(status='PASS' if all(deterministic.values()) else 'FAIL',byte_identical=deterministic),ohlc=ohlc,
        main_k=dict(status='PASS' if comparisons and error<=1e-10 else 'FAIL',closed_bars_compared=comparisons,max_abs_error=error,existing_tolerance=1e-10,early_signal_needs_pre_day_history=True),
        summaries=summaries,paired_follow_minus_invert=difference,signal_counts=dict(Counter(r['follow_side'] for r in rows)),
        feature_distributions=dict(ATR=distribution([finite(r['ATR']) for r in rows]),relative_volume_20=distribution([finite(r['relative_volume_20']) for r in rows])),
        historical_sessions='UNVERIFIED_FROZEN_SERVER_OFFSET_FIELDS_NOT_REAGGREGATED',
        diagnostic_outcome_paths_read=2*len(rows),protected_rows_read=0,training_or_new_policy_scoring=False,prospective_data_used_for_outcomes=False,live_trading=False)
