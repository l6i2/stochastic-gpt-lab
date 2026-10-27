# DEMO executor — READY_BUT_DISABLED_FULL

`DEMO=DISABLED`, `LIVE_TRADING=false`. FULL describe la cobertura de mocks y
persistencia, no órdenes broker. No se implementa ni habilita order_send.

Las pruebas cubren DEMO obligatorio; REAL/UNKNOWN rechazados; US30Cash; max lot,
posiciones, pérdida diaria, pérdidas consecutivas, spread, slippage y trades/día;
kill switch, heartbeat, datos stale, reconnect, idempotencia, intent persistente,
crash recovery y audit log. Se usa SQLite WAL, synchronous FULL y quick_check.

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
- The execution adapter is deliberately absent. The SQLite mock persists an
  idempotency key before accepting any hypothetical intent, survives restart,
  performs `quick_check`, and records an append-only audit event. There is no
  MT5 order adapter and no real account credentials in this path.
- Every refusal and hypothetical decision is auditable. On any exception,
  uncertainty, missing feature, timeout, or policy mismatch, the outcome is
  `NO_TRADE`.

This status does not mean broker execution is implemented or enabled. Any
future real DEMO order adapter would be separate work requiring a frozen,
prospectively validated candidate and explicit user authorization. It never
authorizes LIVE, and `LIVE_TRADING=false` is invariant.

[Estado actual](PROJECT_STATUS.md).
