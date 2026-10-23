# XM session probe captured — 2026-10-23

This checkpoint supersedes the earlier report that probe execution was pending. Read-only environment verification confirms active XM, connected DEMO, US30Cash available, SAFE_FOR_RESEARCH=true.

The local Experts log now contains ten complete START/CLOCK/QUOTE/TRADE/END blocks. The latest captured block is at `2026-10-23T06:48:20Z`; server clock `08:48:20`, observed offset +7200 seconds. Only probe-prefixed records were extracted; account login, balance, trades and unrelated journal content were not published. The log hash is a hash of the whole file at capture, not a promise that the active log will remain unchanged.

Exact latest snapshot, in times returned by the broker API:

| Day | Quote sessions | Trade sessions |
|---|---|---|
| Monday–Wednesday | 00:00–23:00 | 00:05–22:55 |
| Thursday | 01:00–00:00 | 01:05–23:55 |
| Friday | 01:00–00:00 | 01:05–23:50 |
| Saturday–Sunday | No records returned | No records returned |

`00:00` end times are preserved exactly. No UTC expansion, midnight rollover assumption, weekday normalization, or inference from cohort bars has been applied. The observed weekday differences and +02:00 clock reading require reconciliation with authoritative server DST/calendar rules before this becomes an expected-open-session calendar. A current clock offset does not establish past or future offsets or holiday exceptions.

The sanitized latest block, source-log hash and repository probe-source hash are pinned in [session evidence](../configs/xm_session_probe_evidence_20261023.json) and its SHA-256 sidecar. The probe-source hash identifies the repository source; this capture does not independently attest compiled-binary equivalence.

`SESSION_PROBE=CAPTURED`; `SESSION_CALENDAR=FAIL` (still unverified). No need to rerun the probe for this snapshot. Current authoritative XM DST transition rules and holiday/early-close exceptions are still required. The frozen calendar configuration is not replaced by this partial evidence, and its existing hash remains unchanged.

Cohort outcome scoring remains unauthorized; no PnL or labels were read. No orders or backfill occurred. `COHORT_MATURE=NO`, `CAUSAL_AUDIT=FAIL` (incomplete), `DRIFT_MONITOR=NOT_READY`, `FUTURE_EVALUATOR=READY_BUT_GATED`, `DEMO_EXECUTOR=READY_BUT_DISABLED_FULL`, `SHADOW_MODE=READY_BUT_DISABLED`, `HYPOTHESES_TESTED_TOTAL=17`, `HYPOTHESES_SURVIVED=0`, `BEST_CANDIDATE=NONE`, `DISCOVERY_VALIDATION=BLOCKED`, `FINAL_TEST=LOCKED`, `DEMO=DISABLED`, `LIVE_TRADING=false`. Manifest-prefix provenance remains unresolved. `NEXT_STATE=HARD_BLOCKER` for the remaining external calendar/provenance evidence.

Verification: all captured blocks contain START, CLOCK, five quote records, five trade records, END; the latest block has the expected symbol and selected status. Evidence SHA-256 validated. Documentation/evidence-only update; no code changed and no full-suite rerun was needed. Last code suite: 172 tests, 163 executed successfully, 9 native checks skipped for missing g++. Both sealed evaluation protocols and the calendar seal remain unchanged.
