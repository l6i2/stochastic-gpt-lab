# Project status

## FASE 0 — baseline audit: COMPLETE

Repository: `l6i2/stochastic-gpt-lab`, isolated branch `research/full-pipeline`, audit baseline `d8f639578a409acd941ec35b6d5349a66d7007c4`. The pre-existing deletion of `mt5/StochasticResearchEA.mq5` in the user's original worktree remains untouched. No files in `asistente-trader-ia` were accessed or changed.

The completed XM DEMO smoke test used US30Cash M5, real ticks, optimization off, 2026-10-01 through 2026-10-11 server time. MT5 reported 888,125 ticks and 1,932 M5 bars. The audit contains 200 signals and 200 rows (95 BUY, 105 SELL), schema 1.1, `aborted=false`, and no fatal error. Each signal has both FOLLOW and INVERT virtual outcomes. CSV and a fastparquet round-trip both passed validation: 200 rows, 329 columns, 5 censored rows. The raw smoke dataset remains local and is not published.

The active XM MetaEditor build 6257 log reports 0 errors and 0 warnings; the `.ex5` exists. The deployed MQ5 and include files match the audited source. `LIVE_TRADING=false`; no trading operations were performed.

## FASE 1 — Python environment: PASS WITH NATIVE-TEST LIMIT

A project-local `.venv` uses isolated CPython 3.12.10 x64 via portable `uv`. System Python and PATH were not changed. NumPy 1.26.4, pandas 2.2.3, PyArrow 14.0.2, fastparquet 2026.9.0, scikit-learn 1.9.1, joblib 1.6.0, and the read-only MetaTrader5 Python API 5.0.5572 are available. `uv pip check` and `compileall` pass. The full unittest suite passes: 36 tests run, 27 pass, 9 native C++ tests skipped because `g++` is absent (702 seconds on this host).

PyArrow wheels crash on this host's CPU without SSE4.2; the new `python/parquet_io.py` selects fastparquet as the safe fallback. No global compiler or Python installation was added.

## FASE 2 — MT5 compilation: VERIFIED

The EA and two includes are together in the active XM terminal's `MQL5/Experts/StochasticResearch/`. Sanitized compiler evidence is `outputs/verification/metaeditor_compile.log` (0 errors, 0 warnings). No MQL5 logic or parameters were changed.

## FASE 3 — history coverage: MEASURED

MT5's local `MaxBars` was raised from 100,000 to 1,000,000 for this history audit, with a local backup kept outside the repository. The read-only terminal query returned 701,578 US30Cash M5 bars from server time 2011-08-10 00:00 through 2026-10-13 08:05. The next start position returned no more bars.

MT5 returned current bar/tick epochs about three hours ahead of the computer's UTC clock. XM documents GMT+2 in winter and GMT+3 in summer; the EA's existing default is `DST_EU`. UTC values in `outputs/history_coverage.json` are therefore labeled estimates derived by subtracting the seasonal offset, not raw broker timestamps. XM's published server offset is documented at [XM Help Center](https://www.xm.com/mena/help-center/trading-platforms).

Monthly real-tick queries from 2010-01 through 2023-11 returned no ticks; partial December 2023 begins at server time 2023-12-20 12:06:50.263. Every month from January 2024 through October 2026 (partial through Oct 13) had ticks. Intramonth missing intervals were not exhaustively classified. M5 candles extend much further than usable real ticks, so real-tick historical blocks must begin no earlier than 2023-12-20. Coverage details are in `outputs/history_coverage.json`.

## CHECKPOINT_A — historical data: COMPLETE WITH DATA WARNINGS

Four bounded Strategy Tester blocks cover all monthly real ticks returned by the active XM terminal: partial Dec 20–31, 2023; 2024; 2025; and Jan 1–Oct 13, 2026. Each used US30Cash M5, Every tick based on real ticks, optimization OFF, DEMO tester, and `LIVE_TRADING=false`. Each audit reports `aborted=false`; each canonical dataset passes `validate_dataset.py` with schema 1.1 (329 columns). The first 2025 export exposed a real serialization defect: 10-decimal formatting rounded one Stochastic value just below 80 to 80.0. The EA's numeric serializer was changed to 16 decimals without changing the strategy, recompiled to 0 errors/0 warnings, and the corrected export passed validation.

| Block | Signals | BUY | SELL | Tester data warning |
|---|---:|---:|---:|---|
| 2023-12-20..2023-12-31 | 210 | 96 | 114 | 106,168 mismatched tick prices across 1,230 minute bars; tester generated ticks for affected minutes |
| 2024 | 7,390 | 3,458 | 3,932 | 210 minute bars had real ticks discarded; generated ticks used |
| 2025 | 7,175 | 3,338 | 3,837 | None reported |
| 2026-01-01..2026-10-13 | 5,647 | 2,746 | 2,901 | None reported |

