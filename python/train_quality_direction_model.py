"""Train fixed directional models on quality-v1 event features and score once on validation.

The event CSV retains its EA event schema 1.1. Its provenance is the quality-v1
derivative of individually validated schema-3 history blocks; the every-bar
schema-3 trajectories are not mislabeled as event schema 3.0.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from research import purge_at_boundary, walk_forward  # noqa: E402
from train_direction_model import (  # noqa: E402
    _score_fitted,
    _target_rows,
    add_round2_interactions,
    feature_list,
    make_models,
)
from parquet_io import read_parquet  # noqa: E402

MODEL_NAMES = ("logistic_regression", "random_forest", "hist_gradient_boosting")
SEED = 20261013


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_membership(path: Path) -> set[str]:
    if "final_test" in path.as_posix().lower():
        raise ValueError("FINAL_TEST membership path is forbidden")
    return set(read_parquet(path, columns=["signal_id"]).signal_id.astype(str))


def load_partitions(events_path: Path, quality_manifest_path: Path,
                    train_membership: Path, validation_membership: Path,
                    split_manifest_path: Path):
    quality = json.loads(quality_manifest_path.read_text(encoding="utf-8"))
    if quality.get("status") != "PASS_INHERITED_VALIDATION" or quality.get("final_test_accessed") is not False:
        raise ValueError("Quality-v1 manifest is not accepted")
    expected_events_hash = quality.get("output_sha256", {}).get("stochastic_events.csv")
    if digest(events_path) != expected_events_hash:
        raise ValueError("Schema-3 event CSV hash differs from quality-v1 manifest")
    train_ids = _load_membership(train_membership)
    validation_ids = _load_membership(validation_membership)
    if train_ids & validation_ids:
        raise ValueError("Frozen TRAIN and DISCOVERY_VALIDATION memberships overlap")
    excluded_path = events_path.parent / "excluded_signal_ids.csv"
    excluded = set(pd.read_csv(excluded_path, dtype=str).signal_id)
    train_ids -= excluded
    validation_ids -= excluded
    if train_ids & validation_ids:
        raise ValueError("Quality gate introduced a split overlap")

    data = pd.read_csv(events_path, float_precision="round_trip")
    source_schemas = {
        item.get("source_validation", {}).get("schema_version")
        for item in quality.get("blocks", [])
    }
    if source_schemas != {"3.0"}:
        raise ValueError("Quality event provenance is not the validated schema-3 block set")
    if data.signal_id.duplicated().any() or set(data.schema_version.astype(str)) != {"1.1"}:
        raise ValueError("Quality event IDs must be unique and retain homogeneous EA schema 1.1")
    expected_ids = train_ids | validation_ids
    if set(data.signal_id.astype(str)) != expected_ids:
        raise ValueError("Quality event membership differs from frozen splits minus tick exclusions")
    if (data.LIVE_TRADING if "LIVE_TRADING" in data else pd.Series([False])).any():
        raise ValueError("Unexpected live-trading event flag")
    if (data.feature_max_time_msc > data.signal_time_msc).any():
        raise ValueError("Signal-time model received a future feature timestamp")
    if (data.tp_distance.ne(240.0).any() or data.sl_distance.ne(180.0).any()
            or data.time_exit_bars.ne(100).any()):
        raise ValueError("Frozen entry strategy parameters changed")
    if not data.follow_side.isin(("BUY", "SELL")).all() or not data.invert_side.isin(("BUY", "SELL")).all():
        raise ValueError("Unknown FOLLOW/INVERT side")
    if not (data.loc[data.follow_side.eq("BUY"), "invert_side"].eq("SELL").all()
            and data.loc[data.follow_side.eq("SELL"), "invert_side"].eq("BUY").all()):
        raise ValueError("FOLLOW/INVERT side mapping mismatch")

    split = json.loads(split_manifest_path.read_text(encoding="utf-8"))
    validation_start = int(split["boundaries"]["validation_start_signal_time_msc"])
    final_start = int(split["boundaries"]["final_test_start_signal_time_msc"])
    train = data[data.signal_id.astype(str).isin(train_ids)].copy()
    validation = data[data.signal_id.astype(str).isin(validation_ids)].copy()
    if (train.signal_time_msc >= validation_start).any() or (validation.signal_time_msc >= final_start).any():
        raise ValueError("Directional event crossed its protected chronological partition")
    for name, frame, boundary in (("TRAIN", train, validation_start),
                                   ("DISCOVERY_VALIDATION", validation, final_start)):
        label_end = np.maximum(frame.follow_exit_time.to_numpy(dtype=np.int64),
                               frame.invert_exit_time.to_numpy(dtype=np.int64))
        if np.any(label_end >= boundary):
            raise ValueError(f"{name} contains a label horizon crossing its next partition")
    train = add_round2_interactions(train).sort_values("signal_time_msc", kind="stable")
    validation = add_round2_interactions(validation).sort_values("signal_time_msc", kind="stable")
    if list(train.columns) != list(validation.columns):
        raise ValueError("TRAIN and validation feature schemas differ")
    return train, validation, quality, split


def _fit_and_score(train: pd.DataFrame, evaluation: pd.DataFrame, features: list[str],
                   partition: str) -> tuple[list[dict], dict[str, object]]:
    train_rows, y_train = _target_rows(train)
    eval_rows, y_eval = _target_rows(evaluation)
    if len(train_rows) < 100 or len(eval_rows) < 50 or y_train.nunique() != 2:
        raise ValueError(f"Insufficient complete directional labels for {partition}")
    models = make_models()
    metrics, fitted = [], {}
    for name in MODEL_NAMES:
        model = models[name]
        model.fit(train_rows[features], y_train)
        metrics.append(_score_fitted(model, features, train_rows, eval_rows, y_train, y_eval,
                                     name, partition))
        fitted[name] = model
    return metrics, fitted


def run(events_path: Path, quality_manifest_path: Path, train_membership: Path,
        validation_membership: Path, split_manifest_path: Path, output: Path,
        do_walk_forward: bool = True) -> dict:
    output = Path(output)
    if "final_test" in output.as_posix().lower() or output.exists():
        raise ValueError("Refusing FINAL_TEST output or overwriting an existing model run")
    train, validation, quality, split = load_partitions(
        events_path, quality_manifest_path, train_membership, validation_membership, split_manifest_path)
    features = feature_list(train, round2=True)
    if len(features) < 10:
        raise ValueError("Schema-3 causal feature whitelist is too small")
    train_rows, y_train = _target_rows(train)
    validation_rows, y_validation = _target_rows(validation)
    if y_train.nunique() != 2 or y_validation.nunique() != 2:
        raise ValueError("TRAIN and Discovery Validation require both directional classes")
    # Finish all fitting/evaluation in memory before creating the write-once
    # output path. A failed fit therefore leaves no partial run that blocks retry.
    metrics, models = _fit_and_score(train, validation, features, "DISCOVERY_VALIDATION")
    walk_forward_results = []
    if do_walk_forward:
        pool = train.sort_values("signal_time_msc", kind="stable")
        for fold_number, (fold_train, fold_eval, purge) in enumerate(walk_forward(pool, 4000, 2000), 1):
            fold_metrics, _ = _fit_and_score(fold_train, fold_eval, features,
                                             f"TRAIN_WALK_FORWARD_{fold_number:02d}")
            walk_forward_results.extend({**item, "fold": fold_number, **purge} for item in fold_metrics)

    output.mkdir(parents=True)
    (output / "models").mkdir()
    model_hashes = {}
    for name, model in models.items():
        model_path = output / "models" / f"{name}.joblib"
        joblib.dump(model, model_path, compress=3)
        model_hashes[model_path.name] = digest(model_path)
    if do_walk_forward:
        pd.DataFrame(walk_forward_results).to_json(
            output / "walk_forward_metrics.json", orient="records", indent=2)

    feature_hash = hashlib.sha256("\n".join(features).encode()).hexdigest()
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (output / "feature_list.json").write_text(json.dumps(features, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "status": "TRAIN_FIT_VALIDATION_SCORED_ONCE_NOT_PROMOTED",
        "target": "directional_advantage > 0 (FOLLOW PnL greater than INVERT PnL)",
        "features": features,
        "feature_sha256": feature_hash,
        "seed": SEED,
        "policy_threshold": 0.5,
        "models": model_hashes,
        "training_events": len(train), "training_complete_labels": len(train_rows),
        "training_censored": int(len(train) - len(train_rows)),
        "validation_events": len(validation), "validation_complete_labels": len(validation_rows),
        "validation_censored": int(len(validation) - len(validation_rows)),
        "quality_policy": quality["policy_version"],
        "event_schema_version": "1.1",
        "source_history_schema_version": "3.0",
        "event_sha256": quality["output_sha256"]["stochastic_events.csv"],
        "train_membership_sha256": digest(train_membership),
        "validation_membership_sha256": digest(validation_membership),
        "split_manifest_sha256": digest(split_manifest_path),
        "walk_forward_scope": "TRAIN_ONLY_EXPANDING_PURGED_FOLDS" if do_walk_forward else "NOT_RUN",
        "walk_forward_folds": len({item["fold"] for item in walk_forward_results}),
        "baselines": ["FOLLOW_ALWAYS", "INVERT_ALWAYS", "MODEL_SWITCH_AT_0.5"],
        "random_shuffle": False,
        "candidate_selected": False,
        "candidate_promoted": False,
        "final_test_accessed": False,
        "demo_execution": False,
        "live_trading": False,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"manifest": manifest, "metrics": metrics}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, default=Path("outputs/bar_controller/research/quality_v1/stochastic_events.csv"))
    parser.add_argument("--quality-manifest", type=Path,
                        default=Path("outputs/bar_controller/research/quality_v1/tick_quality_manifest.json"))
    parser.add_argument("--train-membership", type=Path, default=Path("outputs/splits/train.parquet"))
    parser.add_argument("--validation-membership", type=Path, default=Path("outputs/splits/validation.parquet"))
    parser.add_argument("--split-manifest", type=Path, default=Path("outputs/splits/split_manifest.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/models/quality_directional_v1"))
    parser.add_argument("--no-walk-forward", action="store_true")
    args = parser.parse_args()
    absolute = lambda p: p if p.is_absolute() else ROOT / p
    result = run(absolute(args.events), absolute(args.quality_manifest), absolute(args.train_membership),
                 absolute(args.validation_membership), absolute(args.split_manifest), absolute(args.output),
                 not args.no_walk_forward)
    print(json.dumps({"status": result["manifest"]["status"],
                      "train_n": result["manifest"]["training_complete_labels"],
                      "validation_n": result["manifest"]["validation_complete_labels"],
                      "walk_forward_folds": result["manifest"]["walk_forward_folds"],
                      "final_test_accessed": result["manifest"]["final_test_accessed"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
