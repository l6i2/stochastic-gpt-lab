# Round 2 research status

Date: 2026-10-13. Branch: `research/full-pipeline`.

## Safety and audit

- FINAL_TEST remains locked and was not read for round-two discovery.
- Demo execution remains disabled. No live or demo trade was placed. The EA source retains `LIVE_TRADING=false`.
- Round 1 master SHA-256: `e2c05a24551078efb584cc4732b796846f3b98793d21978522b36be141de59c1`.
- Chronological split: TRAIN 12,243 events; purged DISCOVERY_VALIDATION 4,077 events; FINAL_TEST is protected and not exported as a standalone file. Split boundaries are recorded in `outputs/splits/split_manifest.json` locally.
- TRAIN observations span 2023-12-20 through 2025-08-19 server-time signal epochs. Round-one real-tick caveats remain: affected 2023 and 2024 minutes had broker tick-price mismatches and tester-generated ticks; see `docs/PROJECT_STATUS.md`.

## Entry research

Round-two entry hypotheses use a fixed, interpretable ten-item candidate list (five BUY, five SELL) defined in `python/round2_entry_research.py`. Definitions use only causal signal-time fields and were frozen from TRAIN before the one validation evaluation. The purged TRAIN has 12,243 signals, of which 12,228 have both virtual outcomes complete; DISCOVERY_VALIDATION has 4,077 signals, of which 4,070 are complete pairs. All ten validation classifications are `INCONCLUSIVE`.

| Frozen hypothesis | n | Mean FOLLOW−INVERT | 99.5% week-cluster CI, Bonferroni | Positive months | Result |
|---|---:|---:|---:|---:|---|
| BUY, HA aligned | 865 | −1.04 | [−35.29, 32.55] | 50.0% | INCONCLUSIVE |
| BUY, relative volume ≥ 1 | 1,008 | −10.37 | [−50.15, 29.63] | 50.0% | INCONCLUSIVE |
| SELL, HA aligned | 968 | +14.55 | [−27.24, 57.35] | 62.5% | INCONCLUSIVE |
| SELL, relative volume ≥ 1 | 817 | +8.24 | [−38.82, 52.21] | 50.0% | INCONCLUSIVE |
| Other six interaction hypotheses | 116–393 | mixed | all cross zero | 37.5–75.0% | INCONCLUSIVE; below 500 support |

Family-wise 99.5% week-cluster bootstrap intervals and the six-month/70%-positive-month stability gate were specified before validation as stricter family promotion rules than the individual hypothesis records' nominal 95% failure criterion. Both intervals are reported; no feature combination survives either. The TRAIN-only interaction tables in `outputs/entry_research_round2/train_report/interactions.csv` are descriptive; for example, BUY with bullish HA and relative volume ≥1 had n=1,238 and mean paired advantage +5.25, but that two-condition variant had only n=393 and validation mean −9.63 (INCONCLUSIVE). TRAIN associations are not a basis for deployment.

Results are local under `outputs/entry_research_round2/` and are not published with raw datasets. The run manifest contains hashes for all ten frozen definitions and the single validation parquet. Validation results are exploratory, account for clustered uncertainty, and do not authorize a candidate unless all predeclared promotion criteria pass.

## Intra-trade research: blocked on source data

The current 329-column event rows have entry-time features and final outcome summaries only. They contain no intervening tick/bar paths. Terminal `MFE`, `MAE`, exit price/time/reason, and PnL cannot reconstruct when conditions changed and are future information; using them as snapshots would leak labels. A read-only Python API probe of the local MT5 terminal produced no usable response. Consequently, no intra-trade dataset, reversal finding, or policy simulation is reported. `docs/INTRATRADE_RESEARCH_PROTOCOL.md` specifies the additional source data required. The next actionable step is an instrumented Strategy Tester export of open-trade path states on the same real-tick configuration, with `LIVE_TRADING=false`, followed by a separately versioned build.

## Checkpoint

- `ROUND2_A` entry discovery/validation: COMPLETE; all ten hypotheses INCONCLUSIVE.
- `ROUND2_B` snapshots: BLOCKED until tick/bar path data is exported.
- `ROUND2_C` intra-trade hypotheses: NOT STARTED; no valid snapshot dataset exists.
- `ROUND2_D` validation: entry hypotheses evaluated once; intra-trade validation not run.
- `ROUND2_E` ML: four entry models evaluated on 4,070 validation pairs; intra-trade models require snapshots and are not fit.
- `ROUND2_F` candidate decision: NO CANDIDATE. Do not open FINAL_TEST or enable Demo.

## Entry ML comparison

Four classifiers used 49 predeclared causal inputs plus 10 fixed interactions and were trained on 12,228 complete TRAIN pairs. Calibration used a chronological `TimeSeriesSplit` inside TRAIN; prediction threshold remained 0.5. On 4,070 DISCOVERY_VALIDATION pairs, AUC was 0.491 (logistic), 0.494 (calibrated logistic), 0.498 (random forest), and 0.482 (histogram gradient boosting). Model-switch mean PnL was −12.68, −11.24, −9.95, and −10.29 price units respectively; FOLLOW-always was −3.83 and INVERT-always −8.50 on the same rows. All model policies underperformed FOLLOW-always. These models are not candidates. Their walk-forward evaluation is not complete; no intra-trade model was fitted.

## Verification

The full unittest suite passes: 41 tests run, 32 passed, and 9 native C++ tests were skipped because `g++` is unavailable. `python -m compileall -q python tests` and `git diff --check` pass. `python/pipeline.py intratrade-status` writes a local blocker manifest and exits 2 when the required path-state export is absent. Historical 2023/2024 tick mismatch caveats remain unchanged.
