# XM reopen check — 2026-10-23 America/Chicago

This checkpoint supersedes the earlier observation that XM was closed. The existing cohort, protocol seals, collector code, hypotheses and protected gates are unchanged.

## Verified read-only operational state

`python/collector_operational_health.py` confirms `account_mode=DEMO`, `mt5_connected=true`, `symbol_status=AVAILABLE`, `runtime_ready=true`, `runtime_status=READY`, `collector_scheduled=true`, `capture_data_health=HEALTHY`, no errors or missing UTC days. The last scheduler attempt observed was `2026-10-23T06:15:03.620264Z`. The last capture-changing success was `2026-10-23T02:02:25.523647Z`; a more recent waiting invocation is not a new capture.

The cohort still contains 4 complete UTC days, 545,461 ticks, 1,104 M5 bars, 60 BUY / 61 SELL metadata signals, latest tick `2026-10-22T23:59:57.051Z`. Manifest hash remains `d3d97be38ed2963e838cea3e5784c9bcfcbf6efb2b96d9aa1bd2dddbc4c1af17`. `COHORT_MATURE=NO`. No collection was forced, no backfill or scoring occurred, and no orders were submitted.

## Session evidence still requires the probe

The active terminal has `MQL5/Scripts/ResearchDiagnostics/SessionCalendarProbe.ex5` installed. A targeted read of the two latest Experts and terminal journal log files found zero `XM_SESSION_PROBE|` records. This is a bounded log search, not a claim about all historical logs.

Windows Computer Use successfully enumerated the active XM window but could not capture it: initial `FrameArrived timed out: timed out waiting on channel`; recovery enumeration succeeded, then activation/capture returned `window capture timed out: timed out waiting on channel`. No click, key input, script execution or security-setting change was performed. The helper cannot currently operate the probe reliably.

Next manual step: in the existing XM terminal, open Navigator > Scripts > ResearchDiagnostics and double-click `SessionCalendarProbe`. It is a read-only diagnostic with no order calls. Its START/CLOCK/QUOTE/TRADE/END output can then be collected from local logs without copying account credentials. Weekly sessions alone do not verify seasonal DST transitions or holiday/early-close exceptions; current authoritative XM evidence remains required.

## Unchanged scientific gates

`SESSION_CALENDAR=FAIL` (unverified); `CAUSAL_AUDIT=FAIL` (incomplete); `DRIFT_MONITOR=NOT_READY`; `FUTURE_EVALUATOR=READY_BUT_GATED`; `DEMO_EXECUTOR=READY_BUT_DISABLED_FULL`; `SHADOW_MODE=READY_BUT_DISABLED`; `SHADOW_ORDER_COUNT=0`.

`HYPOTHESES_TESTED_TOTAL=17`, `HYPOTHESES_SURVIVED=0`, `BEST_CANDIDATE=NONE`, `CANDIDATE_FROZEN=NO`, `DISCOVERY_VALIDATION=BLOCKED`, `FINAL_TEST=LOCKED`, `DEMO=DISABLED`, `LIVE_TRADING=false`. The manifest prefix before the available anchor remains unverified. `NEXT_STATE=HARD_BLOCKER` for external calendar/provenance evidence; runtime availability is now resolved.

This continuation changes documentation only. No additional full suite is necessary for that change; the last code checkpoint passed 172 tests (163 executed, 9 skipped for missing g++), compileall and whitespace checks. Both sealed prospective protocols remain byte-identical.
