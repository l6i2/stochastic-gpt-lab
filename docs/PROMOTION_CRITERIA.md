# Promotion criteria (defined before any FINAL_TEST access)

No rule or model is promoted because of TRAIN performance alone. A candidate must pass every stage below; failure at a stage leaves it rejected or inconclusive and requires a newly versioned hypothesis for further discovery.

1. Frozen definition, feature list, direction, intended FOLLOW/INVERT behavior, missing-value policy, sample threshold, and failure criteria are hashed before validation.
2. On purged chronological DISCOVERY_VALIDATION, the intended directional effect must match the frozen hypothesis, have at least 500 paired observations overall and at least 100 in each BUY and SELL side, and include a 95% bootstrap interval that does not cross zero. Any side with insufficient support is inconclusive.
3. Walk-forward validation must show the same effect direction in at least 70% of eligible folds, with no single fold contributing more than half of aggregate positive advantage. BUY and SELL are reported separately.
4. The candidate must be compared on the same rows against FOLLOW-always, INVERT-always, and the frozen hypothesis/rule. Report mean/median PnL, win rate, profit factor, sample size, and drawdown proxy. No claim of improvement without an out-of-sample advantage over the relevant baseline and no extreme drawdown deterioration.
5. The result must not depend on a highly precise numeric threshold, one calendar period, future information, selectively omitted losses, or undocumented missing-value handling.
6. A candidate is frozen with code, dataset, feature, training and policy hashes before any FINAL_TEST access. A single explicit user authorization is required to evaluate FINAL_TEST once.

These are conservative project gates, not evidence that the strategy has an edge. If the sample/uncertainty requirements are not met, classify as INCONCLUSIVE rather than relaxing criteria after seeing results.
