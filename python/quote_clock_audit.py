"""Read-only latest-tick provenance capture. No orders, clock changes or cache reset."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from temporal_causality import utc_milliseconds, validate_decision_times


def validate_quote_clock(*, seconds: int, milliseconds: int, decision: datetime,
                         feature_time: datetime | None = None) -> tuple[bool, str]:
    """Raw API integers are never rescued by offsets, truncation or guessed units."""
    if (type(seconds) is not int or type(milliseconds) is not int
            or seconds < 0 or milliseconds < 0 or milliseconds // 1000 != seconds):
        return False, 'SECONDS_MILLISECONDS_MISMATCH'
    decision_msc = utc_milliseconds(decision)
    feature = feature_time or decision
    if feature > decision:
        return False, 'FEATURE_LOOKAHEAD'
    return validate_decision_times(feature_max_time_msc=utc_milliseconds(feature),
                                   decision_time_msc=decision_msc, quote_time_msc=milliseconds)


def capture(*, samples: int = 5, interval: float = 1.0, mt5=None, environment=None) -> dict:
    if not 1 <= samples <= 60 or not 0 <= interval <= 5:
        raise ValueError('Bounded diagnostic only')
    if environment is None:
        from controller.mt5_env import status
        environment = status()
    if environment.get('SAFE_FOR_RESEARCH') is not True:
        raise ValueError('UNVERIFIED_TERMINAL')
    if mt5 is None:
        import MetaTrader5 as mt5
    if not mt5.initialize(path=environment['TERMINAL_PATH'], timeout=5000):
        raise RuntimeError('ATTACH_FAILED')
    try:
        terminal, account = mt5.terminal_info(), mt5.account_info()
        if (not terminal or not account or not terminal.connected or account.trade_mode != 0
                or Path(terminal.data_path).resolve() != Path(environment['DATA_FOLDER']).resolve()):
            raise ValueError('ATTACHED_ENVIRONMENT_MISMATCH')
        report = {'source': 'terminal_live_python_native_API', 'strategy_tester': False,
                  'fixture': False, 'orders_sent': 0, 'clock_changed': False,
                  'terminal_build': terminal.build, 'package_version': mt5.__version__,
                  'native_clock_fields': 'not exposed by Python API; use paired MQL export',
                  'market_open': 'UNKNOWN; ticks alone do not attest open market', 'samples': []}
        for index in range(samples):
            for symbol in ('US30Cash', 'EURUSD', 'USDCHF'):
                before = datetime.now(timezone.utc)
                monotonic_before = time.monotonic_ns()
                tick = mt5.symbol_info_tick(symbol)
                after = datetime.now(timezone.utc)
                received_monotonic = time.monotonic_ns()
                latency = received_monotonic - monotonic_before
                row = {'index': index, 'symbol': symbol, 'api': 'symbol_info_tick',
                       'read_before_utc': before.isoformat(), 'read_after_utc': after.isoformat(),
                       'received_monotonic_ns': received_monotonic,
                       'monotonic_latency_ns': latency, 'tick': tick._asdict() if tick else None}
                if tick:
                    row['guard'] = validate_quote_clock(seconds=int(tick.time), milliseconds=int(tick.time_msc), decision=after)[1]
                    row['future_delta_msc'] = int(tick.time_msc) - utc_milliseconds(after)
                # Independently bounded history: diagnostic only, never a replacement quote.
                history = mt5.copy_ticks_range(symbol, after - timedelta(seconds=3), after, mt5.COPY_TICKS_ALL)
                row['history_api'] = 'copy_ticks_range'
                row['history_query_start_utc'] = (after - timedelta(seconds=3)).isoformat()
                row['history_query_end_utc'] = after.isoformat()
                row['history_rows'] = None if history is None else len(history)
                row['history_first'] = None
                row['history_last'] = None
                if history is not None and len(history):
                    for key, item in (('history_first', history[0]), ('history_last', history[-1])):
                        row[key] = {name: item[name].item() for name in history.dtype.names}
                report['samples'].append(row)
            if index + 1 < samples:
                time.sleep(interval)
        from independent_clock_reference import capture_reference
        report['independent_reference'] = capture_reference()
        return report
    finally:
        mt5.shutdown()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--samples', type=int, default=5)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Preserve prior diagnostic evidence')
    result = capture(samples=args.samples)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'samples': len(result['samples']), 'orders_sent': 0, 'output': str(args.output)}))
