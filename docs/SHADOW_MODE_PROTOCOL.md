# Shadow mode protocol — ready, disabled

> Latest operational check: [XM reopened — 2026-10-23](XM_REOPEN_CHECK_20261023.md). XM is connected in DEMO, US30Cash is available, and collector runtime is READY. Session-probe execution and calendar evidence remain pending; no scoring or orders.

> Current operational checkpoint: [2026-10-22 continuation audit](CONTINUATION_AUDIT_20261022.md). It supersedes older operational snapshots: capture data healthy, XM runtime unavailable, cohort not mature; calendar/causal/drift gates remain unresolved. No scoring or orders.

Status: **READY_BUT_DISABLED**. The no-order decision pipeline and narrow
read-only MT5 adapter are implemented; it is not currently connected to MT5.
`LIVE_TRADING=false`, `DEMO=DISABLED`. Shadow mode consumes read-only market
data and a frozen candidate, records hypothetical decisions, and has no order
API or account access.

Before a later activation, require a frozen candidate hash, a read-only source,
UTC timestamps, exact `US30Cash` identity, fresh quotes, and an append-only
decision log. Record signal ID, candidate/policy hash, feature object and hash,
feature max time, quote time, observed spread, decision latency, hypothetical
FOLLOW/INVERT action, baseline action, reconnect/staleness events, and reason
for any missed signal. Every persisted event has `orders_sent=0` and
`order_count=0`; the adapter exposes no order methods and
`SHADOW_ORDER_COUNT` is fixed at zero.
Never write orders, positions, or account settings. Stale data, gaps, unknown
symbol, hash mismatch, or service error produces `NO_DECISION` and an audit
event. Shadow output is kept separate from TRAIN and the sealed future cohort;
it cannot tune a candidate. Comparison reports are descriptive and cannot
promote a policy. Activation remains disabled pending explicit authorization.
