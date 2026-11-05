"""Seal evidence for the permitted native export, never an admission grant."""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from controller.authorized_capture import sha
from controller.native_reconciliation import bars_from_tape
from controller.pretrain_contracts import seal, verify_chain
from controller.strategy_diagnostic import START, END, summarize
from python.validate_bar_path import QUOTE_DTYPE, validate

RUN = 'diag_d17cbe6aedfc'
INVENTORY = '71a52f04e6142021e1eb1cf59f4be9c8f10b151576d1088deb40d842b8019d39'


def build():
    import numpy as np
    source = ROOT / 'research/studies/maxbars_history_20261102_v1'
    manifest = source / 'download_manifest.json'
    if sha(manifest) != INVENTORY:
        raise ValueError('AUTHORIZED_SOURCE_INVENTORY_CHANGED')
    inventory = json.loads(manifest.read_text())
    folder = ROOT / 'outputs/historical_downloads_v1' / RUN
    for name, expected in inventory['files'].items():
        path = folder / name
        if path.resolve().parent != folder or sha(path) != expected:
            raise ValueError('AUTHORIZED_EXPORT_HASH_OR_PATH_CHANGED')
    def export(suffix):
        return folder / (RUN + '_' + suffix)

    with export('stochastic_events.csv').open(encoding='utf-8-sig') as stream:
        events = list(csv.DictReader(stream))
    if any(not START <= int(e['signal_time_msc']) < int(e['entry_time_msc']) < END
           or int(e['feature_max_time_msc']) > int(e['signal_time_msc']) for e in events):
        raise ValueError('DIAGNOSTIC_EVENT_CAUSAL_ORDER_CHANGED')
    tape_path = export('bar_quote_path.bin')
    tape = np.memmap(tape_path, dtype=QUOTE_DTYPE, mode='r')
    times = tape['time_msc']
    if not len(times) or times.min() < START or times.max() >= END or np.any(times[1:] < times[:-1]):
        raise ValueError('DIAGNOSTIC_TICK_DOMAIN_CHANGED')
    for event in events:
        signal_open = int(event['signal_bar_open'])
        entry_open = int(event['entry_bar_open'])
        cutoff = int(event['signal_time_msc'])
        first = times.searchsorted(entry_open * 1000)
        if (event['trigger_line'] != 'MAIN_K' or entry_open != signal_open + 300
                or cutoff != entry_open * 1000 - 1 or first == len(times)
                or not entry_open * 1000 <= int(times[first]) < (entry_open + 300) * 1000
                or int(times[first]) != int(event['entry_time_msc'])
                or int(event['ha_last_bar_open'] or 0) > signal_open
                or tuple(float(event[k]) for k in ('tp_distance','sl_distance','time_exit_bars')) != (240,180,100)):
            raise ValueError('FROZEN_SIGNAL_OR_FIRST_ENTRY_MISMATCH')
        for window in (30, 60, 120, 240):
            for field in ('window_end_msc', 'last_tick_msc'):
                if int(event[f'vp_{window}m_{field}'] or 0) > cutoff:
                    raise ValueError('VOLUME_PROFILE_FUTURE_COORDINATE')
    bars = {}
    for frame, seconds in [('M1', 60), ('M5', 300)]:
        with export('stochastic_events.csv.native_' + frame + '.csv').open() as stream:
            native = list(csv.DictReader(stream))
        derived = bars_from_tape(tape, seconds)
        if len(native) != len(derived):
            raise ValueError('BAR_COVERAGE_MISMATCH')
        mismatches = sum(int(n['time']) != d['time'] or any(float(n[k]) != d[k] for k in ('open','high','low','close'))
                         for n,d in zip(native,derived))
        bars[frame] = dict(count=len(native), ohlc_or_time_mismatches=mismatches,
                           native_volume_sum=sum(int(n['tick_volume']) for n in native),
                           quote_count_volume_disagreements=sum(int(n['tick_volume']) != d['observed_quotes'] for n,d in zip(native,derived)),
                           gaps=[dict(after=int(a['time']), before=int(b['time'])) for a,b in zip(native,native[1:]) if int(b['time'])-int(a['time']) != seconds])
        if mismatches:
            raise ValueError('NATIVE_OHLC_OR_TIMESTAMP_MISMATCH')
    replay = validate(tape_path, export('bar_trade_index.csv'), export('stochastic_events.csv'), export('bar_execution_quotes.csv'), END)
    package = ROOT / 'research/studies/us30cash_m5_native_pretrain_v1'
    ledger_path = package / 'exposure_ledger.json'
    ledger = json.loads(ledger_path.read_text())
    verify_chain(ledger['entries'], ledger['chain_head'])
    matrix = [{k:e.get(k) for k in ('dataset_id','roles','declared_native_date_range','start_native_msc','end_native_exclusive_msc','domain_id','membership','exposure')} for e in ledger['entries']]
    prereg = json.loads((package/'scientific_authorization_package.json').read_text())
    diagnostic = dict(dataset_id='us30cash_native_20240102_diagnostic_d17cbe6aedfc',
                      source_kind='MT5_TESTER_RECOVERED_HISTORICAL', inventory_sha256=INVENTORY,
                      source_version=RUN, native_day=inventory['native_day'],
                      first_observation='UNKNOWN_ORIGINAL_RECEIPT',
                      evidence_observed_ecuador=json.loads((source/'summary.json').read_text())['snapshot_ecuador'],
                      verification_utc=datetime.now(timezone.utc).isoformat(),
                      native_first_msc=int(times[0]), native_last_msc=int(times[-1]), ticks=len(times), bars=bars,
                      sessions='ECUADOR_SESSION_ATTESTATION_UNAVAILABLE_FOR_NATIVE_LABELS',
                      files=inventory['files'], prospective_bars_adopted=0)
    return dict(diagnostic=diagnostic, diagnostic_receipt_hash=seal(diagnostic), replay=replay,
                signal_counts={s:sum(e['follow_side']==s for e in events) for s in ('BUY','SELL')},
                results=[summarize(events,m,s) for m in ('FOLLOW','INVERT') for s in (None,'BUY','SELL')],
                native_feature_cutoffs_checked=len(events), first_next_m5_quotes_checked=len(events),
                feature_scope='DECLARED_NATIVE_CUTOFF_AND_VP_COORDINATES_NOT_INDEPENDENT_FEATURE_VINTAGE_OR_SEEDS',
                external_utc_certified=False,
                period_matrix=matrix, independent_periods=[], exposure_ledger_sha256=sha(ledger_path),
                exposure_complete=ledger['completeness_verified'], missing_evidence=ledger['missing'],
                authorization_template=prereg, candidate_dataset_hash=None, protected_rows_read=0,
                training_executed=False, scientific_authorization_requested=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = build()
    with args.out.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, ensure_ascii=False)
        stream.write('\n')
