# Intra-trade research status

## Current authoritative checkpoint — 2026-10-14 (all base history accepted)

This section supersedes operational statements in older sections below.
Base history: December 2023 PASS; 2024 PASS (`r20261014T052944_07590da1`);
2025 PASS (`r20261014T061439_70753a52`); January 1–March 19 2026 PASS
(`r20261014T070800_6a2dbe02`). No accepted native block was repeated.
The interrupted old 2024 attempt remains rejected and preserved.

Frozen membership is unchanged: 16,320 known signals, ten observed boundary
purges, 47 endpoint-gap quarantines, and two end-of-data censored nonmembers.
The latter two are quarantined with pinned allowed-source evidence; no future
outcome or original protected purge reason is inferred. See the two membership
contract JSON documents. All raw evidence remains available locally.

Postprocess is RUNNING with bounded streaming and SQLite uniqueness checks.
The earlier dense attempt exhausted available memory and was stopped; its
partial outputs were archived, not accepted or deleted. Final consolidation,
combined validation and quality audit have not yet passed.

The separate schema 3 producer adds every-bar states, an ordered quote tape
and trade indices. Baseline strategy functions are preserved. Preview compile
was 0/0; the first deployed compile timed out without a success summary and
was rejected. A fresh compile is being retried with a longer timeout. Native
schema 3 causal proof, smoke/history and dynamic master remain pending.

No new hypothesis validation, model training, walk-forward, robustness result
or candidate is claimed. Legacy future excursion labels and unusable breakout
features remain excluded from promotion. FINAL_TEST=LOCKED;
LIVE_TRADING=false; DEMO_EXECUTOR=NOT_STARTED.

## Current authoritative checkpoint — 2026-10-14

Older sections below are historical, not the current execution plan. The master
request now authorizes safe bounded reruns. December 2023 PASS. Recovery of
2024 run `r20261013T121405_09901cc2` found no completion/artifact evidence and
marked it FAIL. Replacement `r20261014T052944_07590da1` is PASS after revalidating
the existing completed artifacts without another backtest. 2025 run
`r20261014T061439_70753a52` is active; 2026 through March 19 pending. Evidence preserved.

The local quote-mark correction is already deployed and matches the compiled
source and causal proof. Twenty focused existing tests and two quality-audit
tests pass. No new master, hypothesis validation or model results exist yet.

Dynamic research is gated by `DYNAMIC_REPLAY_REQUIREMENTS.md`. Scheduled offsets
lack ordered executable post-decision quotes. Lifetime-extrema increments are
not future path excursions; derived recovery labels are excluded from promotion
research. Strict breakout flags whose reference window includes the current
bar are excluded until corrected and versioned. No candidate can be promoted
using the prototype support-only hypothesis checks.

FINAL_TEST=LOCKED; LIVE_TRADING=false; DEMO disabled; no candidate promoted.

Preparation while C5 runs: `build_bar_replay_producer` derives a separate schema
3.0 producer with every-bar states and a separate first-post-decision quote
table. Baseline execution functions are preserved; preview compilation is 0/0.
It has not been deployed, causally accepted or used for historical exports.
The schema 3 validator requires contiguous bar coverage, baseline-lifetime
agreement and complete, finite, strictly post-cutoff execution rows. None of
this makes the incomplete C5 history or dynamic master ready.

The new inclusive 2024 export has 7,412 signals versus 7,390 in the frozen source.
The 22 additional IDs all occur December 31, a day missing from that source due
to the old exclusive ToDate endpoint. Frozen 2025 has the same endpoint gap.
The explicit hash-verified contract in `FROZEN_UNIVERSE_COVERAGE.json` preserves
all raw evidence while excluding these noncanonical IDs from research. It does
not add observations to TRAIN/VALIDATION, move boundaries, or select by outcome.
Other unexplained nonmember IDs still fail closed. The 2024 block now passes both
validators and causal acceptance; C5 remains incomplete until 2025/2026 pass.

2025 tester PASS: 7,200 signals versus 7,175 in the frozen source. Endpoint
contract v2 uses actual entry time, preserving the old v1 checkpoint. The 25
additional entries on December 31 include a signal whose cutoff is December 30
23:59:59.999. The other ten nonmember signals are genuine TRAIN-boundary purges.
Revalidation reuses this completed export; no additional 2025 tester run is needed.