The canonical blocks contain 20,422 signals (9,638 BUY and 10,784 SELL), including 31 rows censored at end of data. `outputs/history/validation_status.csv` records both the initial failed 2025 export and its passing corrected rerun. Raw CSVs and tester logs remain local and are not published. Warnings for 2023 and 2024 are retained and materially limit claims about those intervals.

## CHECKPOINT_B — master dataset: BUILT, LOCAL

`python/build_master_dataset.py` verified the four canonical block audits, manifests, schema, strategy constants, chronological ordering, monotonic timestamps, symbol and signal uniqueness, causal features, and the real-tick/optimization/live-trading settings. No boundary duplicates were found. It wrote `outputs/master/stochastic_master.csv`, `stochastic_master.parquet`, `master_audit.json`, and `master_manifest.json`; SHA-256 of the Parquet master: `e2c05a24551078efb584cc4732b796846f3b98793d21978522b36be141de59c1`.

The chronological partition is 60/20/20 by signal count. The purged outputs contain 12,243 TRAIN and 4,077 DISCOVERY_VALIDATION signals. A standalone FINAL_TEST file was not written and its rows have not been analyzed; the full master necessarily contains the chronological tail and the split manifest records its protected boundary. The analyzer requires a frozen-hypothesis file for validation and an explicit unlock flag for any FINAL_TEST evaluation. No such unlock has been used.

`tests/test_master.py` checks safe configuration enforcement and confirms that the builder writes TRAIN/VALIDATION but no separate FINAL_TEST Parquet. Its first real-data build found a CSV/Parquet parsing-parity issue; the CSV reader and parity check were corrected, and the successful build round-tripped all 20,422 rows.

## CHECKPOINT_C — TRAIN analysis and descriptive walk-forward: COMPLETE

Descriptive analysis is restricted to TRAIN. The report includes ALL/BUY/SELL summaries, feature correlations, deciles, missingness, exits, and fixed Heikin-Ashi/volume/profile interaction tables. Five expanding temporal folds use TRAIN plus DISCOVERY_VALIDATION only; FINAL_TEST is excluded. Fold metrics include BUY/SELL counts, PnL, win rate, profit factor, and drawdown proxy. No thresholds have been optimized and no candidate has been selected.

## CHECKPOINT_D — hypotheses frozen: COMPLETE

One TRAIN-derived BUY-only hypothesis is registered and SHA-256 frozen. Its causal condition is Stochastic BUY plus bullish Heikin-Ashi at signal time; its target is paired FOLLOW minus INVERT PnL. It is side-specific by design and does not make a claim about SELL.

## CHECKPOINT_E — discovery validation: COMPLETE; HYPOTHESIS REJECTED

The frozen BUY hypothesis was evaluated once on purged DISCOVERY_VALIDATION: 865 paired BUY observations, mean directional advantage −1.04 price units, with a week-cluster bootstrap 95% interval [−23.96, 22.87]. It failed the frozen positive-effect criterion and is not promoted. The result and hypothesis hash are local. FINAL_TEST was not read or evaluated.

## CHECKPOINT_F — walk-forward: BASELINE COMPLETE; ML INCOMPLETE

Five expanding descriptive folds were completed across TRAIN plus DISCOVERY_VALIDATION. The three-model ML walk-forward exceeded the practical runtime of this older CPU and was stopped after the base TRAIN fits; saved base models were scored on validation. This limitation is recorded in the local ML manifest rather than inferred as a pass.

## CHECKPOINT_G — model comparison: COMPLETE; NO CANDIDATE

All three simple classifiers were trained on 12,228 paired TRAIN labels and scored once on 4,070 paired DISCOVERY_VALIDATION outcomes (features: 225 causal columns; fixed 0.5 policy threshold). Validation ROC AUC: Logistic Regression 0.493, Random Forest 0.49, HistGradientBoosting 0.508. The model-switch policy mean PnL was −7.29, −1.81, and −2.30 respectively, against FOLLOW-always −3.83 and INVERT-always −8.50 on identical rows. These results are exploratory; the weak discrimination, incomplete ML walk-forward, and absent validated hypothesis prevent a candidate freeze. No model was selected or promoted.

## CHECKPOINT_H onward

No candidate is frozen, so `WAITING_FINAL_TEST_AUTHORIZATION` has not been reached. FINAL_TEST remains locked. Demo architecture and execution remain pending; no live or Demo trading occurred. Do not open FINAL_TEST or enable Demo execution until the promotion prerequisites exist, then stop and request explicit authorization before any held-out evaluation.
