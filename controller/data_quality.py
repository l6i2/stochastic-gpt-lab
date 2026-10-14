"""Streaming quality audit of accepted blocks; never loads protected datasets."""
import csv
import json
import math
import re
from collections import Counter
from pathlib import Path

from .artifact_collector import atomic_json
from .compile_runner import sha256
from .safety_gate import ROOT, assert_research_range_allowed


def summarize_snapshots(path):
    counts = {name: Counter() for name in ('offset', 'session', 'side', 'mode', 'ha_status', 'vp_30m_status')}
    missing = Counter()
    statistics = {}
    ids = set()
    duplicates = 0
    rows = 0
    features = ('tick_volume', 'real_volume', 'relative_volume_20', 'ATR',
                'ha_body', 'vp_30m_POC', 'vp_30m_VAH', 'vp_30m_VAL', 'current_unrealized_pnl',
                'current_mfe_so_far', 'current_mae_so_far')
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        for row in reader:
            rows += 1
            duplicates += row['snapshot_id'] in ids
            ids.add(row['snapshot_id'])
            for group, column in (('offset', 'snapshot_bar'), ('session', 'session'),
                                  ('side', 'original_signal'), ('mode', 'virtual_mode'),
                                  ('ha_status', 'ha_status'), ('vp_30m_status', 'vp_30m_status')):
                counts[group][row.get(column) or 'MISSING'] += 1
            for column, value in row.items():
                if value is None or value.strip().lower() in ('', 'nan', 'null'):
                    missing[column] += 1
            for column in features:
                value = row.get(column)
                if not value:
                    continue
                try:
                    number = float(value)
                except ValueError:
                    continue
                if not math.isfinite(number):
                    continue
                stat = statistics.setdefault(column, dict(n=0, mean=0., m2=0., min=number, max=number))
                stat['n'] += 1
                delta = number - stat['mean']
                stat['mean'] += delta / stat['n']
                stat['m2'] += delta * (number - stat['mean'])
                stat['min'] = min(stat['min'], number)
                stat['max'] = max(stat['max'], number)
    for stat in statistics.values():
        stat['std'] = math.sqrt(max(0., stat.pop('m2') / max(1, stat['n'] - 1)))
    return dict(rows=rows, duplicate_ids=duplicates, counts=counts, statistics=statistics,
                missing={c: dict(n=missing[c], fraction=missing[c]/rows if rows else None)
                         for c in columns})


def tick_warnings(folder):
    """Keep unknown warning counts unknown, rather than silently reporting zero."""
    warnings = set()
    discarded = set()
    for name in ('tester.log', 'agent_0.log', 'agent_1.log'):
        path = folder / name
        if not path.exists():
            continue
        for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
            if re.search(r'discarded|generated ticks|every tick generation|mismatch|no real ticks', line, re.I):
                # Store only the diagnostic message, not arbitrary log identity fields.
                message = line.split('\t')[-1]
                warnings.add(message)
                for match in re.finditer(r'(\d+)\s+minutes?[^\n]*discarded', message, re.I):
                    discarded.add(int(match.group(1)))
                for match in re.finditer(r'discarded for\s+(\d+)\s+minutes?', message, re.I):
                    discarded.add(int(match.group(1)))
    return dict(messages=sorted(warnings), discarded_minute_counts_reported=sorted(discarded),
                generated_tick_substitution_count=None,
                severity='HIGH' if warnings else 'MEDIUM',
                interpretation='No matching message does not prove perfect real-tick coverage.')


def audit():
    state_path = ROOT / 'outputs/controller/checkpoints/history_state.json'
    state = json.loads(state_path.read_text())
    if not state.get('blocks') or any(b['STATUS'] != 'PASS' for b in state['blocks']):
        raise RuntimeError('DATA_QUALITY: all historical blocks must pass first')
    reports = []
    for block in state['blocks']:
        assert_research_range_allowed(block['DATE_FROM'], block['DATE_TO'])
        folder = ROOT / 'outputs/controller/runs' / block['RUN_ID']
        record = json.loads((folder / 'run_manifest.json').read_text())
        if any(record.get(k) != 'PASS' for k in ('tester_status', 'VALIDATION_STATUS', 'CAUSALITY_STATUS')):
            raise RuntimeError('DATA_QUALITY: run acceptance missing')
        for name, digest in record['artifact_hashes'].items():
            if Path(name).name != name or sha256(folder/name) != digest:
                raise RuntimeError('DATA_QUALITY: accepted evidence changed')
        prefix = block['RUN_ID'] + '_'
        summary = summarize_snapshots(folder / (prefix + 'intratrade_snapshots.csv'))
        signals = Counter()
        censored = Counter()
        with (folder / (prefix + 'stochastic_events.csv')).open(encoding='utf-8-sig', newline='') as stream:
            for row in csv.DictReader(stream):
                signals[row['follow_side']] += 1
                for mode in ('follow', 'invert'):
                    censored[mode] += row[mode + '_exit_reason'] == 'END_OF_DATA'
        reports.append(dict(block=block['BLOCK_ID'], period=[block['DATE_FROM'], block['DATE_TO']],
                            signals=signals, censored_trades=censored, snapshots=summary,
                            tick_quality=tick_warnings(folder),
                            run_manifest_sha256=sha256(folder/'run_manifest.json')))
    result = dict(DATA_QUALITY='WARN', FINAL_TEST='LOCKED', blocks=reports,
                  history_sha256=sha256(state_path), policy_replay='BLOCKING',
                  exclusions=['dynamic/reverse policies without ordered executable quote path',
                              'future excursion/recovery labels derived from lifetime-extrema increments',
                              'strict breakout flags with current bar in reference extrema'],
                  severity_definitions=dict(LOW='descriptive limitation', MEDIUM='requires disclosure',
                                            HIGH='limits generalization', BLOCKING='family cannot be promoted'))
    atomic_json(ROOT/'outputs/controller/research/data_quality.json', result)
    return result


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
