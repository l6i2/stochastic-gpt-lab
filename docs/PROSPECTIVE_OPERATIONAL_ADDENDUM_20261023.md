# Prospective operational addendum â€” 2026-10-23

This is the current authoritative operational checkpoint. It supersedes earlier operational status notes, including claims that XM is closed or that the session probe has not run. It does not amend the sealed research/maturity/evaluation protocols, collector identity, cohort start, splits, rejected hypotheses, candidate rules or scientific thresholds.

## Status and interpretation

| Field | Result |
|---|---|
| SESSION_CALENDAR | PASS_WITH_RUNTIME_GUARD â€” conditional operational containment only |
| DST_RULES | PARTIAL |
| HOLIDAY_EXCEPTIONS | UNKNOWN / REQUIRE_RUNTIME_GUARD |
| RUNTIME_SESSION_GUARD | READY â€” tested engine, read-only diagnostic, disabled shadow/mock integrations |
| CAUSAL_AUDIT | FAIL â€” native-trigger equivalence not established; counterexample documented |
| MANIFEST_CHAIN | PARTIAL â€” all 3 retained snapshots verify from anchor; older prefix unavailable |
| DRIFT_MONITOR | NOT_READY â€” no equivalent fitted baseline/future producer stream |
| FUTURE_COLLECTION_ACTIVE | YES â€” scheduled, active verified XM DEMO, data health HEALTHY |
| COHORT_MATURE | NO |
| FUTURE_EVALUATOR | READY_BUT_GATED |
| DEMO_EXECUTOR | READY_BUT_DISABLED_FULL |
| SHADOW_MODE | READY_BUT_DISABLED |
| DISCOVERY_VALIDATION | BLOCKED |
| FINAL_TEST | LOCKED |
| DEMO | DISABLED |
| LIVE_TRADING | false |
| NEXT_STATE | HARD_BLOCKER â€” frozen metadata/native parity and clock/calendar provenance need resolution |

`PASS_WITH_RUNTIME_GUARD` is an operational risk-containment disposition, not a verified historical UTC calendar. The existing cohort calendar still has `verified=false`, and its unchanged maturity gate remains false. Unknown dates/holidays never become open sessions by default. No automatic scoring, DEMO activation, candidate promotion, or historical gap acceptance follows from this status. Runtime diagnostics currently refuse permission.

## XM session/calendar reconciliation

The already-published probe was reused; it was not rerun. Latest retained snapshot: server `XMGlobal-MT5 10`, symbol `US30Cash`, UTC `2026-10-23T06:48:20Z`, server clock `08:48:20`, observed offset +7200 seconds. Evidence SHA-256: `835ff42202c9ae9308e9431db6bb79e980b7285c9f12cab802ba28e656cf15f3`.

Exact broker-API wall-time snapshot:

| Day | Quotes | Trading |
|---|---|---|
| Mondayâ€“Wednesday | 00:00â€“23:00 | 00:05â€“22:55 |
| Thursday | 01:00â€“00:00 | 01:05â€“23:55 |
| Friday | 01:00â€“00:00 | 01:05â€“23:50 |
| Saturdayâ€“Sunday | No sessions returned | No sessions returned |

Quote availability and trading availability differ: in particular Friday quotes may extend beyond the 23:50 trade cutoff. The runtime parser interprets a nonzero start ending at 00:00 as the day-end boundary, retains separate quote/trade schedules, uses half-open intervals and blocks at the exact close. Equal start/end or unsupported overnight ambiguity is rejected. This guarded boundary interpretation is not asserted as a verified historical holiday/DST conversion. Weekends are checked in broker wall time, including the boundary while the UTC date is still Friday.

