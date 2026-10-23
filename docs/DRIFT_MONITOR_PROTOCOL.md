# Prospective data drift monitor

## Authoritative operational checkpoint — 2026-10-23

[Current addendum and evidence](PROSPECTIVE_OPERATIONAL_ADDENDUM_20261023.md): `SESSION_CALENDAR=PASS_WITH_RUNTIME_GUARD` for operational containment; historical UTC calendar remains unverified. Guard READY, DST PARTIAL, holidays UNKNOWN. Causal audit FAIL (frozen metadata/native-trigger non-equivalence), manifest chain PARTIAL, drift NOT_READY. Collector active/HEALTHY, cohort NOT_MATURE, evaluator READY_BUT_GATED. DEMO executor and shadow READY_BUT_DISABLED; no orders. FINAL_TEST LOCKED; DEMO DISABLED; LIVE_TRADING=false. Full suite: 190 tests, 9 native skips. NEXT_STATE=HARD_BLOCKER.

All operational snapshots below are historical and superseded by the linked addendum; sealed scientific protocols remain unchanged.




**Status:** `PREPARED/NOT_READY`; implementation is fixture-tested, but no baseline is fitted and no real-cohort drift comparison has run. `LIVE_TRADING=false`.

The monitor accepts only an explicit feature whitelist and fixed numeric bin edges from a separately hashed baseline summary. It reports missingness rate, population-stability index (PSI), spread distribution, session coverage, causal regime/volatility coverage, shadow decision-latency distribution, and capture-gap/quality changes. Default alerts are PSI `>0.25` and absolute missingness-rate change `>0.10`; both are descriptive data-quality alerts, never policy or threshold updates.

The reference summary must be frozen before comparing a future cohort and must contain distribution counts only. Candidate outcomes, labels, PnL, win rate, profit factor, MFE/MAE, exit results, and candidate ranking are prohibited inputs. A missing feature, changed bin definition, malformed quality report, or protected column causes a fail-closed error. Reports state `candidate_scored=false` and `threshold_tuning=false`.

Implementation: `python/drift_monitor.py`; synthetic tests: `tests/test_drift_monitor.py`. No baseline was generated from FUTURE_VALIDATION_COHORT, and no real-data drift comparison has run. The current whitelist (`stoch_main_k`, `atr14_over_previous_288_bar_median`, relative volume, Heikin Ashi and Volume Profile features) has not been proven schema-equivalent to any identically computed, allowed future-cohort feature stream. The health report currently emits only fixed eligibility/coverage metadata and is not such a stream. Do not fit the baseline or compare distributions until a TRAIN-only baseline builder and a causally identical, separately governed feature-only future stream are implemented and tested. This state is intentionally NOT_READY; it does not justify using cohort data for hypothesis generation or scoring.
