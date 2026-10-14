"""Validate ordered quote evidence and reproduce the unchanged HOLD baseline."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

QUOTE_DTYPE = np.dtype([('time_msc','<i8'),('bid','<f8'),('ask','<f8'),('bar_index','<i4')])
assert QUOTE_DTYPE.itemsize == 28


def open_quotes(path, allowed_end_exclusive):
    path = Path(path)
    if path.stat().st_size == 0 or path.stat().st_size % 28:
        raise ValueError('Incomplete binary quote record')
    tape = np.memmap(path, dtype=QUOTE_DTYPE, mode='r')
    previous_time = previous_bar = None
    for start in range(0, len(tape), 200000):
        chunk = tape[start:start+200000]
        times, bars = chunk['time_msc'], chunk['bar_index']
        if (int(times.min()) < 0 or int(times.max()) >= allowed_end_exclusive
                or np.any(np.diff(times) < 0)
                or (previous_time is not None and int(times[0]) < previous_time)):
            raise ValueError('Quote timestamp order or protected boundary violation')
        changes = np.diff(bars)
        if (int(bars.min()) < 0 or np.any((changes < 0) | (changes > 1))
                or (previous_bar is not None and int(bars[0])-previous_bar not in (0,1))):
            raise ValueError('Observed bar sequence is incomplete')
        if (not np.all(np.isfinite(chunk['bid'])) or not np.all(np.isfinite(chunk['ask']))
                or np.any(chunk['bid'] <= 0) or np.any(chunk['ask'] < chunk['bid'])):
            raise ValueError('Invalid binary execution quote')
        previous_time, previous_bar = int(times[-1]), int(bars[-1])
    return tape


def baseline(tape, entry_index, end_index, side):
    if side not in (1,-1) or not 0 <= entry_index <= end_index < len(tape):
        raise ValueError('Invalid baseline trade index')
    window = tape[entry_index:end_index+1]
    entry = float(window[0]['ask' if side == 1 else 'bid'])
    prices = window['bid' if side == 1 else 'ask']
    pnl = side*(prices-entry)
    bars = window['bar_index'].astype('int64')-int(window[0]['bar_index'])
    newbar = np.r_[False, np.diff(window['bar_index']) != 0]
    stops, profits = pnl <= -180., pnl >= 240.
    timeout = newbar & (bars >= 100)
    hits = np.flatnonzero(stops | profits | timeout)
    if len(hits):
        end = int(hits[0])
        reason = 'SL' if stops[end] else 'TP' if profits[end] else 'TIME_EXIT'
        exit_price = entry + side*240. if reason == 'TP' else float(prices[end])
        observations = pnl[:end+1].copy()
        if reason == 'TP':
            observations[-1] = 240.
        elapsed = 100 if reason == 'TIME_EXIT' else max(1,int(bars[end])+(0 if newbar[end] else 1))
        result_pnl = side*(exit_price-entry)
    else:
        end = len(window)-1
        reason = 'END_OF_DATA'
        exit_price = float(prices[end])
        observations = pnl
        elapsed = max(1,int(bars[end])+1)
        result_pnl = None
    return dict(entry=entry, exit=exit_price, pnl=result_pnl, reason=reason,
                exit_index=entry_index+end, exit_time_msc=int(window[end]['time_msc']),
                bars=elapsed, mfe=max(0.,float(observations.max())), mae=max(0.,float(-observations.min())))


def validate(quote_path, trade_path, events_path, arrival_path, allowed_end_exclusive):
    tape = open_quotes(quote_path, allowed_end_exclusive)
    events = {}
    with Path(events_path).open(encoding='utf-8-sig',newline='') as stream:
        for row in csv.DictReader(stream):
            signal = row['signal_id']
            for mode in ('FOLLOW','INVERT'):
                key = (signal, mode)
                if key in events:
                    raise ValueError('Duplicate source signal')
                prefix = mode.lower()+'_'
                events[key] = dict(entry_time=int(row['entry_time_msc']),
                    signal_time=int(row['signal_time_msc']), side=row[prefix+'side'],
                    entry=float(row[prefix+'entry_price']), exit=float(row[prefix+'exit_price']),
                    exit_time=int(row[prefix+'exit_time']), reason=row[prefix+'exit_reason'],
                    mfe=float(row[prefix+'MFE']),mae=float(row[prefix+'MAE']),bars=int(row[prefix+'bars_in_trade']),
                    pnl=None if row[prefix+'exit_reason']=='END_OF_DATA' else float(row[prefix+'PnL']))
    indexed = {}
    censored = 0
    with Path(trade_path).open(encoding='utf-8-sig',newline='') as stream:
        for row in csv.DictReader(stream):
            key = (row['signal_id'],row['virtual_mode'])
            if key in indexed or key not in events:
                raise ValueError('Duplicate or unknown indexed trade')
            event = events[key]
            if event['side'] not in ('BUY','SELL'):
                raise ValueError('Invalid virtual trade side')
            first, last = int(row['entry_quote_index']),int(row['exit_quote_index'])
            side = 1 if event['side'] == 'BUY' else -1
            replay = baseline(tape,first,last,side)
            if (row['virtual_side'] != event['side'] or int(tape[first]['time_msc']) != event['entry_time']
                    or event['entry_time'] <= event['signal_time']
                    or int(row['entry_time_msc']) != event['entry_time']
                    or int(row['exit_time_msc']) != event['exit_time']
                    or row['exit_reason'] != event['reason']
                    or replay['exit_index'] != last or replay['reason'] != event['reason']
                    or replay['exit_time_msc'] != event['exit_time'] or replay['bars'] != event['bars']
                    or int(row['bars_in_trade']) != event['bars']):
                raise ValueError('Frozen baseline chronology/exit parity failed')
            for actual, expected in ((replay['entry'],event['entry']),(replay['exit'],event['exit']),
                                     (float(row['entry_price']),event['entry']),
                                     (float(row['exit_price']),event['exit']),
                                     (replay['mfe'],event['mfe']),(replay['mae'],event['mae'])):
                if not np.isfinite(actual) or not np.isfinite(expected) or abs(actual-expected) > 1e-8:
                    raise ValueError('Frozen baseline price/excursion parity failed')
            if event['reason'] == 'END_OF_DATA':
                if last != len(tape)-1:
                    raise ValueError('Censoring before the end of the quote path')
                censored += 1
            elif not np.isfinite(event['pnl']) or abs(replay['pnl']-event['pnl']) > 1e-8:
                raise ValueError('Frozen baseline PnL parity failed')
            indexed[key] = (first,last)
    if set(indexed) != set(events):
        raise ValueError('Trade index coverage is incomplete')
    arrivals = set()
    with Path(arrival_path).open(encoding='utf-8-sig',newline='') as stream:
        for row in csv.DictReader(stream):
            sid = row['snapshot_id']
            key = (row['signal_id'],row['virtual_mode'])
            if sid in arrivals or key not in indexed:
                raise ValueError('Duplicate or unknown decision arrival')
            index = int(row['decision_quote_index'])
            first,last = indexed[key]
            cutoff = int(row['decision_cutoff_msc'])
            if (not first < index <= last or not int(tape[index-1]['time_msc']) <= cutoff < int(tape[index]['time_msc'])
                    or int(tape[index]['bar_index'])-int(tape[first]['bar_index']) != int(row['snapshot_bar'])
                    or int(tape[index]['time_msc']) != int(row['execution_time_msc'])
                    or abs(float(tape[index]['bid'])-float(row['execution_bid'])) > 1e-8
                    or abs(float(tape[index]['ask'])-float(row['execution_ask'])) > 1e-8):
                raise ValueError('Decision arrival quote does not match the ordered tape')
            arrivals.add(sid)
    return dict(BASELINE_REPLAY='PASS', quote_record_bytes=28, quote_records=len(tape),
                indexed_trades=len(indexed), censored_trades=censored, decision_arrivals=len(arrivals),
                policy_fill='STRICTLY_AFTER_DECISION_ARRIVAL_SEQUENCE', final_test_accessed=False)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('quote-path','trade-index','events','execution-quotes','split-manifest'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    bound=json.loads(args.split_manifest.read_text())['boundaries']['final_test_start_signal_time_msc']
    print(json.dumps(validate(args.quote_path,args.trade_index,args.events,args.execution_quotes,int(bound)),indent=2))
