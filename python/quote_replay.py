"""Experimental ordered-quote replay kernel. No dataset or promotion CLI.

The producer must supply independently validated quote coverage and decision
states. This kernel alone does not establish that those inputs exist or that
any policy is profitable. Reversal is deliberately unsupported.
"""
from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class Quote:
    time_msc: int
    sequence: int
    bar_index: int
    bid: float
    ask: float


@dataclass(frozen=True)
class Decision:
    cutoff_msc: int
    feature_max_time_msc: int
    mark_time_msc: int
    action: str
    available_sequence: int | None = None
    latency_msc: int = 0


def replay(quotes, side, decisions=(), *, allowed_end_exclusive, coverage_verified=False):
    """Enter on first quote; execute an EXIT at first quote after its cutoff.

    Frozen baseline barriers have precedence on each quote. TP is filled at
    its fixed level, gap SL at the observed executable quote, matching the
    project's ResearchTickExit/TickTrade. Quotes carry observed-bar indices,
    not elapsed wall-clock bars. Any incomplete position is censored.
    """
    if not coverage_verified:
        raise ValueError('Independently validated ordered quote coverage is required')
    if side not in (1, -1):
        raise ValueError('side must be BUY=1 or SELL=-1')
    quotes = list(quotes)
    decisions = list(decisions)
    if not quotes:
        raise ValueError('No executable entry quote')
    previous = None
    previous_bar = None
    for q in quotes:
        if (q.time_msc >= allowed_end_exclusive or q.time_msc < 0
                or not all(math.isfinite(v) for v in (q.bid, q.ask))
                or q.bid <= 0 or q.ask < q.bid):
            raise ValueError('Invalid quote or protected boundary reached')
        key = (q.time_msc, q.sequence)
        if previous is not None and key <= previous:
            raise ValueError('Quote order/sequence is not strictly increasing')
        if previous_bar is not None and q.bar_index not in (previous_bar, previous_bar + 1):
            raise ValueError('Observed bar indices are incomplete or nonmonotone')
        previous, previous_bar = key, q.bar_index
    availability_times = {q.sequence: q.time_msc for q in quotes}
    for i, d in enumerate(decisions):
        if d.action not in ('HOLD', 'EXIT'):
            raise ValueError('Reversal and unimplemented actions are unavailable')
        if (d.feature_max_time_msc > d.cutoff_msc or d.mark_time_msc > d.cutoff_msc
                or d.cutoff_msc < quotes[0].time_msc
                or d.cutoff_msc >= allowed_end_exclusive
                or (i and d.cutoff_msc <= decisions[i - 1].cutoff_msc)):
            raise ValueError('Noncausal or nonmonotone decision state')
        if d.latency_msc < 0 or not isinstance(d.latency_msc,int):
            raise ValueError('Invalid predeclared execution latency')
        if d.available_sequence is not None:
            available_time = availability_times.get(d.available_sequence)
            if available_time is None or available_time <= d.cutoff_msc:
                raise ValueError('Decision availability quote is missing or noncausal')
    entry = quotes[0].ask if side == 1 else quotes[0].bid
    entry_bar = quotes[0].bar_index
    previous_bar = entry_bar
    pending = 0
    for q in quotes:
        price = q.bid if side == 1 else q.ask
        pnl = side * (price - entry)
        newbar = q.bar_index != previous_bar
        reason = None
        if pnl <= -180:
            reason = 'SL'
        elif pnl >= 240:
            reason, price, pnl = 'TP', entry + side * 240, 240.
        elif newbar and q.bar_index - entry_bar >= 100:
            reason = 'TIME_EXIT'
        if reason is None:
            while pending < len(decisions) and decisions[pending].cutoff_msc < q.time_msc:
                decision = decisions[pending]
                if decision.available_sequence is not None and (
                        q.sequence <= decision.available_sequence
                        or q.time_msc < availability_times[decision.available_sequence]+decision.latency_msc):
                    break
                action = decisions[pending].action
                pending += 1
                if action == 'EXIT':
                    reason = 'POLICY_EXIT'
                    break
        if reason:
            return dict(status='COMPLETE', reason=reason, entry=entry, exit=price,
                        exit_time_msc=q.time_msc, exit_sequence=q.sequence, pnl=pnl)
        previous_bar = q.bar_index
    return dict(status='CENSORED', reason='END_OF_ALLOWED_PATH', entry=entry, pnl=None)


