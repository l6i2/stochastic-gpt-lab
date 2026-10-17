# Dynamic EXIT TRAIN discovery — 2026-10-17

## Frozen simulation

This exploration read quality-v1 TRAIN only: 11,714 signals, 1,810,478 causal
open-trade snapshots, and 23,428 ordered FOLLOW/INVERT quote paths. It replayed
the first occurrence of three fixed rules: Heikin Ashi turns opposite the
virtual position; Stochastic K is on the opposite side of D; or both conditions
hold. No target columns were used as features. Each decision's feature and mark
times were checked against the cutoff, the arrival quote was matched to the
ordered tape, and execution used the first quote strictly after arrival plus
latency. Existing TP=240, SL=180, and TIME_EXIT=100 take precedence. Latencies
were 0, 250, and 500 ms, with 250 ms declared primary.

The local run is `outputs/bar_controller/research/train_exit_exploration_v2.json`;
per-trade outcomes and purge metadata are in the adjacent
`train_exit_exploration_v2_trades.csv`. Both are hash-pinned. These large
derived results remain local. The source quote tapes were already verified by
the immediately preceding TRAIN HOLD replay and matched its accepted manifest
hashes.

## TRAIN-only selection and walk-forward

The predeclared selection target is FOLLOW-mode virtual SELL positions. At
250 ms, HA-opposite had the largest pooled TRAIN mean paired change among the
three fixed rules: +5.508 price units over 6,258 such paths. Its sensitivity
results were +5.498 at 0 ms and +5.483 at 500 ms. It triggered on 6,182 paths;
6,181 discretionary fills occurred. This pooled result is discovery evidence
only and is not a candidate claim.

The expanding, purged walk-forward reselected among the same rules within each
prior TRAIN prefix and evaluated on the next untouched TRAIN fold:

| Fold | Rule selected on earlier TRAIN | FOLLOW-SELL mean change | Candidate FOLLOW portfolio change vs FOLLOW-always |
|---|---|---:|---:|
| 1 | HA and Stochastic | +4.131 | +2.262 |
| 2 | HA and Stochastic | -1.504 | -0.807 |
| 3 | Stochastic K/D | -9.130 | -4.753 |
| 4 | Stochastic K/D | +9.497 | +5.142 |

Only 2 of 4 folds were positive, and the largest fold contributed 69.7% of
positive target-side change. The predefined walk-forward gate requires at least
70% positive folds and no fold above 50% of aggregate positive change. It
failed. **No rule proceeds to Discovery Validation; no candidate exists.**

The local walk-forward report is
`outputs/bar_controller/research/train_exit_walkforward.json`. The entry model
experiment was independently rejected for promotion in
`docs/QUALITY_DIRECTION_MODEL_REPORT.md`. No Validation rows were read by the
dynamic replay, no FINAL_TEST was accessed, and no orders were placed.

The one-sided FOLLOW-SELL hypothesis is archived as
`research/hypotheses/HYP-20261017-DYN-001.json`, SHA-256
`92ba1f88a7a826c41b04275fadeefa334eeee4d8d92d4eabbe4bd704c5f1118f`, with
status `REJECTED_WALK_FORWARD_PRE_VALIDATION`.

`LIVE_TRADING=false`; DEMO execution remains disabled.
