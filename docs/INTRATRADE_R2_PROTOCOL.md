# Intra-trade round 2 preregistration

Frozen 2026-10-18 before inspecting replay outcomes. The eight immutable
hypotheses `HYP-20261018-R2-001` through `-008` use only quality-v1 TRAIN and
the verified ordered quote tapes. The rejected `HYP-20261017-DYN-001` family
(HA opposite, Stochastic K/D opposite, and their conjunction) is excluded.

## Evaluation

Use four expanding, chronological, purged folds with the existing TRAIN split
builder (`initial=4,000`, `step=2,000`). For each hypothesis, replay one fixed
first-trigger exit per FOLLOW position. INVERT paths remain HOLD. Every fold
is compared with the identical FOLLOW HOLD portfolio and with INVERT-always.
Report BUY and SELL separately, all three execution latencies (0/250/500 ms),
source block, and NY session. No threshold, side, or rule is selected using
Discovery Validation.

## Gates to a single Discovery Validation score

A hypothesis must satisfy every gate below on purged TRAIN walk-forward:

1. At least 500 triggered positions overall, at least 200 per side, and at
   least 100 per side in every scored fold. Trigger prevalence must be at least
   5% overall and separately for BUY and SELL.
2. Paired policy-minus-HOLD mean change is positive in at least 70% of scored
   folds overall and for each side. No fold may contribute over 50% of positive
   aggregate change overall or for either side.
3. Mean paired change is positive at all three latencies. Each sensitivity
   result must be within `max(1.0 price unit, 25% of |250 ms effect|)` of the
   250 ms effect.
4. Candidate FOLLOW portfolio maximum drawdown proxy may not be more than 20%
   worse than FOLLOW HOLD. The policy must beat neither baseline by hiding
   losses; all trades remain included.
5. At least two source blocks (2024, 2025, 2026 allowed TRAIN) and two NY
   sessions with at least 100 triggered positions each must show positive mean
   paired change. No single block or session may contribute over 50% of total
   positive paired change.
6. Conditions remain the exact broad thresholds in the hashed hypothesis
   records. No threshold search, random shuffle, outcome filtering, or family
   expansion is permitted in this round.

If multiple hypotheses pass, select exactly one using highest mean paired
walk-forward portfolio change at 250 ms; ties resolve by ascending hypothesis
ID. Freeze its report, data/code hashes, and full rule before one Discovery
Validation evaluation. If none pass, all eight are rejected or inconclusive;
do not open Validation. A later round must use new families and new IDs.

## Safeguards

The source quality derivative is `PASS_INHERITED_VALIDATION`; full row-by-row
aggregate validation was not completed. This caveat carries forward. The
runner must authenticate each trigger arrival against the accepted ordered
quote tape and enforce the protected 2026-03-20 boundary. Snapshot feature and
mark times must be no later than the decision cutoff. Targets are never read
as features. FINAL_TEST, DEMO execution and live trading stay disabled;
`LIVE_TRADING=false`.
