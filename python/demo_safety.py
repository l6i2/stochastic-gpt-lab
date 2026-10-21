"""Pure safety gate for a future Demo executor; deliberately sends no orders."""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class DemoLimits:
    max_lot: float
    max_positions: int
    max_daily_loss: float
    max_consecutive_losses: int
    max_spread: float
    max_slippage: float
    max_trades_per_day: int
    max_equity_drawdown: float = 0.0


@dataclass(frozen=True)
class RuntimeState:
    account_mode: str
    symbol: str
    demo_trading_allowed: bool
    kill_switch: bool
    heartbeat_age_seconds: float
    quote_age_seconds: float
    open_positions: int
    daily_loss: float
    consecutive_losses: int
    spread: float
    trades_today: int
    signal_key: str
    requested_lot: float = 0.0
    observed_slippage: float = 0.0
    equity_drawdown: float = 0.0
    reconnect_pending: bool = False
    persistent_state_valid: bool = True
    audit_log_writable: bool = True


def authorize_demo_decision(state: RuntimeState, limits: DemoLimits,
                            seen_signal_keys: set[str], *, max_heartbeat_age: float = 30.0,
                            max_quote_age: float = 5.0) -> tuple[bool, str]:
    """Return a decision gate only; the caller must still use a separate adapter."""
    if state.account_mode != "DEMO":
        return False, "ACCOUNT_MODE_NOT_DEMO"
    if state.symbol != "US30Cash":
        return False, "SYMBOL_NOT_ALLOWED"
    if state.demo_trading_allowed is not True:
        return False, "DEMO_DISABLED"
    if state.kill_switch:
        return False, "KILL_SWITCH"
    if state.reconnect_pending:
        return False, "RECONNECT_RECONCILIATION_REQUIRED"
    if state.persistent_state_valid is not True:
        return False, "PERSISTENT_STATE_UNAVAILABLE"
    if state.audit_log_writable is not True:
        return False, "AUDIT_LOG_UNAVAILABLE"
    if any(value <= 0 for value in (limits.max_lot, limits.max_positions,
                                    limits.max_daily_loss, limits.max_consecutive_losses,
                                    limits.max_spread, limits.max_slippage,
                                    limits.max_trades_per_day,
                                    limits.max_equity_drawdown)):
        return False, "INVALID_RISK_LIMIT"
    numeric_state = (state.heartbeat_age_seconds, state.quote_age_seconds,
                     state.daily_loss, state.spread, state.requested_lot,
                     state.observed_slippage, state.equity_drawdown)
    numeric_limits = (limits.max_lot, limits.max_daily_loss, limits.max_spread,
                      limits.max_slippage, limits.max_equity_drawdown)
    if (not all(math.isfinite(value) for value in numeric_state + numeric_limits)
            or min(state.open_positions, state.consecutive_losses, state.trades_today) < 0):
        return False, "INVALID_RUNTIME_STATE"
    if state.heartbeat_age_seconds < 0 or state.heartbeat_age_seconds > max_heartbeat_age:
        return False, "STALE_HEARTBEAT"
    if state.quote_age_seconds < 0 or state.quote_age_seconds > max_quote_age:
        return False, "STALE_QUOTE"
    if state.open_positions >= limits.max_positions:
        return False, "POSITION_LIMIT"
    if state.daily_loss >= limits.max_daily_loss:
        return False, "DAILY_LOSS_LIMIT"
    if state.equity_drawdown < 0 or state.equity_drawdown >= limits.max_equity_drawdown:
        return False, "EQUITY_DRAWDOWN_LIMIT"
    if state.consecutive_losses >= limits.max_consecutive_losses:
        return False, "CONSECUTIVE_LOSS_LIMIT"
    if state.spread < 0 or state.spread > limits.max_spread:
        return False, "SPREAD_LIMIT"
    if state.observed_slippage < 0 or state.observed_slippage > limits.max_slippage:
        return False, "SLIPPAGE_LIMIT"
    if state.requested_lot <= 0 or state.requested_lot > limits.max_lot:
        return False, "LOT_LIMIT"
    if state.trades_today >= limits.max_trades_per_day:
        return False, "DAILY_TRADE_LIMIT"
    if not state.signal_key or state.signal_key in seen_signal_keys:
        return False, "DUPLICATE_OR_EMPTY_SIGNAL"
    return True, "GATES_PASS_NO_ORDER_SENT"