Date: 2026-10-13. Branch: `research/full-pipeline`. Current remote base: `fc178e7577f2c372194fedd295805cff3932440a`.

## INTRA_A — instrumentation

**Status: source and compiler checks pass; smoke evidence rejected.** The independent `mt5/StochasticIntratradeResearchEA.mq5` exports open virtual FOLLOW/INVERT states at offsets 1, 2, 3, 5, 10, 15, 20, 30, and 50. It retains `LIVE_TRADING=false`, requires Strategy Tester with optimization OFF and `TICK_QUOTES`, uses the same unchanged `ResearchCore.mqh`, and does not call trading APIs. The dedicated EA and both includes are in the active XM data folder. XM MetaEditor build 6257 compiled that exact copy with 0 errors and 0 warnings; evidence is in the local-only `outputs/verification/metaeditor_intratrade_compile.log`.

Static regression tests confirm that the base signal thresholds and the `TickTrade`/`BarTrade` execution routines are unchanged. Validator and frozen-hypothesis tests verify snapshot cutoffs, separate targets, no final-test IDs, and single-use validation. `python -m compileall -q python tests` passes. The full suite passes: 54 tests, 9 skipped because `g++` is unavailable.

## MT5 smoke test gate

**Status: REJECTED; do not use these artifacts.** MT5 produced snapshot, target, audit, entry CSV, and tester log files in the local Agent-127.0.0.1-3000 `MQL5/Files` directory on 2026-10-13. The tester log identifies the run period as 2026-10-01 through 2026-10-12. This is after the protected FINAL_TEST boundary (`final_test_start_signal_time_msc=1773980099999`, 2026-03-20). The tester also loaded `Experts\StochasticResearch\StochasticIntratradeResearchEA.ex5`, not the dedicated EA at `Experts\StochasticIntratradeResearch\StochasticIntratradeResearchEA.ex5`. Consequently this is neither an allowed discovery smoke run nor evidence for the newly deployed binary. The generated files remain in the tester agent folder and were not copied into the repository or used for research.

The structural validator initially returned PASS without split Parquet arguments. That only checks schema and timestamp/label separation; it did not verify inherited signal membership. The validator now marks split membership as unverified and reports `final_test_accessed: null` for a structural-only pass. Pipeline validation supplies TRAIN and DISCOVERY_VALIDATION membership and rejects unknown IDs. Do not treat the structural-only result as a dataset approval.

The correct deployed EA and includes now exist in the active XM Data Folder under `MQL5/Experts/StochasticIntratradeResearch/`; XM MetaEditor build 6257 compiled that exact copy with 0 errors and 0 warnings. No additional smoke run has been started. To accept smoke evidence, run only a short pre-boundary period such as 2024-01-01 through 2024-01-31, select the dedicated folder's EA, and validate with both inherited TRAIN and DISCOVERY_VALIDATION membership files. Existing bounded historical presets stop at 2026-03-19; the requested period after 2026-03-20 must remain excluded.

## Data and evaluation limitations

The snapshot CSV and target CSV are separate. The exporter writes causal features only through the completed-bar cutoff and delays targets until closure; end-of-data records remain censored. Profile windows are recomputed at snapshot time and cached for paired FOLLOW/INVERT rows on that bar.

The current source records scheduled snapshot states and terminal labels, not the full ordered quote path after each snapshot. Therefore a decision policy that exits at a later tick or reverses direction cannot yet be faithfully simulated; `REVERSE_DIRECTION` is marked unavailable until that path is exported. The fixed-bar-3 HOLD, EARLY_EXIT, and +60 PROTECT_PROFIT comparisons are predeclared and research-only. They cannot create or promote a candidate.

No raw blocks, master snapshots, TRAIN analysis, intra-trade hypotheses, model metrics, or walk-forward metrics exist yet. `NO CANDIDATE`; FINAL_TEST remains locked and DEMO execution remains disabled.

## 2025 annual run audit — 2026-10-13

