"""Select among fixed EXIT rules on each TRAIN prefix and score later TRAIN folds."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RULES = ("HA_OPPOSITE", "STOCH_KD_OPPOSITE", "HA_AND_STOCH_OPPOSITE")
PRIMARY_LATENCY = 250


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stats(values: list[float]) -> dict:
    pnl = np.asarray(values, dtype=float)
    gains, losses = pnl[pnl > 0], pnl[pnl < 0]
    curve = np.cumsum(pnl)
    drawdown = curve - np.maximum.accumulate(np.r_[0.0, curve])[1:]
    return {
        "n": int(len(pnl)), "mean_pnl": float(pnl.mean()) if len(pnl) else None,
        "median_pnl": float(np.median(pnl)) if len(pnl) else None,
        "win_rate": float((pnl > 0).mean()) if len(pnl) else None,
        "profit_factor": float(gains.sum() / -losses.sum()) if len(losses) else None,
        "drawdown_proxy": float(drawdown.min()) if len(drawdown) else None,
    }


def build_folds(events: pd.DataFrame, initial: int = 4000, step: int = 2000) -> list[dict]:
    events = events.sort_values("signal_time_msc", kind="stable").reset_index(drop=True)
    folds = []
    for number, start in enumerate(range(initial, len(events), step), 1):
        end = min(start + step, len(events))
        evaluation = events.iloc[start:end].copy()
        boundary = int(events.signal_time_msc.iloc[end]) if end < len(events) else None
        if boundary is None:
            kept = evaluation
        else:
            kept = evaluation[evaluation.label_end_msc < boundary]
        train = events.iloc[:start]
        train_boundary = int(evaluation.signal_time_msc.iloc[0])
        train = train[train.label_end_msc < train_boundary]
        folds.append({
            "fold": number, "train_ids": set(train.signal_id.astype(str)),
            "eval_ids": set(kept.signal_id.astype(str)),
            "train_rows_before_purge": start, "train_rows_after_purge": len(train),
            "eval_rows_before_purge": end-start, "eval_rows_after_purge": len(kept),
            "eval_start_msc": train_boundary,
            "eval_end_msc": int(kept.signal_time_msc.max()) if len(kept) else None,
            "purged_eval_ids": int(len(evaluation)-len(kept)),
        })
    return folds


def run(root: Path = ROOT, *, output: Path | None = None) -> dict:
    root = Path(root)
    if output is not None and ("final_test" in Path(output).as_posix().lower() or Path(output).exists()):
        raise ValueError("Refusing protected or existing output path")
    qdir = root / "outputs/bar_controller/research/quality_v1"
    quality_path = qdir / "tick_quality_manifest.json"
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    if quality.get("status") != "PASS_INHERITED_VALIDATION" or quality.get("final_test_accessed") is not False:
        raise ValueError("Quality-v1 provenance is not accepted")
    trade_path = root / "outputs/bar_controller/research/train_exit_exploration_v2_trades.csv"
    run_path = root / "outputs/bar_controller/research/train_exit_exploration_v2.json"
    run_manifest = json.loads(run_path.read_text(encoding="utf-8"))
    if (run_manifest.get("status") != "TRAIN_EXIT_RULES_EXPLORED_NOT_PROMOTED"
            or run_manifest.get("validation_accessed") is not False
            or sha256(trade_path) != run_manifest.get("trade_results_sha256")):
        raise ValueError("TRAIN exit exploration evidence/hash is invalid")
    split_path = root / "outputs/splits/split_manifest.json"
    split = json.loads(split_path.read_text(encoding="utf-8"))
    events_path = qdir / "stochastic_events.csv"
    events = pd.read_csv(events_path, usecols=["signal_id", "signal_time_msc",
                                               "follow_exit_time", "invert_exit_time"],
                         dtype={"signal_id": str})
    events["label_end_msc"] = events[["follow_exit_time", "invert_exit_time"]].max(axis=1)
    train_ids = set(pd.read_parquet(root / "outputs/splits/train.parquet",
                                    columns=["signal_id"], engine="fastparquet")
                    .signal_id.astype(str))
    excluded = set(pd.read_csv(qdir / "excluded_signal_ids.csv", dtype=str).signal_id)
    train_ids -= excluded
    events = events[events.signal_id.astype(str).isin(train_ids)].copy()
    if set(events.signal_id.astype(str)) != train_ids:
        raise ValueError("Quality-v1 TRAIN event membership differs from frozen split")
    folds = build_folds(events)
    by_signal: dict[str, dict] = {}
    with trade_path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if int(row["latency_msc"]) != PRIMARY_LATENCY:
                continue
            signal_id = row["signal_id"]
            record = by_signal.setdefault(signal_id, {"signal_time_msc": int(row["signal_time_msc"]),
                                                       "label_end_msc": int(row["label_end_msc"]),
                                                       "rows": {}})
            key = (row["virtual_mode"], row["virtual_side"], row["policy"])
            if key in record["rows"]:
                raise ValueError(f"Duplicate per-signal policy result: {signal_id}/{key}")
            record["rows"][key] = {
                "baseline": float(row["baseline_pnl"]), "pnl": float(row["policy_pnl"]),
                "delta": float(row["paired_delta"]),
            }
    if set(by_signal) != train_ids:
        raise ValueError("Per-trade results do not cover exactly quality-v1 TRAIN")

    fold_results = []
    for fold in folds:
        train = fold["train_ids"]
        evaluation = fold["eval_ids"]
        if len(evaluation) < 500:
            continue
        selection_effects = {}
        for rule in RULES:
            changes = [by_signal[sid]["rows"][("FOLLOW", "SELL", rule)]["delta"]
                       for sid in train if ("FOLLOW", "SELL", rule) in by_signal[sid]["rows"]]
            if len(changes) < 500:
                raise ValueError("Insufficient TRAIN prefix support for rule selection")
            selection_effects[rule] = float(np.mean(changes))
        selected = max(RULES, key=lambda name: (selection_effects[name], -RULES.index(name)))

        candidate_follow, follow_baseline, invert_baseline = [], [], []
        target_pnl, target_baseline = [], []
        # Preserve chronological order for the drawdown proxy.
        evaluation_order = sorted(evaluation, key=lambda sid: by_signal[sid]["signal_time_msc"])
        for sid in evaluation_order:
            event = by_signal[sid]["rows"]
            follow_key = next(key for key in event if key[0] == "FOLLOW")
            invert_key = next(key for key in event if key[0] == "INVERT")
            follow_row = event[follow_key]
            invert_row = event[invert_key]
            follow_base_signal = follow_row["baseline"]
            invert_base_signal = invert_row["baseline"]
            follow_sell = event.get(("FOLLOW", "SELL", selected))
            dynamic_signal = follow_sell["pnl"] if follow_sell is not None else follow_base_signal
            candidate_follow.append(dynamic_signal)
            follow_baseline.append(follow_base_signal)
            invert_baseline.append(invert_base_signal)
            if follow_sell is not None:
                target_pnl.append(follow_sell["pnl"])
                target_baseline.append(follow_sell["baseline"])
        fold_results.append({
            "fold": fold["fold"], "selected_rule_from_prior_train": selected,
            "selection_effects_follow_sell": selection_effects,
            "train_n_after_purge": fold["train_rows_after_purge"],
            "eval_signals_after_purge": len(evaluation),
            "purged_eval_signals": fold["purged_eval_ids"],
            "eval_follow_sell_n": len(target_pnl),
            "follow_sell_mean_pnl": float(np.mean(target_pnl)),
            "follow_sell_baseline_mean_pnl": float(np.mean(target_baseline)),
            "follow_sell_mean_delta": float(np.mean(np.asarray(target_pnl)-target_baseline)),
            "selected_policy_follow_portfolio": _stats(candidate_follow),
            "FOLLOW_always": _stats(follow_baseline),
            "INVERT_always": _stats(invert_baseline),
            "policy_mean_delta_vs_FOLLOW_always": float(np.mean(np.asarray(candidate_follow)-follow_baseline)),
        })

    effects = [r["follow_sell_mean_delta"] for r in fold_results]
    positive = [v for v in effects if v > 0]
    concentration = max(positive) / sum(positive) if positive and sum(positive) > 0 else None
    report = {
        "status": "TRAIN_ONLY_EXPANDING_PURGED_EXIT_RULE_SELECTION",
        "scope": "QUALITY_V1_TRAIN_ONLY", "selection_target": "FOLLOW mode, virtual SELL positions",
        "primary_latency_msc": PRIMARY_LATENCY, "rule_family": list(RULES),
        "folds": fold_results,
        "positive_effect_folds": sum(v > 0 for v in effects), "eligible_folds": len(effects),
        "positive_effect_fraction": float(np.mean(np.asarray(effects) > 0)) if effects else None,
        "largest_fold_share_of_positive_target_delta": concentration,
        "walk_forward_gate_pass": bool(len(effects) >= 3 and sum(v > 0 for v in effects) / len(effects) >= 0.70
                                        and (concentration is None or concentration <= 0.50)),
        "quality_manifest_sha256": sha256(quality_path),
        "trade_results_sha256": sha256(trade_path),
        "split_manifest_sha256": sha256(split_path),
        "validation_accessed": False, "final_test_accessed": False,
        "candidate_promoted": False, "demo_execution": False, "live_trading": False,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path,
                        default=Path("outputs/bar_controller/research/train_exit_walkforward.json"))
    args = parser.parse_args()
    root = args.root if args.root.is_absolute() else ROOT / args.root
    output = args.output if args.output.is_absolute() else root / args.output
    result = run(root, output=output)
    print(json.dumps({"status": result["status"], "positive_effect_folds": result["positive_effect_folds"],
                      "eligible_folds": result["eligible_folds"],
                      "walk_forward_gate_pass": result["walk_forward_gate_pass"],
                      "validation_accessed": result["validation_accessed"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
