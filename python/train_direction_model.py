"""Fit causal directional models on TRAIN and compare on DISCOVERY_VALIDATION only."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, brier_score_loss,
                             confusion_matrix, roc_auc_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import TimeSeriesSplit

from research import FEATURE_COLUMNS, purge_at_boundary, read_dataset, validate, walk_forward

SEED = 20261013
TARGET = "directional_advantage > 0"
ROUND2_INTERACTIONS = {
    "r2_ha_alignment", "r2_volume_x_ha_alignment", "r2_volume_x_ha_transition",
    "r2_stoch_exit_speed_x_volume", "r2_ha_body_expansion_x_volume",
    "r2_trend_alignment_x_ha", "r2_atr_percentile_x_volume",
    "r2_price_to_poc_x_side", "r2_price_to_vah_x_side", "r2_price_to_val_x_side",
}
ROUND2_BASE_FEATURES = [
    "stoch_k", "stoch_d", "stoch_k_prev", "stoch_d_prev", "distance_to_20", "distance_to_80",
    "delta_k_1", "delta_d_1", "bars_in_oversold", "bars_in_overbought", "exit_speed_from_zone",
    "relative_volume_5", "relative_volume_20", "relative_volume_50", "volume_change_1",
    "volume_change_3", "volume_percentile_20", "volume_percentile_50", "volume_zscore_20",
    "volume_expansion", "ATR", "ATR_normalized", "ATR_percentile_20", "ATR_percentile_50",
    "rolling_std_20", "range_expansion", "ema20_slope", "ema50_slope", "ema20_minus_50",
    "bull_alignment", "bear_alignment", "ha_direction", "ha_delta_close_1", "ha_delta_body_1",
    "ha_body_expansion", "ha_consecutive_bullish", "ha_consecutive_bearish",
    "ha_changed_to_bullish", "ha_changed_to_bearish", "ha_bullish_strong", "ha_bearish_strong",
    "NY_hour", "weekday", "vp_session_distance_price_to_POC", "vp_session_distance_price_to_VAH",
    "vp_session_distance_price_to_VAL", "vp_session_inside_value_area", "vp_session_above_value_area",
    "vp_session_below_value_area",
]


def add_round2_interactions(frame: pd.DataFrame) -> pd.DataFrame:
    """Add a fixed whitelist of interpretable signal-time interactions only."""
    required = {"follow_side", "ha_direction", "relative_volume_20", "ha_changed_to_bullish",
                "ha_changed_to_bearish", "exit_speed_from_zone", "ha_body_expansion",
                "bull_alignment", "bear_alignment", "ATR_percentile_20",
                "vp_session_distance_price_to_POC", "vp_session_distance_price_to_VAH",
                "vp_session_distance_price_to_VAL"}
    if not required.issubset(frame.columns):
        return frame.copy()
    result = frame.copy()
    side = result.follow_side.map({"BUY": 1.0, "SELL": -1.0})
    ha_aligned = result.ha_direction * side
    result["r2_ha_alignment"] = ha_aligned
    result["r2_volume_x_ha_alignment"] = result.relative_volume_20 * ha_aligned
    transition_aligned = (result.ha_changed_to_bullish - result.ha_changed_to_bearish) * side
    result["r2_volume_x_ha_transition"] = result.relative_volume_20 * transition_aligned
    result["r2_stoch_exit_speed_x_volume"] = result.exit_speed_from_zone * result.relative_volume_20
    result["r2_ha_body_expansion_x_volume"] = result.ha_body_expansion * result.relative_volume_20
    result["r2_trend_alignment_x_ha"] = (result.bull_alignment - result.bear_alignment) * ha_aligned
    result["r2_atr_percentile_x_volume"] = result.ATR_percentile_20 * result.relative_volume_20
    for level in ("POC", "VAH", "VAL"):
        name = f"vp_session_distance_price_to_{level}"
        result[f"r2_price_to_{level.lower()}_x_side"] = result[name] * side
    return result


def feature_list(frame: pd.DataFrame, round2: bool = False) -> list[str]:
    if round2:
        features = [column for column in ROUND2_BASE_FEATURES if column in frame.columns]
        features += [column for column in sorted(ROUND2_INTERACTIONS) if column in frame.columns]
    else:
        features = [column for column in FEATURE_COLUMNS if column in frame.columns]
    if not features or any(not pd.api.types.is_numeric_dtype(frame[c]) for c in features):
        raise ValueError("Causal feature contract is missing or includes non-numeric columns")
    forbidden = {"PnL", "exit_price", "exit_reason", "MFE", "MAE", "directional_advantage"}
    if any(any(token in feature for token in forbidden) for feature in features):
        raise ValueError("Outcome leakage found in model feature list")
    return features


def make_models():
    imputer = lambda: SimpleImputer(strategy="median", keep_empty_features=True)
    logistic = make_pipeline(imputer(), StandardScaler(),
            LogisticRegression(max_iter=1000, solver="lbfgs", random_state=SEED))
    return {
        "logistic_regression": logistic,
        "calibrated_logistic": CalibratedClassifierCV(
            estimator=make_pipeline(imputer(), StandardScaler(),
                LogisticRegression(max_iter=1000, solver="lbfgs", random_state=SEED)),
            method="sigmoid", cv=TimeSeriesSplit(n_splits=5), ensemble=True),
        "random_forest": make_pipeline(imputer(), RandomForestClassifier(
            n_estimators=200, max_depth=6, min_samples_leaf=100, max_features=None,
            bootstrap=False, n_jobs=1, random_state=SEED)),
        "hist_gradient_boosting": make_pipeline(imputer(), HistGradientBoostingClassifier(
            max_iter=100, max_leaf_nodes=15, min_samples_leaf=100, learning_rate=0.1,
            l2_regularization=1.0, early_stopping=False, random_state=SEED)),
    }


def _target_rows(frame: pd.DataFrame):
    complete = frame.follow_PnL.notna() & frame.invert_PnL.notna() & frame.directional_advantage.notna()
    selected = frame.loc[complete]
    return selected, selected.directional_advantage.gt(0).astype("int8")


def _policy_stats(frame: pd.DataFrame, prediction: np.ndarray, model: str, partition: str) -> dict:
    chosen = np.where(prediction, frame.follow_PnL.to_numpy(), frame.invert_PnL.to_numpy())
    result = {"model": model, "partition": partition, "signals": len(frame),
              "mean_pnl": float(np.mean(chosen)), "median_pnl": float(np.median(chosen)),
              "win_rate": float(np.mean(chosen > 0)),
              "profit_factor": float(chosen[chosen > 0].sum() / -chosen[chosen < 0].sum())
                               if np.any(chosen < 0) else None,
              "drawdown_proxy": float(np.min(np.cumsum(chosen) - np.maximum.accumulate(np.cumsum(chosen))))}
    for side in ("BUY", "SELL"):
        mask = frame.follow_side.eq(side).to_numpy()
        pnl = chosen[mask]
        result[side.lower()] = {"n": int(mask.sum()), "mean_pnl": float(pnl.mean()) if len(pnl) else None,
                                "win_rate": float(np.mean(pnl > 0)) if len(pnl) else None}
    return result


def _evaluate(model, features, train, evaluation, name, partition):
    train_rows, y_train = _target_rows(train)
    eval_rows, y_eval = _target_rows(evaluation)
    model.fit(train_rows[features], y_train)
    return _score_fitted(model, features, train_rows, eval_rows, y_train, y_eval, name, partition)


def _score_fitted(model, features, train_rows, eval_rows, y_train, y_eval, name, partition):
    probability = model.predict_proba(eval_rows[features])[:, 1]
    prediction = probability >= 0.5  # threshold fixed before validation; no tuning
    metrics = {
        "model": name, "partition": partition, "n_train": len(train_rows), "n_evaluation": len(eval_rows),
        "class_one_rate_train": float(y_train.mean()), "class_one_rate_evaluation": float(y_eval.mean()),
        "accuracy": float(accuracy_score(y_eval, prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(y_eval, prediction)),
        "roc_auc": float(roc_auc_score(y_eval, probability)) if y_eval.nunique() == 2 else None,
        "brier_score": float(brier_score_loss(y_eval, probability)),
        "confusion_matrix_labels_0_1": confusion_matrix(y_eval, prediction, labels=[0, 1]).tolist(),
        "policy": _policy_stats(eval_rows, prediction, name, partition),
        "baselines": {
            "FOLLOW_ALWAYS": _policy_stats(eval_rows, np.ones(len(eval_rows), dtype=bool), "FOLLOW_ALWAYS", partition),
            "INVERT_ALWAYS": _policy_stats(eval_rows, np.zeros(len(eval_rows), dtype=bool), "INVERT_ALWAYS", partition),
        },
    }
    estimator = model.steps[-1][1] if hasattr(model, "steps") else model
    if hasattr(estimator, "feature_importances_"):
        metrics["feature_importance"] = dict(sorted(
            ((feature, float(value)) for feature, value in zip(features, estimator.feature_importances_)),
            key=lambda item: item[1], reverse=True)[:30])
    elif hasattr(estimator, "coef_"):
        metrics["feature_importance_abs_coefficient"] = dict(sorted(
            ((feature, float(value)) for feature, value in zip(features, np.abs(estimator.coef_[0]))),
            key=lambda item: item[1], reverse=True)[:30])
    return metrics


def score_saved_models(train_path: Path, validation_path: Path, output: Path) -> dict:
    """Score already-fitted TRAIN models without refitting or entering FINAL_TEST."""
    if "final_test" in str(train_path).lower() or "final_test" in str(validation_path).lower():
        raise ValueError("FINAL_TEST paths are categorically refused")
    if not output.is_dir() or not (output / "models").is_dir():
        raise ValueError("No saved model directory exists")
    if (output / "metrics.json").exists():
        raise ValueError("Saved-model metrics already exist; refusing to overwrite")
    train, validation = add_round2_interactions(read_dataset(train_path)), add_round2_interactions(read_dataset(validation_path))
    for name, frame in (("TRAIN", train), ("DISCOVERY_VALIDATION", validation)):
        errors = validate(frame)
        if errors:
            raise ValueError(f"{name} failed dataset contract: {'; '.join(errors)}")
    features = feature_list(train)
    train_rows, y_train = _target_rows(train)
    eval_rows, y_eval = _target_rows(validation)
    metrics = []
    for name in ("logistic_regression", "calibrated_logistic", "random_forest", "hist_gradient_boosting"):
        model_path = output / "models" / f"{name}.joblib"
        if not model_path.is_file():
            raise ValueError(f"Missing saved model: {model_path.name}")
        model = joblib.load(model_path)
        metrics.append(_score_fitted(model, features, train_rows, eval_rows, y_train, y_eval,
                                     name, "DISCOVERY_VALIDATION"))
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (output / "feature_list.json").write_text(json.dumps(features, indent=2) + "\n", encoding="utf-8")
    manifest = {"status": "COMPARISON_ONLY_NOT_PROMOTED", "target": TARGET,
                "feature_count": len(features), "training_rows": len(train_rows),
                "validation_rows": len(eval_rows),
                "train_sha256": hashlib.sha256(train_path.read_bytes()).hexdigest(),
                "validation_sha256": hashlib.sha256(validation_path.read_bytes()).hexdigest(),
                "threshold": 0.5, "models": {
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted((output / "models").glob("*.joblib"))},
                "walk_forward_status": "NOT_COMPLETED_LIMITED_RUNTIME",
                "final_test_used": False, "candidate_selected": False,
                "baselines": ["FOLLOW_ALWAYS", "INVERT_ALWAYS", "MODEL_SWITCH_AT_0.5"]}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"manifest": manifest, "metrics": metrics}


def run(train_path: Path, validation_path: Path, output: Path, do_walk_forward: bool,
        round2: bool = False) -> dict:
    if "final_test" in str(train_path).lower() or "final_test" in str(validation_path).lower():
        raise ValueError("FINAL_TEST paths are categorically refused")
    if output.exists():
        raise ValueError("Output exists; use a new model run directory")
    train, validation = add_round2_interactions(read_dataset(train_path)), add_round2_interactions(read_dataset(validation_path))
    for name, frame in (("TRAIN", train), ("DISCOVERY_VALIDATION", validation)):
        errors = validate(frame)
        if errors:
            raise ValueError(f"{name} failed dataset contract: {'; '.join(errors)}")
    if set(train.columns) != set(validation.columns):
        raise ValueError("TRAIN and validation schemas differ")
    features = feature_list(train, round2=round2)
    output.mkdir(parents=True)
    (output / "models").mkdir()
    metrics = []
    training_rows, y = _target_rows(train)
    if y.nunique() != 2:
        raise ValueError("TRAIN target must contain both classes")
    for name, model in make_models().items():
        result = _evaluate(model, features, train, validation, name, "DISCOVERY_VALIDATION")
        metrics.append(result)
        joblib.dump(model, output / "models" / f"{name}.joblib", compress=3)

    # Fixed, expanding temporal folds over only TRAIN + DISCOVERY_VALIDATION.
    if do_walk_forward:
        pool = pd.concat([train, validation], ignore_index=True).sort_values("signal_time_msc", kind="stable")
        fold_results = []
        for fold_number, (fold_train, fold_validation, purge) in enumerate(walk_forward(pool, 5000, 2500), 1):
            for name, model in make_models().items():
                result = _evaluate(model, features, fold_train, fold_validation, name,
                                   f"WF_{fold_number:02d}_VALIDATION")
                result["fold"] = fold_number
                result["purge"] = purge
                fold_results.append(result)
        pd.DataFrame([{"fold": r["fold"], "model": r["model"], "partition": r["partition"],
                       "n_train": r["n_train"], "n_evaluation": r["n_evaluation"], "roc_auc": r["roc_auc"],
                       "brier_score": r["brier_score"], "policy_mean_pnl": r["policy"]["mean_pnl"],
                       "policy_win_rate": r["policy"]["win_rate"], "policy_profit_factor": r["policy"]["profit_factor"],
                       "policy_drawdown_proxy": r["policy"]["drawdown_proxy"],
                       "follow_baseline_mean_pnl": r["baselines"]["FOLLOW_ALWAYS"]["mean_pnl"],
                       "invert_baseline_mean_pnl": r["baselines"]["INVERT_ALWAYS"]["mean_pnl"], **r["purge"]}
                      for r in fold_results]).to_csv(output / "walk_forward_metrics.csv", index=False)

    (output / "metrics.json").write_text(json.dumps(metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (output / "feature_list.json").write_text(json.dumps(features, indent=2) + "\n", encoding="utf-8")
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted((output / "models").glob("*.joblib"))}
    manifest = {"status": "RESEARCH_COMPARISON_NOT_PROMOTED", "target": TARGET,
                "feature_count": len(features), "features": features,
                "feature_profile": "round2_domain_subset" if round2 else "causal_full_v1",
                "training_rows": len(training_rows), "validation_rows": len(_target_rows(validation)[0]),
                "train_sha256": hashlib.sha256(train_path.read_bytes()).hexdigest(),
                "validation_sha256": hashlib.sha256(validation_path.read_bytes()).hexdigest(),
                "seed": SEED, "threshold": 0.5, "models": hashes,
                "final_test_used": False, "candidate_selected": False,
                "policy_baselines": ["FOLLOW_ALWAYS", "INVERT_ALWAYS", "MODEL_SWITCH_AT_0.5"]}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"manifest": manifest, "metrics": metrics}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("train", type=Path)
    parser.add_argument("validation", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--walk-forward", action="store_true")
    parser.add_argument("--round2", action="store_true",
                        help="use the fixed market-motivated feature subset and predefined interactions")
    parser.add_argument("--score-existing", action="store_true",
                        help="score saved base models; do not refit or run walk-forward")
    args = parser.parse_args()
    try:
        result = (score_saved_models(args.train, args.validation, args.output) if args.score_existing
                  else run(args.train, args.validation, args.output, args.walk_forward, args.round2))
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Model training failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
