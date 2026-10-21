# Prospective data drift monitor

**Status:** feature/coverage-only implementation prepared and fixture-tested; no real-cohort performance evaluation. `LIVE_TRADING=false`.

The monitor accepts only an explicit feature whitelist and fixed numeric bin edges from a separately hashed baseline summary. It reports missingness rate, population-stability index (PSI), spread distribution, session coverage, causal regime/volatility coverage, shadow decision-latency distribution, and capture-gap/quality changes. Default alerts are PSI `>0.25` and absolute missingness-rate change `>0.10`; both are descriptive data-quality alerts, never policy or threshold updates.

The reference summary must be frozen before comparing a future cohort and must contain distribution counts only. Candidate outcomes, labels, PnL, win rate, profit factor, MFE/MAE, exit results, and candidate ranking are prohibited inputs. A missing feature, changed bin definition, malformed quality report, or protected column causes a fail-closed error. Reports state `candidate_scored=false` and `threshold_tuning=false`.

Implementation: `python/drift_monitor.py`; synthetic tests: `tests/test_drift_monitor.py`. No baseline was generated from FUTURE_VALIDATION_COHORT, and no real-data drift comparison has run.
