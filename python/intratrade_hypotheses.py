"""Freeze fixed, small intra-trade hypotheses on TRAIN and evaluate once on validation."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

try:
    from .parquet_io import read_parquet
    from .train_event_source import assert_train_only_source_path, read_rows_for_ids
except ImportError:
    from parquet_io import read_parquet
    from train_event_source import assert_train_only_source_path, read_rows_for_ids

ROOT = Path(__file__).resolve().parents[1]
RULES = {
    "ITH-HA-ADVERSE": {"feature": "ha_direction", "condition": "ha_direction != virtual_side_sign",
                       "minimum_support": 100},
    "ITH-STOCH-TURN": {"feature": "stoch_direction_change", "condition": "stoch_direction_change == 1",
                        "minimum_support": 100},
    "ITH-VP-OUTSIDE": {"feature": "vp_30m_inside_value_area", "condition": "inside_value_area == 0",
                       "minimum_support": 100},
    "ITH-PROFIT-HA": {"feature": "current_unrealized_pnl", "condition": "current_unrealized_pnl >= 60 and ha adverse",
                       "minimum_support": 100},
}


def _reject_final(path: Path) -> None:
    assert_train_only_source_path(path)


def condition(frame: pd.DataFrame, hypothesis_id: str) -> pd.Series:
    side_sign = frame["virtual_side"].map({"BUY": 1, "SELL": -1})
    if hypothesis_id == "ITH-HA-ADVERSE":
        return pd.to_numeric(frame["ha_direction"], errors="coerce") == -side_sign
    if hypothesis_id == "ITH-STOCH-TURN":
        return pd.to_numeric(frame["stoch_direction_change"], errors="coerce") == 1
    if hypothesis_id == "ITH-VP-OUTSIDE":
        return pd.to_numeric(frame["vp_30m_inside_value_area"], errors="coerce") == 0
    if hypothesis_id == "ITH-PROFIT-HA":
        ha = pd.to_numeric(frame["ha_direction"], errors="coerce") == -side_sign
        pnl = pd.to_numeric(frame["current_unrealized_pnl"], errors="coerce")
        return (pnl >= 60) & ha
    raise ValueError(f"Unknown hypothesis: {hypothesis_id}")


def load_joined(snapshots_path: Path, targets_path: Path) -> pd.DataFrame:
    _reject_final(snapshots_path)
    _reject_final(targets_path)
    snapshots = read_parquet(snapshots_path)
    targets = read_rows_for_ids(targets_path, set(snapshots.signal_id.astype(str)))
    return snapshots.merge(targets, on=["snapshot_id", "signal_id", "virtual_mode", "snapshot_bar"],
                           how="inner", validate="one_to_one")


def freeze(train_path: Path, targets_path: Path, output: Path) -> dict:
    data = load_joined(train_path, targets_path)
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"Refusing to overwrite frozen hypothesis manifest: {manifest_path}")
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"status": "FROZEN_TRAIN_ONLY", "final_test_accessed": False, "hypotheses": []}
    for hypothesis_id, rule in RULES.items():
        matched = data.loc[condition(data, hypothesis_id)]
        rest = data.loc[~condition(data, hypothesis_id)]
        n = int(len(matched))
        hypothesis = {"hypothesis_id": hypothesis_id, "version": 1,
                      "date": datetime.now(timezone.utc).date().isoformat(),
                      "source": "pre-registered simple rule family; freeze before validation",
                      "feature_family": rule["feature"], "signal_side": "BUY and SELL reported separately",
                      "expected_direction": "higher reversal risk than unmatched snapshots",
                      "FOLLOW_INVERT": "evaluate both separately", "definition": rule["condition"],
                      "sample_size_train": n,
                      "train_reversal_rate": float(matched.reversal_event.mean()) if n else None,
                      "train_comparison_rate": float(rest.reversal_event.mean()) if len(rest) else None,
                      "minimum_support": rule["minimum_support"],
                      "missing_handling": "missing values do not satisfy the rule",
                      "failure_criterion": "validation effect is not positive or support is below minimum",
                      "validation_criterion": "same frozen definition, sample support, and positive reversal-rate difference",
                      "status": "FROZEN"}
        path = output / f"{hypothesis_id}.json"
        payload = json.dumps(hypothesis, indent=2, sort_keys=True) + "\n"
        path.write_text(payload, encoding="utf-8")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest["hypotheses"].append({"hypothesis_id": hypothesis_id, "path": path.name, "sha256": digest})
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def evaluate(validation_path: Path, targets_path: Path, frozen_dir: Path, output: Path) -> dict:
    _reject_final(validation_path)
    _reject_final(targets_path)
    output.mkdir(parents=True, exist_ok=True)
    result_path = output / "validation.json"
    if result_path.exists():
        raise FileExistsError("Validation is single-use; refusing to overwrite existing results")
    manifest = json.loads((frozen_dir / "manifest.json").read_text(encoding="utf-8"))
    data = load_joined(validation_path, targets_path)
    results = []
    for frozen in manifest["hypotheses"]:
        path = frozen_dir / frozen["path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != frozen["sha256"]:
            raise ValueError(f"Frozen hypothesis hash mismatch: {path.name}")
        hypothesis = json.loads(path.read_text(encoding="utf-8"))
        matched_mask = condition(data, hypothesis["hypothesis_id"])
        matched, other = data.loc[matched_mask], data.loc[~matched_mask]
        n = int(len(matched))
        difference = float(matched.reversal_event.mean() - other.reversal_event.mean()) if n and len(other) else None
        side_metrics = {}
        for side in ("BUY", "SELL"):
            side_rows = matched[matched.original_signal == side]
            side_metrics[side] = {"n": int(len(side_rows)),
                                  "reversal_rate": float(side_rows.reversal_event.mean()) if len(side_rows) else None}
        status = "INCONCLUSIVE"
        if n >= int(hypothesis["minimum_support"]) and difference is not None and difference > 0:
            status = "SURVIVES_VALIDATION"
        elif n >= int(hypothesis["minimum_support"]) and difference is not None and difference <= 0:
            status = "REJECTED"
        results.append({"hypothesis_id": hypothesis["hypothesis_id"], "definition_sha256": digest,
                        "n": n, "comparison_n": int(len(other)), "reversal_rate_difference": difference,
                        "BUY": side_metrics["BUY"], "SELL": side_metrics["SELL"], "status": status})
    result = {"status": "EVALUATED_ONCE", "final_test_accessed": False,
              "validation_snapshot_rows": len(data), "results": results}
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    fr = sub.add_parser("freeze")
    fr.add_argument("--train", type=Path, default=Path("outputs/intratrade/splits/train.parquet"))
    fr.add_argument("--targets", type=Path, default=Path("outputs/intratrade/master/intratrade_targets.csv"))
    fr.add_argument("--out", type=Path, default=Path("research/intratrade_hypotheses"))
    va = sub.add_parser("validate")
    va.add_argument("--validation", type=Path, default=Path("outputs/intratrade/splits/validation.parquet"))
    va.add_argument("--targets", type=Path, default=Path("outputs/intratrade/master/intratrade_targets.csv"))
    va.add_argument("--hypotheses", type=Path, default=Path("research/intratrade_hypotheses"))
    va.add_argument("--out", type=Path, default=Path("outputs/intratrade/validation"))
    args = parser.parse_args()
    def absolute(path: Path) -> Path:
        return path if path.is_absolute() else ROOT / path
    if args.action == "freeze":
        result = freeze(absolute(args.train), absolute(args.targets), absolute(args.out))
    else:
        result = evaluate(absolute(args.validation), absolute(args.targets), absolute(args.hypotheses), absolute(args.out))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
