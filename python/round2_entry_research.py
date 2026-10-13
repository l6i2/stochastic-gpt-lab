"""Freeze a small domain-defined entry hypothesis set on TRAIN, then validate once.

No FINAL_TEST data is read or accepted. Hypotheses never remove/skip signals;
they describe conditional FOLLOW-versus-INVERT outcomes for research only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from evaluate_hypotheses import _bootstrap_ci, _select
from research import FEATURE_COLUMNS, read_dataset, validate

SEED = 20261013


def hypotheses() -> list[dict]:
    """Fixed market-motivated conditions; no outcome-based threshold search."""
    definitions = []
    for side, aligned_ha, transition, profile_state in (
        ("BUY", 1, "ha_changed_to_bullish", "vp_session_above_value_area"),
        ("SELL", -1, "ha_changed_to_bearish", "vp_session_below_value_area"),
    ):
        candidates = [
            ("ha_alignment", [{"column": "ha_direction", "operator": "eq", "value": aligned_ha}], ["heikin_ashi"]),
            ("volume_at_or_above_baseline", [{"column": "relative_volume_20", "operator": "ge", "value": 1.0}], ["volume"]),
            ("ha_alignment_and_volume", [
                {"column": "ha_direction", "operator": "eq", "value": aligned_ha},
                {"column": "relative_volume_20", "operator": "ge", "value": 1.0}], ["heikin_ashi", "volume"]),
            ("ha_transition_and_volume", [
                {"column": transition, "operator": "eq", "value": 1},
                {"column": "relative_volume_20", "operator": "ge", "value": 1.0}], ["heikin_ashi", "volume"]),
            ("ha_alignment_and_outside_value_area", [
                {"column": "ha_direction", "operator": "eq", "value": aligned_ha},
                {"column": profile_state, "operator": "eq", "value": 1}], ["heikin_ashi", "volume_profile"]),
        ]
        for name, conditions, family in candidates:
            definitions.append({"hypothesis_id": f"R2-{side}-{name}", "signal_side": side,
                                "conditions": [{"column": "follow_side", "operator": "eq", "value": side}, *conditions],
                                "feature_family": family})
    return definitions


def validate_contract(path: Path, expected_partition: str) -> pd.DataFrame:
    if "final_test" in str(path).lower() or path.name.lower().startswith("final"):
        raise ValueError("FINAL_TEST paths are categorically refused")
    if path.name.lower() != ("train.parquet" if expected_partition == "TRAIN" else "validation.parquet"):
        raise ValueError(f"Expected the purged {expected_partition} parquet, got {path.name}")
    frame = read_dataset(path)
    errors = validate(frame)
    if errors:
        raise ValueError("Dataset contract failed: " + "; ".join(errors))
    return frame


def _paired(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.loc[frame.follow_PnL.notna() & frame.invert_PnL.notna()].copy()


def freeze(train_path: Path, out: Path) -> dict:
    train = _paired(validate_contract(train_path, "TRAIN"))
    if out.exists():
        raise ValueError(f"Refusing to overwrite frozen hypothesis directory: {out}")
    split_manifest = json.loads(Path("outputs/splits/split_manifest.json").read_text(encoding="utf-8"))
    master_hash = split_manifest.get("dataset_sha256")
    if not master_hash or split_manifest.get("final_test_parquet_written") is not False:
        raise ValueError("Split manifest missing protected-master fingerprint or FINAL_TEST guard")
    out.mkdir(parents=True)
    rows = []
    for spec in hypotheses():
        selected = _paired(_select(train, spec["conditions"]))
        side = spec["signal_side"]
        vals = selected.directional_advantage.to_numpy(dtype=float)
        item = {
            **spec, "date_utc": "2026-10-13", "version": 1,
            "source": "Predeclared round-two causal entry research protocol",
            "causal_at_signal_time": True, "outcome": "directional_advantage",
            "expected_sign": 1,
            "train_sample_size": int(len(selected)),
            "train_effect": {"mean_directional_advantage": float(np.mean(vals)) if len(vals) else None,
                             "median_directional_advantage": float(np.median(vals)) if len(vals) else None,
                             "mean_follow_pnl": float(selected.follow_PnL.mean()) if len(vals) else None,
                             "mean_invert_pnl": float(selected.invert_PnL.mean()) if len(vals) else None},
            "minimum_support": {"overall": 500, "intended_side": 500},
            "missing_handling": "No imputation; conditions and outcomes must be observed.",
            "failure_criterion": "Do not promote if validation's week-cluster 95% CI crosses zero, mean FOLLOW is not greater than mean INVERT, support is insufficient, or promotion gates otherwise fail.",
            "validation_criterion": "One evaluation on purged DISCOVERY_VALIDATION; report BUY and SELL separately; apply docs/PROMOTION_CRITERIA.md as frozen before validation.",
            "status": "FROZEN_TRAIN_READY_FOR_VALIDATION",
            "dataset_sha256": master_hash,
            "train_split_sha256": hashlib.sha256(train_path.read_bytes()).hexdigest(),
            "signal_side_scope": side,
            "interpretation": "Conditional research association only; does not skip or alter any Stochastic signal.",
        }
        path = out / f"{spec['hypothesis_id']}.json"
        raw = (json.dumps(item, indent=2, allow_nan=False) + "\n").encode()
        path.write_bytes(raw)
        rows.append({"hypothesis_id": spec["hypothesis_id"], "train_n": len(selected),
                     "mean_advantage": item["train_effect"]["mean_directional_advantage"],
                     "follow_mean": item["train_effect"]["mean_follow_pnl"],
                     "invert_mean": item["train_effect"]["mean_invert_pnl"],
                     "sha256": hashlib.sha256(raw).hexdigest()})
    report_dir = Path("outputs/entry_research_round2/train_report")
    report_dir.mkdir(parents=True, exist_ok=True)
    summary_path = report_dir / "frozen_hypotheses_train.csv"
    if summary_path.exists():
        raise ValueError(f"Refusing to overwrite frozen TRAIN report: {summary_path}")
    pd.DataFrame(rows).to_csv(summary_path, index=False)
    manifest = {"partition": "TRAIN", "rows": len(train), "candidate_count": len(rows),
                "hypothesis_sha256": {r["hypothesis_id"]: r["sha256"] for r in rows},
                "final_test_accessed": False, "skip_or_no_trade_policy": False}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def evaluate_one(frame: pd.DataFrame, spec: dict) -> dict:
    selected = _paired(_select(frame, spec["conditions"]))
    values = selected.directional_advantage.to_numpy(dtype=float)
    ci = _bootstrap_ci(selected, "directional_advantage", SEED, repetitions=12000,
                       quantiles=(0.0025, 0.9975)) if len(selected) else [None, None]
    nominal_ci = _bootstrap_ci(selected, "directional_advantage", SEED) if len(selected) else [None, None]
    side_counts = {side: int(selected.follow_side.eq(side).sum()) for side in ("BUY", "SELL")}
    minimum = spec["minimum_support"]
    enough = len(values) >= minimum["overall"] and side_counts[spec["signal_side"]] >= minimum["intended_side"]
    mean = float(values.mean()) if len(values) else None
    months = pd.to_datetime(selected.signal_utc_epoch, unit="s", utc=True).dt.tz_convert(None).dt.to_period("M")
    month_means = selected.assign(_month=months).groupby("_month").directional_advantage.mean()
    month_consistency = float((month_means > 0).mean()) if len(month_means) else None
    month_gate = len(month_means) >= 6 and month_consistency is not None and month_consistency >= 0.70
    survives = bool(enough and mean is not None and ci[0] > 0 and
                    selected.follow_PnL.mean() > selected.invert_PnL.mean() and month_gate)
    rejected = bool(enough and mean is not None and ci[1] < 0)
    return {"hypothesis_id": spec["hypothesis_id"], "signal_side": spec["signal_side"],
            "status": "SURVIVES_VALIDATION" if survives else ("REJECTED" if rejected else "INCONCLUSIVE"),
            "n_paired": len(values), "n_by_signal_side": side_counts,
            "mean_directional_advantage": mean,
            "median_directional_advantage": float(np.median(values)) if len(values) else None,
            "mean_follow_pnl": float(selected.follow_PnL.mean()) if len(values) else None,
            "mean_invert_pnl": float(selected.invert_PnL.mean()) if len(values) else None,
            "follow_win_rate": float((selected.follow_PnL > 0).mean()) if len(values) else None,
            "invert_win_rate": float((selected.invert_PnL > 0).mean()) if len(values) else None,
            "directional_advantage_ci99_5_week_cluster_bootstrap_bonferroni": ci,
            "directional_advantage_ci95_nominal": nominal_ci,
            "month_count": int(len(month_means)), "positive_month_fraction": month_consistency,
            "monthly_mean_directional_advantage": {str(k): float(v) for k, v in month_means.items()},
            "bootstrap_seed": SEED, "bootstrap_repetitions": 12000,
            "minimum_support_met": enough,
            "warning": "Ten related hypotheses were evaluated as one discovery family; the 99.5% interval uses Bonferroni alpha 0.005 per hypothesis, while the nominal 95% interval is descriptive. No candidate promotion follows from this status alone."}


def write_train_interactions(train_path: Path, out: Path) -> dict:
    train = _paired(validate_contract(train_path, "TRAIN"))
    if out.exists():
        raise ValueError(f"Refusing to overwrite TRAIN interaction report: {out}")
    work = train.copy()
    work["_volume_state"] = np.where(work.relative_volume_20.ge(1.0), "at_or_above_1", "below_1")
    work.loc[work.relative_volume_20.isna(), "_volume_state"] = "missing"
    work["_ha_state"] = work.ha_direction.map({1: "bullish", -1: "bearish", 0: "doji"}).fillna("missing")
    work["_ha_transition"] = np.select(
        [work.ha_changed_to_bullish.eq(1), work.ha_changed_to_bearish.eq(1)],
        ["to_bullish", "to_bearish"], default="unchanged")
    work.loc[work.ha_status.ne("ready"), "_ha_transition"] = "missing"
    state = np.select([work.vp_session_inside_value_area.eq(1),
                       work.vp_session_above_value_area.eq(1),
                       work.vp_session_below_value_area.eq(1)],
                      ["inside", "above", "below"], default="unavailable")
    work["_profile_state"] = state
    profile_available = work.vp_session_status.astype("string").str.startswith("available", na=False)
    work.loc[~profile_available, "_profile_state"] = "unavailable"
    edges = work.exit_speed_from_zone.dropna().quantile([.25, .5, .75]).tolist()
    bands = np.searchsorted(np.asarray(edges, dtype=float), work.exit_speed_from_zone.to_numpy(dtype=float), side="left") + 1
    work["_exit_speed_band"] = pd.Series([f"Q{n}" for n in bands], index=work.index, dtype="string")
    work.loc[work.exit_speed_from_zone.isna(), "_exit_speed_band"] = "missing"
    rows = []
    definitions = [
        ("volume_x_ha_direction", "_volume_state", "_ha_state"),
        ("volume_x_ha_transition", "_volume_state", "_ha_transition"),
        ("ha_x_session_value_area", "_ha_state", "_profile_state"),
        ("exit_speed_x_volume", "_exit_speed_band", "_volume_state"),
    ]
    for side in ("BUY", "SELL"):
        subset = work.loc[work.follow_side.eq(side)]
        for family, left, right in definitions:
            for (a, b), group in subset.groupby([left, right], dropna=False, observed=False):
                rows.append({"family": family, "signal_side": side, "feature_a": left,
                             "group_a": str(a), "feature_b": right, "group_b": str(b),
                             "n_paired": len(group),
                             "mean_directional_advantage": float(group.directional_advantage.mean()) if len(group) else None,
                             "median_directional_advantage": float(group.directional_advantage.median()) if len(group) else None,
                             "follow_mean_pnl": float(group.follow_PnL.mean()) if len(group) else None,
                             "invert_mean_pnl": float(group.invert_PnL.mean()) if len(group) else None})
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    meta = {"partition": "TRAIN", "source_sha256": hashlib.sha256(train_path.read_bytes()).hexdigest(),
            "paired_train_rows": len(train), "exit_speed_train_quartile_edges": edges,
            "definitions": [item[0] for item in definitions], "final_test_accessed": False,
            "note": "Descriptive, fixed interaction groups; no outcome threshold search or promotion."}
    out.with_suffix(".manifest.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def validate_frozen(validation_path: Path, hypothesis_dir: Path, out: Path) -> list[dict]:
    frame = _paired(validate_contract(validation_path, "DISCOVERY_VALIDATION"))
    if out.exists():
        raise ValueError(f"Refusing to overwrite validation results: {out}")
    specs = sorted(hypothesis_dir.glob("R2-*.json"))
    if len(specs) != 10:
        raise ValueError(f"Expected exactly 10 frozen hypotheses, found {len(specs)}")
    raw_items = [(p, p.read_bytes(), json.loads(p.read_text(encoding="utf-8"))) for p in specs]
    if any("final_test" in item.get("hypothesis_id", "").lower() for _, _, item in raw_items):
        raise ValueError("Invalid hypothesis identifier")
    out.mkdir(parents=True)
    results = []
    for path, raw, spec in raw_items:
        result = evaluate_one(frame, spec)
        result["hypothesis_sha256"] = hashlib.sha256(raw).hexdigest()
        results.append(result)
    (out / "results.json").write_text(json.dumps(results, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    manifest = {"partition": "DISCOVERY_VALIDATION", "rows": len(frame),
                "validation_file_sha256": hashlib.sha256(validation_path.read_bytes()).hexdigest(),
                "hypothesis_hashes": {p.name: hashlib.sha256(raw).hexdigest() for p, raw, _ in raw_items},
                "final_test_accessed": False, "run_once": True}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    f = subs.add_parser("freeze"); f.add_argument("train", type=Path); f.add_argument("--out", type=Path, required=True)
    i = subs.add_parser("train-interactions"); i.add_argument("train", type=Path); i.add_argument("--out", type=Path, required=True)
    v = subs.add_parser("validate"); v.add_argument("validation", type=Path); v.add_argument("hypotheses", type=Path); v.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "freeze":
            result = freeze(args.train, args.out)
        elif args.command == "train-interactions":
            result = write_train_interactions(args.train, args.out)
        else:
            result = validate_frozen(args.validation, args.hypotheses, args.out)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"Round-two entry research failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
