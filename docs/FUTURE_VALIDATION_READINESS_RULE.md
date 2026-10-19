# Future validation cohort maturity rule

**Frozen before cohort outcomes are inspected.** This is an eligibility gate,
not authorization to evaluate. `evaluation_authorized` remains false until the
user explicitly authorizes a single evaluation after a frozen candidate is
present. No legacy Discovery Validation or FINAL_TEST data may be opened.

The cohort may be declared mature only when every condition below passes on
the immutable raw cohort and a separately versioned, causally derived event
table:

- At least 300 unique Stochastic signals total, with at least 120 BUY and 120
  SELL.
- At least 16 complete UTC calendar weeks spanning at least four complete
  calendar months after the fixed cohort start.
- At least 30 signals in each of Asia, London, and New_York sessions; each
  session must contain at least 10 BUY and 10 SELL signals.
- At least 25 signals in each of four predeclared causal market states
  (uptrend, downtrend, range, transition), and at least 30 in each of the
  predeclared low/medium/high volatility states. State definitions and cut
  points must be frozen in the candidate package, using only prior TRAIN data.
- Raw tick and bar files, daily manifests, hash chain, timestamps, source
  identity, and UTC bounds validate. No duplicate signal IDs, overlapping
  capture windows, pre-start observations, invalid quotes, or unexplained
  missing market sessions are allowed.
- Missing expected M5 bars must be below 1% of broker-session bars after
  scheduled closures are excluded using a frozen calendar. No single missing
  interval may exceed 60 consecutive minutes during a broker-open session.
- Event/snapshot features pass the causal whitelist, `feature_max_time <=
  decision_time`, and independent replay parity checks. Targets remain
  physically separate from features.
- The candidate and evaluator inputs have immutable SHA-256 manifests; the
  candidate passed its predeclared TRAIN walk-forward gates before the cohort
  is considered for scoring.

If any count, coverage, quality, or provenance condition fails, status is
`NOT_MATURE`; do not lower thresholds, merge another cohort, backfill before
the start, or substitute a legacy split. Maturity must be determined before
computing candidate outcome metrics. The evaluator must refuse immature or
unauthorized cohorts.

```text
COHORT_MATURE=false (until an independent audit proves all gates)
EVALUATION_AUTHORIZED=false
DISCOVERY_VALIDATION=BLOCKED
FINAL_TEST=LOCKED
DEMO=DISABLED
LIVE_TRADING=false
```
