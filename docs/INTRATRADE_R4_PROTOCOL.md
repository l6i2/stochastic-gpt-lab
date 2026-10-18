# Intra-trade round 4 preregistration

Frozen 2026-10-18 before replay. Four not-yet-tested dynamic families are
specified in the hashed hypothesis records: adverse EMA alignment, adverse
structure break, a fixed 50-bar loss stop, and realized-volatility contraction
while profitable. No R1/R2/R3 definition is reused or retuned.

Use quality-v1 TRAIN only, four expanding chronological purged folds
(`initial=4,000`, `step=2,000`), causal every-bar snapshots, and the validated
ordered quote paths. One first-trigger exit applies only to FOLLOW; INVERT stays
HOLD. Report BUY and SELL separately and compare with FOLLOW HOLD and INVERT
HOLD. Execute at 0/250/500 ms with 250 ms primary and frozen TP=240, SL=180,
TIME_EXIT=100 precedence. Never read target fields as features.

Pass all gates to reach one Discovery Validation score: at least 500 triggers
overall, 200 per side, and 100 per side per fold; at least 5% prevalence overall
and by side; positive paired policy-minus-HOLD changes in at least 70% of folds
overall and on each side; no fold above 50% of positive effect; positive result
at each latency with sensitivity within `max(1.0, 25% of |250 ms effect|)`;
drawdown proxy no more than 20% worse than FOLLOW HOLD; positive supported
effects in at least two source blocks and two NY sessions with at least 100
triggers each, with no block/session contributing over 50%. No threshold
search, random shuffle, or rule alteration is permitted.

If more than one passes, select the highest mean purged walk-forward portfolio
change at 250 ms; ties resolve by ascending ID. If none passes, do not open
Validation. FINAL_TEST stays locked; Demo is disabled; `LIVE_TRADING=false`.
