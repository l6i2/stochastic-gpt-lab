"""Read-only quote availability diagnostic; never infer execution permission from ticks."""
from __future__ import annotations
from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from runtime_session_guard import RuntimeSessionGuard, SessionObservation
from native_time_mapping import NativeTimestamp, load_mapping, native_to_utc


def read_session_runtime(*, environment_status=None, mt5_module=None, now_utc=None) -> dict:
    now = now_utc or datetime.now(timezone.utc)
    result = {"runtime_session_guard": "READY", "quote_market_state": "UNKNOWN",
              "execution_market_state": "UNKNOWN", "holiday_status": "UNKNOWN",
              "orders_sent": 0, "live_trading": False}
    result.update(decision_clock_source="LOCAL_UTC_UNATTESTED", clock_reference_status="UNVERIFIED",
                  quote_clock_basis="UNVERIFIED_NATIVE", timestamp_normalization="BLOCKED_PENDING_CLOCK_MAPPING")
    result.update(native_mt5_time=None, normalized_utc=None, ecuador_time=None,
                  new_york_time=None, xm_server_time=None)
    if environment_status is None:
        from controller.mt5_env import status
        environment_status = status
    try:
        environment = environment_status()
    except Exception as exc:
        return {**result, "reason": "ENVIRONMENT_PROBE_FAILED:" + type(exc).__name__, "allowed": False}
    if environment.get("SAFE_FOR_RESEARCH") is not True:
        return {**result, "reason": "ENVIRONMENT_NOT_VERIFIED_DEMO", "allowed": False}
    if mt5_module is None:
        import MetaTrader5 as mt5_module
    mt5 = mt5_module
    try:
        if not mt5.initialize(path=environment["TERMINAL_PATH"], timeout=5000):
            return {**result, "reason": "READ_ONLY_ATTACH_FAILED", "allowed": False}
        terminal, account = mt5.terminal_info(), mt5.account_info()
        if (terminal is None or account is None or not terminal.connected or account.trade_mode != 0
                or Path(terminal.data_path).resolve() != Path(environment["DATA_FOLDER"]).resolve()):
            return {**result, "reason": "ATTACHED_ENVIRONMENT_MISMATCH", "allowed": False}
        info, tick = mt5.symbol_info("US30Cash"), mt5.symbol_info_tick("US30Cash")
        # Establish decision time after the reads, rather than before environment/IPC latency.
        if now_utc is None:
            now = datetime.now(timezone.utc)
        result["system_utc_observed"] = now.isoformat()
        result["decision_time_utc"] = None
        quote_time = now
        bid = ask = 0.0
        state = "UNKNOWN"
        if info is None or info.trade_mode == 0:
            result["quote_market_state"] = "SYMBOL_UNAVAILABLE_OR_DISABLED"
            state = "CLOSED"
        elif tick is not None:
            seconds, milliseconds = getattr(tick, 'time', None), getattr(tick, 'time_msc', None)
            if (type(seconds) is not int or type(milliseconds) is not int or seconds < 0
                    or milliseconds < 0 or milliseconds // 1000 != seconds):
                time_reason = 'SECONDS_MILLISECONDS_MISMATCH'
                return {**result, "allowed": False, "reason": time_reason,
                        "quote_market_state": "INVALID_TIMESTAMP_UNITS"}
            bid, ask = float(tick.bid), float(tick.ask)
            raw = {'time': int(tick.time), 'time_msc': int(tick.time_msc), 'bid': bid, 'ask': ask}
            result['native_mt5_time'] = raw
            raw_sha = hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            result['captured_native_record_sha256'] = raw_sha
            try:
                mapping = load_mapping(ROOT / 'configs/native_time_mapping_v1.prepared.json')
                normalized = native_to_utc(NativeTimestamp(int(tick.time), int(tick.time_msc),
                    'US30Cash', account.server, raw_sha), mapping)
            except ValueError as exc:
                return {**result, 'allowed': False, 'reason': str(exc),
                        'quote_market_state': 'NATIVE_TIME_UNMAPPED'}
            result.update(normalized.views)
            # A valid historical mapping does not attest the current decision clock.
            return {**result, 'allowed': False, 'reason': 'CURRENT_AUTHORITATIVE_CLOCK_UNATTESTED',
                    'quote_market_state': 'DECISION_CLOCK_UNVERIFIED'}
        result["execution_market_state"] = state
        observation = SessionObservation(now, quote_time, True, "DEMO", account.server, "US30Cash", bid, ask,
                                         holiday_status="UNKNOWN", broker_market_state=state)
        decision = RuntimeSessionGuard().check(observation, now_utc=now)
        result.update(allowed=decision.allowed, reason=decision.reason,
                      evidence_sha256=decision.evidence_sha256)
        return result
    except Exception as exc:
        return {**result, "allowed": False, "reason": "RUNTIME_READ_FAILED:" + type(exc).__name__}
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    print(json.dumps(read_session_runtime(), indent=2, sort_keys=True))
