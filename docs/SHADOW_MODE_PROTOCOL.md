# Shadow mode protocol — ready, disabled

## Authoritative operational checkpoint — 2026-10-23

[Current addendum and evidence](PROSPECTIVE_OPERATIONAL_ADDENDUM_20261023.md): `SESSION_CALENDAR=PASS_WITH_RUNTIME_GUARD` for operational containment; historical UTC calendar remains unverified. Guard READY, DST PARTIAL, holidays UNKNOWN. Causal audit FAIL (frozen metadata/native-trigger non-equivalence), manifest chain PARTIAL, drift NOT_READY. Collector active/HEALTHY, cohort NOT_MATURE, evaluator READY_BUT_GATED. DEMO executor and shadow READY_BUT_DISABLED; no orders. FINAL_TEST LOCKED; DEMO DISABLED; LIVE_TRADING=false. Full suite: 190 tests, 9 native skips. NEXT_STATE=HARD_BLOCKER.

All operational snapshots below are historical and superseded by the linked addendum; sealed scientific protocols remain unchanged.




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