The requested `US30Cash`, M5, real-tick, optimization-OFF, `LIVE_TRADING=false` test completed for 2025-01-01..2025-12-31. The entry audit reports 7,175 signals (3,338 BUY; 3,837 SELL), no fatal/abort, and the baseline event CSV matches the canonical 2025 event hash. The intra-trade audit reports 116,929 snapshots and 116,825 targets; offsets are +1 14,302, +2 14,228, +3 14,135, +5 13,935, +10 13,387, +15 12,916, +20 12,437, +30 11,545, +50 10,044. FOLLOW has 58,428 snapshots; INVERT has 58,501.

**Rejected for research.** Split-aware `validate_intratrade_dataset.py` fails because current MFE does not bound current unrealized PnL. A full streaming audit found 207 MFE-bound violations, 0 MAE-bound violations, 0 future timestamp violations, 0 FOLLOW/INVERT side-mapping violations, 0 duplicate snapshot IDs, and no monotonic MFE/MAE regressions. The export's mark quote was reconstructed from bar close and bar spread while excursion tracking used actual ticks. That can create a mark PnL larger than observed MFE. No raw data was canonicalized, no master/split/research was built, and no FINAL_TEST data was opened.

The exporter was minimally changed to mark each snapshot from the last observed bid/ask at or before the cutoff; Stochastic logic, parameters, and tick/bar exit routines were left intact. The dedicated XM MetaEditor compile log reports 0 errors and 0 warnings. Focused Python tests are being run. Per the instruction not to start the Tester again yet, the corrected 2025 block has not been rerun. A corrected 2025 preset and bounded presets for 2023-12-20..31, 2024, and 2026-01-01..2026-03-19 are prepared under `outputs/verification/intratrade_export_plan/corrected/` and the `.set` files are copied to the active XM `MQL5/Profiles/Tester` folder. The 2026 range ends before the protected FINAL_TEST boundary.

**Next required run:** start only `intratrade_2025_quote_markfix_20261013.set` (dedicated expert path) and stop after it finishes. Do not build the intratrade master or analyze hypotheses until the corrected 2025 export passes validation. Remaining bounded blocks stay queued.

## 2026-10-16 continuation: schema 3 dynamic replay gate

Authoritative local HEAD at audit start: `71667a86597adee298cbfd56c37c6be55c162b40`, branch `research/full-pipeline`, equal to `origin/research/full-pipeline`. Four schema 2 blocks (Dec 20–31 2023, 2024, 2025, and 2026-01-01..03-19) are PASS. The schema 2 master and TRAIN descriptive analysis exist, but the scheduled snapshots and legacy excursion deltas are not a faithful dynamic exit policy dataset; they remain descriptive only.

The separate schema 3 exporter is now compiled on the active XM installation (0 errors, 0 warnings; EA SHA `f2e9bf43cbbdc716148847fe53e1f3dd14b21393775ccc809d05cb5e134cb88d`; EX5 SHA `2943e6fc9d35798dd00b3565f7f4b9695346944b7686a4202b54c5617cf55ecd`). The updated causal probe passed 1,060 snapshots × 257 features under future-only input mutation; 404 quote records through the cutoff were byte-identical. Baseline replay passed both fixtures. This is synthetic causality/fixture evidence, not historical acceptance.

A real US30Cash M5 real-tick Tester smoke for 2025-01-01..31 passed: 611 signals, 92,023 every-bar snapshots (offsets 1..100 while open), 91,893 terminal targets, 1,952,817 ticks and 5,850 bars; event and schema 3 validators, exact HOLD baseline replay, and causal-hash verification all pass. `LIVE_TRADING=false`, optimization OFF, DEMO account in Tester, no trading APIs. Run ID `r20261016T154619_288daa1d`. The accepted raw run is local in `outputs/bar_controller/runs/`; the source manifest records the run identity and hashes.

**Next:** run the four complete permitted schema 3 blocks under the isolated `bar_controller` namespace. Then validate all tapes, build schema 3 master and split partitions, run data-quality and TRAIN-only dynamic replay research, freeze hypotheses, validate once on DISCOVERY_VALIDATION, and run walk-forward/ML/robustness. No dynamic hypothesis has been tested, no candidate exists. FINAL_TEST stays locked; DEMO stays disabled; live trading stays false.
