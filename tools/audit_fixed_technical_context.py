"""Descriptive context audit over the existing hash-bound XM diagnostic day."""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import correlation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from controller.authorized_capture import sha
from controller.strategy_diagnostic import END, START, authorized_inputs, finite

FRAME = 300


def closed_context(bars, cutoff_msc, period):
    """Use the last calendar bucket only if every constituent M5 is available."""
    stop = (cutoff_msc // (period * 1000)) * period
    opens = range(stop - period, stop, FRAME)
    if any(stamp not in bars for stamp in opens):
        return None
    children = [bars[stamp] for stamp in opens]
    return dict(available_native_msc=stop * 1000,
                displacement=float(children[-1]['close']) - float(children[0]['open']),
                range=max(float(row['high']) for row in children)
                - min(float(row['low']) for row in children))


def coefficient(rows, left, right):
    pairs = [(r[left], r[right]) for r in rows if r[left] is not None and r[right] is not None]
    if len(pairs) < 2:
        return dict(n=len(pairs), r=None)
    x, y = zip(*pairs)
    return dict(n=len(pairs), r=correlation(x, y) if len(set(x)) > 1 and len(set(y)) > 1 else None)


def audit():
    import numpy as np
    from python.validate_bar_path import QUOTE_DTYPE

    folder, run = authorized_inputs()[0]
    def load(suffix):
        path = folder / (run['run_id'] + '_' + suffix)
        with path.open(encoding='utf-8-sig', newline='') as stream:
            return list(csv.DictReader(stream)), sha(path)

    events, event_hash = load('stochastic_events.csv')
    snapshots, snapshot_hash = load('intratrade_snapshots.csv')
    native_m5, bar_hash = load('stochastic_events.csv.native_M5.csv')
    tape_path = folder / (run['run_id'] + '_bar_quote_path.bin')
    tape = np.memmap(tape_path, dtype=QUOTE_DTYPE, mode='r')
    bars = {int(row['time']): row for row in native_m5}
    assert len(events) == len({r['signal_id'] for r in events}) == 28
    by_id = {r['signal_id']: r for r in events}
    fields = ('stoch_k', 'stoch_d', 'ATR', 'relative_volume_20', 'ha_direction', 'range_to_ATR')
    entry = {'BUY': [], 'SELL': []}
    availability = {str(p): Counter() for p in (5, 15, 30, 60)}
    displacements = defaultdict(list)
    for row in events:
        cutoff = int(row['signal_time_msc'])
        decision = int(row['entry_time_msc'])
        assert START <= int(row['feature_max_time_msc']) <= cutoff < decision < END
        side = row['follow_side']
        for minutes in availability:
            context = closed_context(bars, decision, int(minutes) * 60)
            if context is not None:
                assert context['available_native_msc'] <= decision
                availability[minutes][side] += 1
                displacements[(minutes, side)].append(context['displacement'])
        entry[side].append({name: finite(row[name]) for name in fields})

    groups = {}
    rejected = Counter()
    mark_counts = Counter()
    seen = set()
    for row in snapshots:
        key = (row['signal_id'], row['virtual_mode'], row['snapshot_bar'])
        assert key not in seen
        seen.add(key)
        parent = by_id[row['signal_id']]
        mode = row['virtual_mode'].lower()
        assert mode in ('follow', 'invert')
        entry_time = int(row['entry_time_msc'])
        cutoff = int(row['snapshot_time_msc'])
        if not (entry_time == int(parent['entry_time_msc'])
                and row['original_signal'] == parent['follow_side']
                and row['virtual_side'] == parent[mode + '_side']):
            rejected['parent_mismatch'] += 1
        elif not (START <= entry_time < cutoff < END
                  and START <= int(row['feature_max_time_msc']) <= cutoff
                  and entry_time <= int(row['mark_time_msc']) <= cutoff):
            rejected['temporal_order'] += 1
        elif cutoff >= int(parent[mode + '_exit_time']):
            rejected['at_or_after_exit'] += 1
        else:
            mark = int(row['mark_time_msc'])
            left, right = np.searchsorted(tape['time_msc'], [mark, mark + 1])
            matched = any(float(tick['bid']) == float(row['current_bid'])
                          and float(tick['ask']) == float(row['current_ask'])
                          for tick in tape[left:right])
            mark_counts['exact_tape_quote' if matched else 'not_exact_tape_quote'] += 1
            group = groups.setdefault(parent['follow_side'] + '_' + mode.upper(), [])
            group.append(row)

    pairs = (('stoch_k', 'stoch_d'), ('ATR', 'range_to_ATR'), ('ATR', 'relative_volume_20'))
    context = {}
    for side, rows in entry.items():
        middle = len(rows) // 2
        context[side] = {f'{x}/{y}': dict(all=coefficient(rows, x, y),
            early=coefficient(rows[:middle], x, y), late=coefficient(rows[middle:], x, y)) for x, y in pairs}
    return dict(source_hashes=dict(events=event_hash, snapshots=snapshot_hash, m5=bar_hash,
                                   tick_tape=sha(tape_path)),
        entries={side: len(rows) for side, rows in entry.items()}, closed_context=availability,
        mean_displacement_by_frame_and_side={f'M{frame}_{side}': sum(values) / len(values)
                                            for (frame, side), values in displacements.items()},
        entry_descriptive_correlations=context, snapshot_rows=len(snapshots), rejected_snapshots=rejected,
        snapshot_mark_quote_check=mark_counts,
        intratrade={name: dict(rows=len(rows), signals=len({r['signal_id'] for r in rows}),
             mean_unrealized=sum(float(r['current_unrealized_pnl']) for r in rows) / len(rows),
             mean_mfe=sum(float(r['current_mfe_so_far']) for r in rows) / len(rows),
             mean_mae=sum(float(r['current_mae_so_far']) for r in rows) / len(rows))
             for name, rows in groups.items()}, protected_rows_read=0, hypotheses_tested=0, fits=0)


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2, allow_nan=False))
