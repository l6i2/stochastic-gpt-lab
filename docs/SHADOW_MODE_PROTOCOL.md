# Shadow mode protocol — disabled

Status: **READY_BUT_DISABLED** as a no-order design; not connected to MT5.
`LIVE_TRADING=false`, `DEMO=DISABLED`. Shadow mode consumes read-only market
data and a frozen candidate, records hypothetical decisions, and has no order
API or account access.

Before a later activation, require a frozen candidate hash, a read-only source,
UTC timestamps, exact `US30Cash` identity, fresh quotes, and an append-only
decision log. Record signal ID, candidate/policy hash, feature hash, quote
time, observed spread, decision latency, hypothetical FOLLOW/INVERT action,
baseline action, reconnect/staleness events, and reason for any missed signal.
Never write orders, positions, or account settings. Stale data, gaps, unknown
symbol, hash mismatch, or service error produces `NO_DECISION` and an audit
event. Shadow output is kept separate from TRAIN and the sealed future cohort;
it cannot tune a candidate. Comparison reports are descriptive and cannot
promote a policy. Activation remains disabled pending explicit authorization.
