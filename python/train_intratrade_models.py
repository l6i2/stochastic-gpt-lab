"""Fit fixed intra-trade models on TRAIN and score once on DISCOVERY_VALIDATION."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import (HistGradientBoostingClassifier, HistGradientBoostingRegressor,
                              RandomForestClassifier, RandomForestRegressor)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, brier_score_loss, confusion_matrix, mean_absolute_error,
                             mean_squared_error, r2_score, roc_auc_score)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

try:
    from .parquet_io import read_parquet
except ImportError:
    from parquet_io import read_parquet

ROOT = Path(__file__).resolve().parents[1]
FEATURES = (
    "current_unrealized_pnl", "distance_to_tp", "distance_to_sl", "current_mfe_so_far", "current_mae_so_far",
    "bars_open", "stoch_k", "stoch_d", "stoch_k_prev", "stoch_d_prev", "stoch_k_slope_1", "stoch_k_slope_3",
    "stoch_d_slope_1", "stoch_d_slope_3", "stoch_k_minus_d", "stoch_reentered_oversold",
    "stoch_reentered_overbought", "stoch_distance_to_opposite_zone", "stoch_direction_change",
    "ha_direction", "ha_body", "ha_range", "ha_body_percent", "ha_upper_wick", "ha_lower_wick",
    "ha_consecutive_bullish", "ha_consecutive_bearish", "ha_body_expansion", "ha_range_expansion",
    "ha_bullish_strong", "ha_bearish_strong", "ha_indecision", "ha_changed_to_bullish", "ha_changed_to_bearish",
    "tick_volume", "real_volume", "relative_volume_5", "relative_volume_10", "relative_volume_20",
    "relative_volume_50", "volume_change_1", "volume_change_3", "volume_zscore_20", "volume_zscore_50",
    "volume_expansion", "open", "high", "low", "close", "body", "range", "upper_wick", "lower_wick",
    "return_1", "return_3", "return_5", "momentum_3", "momentum_5", "ATR", "ATR_percentile_20",
    "rolling_std_20", "rolling_std_50", "range_expansion", "HH_count_20", "HL_count_20", "LH_count_20",
    "LL_count_20", "distance_to_recent_high", "distance_to_recent_low", "EMA20", "EMA50", "EMA100", "EMA200",
    "ema20_slope", "ema50_slope", "ema100_slope", "ema200_slope", "price_to_ema20", "price_to_ema50",
    "price_to_ema100", "price_to_ema200", "ema_bull_alignment", "ema_bear_alignment",
    "vp_30m_distance_price_to_POC", "vp_30m_distance_price_to_VAH", "vp_30m_distance_price_to_VAL",
    "vp_30m_inside_value_area", "vp_30m_above_value_area", "vp_30m_below_value_area",
    "vp_60m_distance_price_to_POC", "vp_120m_distance_price_to_POC", "vp_240m_distance_price_to_POC",
    "vp_session_distance_price_to_POC",
)
CLASS_TARGETS = ("tp_before_sl_after_snapshot", "sl_before_tp_after_snapshot", "reversal_event")
REGRESSION_TARGETS = ("future_pnl_to_exit",)
MODELS = ("calibrated_logistic", "random_forest", "hist_gradient_boosting")


def _safe_path(path: Path) -> None:
    if "final_test" in path.as_posix().lower():
        raise ValueError("FINAL_TEST is not accepted by this trainer")


def _join(snapshot_path: Path, targets_path: Path) -> pd.DataFrame:
    _safe_path(snapshot_path); _safe_path(targets_path)
    snapshots, targets = read_parquet(snapshot_path), pd.read_csv(targets_path)
    return snapshots.merge(targets, on=["snapshot_id", "signal_id", "virtual_mode", "snapshot_bar"],
                           how="inner", validate="one_to_one")


def _temporal_group_folds(frame: pd.DataFrame, n_splits: int = 3):
    signals = (frame[["signal_id", "signal_time_msc"]].drop_duplicates("signal_id")
               .sort_values(["signal_time_msc", "signal_id"], kind="stable").reset_index(drop=True))
    if len(signals) < n_splits + 2:
        raise ValueError("Not enough distinct TRAIN signals for temporal calibration folds")
    groups = signals.signal_id.to_numpy()
    folds = []
    for train_idx, test_idx in TimeSeriesSplit(n_splits=n_splits).split(groups):
        train_ids, test_ids = set(groups[train_idx]), set(groups[test_idx])
        if train_ids & test_ids:
            raise AssertionError("Temporal calibration split crosses a signal")
        tr = np.flatnonzero(frame.signal_id.isin(train_ids).to_numpy())
        te = np.flatnonzero(frame.signal_id.isin(test_ids).to_numpy())
        folds.append((tr, te))
    return folds


def _models(target: str, calibration_folds):
    imputer = SimpleImputer(strategy="median", add_indicator=True)
    if target in CLASS_TARGETS:
        logistic = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                                 LogisticRegression(max_iter=1000, class_weight="balanced", random_state=1729))
        return {
            "calibrated_logistic": CalibratedClassifierCV(logistic, method="sigmoid", cv=calibration_folds),
            "random_forest": make_pipeline(imputer, RandomForestClassifier(n_estimators=100, max_depth=6,
                min_samples_leaf=20, class_weight="balanced_subsample", random_state=1729, n_jobs=1)),
            "hist_gradient_boosting": make_pipeline(imputer, HistGradientBoostingClassifier(max_iter=100,
                max_leaf_nodes=15, l2_regularization=1.0, random_state=1729)),
        }
    return {
        "random_forest": make_pipeline(imputer, RandomForestRegressor(n_estimators=100, max_depth=6,
            min_samples_leaf=20, random_state=1729, n_jobs=1)),
        "hist_gradient_boosting": make_pipeline(imputer, HistGradientBoostingRegressor(max_iter=100,
            max_leaf_nodes=15, l2_regularization=1.0, random_state=1729)),
    }


def _performance(values: pd.Series, times: pd.Series) -> dict:
    frame = pd.DataFrame({"pnl": pd.to_numeric(values, errors="coerce"), "time": times}).dropna()
    if frame.empty:
        return {"n": 0, "mean_pnl": None, "median_pnl": None, "profit_factor": None,
                "win_rate": None, "drawdown_proxy": None}
    frame = frame.sort_values("time", kind="stable")
    pnl = frame.pnl.to_numpy(dtype=float)
    positive, negative = pnl[pnl > 0].sum(), abs(pnl[pnl < 0].sum())
    cumulative = np.cumsum(pnl)
    drawdown = np.maximum.accumulate(np.r_[0.0, cumulative])[1:] - cumulative
    return {"n": len(pnl), "mean_pnl": float(np.mean(pnl)), "median_pnl": float(np.median(pnl)),
            "profit_factor": float(positive / negative) if negative else None,
            "win_rate": float(np.mean(pnl > 0)), "drawdown_proxy": float(np.max(drawdown))}


def _policy_report(val: pd.DataFrame, predictions: dict[str, pd.Series]) -> dict:
    rows = val[val.snapshot_bar.astype(int) == 3].copy()
    if rows.empty:
        return {"status": "NO_BAR_3_VALIDATION_ROWS", "policies": {}}
    modes = rows.groupby("signal_id").virtual_mode.agg(lambda x: set(x))
    paired = set(modes[modes.map(lambda x: {"FOLLOW", "INVERT"}.issubset(x))].index)
    rows = rows[rows.signal_id.isin(paired)].copy()
    if rows.empty:
        return {"status": "NO_PAIRED_BAR_3_VALIDATION_ROWS", "policies": {}}
    current = pd.to_numeric(rows.current_unrealized_pnl, errors="coerce")
    future = pd.to_numeric(rows.future_pnl_to_exit, errors="coerce")
    hold = current + future
    policies = {"HOLD": hold, "EARLY_EXIT": current,
                "PROTECT_PROFIT_AT_60": current.where(current >= 60, hold)}
    report = {"status": "SIMULATED_AT_FIXED_BAR_3_ONLY", "paired_signals": len(paired),
              "same_virtual_rows_for_comparison": len(rows), "thresholds_frozen": {"snapshot_bar": 3,
              "protect_profit_pnl": 60, "model_early_exit_probability": 0.7},
              "baselines": {mode: _performance(hold[rows.virtual_mode == mode],
                  rows.loc[rows.virtual_mode == mode, "signal_time_msc"]) for mode in ("FOLLOW", "INVERT")},
              "policies": {name: _performance(value, rows.signal_time_msc) for name, value in policies.items()},
              "stability_by_month": {}}
    months = pd.to_datetime(rows.signal_time_msc, unit="ms", utc=True).dt.strftime("%Y-%m")
    for month in sorted(months.unique()):
        mask = months == month
        report["stability_by_month"][month] = {name: _performance(value[mask], rows.loc[mask, "signal_time_msc"])
                                                for name, value in policies.items()}
    report["model_early_exit"] = {}
    for name, probabilities in predictions.items():
        prob = probabilities.reindex(rows.index)
        report["model_early_exit"][name] = _performance(current.where(prob >= 0.7, hold), rows.signal_time_msc)
    report["REVERSE_DIRECTION"] = {"status": "NOT_SIMULATED_MISSING_POST_SNAPSHOT_QUOTE_PATH",
                                   "reason": "Snapshot labels do not contain the ordered future tick path needed to reproduce reversed fixed TP/SL exits."}
    return report


def train(train_path: Path, validation_path: Path, targets_path: Path, output: Path) -> dict:
    train_data, validation_data = _join(train_path, targets_path), _join(validation_path, targets_path)
    if set(train_data.signal_id) & set(validation_data.signal_id):
        raise ValueError("TRAIN and VALIDATION signal IDs overlap")
    features = [name for name in FEATURES if name in train_data.columns and name in validation_data.columns]
    if len(features) < 10:
        raise ValueError("Intratrade feature whitelist has fewer than ten available fields")
    forbidden = [name for name in features if any(t in name.lower() for t in
                 ("future_", "final_", "exit_", "target", "label", "reversal_event", "profit_erosion"))]
    if forbidden:
        raise ValueError(f"Outcome leakage in feature whitelist: {forbidden}")
    train_data = train_data.sort_values(["signal_time_msc", "snapshot_time_msc", "signal_id"], kind="stable")
    validation_data = validation_data.sort_values(["signal_time_msc", "snapshot_time_msc", "signal_id"], kind="stable")
    output.mkdir(parents=True, exist_ok=True)
    feature_hash = hashlib.sha256("\n".join(features).encode()).hexdigest()
    results = []
    reversal_predictions = {}
    target_names = (*CLASS_TARGETS, *REGRESSION_TARGETS)
    for target in target_names:
        train_mask = pd.to_numeric(train_data[target], errors="coerce").notna()
        val_mask = pd.to_numeric(validation_data[target], errors="coerce").notna()
        train_frame, val_frame = train_data.loc[train_mask], validation_data.loc[val_mask]
        if len(train_frame) < 100 or len(val_frame) < 20:
            results.append({"target": target, "status": "INSUFFICIENT_LABEL_SUPPORT",
                            "train_n": len(train_frame), "validation_n": len(val_frame)})
            continue
        y_train = pd.to_numeric(train_frame[target]).astype(int if target in CLASS_TARGETS else float)
        y_val = pd.to_numeric(val_frame[target]).astype(int if target in CLASS_TARGETS else float)
        x_train, x_val = train_frame[features], val_frame[features]
        if target in CLASS_TARGETS and y_train.nunique() != 2:
            results.append({"target": target, "status": "INSUFFICIENT_CLASS_VARIATION",
                            "train_n": len(train_frame), "validation_n": len(val_frame)})
            continue
        model_list = _models(target, _temporal_group_folds(train_frame)) if target in CLASS_TARGETS else _models(target, [])
        for model_name, model in model_list.items():
            model.fit(x_train, y_train)
            pred = model.predict(x_val)
            item = {"target": target, "model": model_name, "train_n": len(train_frame),
                    "validation_n": len(val_frame), "feature_hash": feature_hash}
            if target in CLASS_TARGETS:
                probs = model.predict_proba(x_val)[:, 1]
                item.update({"roc_auc": float(roc_auc_score(y_val, probs)) if y_val.nunique() == 2 else None,
                             "brier": float(brier_score_loss(y_val, probs)),
                             "accuracy_at_0_5": float(accuracy_score(y_val, pred)),
                             "confusion_matrix": confusion_matrix(y_val, pred, labels=[0, 1]).tolist()})
                if target == "reversal_event":
                    reversal_predictions[model_name] = pd.Series(probs, index=val_frame.index)
                final_estimator = getattr(model, "steps", [(None, model)])[-1][1]
                if hasattr(final_estimator, "feature_importances_"):
                    item["top_feature_importance"] = sorted(
                        zip(features, final_estimator.feature_importances_.tolist()),
                        key=lambda pair: pair[1], reverse=True)[:20]
            else:
                item.update({"mae": float(mean_absolute_error(y_val, pred)),
                             "rmse": float(mean_squared_error(y_val, pred) ** 0.5),
                             "r2": float(r2_score(y_val, pred))})
            model_path = output / f"{target}_{model_name}.joblib"
            joblib.dump(model, model_path)
            item["model_sha256"] = hashlib.sha256(model_path.read_bytes()).hexdigest()
            results.append(item)
    policy_rows = validation_data.loc[pd.to_numeric(validation_data.reversal_event, errors="coerce").notna()].copy()
    for model_name, prediction in reversal_predictions.items():
        policy_rows.loc[prediction.index, f"prob_{model_name}"] = prediction
    policy_probabilities = {name: policy_rows[f"prob_{name}"] for name in reversal_predictions
                            if f"prob_{name}" in policy_rows}
    manifest = {"status": "FIT_TRAIN_SCORED_VALIDATION", "final_test_accessed": False,
                "training_signal_count": int(train_data.signal_id.nunique()),
                "validation_signal_count": int(validation_data.signal_id.nunique()),
                "features": features, "feature_hash": feature_hash, "targets": results,
                "fixed_threshold_policy": 0.7, "random_shuffle": False,
                "policy_simulation": _policy_report(policy_rows, policy_probabilities),
                "candidate_promoted": False, "live_trading": False, "demo_execution": False}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, default=Path("outputs/intratrade/splits/train.parquet"))
    parser.add_argument("--validation", type=Path, default=Path("outputs/intratrade/splits/validation.parquet"))
    parser.add_argument("--targets", type=Path, default=Path("outputs/intratrade/master/intratrade_targets.csv"))
    parser.add_argument("--output", type=Path, default=Path("outputs/intratrade/models/current"))
    args = parser.parse_args()
    def absolute(path: Path) -> Path:
        return path if path.is_absolute() else ROOT / path
    result = train(absolute(args.train), absolute(args.validation), absolute(args.targets), absolute(args.output))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