[XM's official terminal FAQ](https://www.xm.com/se/help-center/trading-platforms/faq-can-i-change-the-time-zone-on-my-trading-terminal) publishes the seasonal GMT+2/GMT+3 convention and describes EU platform time. The [EU 2026 schedule](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=oj%3AJOC_2021_149_R) puts the transition at 01:00 UTC on March 29 and October 25. Applying that EU convention as a diagnostic expectation yields +03:00 on October 23, differing from the captured +02:00. This is a discrepancy, not evidence that the active account server necessarily follows the inferred EU transition rule.

MQL5 documents [TimeTradeServer](https://www.mql5.com/en/docs/dateandtime/timetradeserver) as client-calculated and dependent on computer time settings; [TimeGMT](https://www.mql5.com/en/docs/dateandtime/timegmt) also depends on local computer time/DST handling. Their difference therefore does not independently attest the server timezone. No tick UTC timestamp is repurposed as a broker-wall-clock offset.

[XM's public index page](https://www.xm.com/equity-indices) directs clients to account access for instrument hours; it does not establish a uniform public schedule to override this server's observed weekday differences. No current account-specific holiday/early-close schedule was verified. Previously located historical holiday PDFs are not evidence for this cohort's dates. Missing exceptions are explicitly UNKNOWN, never presumed normal. Other brokers, affiliates and exchange hours were not substituted for XMGlobal server evidence.

Formal disposition: the observed weekly sessions are preserved, DST remains PARTIAL, holidays UNKNOWN, and uncertain runtime dates are blocked. Closing the historical maturity calendar still requires reconciled active-server clock/session evidence and authoritative exceptions. Frozen `configs/xm_us30cash_sessions_utc.json` remains unchanged.

## Runtime guard and disabled integrations

`python/runtime_session_guard.py` verifies the existing evidence hash, symbol/server, clock arithmetic, session indexes, interval validity and quote/trade containment. Decisions require all of: independently verified current clock, reconciled active-server date/session, attested normal/non-holiday date, affirmative independent broker-open evidence, valid fresh bid/ask and fresh observation. Five-second runtime freshness and seven-day maximum snapshot age are operational safety limits, not research thresholds. Offset changes, an intervening EU DST boundary, expired snapshots, stale/future quotes, unknown holidays, disconnection, REAL/UNKNOWN account mode and market-closed state block. Missing proof never authorizes a hypothetical decision.

`python/session_runtime_status.py` attaches only after active XM DEMO/Data Folder verification, uses read-only account/symbol/quote queries and disconnects after the check. A disabled/unavailable symbol is closed for permission purposes; stale/invalid quotes block. Fresh quotes are reported as quote availability only and never as proof of executable market availability. There is no order API in this diagnostic. No automated source currently supplies missing clock/holiday/broker-open attestations, so they remain UNKNOWN and blocked.

Actual diagnostic during this continuation: `INVALID_OR_FUTURE_QUOTE`, with quote age approximately **-60,623 seconds** (about 16.8 hours ahead of the observation's UTC clock); execution state UNKNOWN; permission false; reason `CLOCK_OR_CALENDAR_AMBIGUOUS`. This is an observed timestamp discrepancy whose cause is unresolved. No clock setting, timestamp shift, timezone rewrite or automatic offset repair was attempted.

Shadow now requires a supplied guard and successful session observation before its policy callback runs; absent/closed sessions produce `NO_DECISION` and a zero-order audit. The mock safety state defaults `session_guard_pass=false` and rejects an unvalidated session. All other mock risk/account/idempotency gates still apply. Both components remain disabled. A future trusted bridge would have to obtain independent attestations and evaluate the guard for the current decision; a caller-supplied flag is not itself broker evidence. There is still no broker order adapter.

## Causal chain audit: concrete negative evidence

The previously accepted native producer fixture proof was reused rather than rerun: 1,060 snapshots, 257 columns, reported PASS. All five recorded producer source hashes still match the repository. Its finite synthetic scope does not attest a future evaluation table or native-indicator equivalence for the health stream.

A new metadata-only independent check examined the installed standard MT5 `Stochastic.mq5` example (source hash `ec53c80d0d8dd0864885c824ed6d57d05fb895b9cb7c559fddf249a3f3f63bbc`). It computes slowed MAIN_K as the ratio of sums of the close-minus-low and high-minus-low terms. The frozen metadata specification and health implementation instead use an arithmetic mean of three Fast %K values. Those functions are not generally identical.

A valid seven-bar synthetic counterexample gives frozen metadata MAIN_K **30.6666667** versus standard-example MAIN_K **5.2380952**. Flat-window behavior also differs: metadata 50 versus example 100. These are synthetic feature values only, not observations or performance from the cohort. This does not claim an executed parity test against the built-in indicator binary; that independent attestation remains absent. It disproves treating the two written algorithms as interchangeable without further work.

`CAUSAL_AUDIT=FAIL`. Existing 60 BUY / 61 SELL counts are retained as outputs of the frozen metadata implementation and cannot certify native-trigger maturity support. The frozen metadata spec/code and prior health artifacts were not silently rewritten. The negative audit is hash-pinned at `outputs/prospective/causality_audit.json`; the wrapper refreshed health and bound that failed audit. `causality_audit_pass=false`, `cohort_mature=false`, health report SHA-256 `d8d7ca50de4dba745e2c541043846ed1c3a8dfaed2de45631592344c778b6b55`.

The evaluator now also requires an actual independent hash-verified causal artifact bound to the exact candidate, table, cohort and metadata specification, with explicit base-trigger parity, timestamp, target-separation and independent-replay checks. Health must bind the same audit; evaluation manifest and one-use authorization bind its hash. A self-declared `causality_status=PASS` cannot bypass a missing, failed or mismatched audit. Rejection occurs before authorization consumption and outcome-row parsing. No real candidate/table/authorization was generated or evaluated.

Resolving a contradiction in the already-frozen metadata specification needs an explicitly documented versioned correction decision, preserving old artifacts and the scientific boundaries. No new TRAIN hypothesis, retuning or silent preregistration amendment was performed.

## Manifest chain, drift and collector

`python/manifest_chain_audit.py` independently verifies canonical hash-named snapshot paths, sidecars, parent links, immutable identities, append-only raw-segment membership and nondecreasing cursors. All three retained snapshots verify. The pre-anchor predecessor `d95984df57447f8caf56de2d071f7cdca0889ef6ec6ce9513d6f54fb94896664` is still unavailable; status remains PARTIAL. No lost bytes or synthetic ancestry were invented. Forward restart recovery remains tested.

Drift comparisons now require equal SHA-256 identities for feature definitions and producer code in addition to equal feature sets and bin edges. CLI inputs require a sealed definition artifact matching the producer source and schema. Missing or changed contracts fail closed. The template is still unfitted, and no equivalent baseline/future feature producer has passed parity, so `DRIFT_MONITOR=NOT_READY`. No baseline was fitted, future feature distribution compared, ranking performed or threshold tuned.

The collector remains scheduled and connected to verified XM DEMO; capture-data health is HEALTHY. Wrapper verification exited 0 with `CAUGHT_UP_WAITING_FOR_CLOSED_DAY`, collected 0, and refreshed only health metadata. Cohort remains four settled UTC days, 545,461 ticks, 1,104 M5 bars, no missing UTC capture days. Manifest hash is unchanged at `d3d97be38ed2963e838cea3e5784c9bcfcbf6efb2b96d9aa1bd2dddbc4c1af17`. Operational session permission is kept separate from raw collection; ambiguity does not rewrite raw timestamps or move cohort boundaries.

Hypotheses remain 17 tested, zero survivors, no frozen candidate. The remaining blockers are scientific/provenance boundaries rather than more same-TRAIN search opportunities.

## Verification and publication

Full suite: **190 tests in 133.612 seconds, OK; 181 executed successfully, 9 native tests skipped because g++ is unavailable**. Includes both DST boundaries, weekday differences, daily breaks, Friday exact close, server-weekend boundaries, holiday unknown/closed, broker closed, stale/future/invalid quotes, disabled integrations, session-before-policy enforcement, manifest tamper/rewrite/path checks, drift producer/definition mismatches, evaluator audit binding and single-use authorization behavior. Compileall and whitespace checks pass.

The collector source, metadata specification, both sealed prospective protocols and the cohort UTC calendar retain their existing hashes. Raw cohort data, account identifiers, unrelated logs and local workspace files are not committed. Machine-readable sanitized status and operational policy are [technical audit](../configs/technical_readiness_audit_20261023.json) and [guard policy](../configs/xm_runtime_session_policy.json), both with SHA-256 sidecars.

Git checkout integrity: targeted `-text` attributes preserve exact bytes for hash-bound protocols, evidence, metadata and runtime sources. Staged Git payloads were checked byte-for-byte against audited working files, and all existing seals and the collector manifest binding still match. No sealed payload was edited or re-signed. This prevents platform line-ending normalization from changing hash identities on checkout.
