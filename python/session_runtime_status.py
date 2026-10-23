"""Read-only quote availability diagnostic; never infer execution permission from ticks."""
from __future__ import annotations
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from runtime_session_guard import RuntimeSessionGuard, SessionObservation


def read_session_runtime(*, environment_status=None, mt5_module=None, now_utc=None) -> dict:
    now = now_utc or datetime.now(timezone.utc)
    result = {"runtime_session_guard": "READY", "quote_market_state": "UNKNOWN",
              "execution_market_state": "UNKNOWN", "holiday_status": "UNKNOWN",
              "orders_sent": 0, "live_trading": False}
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
        quote_time = now
        bid = ask = 0.0
        state = "UNKNOWN"
        if info is None or info.trade_mode == 0:
            result["quote_market_state"] = "SYMBOL_UNAVAILABLE_OR_DISABLED"
            state = "CLOSED"
        elif tick is not None:
            quote_time = datetime.fromtimestamp(tick.time_msc / 1000, timezone.utc)
            bid, ask = float(tick.bid), float(tick.ask)
            age = (now - quote_time).total_seconds()
            result["quote_age_seconds"] = age
            if not (math.isfinite(bid) and math.isfinite(ask) and 0 < bid <= ask and age >= 0):
                result["quote_market_state"] = "INVALID_OR_FUTURE_QUOTE"
            elif age > 5:
                result["quote_market_state"] = "NO_FRESH_QUOTES"
            else:
                result["quote_market_state"] = "FRESH_QUOTES_OBSERVED"
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
