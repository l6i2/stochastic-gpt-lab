# Continuation audit — 2026-10-22 America/Chicago

## Current authoritative operational state

This checkpoint supersedes earlier operational snapshots. Research rules and sealed protocols remain unchanged. No protected data, outcome labels, PnL, scoring, new hypotheses, orders, or backfill were used.

- Branch: `research/full-pipeline`; starting local/origin commit `6819e90406a6eea0c9d971f7a562b62703d47a88`.
- Scheduler enabled/Ready, last observed result 0 at October 22 23:45:45 CDT, next October 23 00:00 CDT. `StartWhenAvailable=true`, `MultipleInstances=IgnoreNew`; task uses the interactive user. It cannot collect while logged out or while the verified XM terminal is absent.
- Latest completed wrapper invocation: `2026-10-23T04:45:04.524136Z`, exit 0, `CAUGHT_UP_WAITING_FOR_CLOSED_DAY`. A waiting invocation does not prove MT5 connectivity.
- Fresh read-only environment probe: zero active terminals, `XM_ACTIVE=false`, connection/account/symbol UNKNOWN, `SAFE_FOR_RESEARCH=false`. Collection is scheduled, but runtime is currently `BLOCKED_ENVIRONMENT`. Capture-data health is `HEALTHY`; this must not be reported as end-to-end operational readiness.
- Sealed health metadata: 4 complete UTC days, 545,461 ticks, 1,104 M5 bars, 60 BUY / 61 SELL; zero invalid rows and missing UTC capture days; 41 duplicate tick timestamps explicitly retained. Latest tick `2026-10-22T23:59:57.051Z`. Cohort manifest hash `d3d97be38ed2963e838cea3e5784c9bcfcbf6efb2b96d9aa1bd2dddbc4c1af17`. Cohort is NOT_MATURE.
- Manifest snapshots verify links from the retained anchor through the current manifest. The predecessor `d95984df57447f8caf56de2d071f7cdca0889ef6ec6ce9513d6f54fb94896664` is not present in the retained ledger. No reconstruction or full-chain PASS is claimed; `BASELINE_ANCHORED_PREFIX_UNVERIFIED` remains a failing maturity gate.

## Implemented corrections

Drift summaries now carry and validate exact bin edges, positive row totals, finite consistent missing rates, nonnegative integer counts, exact feature sets, CSV header uniqueness and row width. Comparison rejects same-length histograms with different edges. These checks do not prove identical feature producers: `DRIFT_MONITOR=NOT_READY`; no real baseline was fitted and no future feature comparison ran.

Manifest archiving recovers a verified current snapshot left by interruption before ledger append, checks its parent against the latest ledger entry, and remains idempotent. Tests cover first-anchor recovery, later-link recovery and refusal of incorrect parents. This repairs forward crash recovery without inventing the missing historical prefix.

The separate read-only `python/collector_operational_health.py` reports `runtime_ready` and `runtime_status` independently from stored-capture health. Its latest scheduler attempt takes precedence over the last manifest-changing attempt. The collector itself remains byte-identical to its manifest-pinned code hash; no cohort identity migration occurred.

## Remaining blockers and stopping state

`SESSION_CALENDAR=FAIL` (unverified): the read-only probe is already compiled/deployed but has not run. Weekly quote/trade sessions require the active XM server; DST transition rules and current authoritative holiday exceptions remain missing. Public XM search did not establish those account-specific facts; no third-party hours were substituted. See [calendar evidence](XM_SESSION_CALENDAR_STATUS.md).

`CAUSAL_AUDIT=FAIL` (incomplete): fixture-level causality tests do not establish full native producer/feature-table equivalence. No complete candidate-bound causal table/audit exists. No PASS artifact was manufactured. Native g++ checks are unavailable on this host.

`FUTURE_EVALUATOR=READY_BUT_GATED`; `DEMO_EXECUTOR=READY_BUT_DISABLED_FULL`; `SHADOW_MODE=READY_BUT_DISABLED`; `SHADOW_ORDER_COUNT=0`. Seventeen hypotheses remain rejected; zero survivors, `BEST_CANDIDATE=NONE`, `CANDIDATE_FROZEN=NO`. `DISCOVERY_VALIDATION=BLOCKED`, `FINAL_TEST=LOCKED`, `DEMO=DISABLED`, `LIVE_TRADING=false`.

`NEXT_STATE=HARD_BLOCKER`: require externally verifiable active-server calendar evidence and missing historical provenance (or a separately authorized scientific decision about that unavailable evidence). Reopen the existing XM terminal and run the already deployed read-only session probe when available; do not activate an order adapter. No threshold, split, cohort start or sealed protocol is changed. No percentage readiness estimate is defensible while these gates fail.

The frozen FUTURE_VALIDATION_PROTOCOL and PROSPECTIVE_EVALUATION_PROTOCOL remain byte-identical to their published SHA-256 seals. Operational updates live here rather than rewriting preregistration after collection began.

## Verification

Final verification completed October 23 CDT: `python -m unittest discover -s tests -v` ran 172 tests in 75.089 seconds, OK with 9 native g++ checks skipped (163 executed successfully). Compileall and `git diff --check` passed. Collector source hash matches its existing manifest seal; both frozen protocol seals and the maturity metadata seal match. No full native causal PASS is claimed.
