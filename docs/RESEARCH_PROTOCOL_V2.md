# Research Protocol V2 — preregistered TRAIN-only work

**Status:** frozen before any V2 result is computed. This protocol does not
authorize Discovery Validation, FUTURE_VALIDATION_COHORT scoring, FINAL_TEST,
or DEMO execution. The existing R2–R4 rules stay rejected and are not inputs
to V2 selection.

## Scope and data boundary

V2 may read only the frozen schema-3 quality-v1 TRAIN snapshots, their causal
features, and the ordered quote tape needed for paired FOLLOW/INVERT replay.
Each entrypoint must reject paths containing `validation`, `final_test`, or
`future_validation_cohort` before opening them. For shared source files, rows
must first be restricted to the fixed TRAIN signal-ID manifest; no outcome,
fold edge, quantile, ranking, or threshold may use non-TRAIN IDs. The
potential-isolation incident remains open as a separate blocker for legacy
Discovery Validation.

The basic unit is a Stochastic signal, grouped with its virtual mode and full
label horizon. BUY and SELL receive separate results. Features must be known
at or before the corresponding signal or state time. Targets, PnL, exit fields,
future extrema, and future timestamps are never model features. Losses,
censored observations, and missing values remain in their original
categories.

## Fixed family and search budget

V2 permits one preregistered family with at most **two policy variants**:
an entry quote-friction regime router fitted separately for BUY and SELL.
The input is the signal-time ratio `spread / ATR`, both already available in
the frozen causal schema. In each expanding-fold training portion only, the
router computes the 1/3 and 2/3 empirical cut points; those cut points are
then fixed for the next evaluation fold. Within each side and regime, it
chooses FOLLOW or INVERT by higher mean paired training PnL; ties and cells
with fewer than 100 distinct training signals default to FOLLOW. No state or
outcome from an evaluation fold may update the router. The fixed policy
algorithm, rather than individual bins or thresholds, is the hypothesis.

This family addresses entry execution friction and side asymmetry. It does
not reuse the R2–R4 intra-trade triggers (adverse EMA/bar, MAE recovery,
fixed time loss stop, or volatility contraction). It changes neither the
Stochastic signal nor TP/SL/time-exit values. If the ratio or ATR is missing,
the policy defaults to FOLLOW and reports missingness; it does not impute from
future rows.

No additional rules, interactions, model classes, thresholds, or policy
variants may be added after this preregistration. If the required source
columns, ordered quotes, or purged fold metadata are unavailable, V2 is
`NOT_RUN`; do not substitute another feature family.

## Evaluation design

- Four expanding chronological TRAIN folds, using the already frozen fold
  boundaries and signal grouping; purge any training label that reaches the
  next fold's first evaluation signal.
- Primary quote-arrival latency: 250 ms. Required sensitivity: 0 ms and
  500 ms, with the same strictly post-arrival quote fill rule.
- Evaluate each side independently and jointly against FOLLOW-always,
  INVERT-always, and the pre-registered router. Keep the identical eligible
  signal set for every baseline.
- Report sample size, mean and median paired PnL difference, win rate, profit
  factor, drawdown proxy, fold effect, source-block effect, session effect,
  and regime-cell support. Use signal-clustered uncertainty intervals; do
  not treat snapshots from one signal as independent observations.
- Threshold robustness is the fixed 25/75-quantile router sensitivity, fitted
  on each fold's training portion only. It is diagnostic and cannot replace or
  rescue the primary 1/3–2/3 router.

## Gates fixed before execution

A variant survives TRAIN only if every applicable condition passes:

1. At least 200 distinct evaluation signals overall and at least 80 per side
   across supported folds; each side must have at least three evaluable folds.
2. At least 70% of eligible folds are positive for the same baseline-relative
   effect, separately for each side; no single fold contributes more than 50%
   of the positive cumulative effect.
3. Positive support appears in at least two source blocks and two sessions;
   no one block or session contributes over 50% of positive effect. A side
   with inadequate cell support is `INCONCLUSIVE`, never a pass.
4. Both sides must meet the sample and sign gates. A BUY-only or SELL-only
   result cannot be promoted as a universal policy.
5. At 0/250/500 ms, the effect sign must remain stable and its magnitude must
   not vary by more than 50% of the primary absolute effect. A zero primary
   effect fails.
6. The fixed 25/75 sensitivity must preserve the primary effect sign on both
   sides and at least 70% fold direction. It cannot be used as the selected
   policy.
7. The policy drawdown proxy must not worsen by more than 20% versus the
   better fixed baseline on identical rows. Report the limitation that this
   is not account-level sizing or capital drawdown.

Failure of any gate means `REJECTED`; inadequate support means
`INCONCLUSIVE`. No thresholds are adjusted and no failed variant is recycled.
No Discovery Validation or future-cohort evaluation follows automatically.

## Candidate and holdout rules

Only a variant that passes every TRAIN gate can become a provisional frozen
candidate, with source hashes, code hash, feature/decision contract, fold
metrics, baselines, latency, and failure conditions. If neither variant
passes, record `NO_CREDIBLE_CANDIDATE` for this family and stop rather than
spawning another family. Candidate creation alone does not authorize a
holdout. The prospective-cohort maturity rule and explicit human authorization
are required before any future scoring; FINAL_TEST remains independently
locked.

## Safety invariants

```text
DISCOVERY_VALIDATION=BLOCKED
FUTURE_VALIDATION_COHORT evaluation_authorized=false
FINAL_TEST=LOCKED
DEMO=DISABLED
LIVE_TRADING=false
```

Protocol SHA-256 is published in `docs/RESEARCH_PROTOCOL_V2.md.sha256`.