def replay_memmap_window(tape, entry_index, baseline_exit_index, side, *,
                         decision=None, allowed_end_exclusive, coverage_verified=False):
    """Replay a single EXIT decision over an independently validated quote memmap.

    `decision.available_sequence` is the row position in the full binary tape.
    A market EXIT uses the first quote strictly after that arrival sequence and
    no earlier than its frozen latency. Existing SL/TP/TIME_EXIT barriers win
    ties at the fill quote. This avoids materializing millions of Python Quote
    objects for dataset-level policy evaluation.
    """
    if not coverage_verified:
        raise ValueError('Independently validated ordered quote coverage is required')
    if side not in (1, -1):
        raise ValueError('side must be BUY=1 or SELL=-1')
    if not 0 <= entry_index <= baseline_exit_index < len(tape):
        raise ValueError('Invalid baseline trade quote bounds')
    if int(tape[entry_index]['time_msc']) >= allowed_end_exclusive or int(tape[baseline_exit_index]['time_msc']) >= allowed_end_exclusive:
        raise ValueError('Protected boundary reached')

    start, stop = int(entry_index), int(baseline_exit_index)
    window = tape[start:stop + 1]
    entry = float(window[0]['ask' if side == 1 else 'bid'])
    prices = window['bid' if side == 1 else 'ask']
    pnl = side * (prices - entry)
    bars = window['bar_index'].astype(np.int64) - int(window[0]['bar_index'])
    newbar = np.r_[False, np.diff(window['bar_index']) != 0]
    stops, profits = pnl <= -180.0, pnl >= 240.0
    timeouts = newbar & (bars >= 100)
    hits = np.flatnonzero(stops | profits | timeouts)
    baseline_hit = int(hits[0]) + start if len(hits) else None
    if decision is None:
        if baseline_hit is None:
            return dict(status='CENSORED', reason='END_OF_ALLOWED_PATH', entry=entry, pnl=None)
        local = baseline_hit - start
        reason = 'SL' if stops[local] else 'TP' if profits[local] else 'TIME_EXIT'
        exit_price = entry + side * 240.0 if reason == 'TP' else float(prices[local])
        return dict(status='COMPLETE', reason=reason, entry=entry, exit=exit_price,
                    exit_time_msc=int(tape[baseline_hit]['time_msc']), exit_sequence=baseline_hit,
                    pnl=side * (exit_price-entry))

    if decision.action != 'EXIT':
        raise ValueError('Memmap policy replay accepts one frozen EXIT decision or None')
    if (decision.feature_max_time_msc > decision.cutoff_msc
            or decision.mark_time_msc > decision.cutoff_msc
            or decision.cutoff_msc >= allowed_end_exclusive
            or not isinstance(decision.available_sequence, int)
            or decision.latency_msc < 0 or not isinstance(decision.latency_msc, int)):
        raise ValueError('Invalid or noncausal EXIT decision')
    arrival = decision.available_sequence
    if not start < arrival <= stop or int(tape[arrival]['time_msc']) <= decision.cutoff_msc:
        raise ValueError('Decision arrival is outside the trade or not strictly after cutoff')
    fill_target_time = int(tape[arrival]['time_msc']) + decision.latency_msc
    after_arrival = tape['time_msc'][arrival + 1:stop + 1]
    fill_offset = int(np.searchsorted(after_arrival, fill_target_time, side='left'))
    fill = arrival + 1 + fill_offset
    if fill > stop:
        fill = None

    # A barrier at or before the policy fill takes precedence. The unaltered
    # baseline exit index is also authoritative if no event was found in-path.
    if baseline_hit is not None and (fill is None or baseline_hit <= fill):
        local = baseline_hit - start
        reason = 'SL' if stops[local] else 'TP' if profits[local] else 'TIME_EXIT'
        exit_price = entry + side * 240.0 if reason == 'TP' else float(prices[local])
        return dict(status='COMPLETE', reason=reason, entry=entry, exit=exit_price,
                    exit_time_msc=int(tape[baseline_hit]['time_msc']), exit_sequence=baseline_hit,
                    pnl=side * (exit_price-entry))
    if fill is None:
        return dict(status='CENSORED', reason='END_OF_ALLOWED_PATH', entry=entry, pnl=None)
    exit_price = float(tape[fill]['bid' if side == 1 else 'ask'])
    return dict(status='COMPLETE', reason='POLICY_EXIT', entry=entry, exit=exit_price,
                exit_time_msc=int(tape[fill]['time_msc']), exit_sequence=fill,
                pnl=side * (exit_price-entry), decision_arrival_sequence=arrival,
                fill_sequence=fill, latency_msc=decision.latency_msc)
