# Quality-v1 entry-direction experiment — 2026-10-16

## Scope and provenance

This was one preregistered entry-direction study, not an intra-trade exit
policy evaluation. It used 11,714 eligible TRAIN events and 4,077
DISCOVERY_VALIDATION events from the quality-v1 derivative. All had complete
paired FOLLOW/INVERT labels; no row was dropped for being a loss. The event
file retains EA schema 1.1 and is derived from four accepted schema 3.0 history
blocks. The model checked `feature_max_time_msc <= signal_time_msc`, fixed
strategy parameters, side mapping, split membership and label horizons before
fitting.

The feature whitelist, ten fixed interactions, three classifier families,
random seed 20261013, target (`directional_advantage > 0`), and 0.5 policy
threshold were fixed before the one Validation score. Walk-forward used four
expanding, purged folds drawn only from TRAIN. Baselines were FOLLOW-always and
INVERT-always. There was no hyperparameter search, threshold tuning, candidate
selection, FINAL_TEST access, Demo execution, or live trading.

## Results

| Policy | Validation accuracy | Balanced accuracy | ROC AUC | Mean PnL | Profit factor |
|---|---:|---:|---:|---:|---:|
| FOLLOW always | — | — | — | -3.81 | 0.946 |
| INVERT always | — | — | — | -8.52 | 0.883 |
| Logistic regression | 0.490 | 0.490 | 0.488 | -14.13 | 0.813 |
| Random forest | 0.501 | 0.501 | 0.501 | -7.86 | 0.891 |
| Hist. gradient boosting | 0.498 | 0.499 | 0.491 | -9.90 | 0.864 |

None of the fixed models beat FOLLOW-always on mean PnL, win rate, profit
factor, or drawdown proxy. Discrimination remained near chance. The four
TRAIN-only folds were unstable: each model's ROC AUC ranged from roughly 0.47
to 0.54, with changing PnL direction across periods. The entry-direction
hypothesis is **REJECTED for promotion**; these results do not support a
candidate.

The machine-readable metrics, four-fold results, frozen feature list,
serialized models, and hashes are local under
`outputs/models/quality_directional_v1/` (ignored from Git because they contain
large binary artifacts). The committed trainer is
`python/train_quality_direction_model.py`. The study does not answer whether
a dynamic intra-trade policy can improve decisions using the full every-bar
quote trajectory; that bounded replay still needs an end-to-end dataset runner
and a frozen execution-latency assumption before any policy Validation.

FINAL_TEST remains locked. `LIVE_TRADING=false`; no real or Demo execution was
performed.
