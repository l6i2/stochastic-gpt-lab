# Intra-trade round 3 preregistration

Frozen 2026-10-18 after round 2 failed all promotion gates. This round tests four
new families only: MAE recovery, proximity to the frozen TP, low relative
volume after favorable excursion, and adverse crossing of causal 60-minute
POC. None reuses the rejected HA-opposite, Stochastic K/D-opposite, HA/volume
reversal, ATR adverse-bar, VAH/VAL edge, or 15:30 session-exit definitions.
Definitions and values are immutable in the four SHA-256-pinned hypothesis
records `HYP-20261018-R3-001` through `-004`.

## Evaluation

Use the same quality-v1 TRAIN-only every-bar snapshots and previously verified
quote paths. Four expanding chronological folds use the existing purged
builder (`initial=4,000`, `step=2,000`). One first-trigger exit per FOLLOW
position; INVERT stays HOLD. Evaluate BUY and SELL separately; compare against
FOLLOW HOLD and INVERT HOLD. Execute at 0/250/500 ms, with 250 ms primary and
existing TP=240, SL=180, TIME_EXIT=100 precedence. No Validation or FINAL_TEST
features or labels are read.

## Fixed gates

1. At least 500 triggered positions overall, 200 per side, 100 per side in
   every scored fold, and at least 5% trigger prevalence overall and by side.
2. Paired policy-minus-HOLD mean change is positive in at least 70% of folds
   overall and for each side; no fold contributes over 50% of positive change.
3. Mean change is positive at all three latencies; sensitivity must be within
   `max(1.0 price unit, 25% of |250 ms effect|)` of the primary result.
4. The candidate FOLLOW portfolio drawdown proxy may not worsen by more than
   20% relative to FOLLOW HOLD; retain all losses and censored coverage.
5. At least two eligible source blocks and two NY sessions with at least 100
   triggered trades each must have positive mean change; no one block or
   session may contribute more than 50% of positive change.
6. No threshold search, random shuffle, hypothesis expansion, or rule change.

If a single hypothesis passes all gates, freeze it and its evidence before one
Discovery Validation score. If none passes, reject/inconclude all four and
start any later round with new preregistered families. Data-quality caveat
`PASS_INHERITED_VALIDATION` remains explicit; this derivative has not received
a separate aggregate row-by-row validator pass. FINAL_TEST stays locked,
DEMO is disabled, and `LIVE_TRADING=false`.
