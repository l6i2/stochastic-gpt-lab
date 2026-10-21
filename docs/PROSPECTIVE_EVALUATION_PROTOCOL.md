# Prospective evaluation protocol

**Status:** preregistered, sealed, and gated. Written before this task inspected any cohort contents.
**Cohort:** `us30cash_m5_future_20261019_v1`; fixed start `2026-10-19T00:00:00Z`.
**Authority:** this protocol defines eligibility and a single evaluation; it does not authorize scoring.

## 1. Separation and permitted health checks

The future cohort is physically separate from legacy TRAIN, blocked Discovery Validation, and FINAL_TEST. Its raw bars/ticks may be used only for integrity, capture coverage, timestamps, hashes, deterministic signal-support counts, session/regime coverage, and data-quality checks before explicit evaluation authorization. Health output must not contain or calculate PnL, win rate, profit factor, MFE/MAE outcomes, candidate-vs-baseline differences, rankings, or threshold comparisons. Signal BUY/SELL counts are eligibility metadata only.

No cohort-derived value may create hypotheses, alter a candidate, choose thresholds, rank candidates, or select a model. No missing day may be backfilled before the fixed start. Once the maturity audit is generated, its raw-input hashes and report hash are frozen; a changed cohort manifest requires a new health report and invalidates a prior maturity result.

## 2. Exact maturity gate

Every requirement in [`FUTURE_VALIDATION_READINESS_RULE.md`](FUTURE_VALIDATION_READINESS_RULE.md) is conjunctive; the stricter outcome applies if another document adds a condition:

- At least **300 unique signals** total, with **120 BUY** and **120 SELL** minimums.
- At least **16 complete UTC weeks** spanning **4 complete UTC calendar months** after the fixed start.
- At least **30 signals** in each Asia, London, and New_York session; each session must include **10 BUY and 10 SELL**.
- At least **25 signals** in each predeclared uptrend, downtrend, range, and transition state; at least **30** in each low, medium, and high volatility state. The state algorithms, lookbacks, thresholds, missing-data policy, and source-code hash must be present in a frozen candidate-independent maturity specification before cohort state counts are calculated. The candidate package must independently confirm that it uses the same state definitions before outcome evaluation.
- Immutable collector manifest, complete previous-manifest hash chain, every raw segment SHA-256, exact start/end bounds, strictly ordered UTC timestamps, valid bid/ask (`0 < bid <= ask`), valid OHLC, and no duplicate UTC-day segment.
- All captured broker-open sessions accounted for against a separately frozen XM `US30Cash` UTC session/holiday calendar. Missing expected M5 bars must be **<1%** after scheduled closures are excluded; no unexplained gap may exceed **60 consecutive minutes** during an open session. If the authoritative calendar cannot be obtained or verified, maturity is `NOT_MATURE`.
- Tick-quality acceptance is **100%** for required timestamp and finite positive bid/ask fields; no crossed quotes. Duplicate timestamps are counted and reported, never silently removed. Segment row counts must exactly match the manifest.
- Deterministic signal metadata must reproduce the frozen base trigger on closed M5 bars only: Stochastic K=5, D=3, slowing=3, MAIN_K; BUY previous `<=20` then current `>20`; SELL previous `>=80` then current `<80`. No entry replay, labels, outcomes, or PnL are computed for the health report.
- Any causal event/features needed for evaluation must pass the frozen feature whitelist, `feature_max_time <= decision_time`, target/feature separation, and independent synthetic replay-parity tests before maturity can pass.
- Candidate status must already be `FROZEN` with immutable candidate, policy, feature, and code hashes, and documented TRAIN walk-forward evidence. This is an eligibility check only; it does not read cohort performance.

The existing readiness rule and its SHA-256 sidecar remain authoritative and unchanged. A failed condition means `NOT_MATURE`; no threshold may be lowered, no legacy observations may be substituted, and no cohort boundary may be moved.

## 3. Frozen single evaluation

Evaluation requires all of the following, checked before reading any outcome row: maturity report `PASS`; independently audited causal evaluation table; a hash-pinned candidate with status `FROZEN`; exact candidate, cohort manifest, evaluation table, evaluator source, and protocol hashes; and a one-use authorization artifact explicitly supplied after the user sees the maturity report. The artifact binds those hashes and contains a fresh 256-bit nonce. The evaluator atomically consumes the candidate/cohort authorization key before opening the outcome table. A consumed attempt cannot be retried, including after a crash or malformed table. There is no automated authorization when maturity first becomes true.

The sole policy is the frozen candidate. No filtering, threshold adjustment, model refit, side reassignment, latency selection, or second candidate comparison is allowed. Include every eligible signal, including losses, censored exits, and missing outcomes as required by the frozen policy. Any missing/invalid outcome causes the evaluation to fail closed rather than dropping that signal.

### Baselines and reported metrics

Compare the candidate on the same signals against both `FOLLOW_ALWAYS` and `INVERT_ALWAYS`; do not pick a baseline after seeing results. Report paired mean and median outcome delta versus each baseline overall and separately for BUY and SELL, 95% signal-cluster bootstrap confidence intervals for those paired means using the frozen evaluator seed and resample count, win rate, profit factor, fixed-size equity drawdown, support/censoring, and all frozen quality diagnostics. The report must include the immutable inputs and evaluator/protocol hashes. No post-result charts or subgroup rankings may alter status.

### Status rule

- **PASS:** overall, BUY, and SELL candidate-minus-FOLLOW and candidate-minus-INVERT mean deltas are positive, and each corresponding 95% lower confidence bound is above zero; fixed-size drawdown is no more than 20% worse than FOLLOW_ALWAYS; all maturity, completeness, causality, and integrity checks remain PASS.
- **FAIL:** a predefined integrity/causality gate fails, drawdown exceeds the fixed limit, or any primary paired mean-delta 95% upper confidence bound is at or below zero.
- **INCONCLUSIVE:** the evaluation is valid but neither every PASS condition nor any FAIL condition is met (including intervals spanning zero, or insufficient non-censored outcomes).

The status is computed once. `INCONCLUSIVE` is terminal for this candidate/cohort pair. Do not retune or retry against the same cohort; any later candidate requires a separately preregistered, untouched cohort and a new authorization. A PASS is evidence for review only; it does not enable DEMO or LIVE.

## 4. Authorization and safety states

When all maturity conditions pass, automation changes status only to `WAITING_PROSPECTIVE_EVALUATION_AUTHORIZATION` and stops. It must not create the authorization artifact or invoke evaluation. `FINAL_TEST` remains locked and is never a substitute. DEMO stays disabled until prospective PASS, candidate freeze, successful disabled shadow run, and separate explicit user authorization. `LIVE_TRADING=false` is invariant.

```text
DISCOVERY_VALIDATION=BLOCKED
FUTURE_COHORT_SCORING=NOT_AUTHORIZED
FINAL_TEST=LOCKED
DEMO=DISABLED
LIVE_TRADING=false
```
