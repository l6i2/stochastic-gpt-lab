# DEMO executor design — disabled

Status: **NOT_READY**. This document defines safety controls only. There is no
validated candidate, executable order adapter, or authorization to activate
DEMO. `LIVE_TRADING=false`; no orders were sent.

Any future executor must fail closed unless all gates pass simultaneously:

- `DEMO_TRADING_ALLOWED` defaults false and must be explicitly enabled by a
  later user instruction.
- Terminal account mode must equal DEMO; REAL, CONTEST, UNKNOWN, or unavailable
  mode aborts before strategy evaluation. The symbol allowlist is exactly
  `US30Cash`.
- A candidate package must be frozen and hash-verified. Policy version,
  feature schema, signal ID, decision, quote, spread, latency, and risk checks
  are written to an append-only audit record before an order can be considered.
- Risk limits are mandatory configuration, not inferred defaults: maximum lot,
  open positions, daily loss, consecutive losses, spread, slippage, trades per
  day, and account equity drawdown. Missing or non-positive limits abort.
- A persistent kill switch, heartbeat freshness, market-data staleness,
  reconnect state, duplicate signal/order key, and daily/session boundaries
  are checked before every decision. A reconnect requires explicit state
  reconciliation; stale or conflicting state blocks execution.
- The execution adapter is isolated behind an interface. Unit tests use a
  mock that raises if an order method is invoked; test runs have no MT5 order
  adapter and no real account credentials.
- Every refusal and hypothetical decision is auditable. On any exception,
  uncertainty, missing feature, timeout, or policy mismatch, the outcome is
  `NO_TRADE`.

Activation requires a later explicit DEMO authorization after a validated,
frozen candidate. It never authorizes LIVE, and a REAL-account guard is
independent of the user-controlled enable flag.
