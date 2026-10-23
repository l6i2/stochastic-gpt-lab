# Prospective data drift monitor

> Latest evidence: [session probe captured — 2026-10-23](XM_SESSION_CAPTURE_20261023.md). Probe execution is complete and hash-pinned. Current snapshot shows UTC+02:00 with weekday-dependent sessions; DST/holiday reconciliation is still pending. Calendar remains unverified; no scoring or orders.

> Latest operational check: [XM reopened — 2026-10-23](XM_REOPEN_CHECK_20261023.md). XM is connected in DEMO, US30Cash is available, and collector runtime is READY. Session-probe execution and calendar evidence remain pending; no scoring or orders.

> Current operational checkpoint: [2026-10-22 continuation audit](CONTINUATION_AUDIT_20261022.md). It supersedes older operational snapshots: capture data healthy, XM runtime unavailable, cohort not mature; calendar/causal/drift gates remain unresolved. No scoring or orders.

**Status:** `PREPARED/NOT_READY`; implementation is fixture-tested, but no baseline is fitted and no real-cohort drift comparison has run. `LIVE_TRADING=false`.

The monitor accepts only an explicit feature whitelist and fixed numeric bin edges from a separately hashed baseline summary. It reports missingness rate, population-stability index (PSI), spread distribution, session coverage, causal regime/volatility coverage, shadow decision-latency distribution, and capture-gap/quality changes. Default alerts are PSI `>0.25` and absolute missingness-rate change `>0.10`; both are descriptive data-quality alerts, never policy or threshold updates.

The reference summary must be frozen before comparing a future cohort and must contain distribution counts only. Candidate outcomes, labels, PnL, win rate, profit factor, MFE/MAE, exit results, and candidate ranking are prohibited inputs. A missing feature, changed bin definition, malformed quality report, or protected column causes a fail-closed error. Reports state `candidate_scored=false` and `threshold_tuning=false`.

Implementation: `python/drift_monitor.py`; synthetic tests: `tests/test_drift_monitor.py`. No baseline was generated from FUTURE_VALIDATION_COHORT, and no real-data drift comparison has run. The current whitelist (`stoch_main_k`, `atr14_over_previous_288_bar_median`, relative volume, Heikin Ashi and Volume Profile features) has not been proven schema-equivalent to any identically computed, allowed future-cohort feature stream. The health report currently emits only fixed eligibility/coverage metadata and is not such a stream. Do not fit the baseline or compare distributions until a TRAIN-only baseline builder and a causally identical, separately governed feature-only future stream are implemented and tested. This state is intentionally NOT_READY; it does not justify using cohort data for hypothesis generation or scoring.
