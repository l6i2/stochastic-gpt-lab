# Project status

## CHECKPOINT_A — baseline audit: COMPLETE

Repository: `l6i2/stochastic-gpt-lab`, branch `research/full-pipeline`; audit baseline HEAD `d8f639578a409acd941ec35b6d5349a66d7007c4`. No project code was changed before the audit. The original worktree's pre-existing deletion of `mt5/StochasticResearchEA.mq5` remains untouched.

- XM Global SC MT5 / MetaEditor build 6257. The active terminal title showed a DEMO account. The completed smoke test used US30Cash M5, every tick based on real ticks, optimization OFF, 2026-10-01 through 2026-10-11 server time, 888,125 ticks and 1,932 M5 bars.
- Smoke audit: 200 signals / 200 rows; schema 1.1; `aborted=false`, no fatal error; 95 BUY and 105 SELL. Each event contains FOLLOW and INVERT virtual outcomes. CSV validator: PASS (200 rows, 329 columns, 5 censored rows). A local Parquet round-trip and second validation also passed using fastparquet. Raw CSV remains local and is not committed.
- The deployed EA and both includes are byte-for-byte identical to the corresponding files at the audited main HEAD. The current `.ex5` exists; the saved MetaEditor log reports 0 errors and 0 warnings. `LIVE_TRADING=false`; no trading occurred.

## FASE 1 — Python environment: PASS WITH NATIVE-TEST LIMIT

- Created project `.venv` with isolated CPython 3.12.10 x64 via portable `uv` 0.12.19; system Python registrations and PATH were not changed.
- Verified: NumPy 1.26.4, pandas 2.2.3, PyArrow 14.0.2, fastparquet 2026.9.0, scikit-learn 1.9.1, joblib 1.6.0. `uv pip check` passed.
- This host exposes SSE4.1 but not SSE4.2. The installed PyArrow wheels can terminate with an illegal instruction during Parquet reads. Added `python/parquet_io.py` to select fastparquet on CPUs without SSE4.2; CSV→Parquet→read validation now works. Requirements cap NumPy and pandas to avoid wheels that require unsupported CPU features.
- `python -m compileall -q python tests`: PASS. Full unittest run: 29 tests, 9 skipped and the remaining 20 passed. The skipped tests are the native C++ HA/core tests because `g++` is not installed; Python-only causal, split, audit, Parquet, and FINAL_TEST-lock checks passed.
- No g++ was installed. Installing a native toolchain is deferred; it is not required for the Python research path.

## FASE 2 — MT5 compilation: VERIFIED

Required files are together at the active terminal's `MQL5/Experts/StochasticResearch/`. MetaEditor build 6257 reports **0 errors, 0 warnings**, with `.ex5` present. Sanitized evidence is saved at `outputs/verification/metaeditor_compile.log`. No MQL5 strategy or parameters were changed.

## FASE 3 — history coverage: IN PROGRESS

Read-only queries through the official MT5 Python integration found US30Cash ticks from at least `2023-12-20T12:06:50.263Z` through `2026-10-13T07:50:51.320Z`; ticks were present in sampled windows in 2024, 2025, and 2026. Samples from July–November 2023 returned no ticks. These are observations, not a complete gap audit.

The active terminal exposes only its newest 100,000 M5 bars through `copy_rates_from_pos`, from `2025-05-14T22:45:00Z` through `2026-10-13T07:50:00Z`. The exact earliest broker M5 bar beyond that chart limit is not yet established. No historical dataset block has been run.

**Next:** resolve the MT5 chart-history limit / broker M5 coverage, produce `outputs/history_coverage.json`, then run bounded historical blocks only after validating their per-block outputs. Preserve causal splits; never open FINAL_TEST or enable Demo execution. Keep `LIVE_TRADING=false`.
