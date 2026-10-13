# Intra-trade research status

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
