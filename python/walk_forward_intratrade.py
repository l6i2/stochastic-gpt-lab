"""Expanding temporal walk-forward over TRAIN then DISCOVERY_VALIDATION only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

try:
    from .parquet_io import read_parquet
    from .train_event_source import assert_train_only_source_path
    from .train_intratrade_models import FEATURES, _performance, _purge_training_groups
except ImportError:
    from parquet_io import read_parquet
    from train_event_source import assert_train_only_source_path
    from train_intratrade_models import FEATURES, _performance, _purge_training_groups

ROOT = Path(__file__).resolve().parents[1]


def walk_forward(train_path: Path, validation_path: Path, targets_path: Path, out: Path) -> dict:
    for path in (train_path, validation_path, targets_path, out):
        assert_train_only_source_path(path)
    targets = pd.read_csv(targets_path)
    train = read_parquet(train_path).merge(targets, on=["snapshot_id", "signal_id", "virtual_mode", "snapshot_bar"],
                                           how="inner", validate="one_to_one")
    validation = read_parquet(validation_path).merge(targets,
        on=["snapshot_id", "signal_id", "virtual_mode", "snapshot_bar"], how="inner", validate="one_to_one")
    if set(train.signal_id) & set(validation.signal_id):
        raise ValueError("Split contamination between TRAIN and VALIDATION")
    features = [f for f in FEATURES if f in train and f in validation]
    train = train[pd.to_numeric(train.reversal_event, errors="coerce").notna()].copy()
    validation = validation[pd.to_numeric(validation.reversal_event, errors="coerce").notna()].copy()
    signals = (validation[["signal_id", "signal_time_msc"]].drop_duplicates("signal_id")
               .sort_values(["signal_time_msc", "signal_id"], kind="stable").reset_index(drop=True))
    if len(signals) < 6:
        raise ValueError("Not enough validation signals for temporal folds")
    splitter = TimeSeriesSplit(n_splits=4)
    fold_results = []
    for fold_id, (train_ix, test_ix) in enumerate(splitter.split(signals), 1):
        fold_train_ids = set(signals.iloc[train_ix].signal_id.astype(str))
        test_ids = set(signals.iloc[test_ix].signal_id.astype(str))
        fold_train = pd.concat([train, validation[validation.signal_id.astype(str).isin(fold_train_ids)]],
                               ignore_index=True)
        fold_test = validation[validation.signal_id.astype(str).isin(test_ids)].copy()
        before_purge = len(fold_train)
        fold_train = _purge_training_groups(fold_train, int(fold_test.signal_time_msc.min()))
        y_train = pd.to_numeric(fold_train.reversal_event).astype(int)
        y_test = pd.to_numeric(fold_test.reversal_event).astype(int)
        if y_train.nunique() < 2 or y_test.nunique() < 2:
            result = {"fold": fold_id, "status": "INSUFFICIENT_CLASS_VARIATION", "train_n": len(fold_train),
                      "validation_n": len(fold_test), "final_test_accessed": False}
        else:
            model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                LogisticRegression(max_iter=1000, class_weight="balanced", random_state=1729))
            model.fit(fold_train[features], y_train)
            probability = model.predict_proba(fold_test[features])[:, 1]
            scored = fold_test.copy(); scored["prob_reversal"] = probability
            bar3 = scored[scored.snapshot_bar.astype(int) == 3].copy()
            current = pd.to_numeric(bar3.current_unrealized_pnl, errors="coerce")
            future = pd.to_numeric(bar3.future_pnl_to_exit, errors="coerce")
            hold = current + future
            candidate = current.where(bar3.prob_reversal >= 0.7, hold)
            result = {"fold": fold_id, "status": "SCORED", "train_n": len(fold_train),
                      "validation_n": len(fold_test), "train_signals": int(fold_train.signal_id.nunique()),
                      "validation_signals": int(fold_test.signal_id.nunique()),
                      "auc": float(roc_auc_score(y_test, probability)),
                      "brier": float(brier_score_loss(y_test, probability)),
                      "bar3_hold": _performance(hold, bar3.signal_time_msc),
                      "bar3_early_exit_if_reversal_ge_0_7": _performance(candidate, bar3.signal_time_msc),
                      "final_test_accessed": False}
        fold_results.append(result)
        result['purged_training_snapshots'] = before_purge - len(fold_train)
    out.mkdir(parents=True, exist_ok=True)
    result = {"status": "EXPANDING_TRAIN_VALIDATION_WALK_FORWARD", "final_test_accessed": False,
              "random_shuffle": False, "features": features, "threshold": 0.7,
              "reverse_direction": "NOT_SIMULATED_MISSING_ORDERED_POST_SNAPSHOT_QUOTE_PATH",
              "folds": fold_results}
    (out / "walk_forward.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, default=Path("outputs/intratrade/splits/train.parquet"))
    parser.add_argument("--validation", type=Path, default=Path("outputs/intratrade/splits/validation.parquet"))
    parser.add_argument("--targets", type=Path, default=Path("outputs/intratrade/master/intratrade_targets.csv"))
    parser.add_argument("--output", type=Path, default=Path("outputs/intratrade/walk_forward"))
    args = parser.parse_args()
    def absolute(path: Path) -> Path:
        return path if path.is_absolute() else ROOT / path
    result = walk_forward(*(absolute(p) for p in (args.train, args.validation, args.targets, args.output)))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
