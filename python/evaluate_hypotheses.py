"""Evaluate frozen hypotheses on DISCOVERY_VALIDATION only; FINAL_TEST is not accepted."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from research import FEATURE_COLUMNS, read_dataset, validate

ALLOWED_COLUMNS = set(FEATURE_COLUMNS) | {
    "follow_side", "invert_side", "trigger_line", "signal_time_msc", "NY_hour", "NY_minute", "session"
}
OPERATORS = {"eq", "ge", "le", "gt", "lt"}


def _bootstrap_ci(values: pd.DataFrame, outcome: str, seed: int, repetitions: int = 4000):
    weeks = (pd.to_datetime(values.signal_utc_epoch, unit="s", utc=True)
             .dt.tz_localize(None).dt.to_period("W").astype(str))
    groups = [part[outcome].to_numpy(dtype=float) for _, part in values.assign(_week=weeks).groupby("_week", sort=True)]
    if len(groups) < 2:
        return [None, None]
    rng = np.random.default_rng(seed)
    estimates = np.empty(repetitions)
    for i in range(repetitions):
        draw = rng.integers(0, len(groups), size=len(groups))
        estimates[i] = np.concatenate([groups[j] for j in draw]).mean()
    return [float(x) for x in np.quantile(estimates, [0.025, 0.975])]


def _select(frame: pd.DataFrame, conditions: list[dict]) -> pd.DataFrame:
    mask = pd.Series(True, index=frame.index)
    for condition in conditions:
        column, operator, value = condition.get("column"), condition.get("operator"), condition.get("value")
        if column not in ALLOWED_COLUMNS or operator not in OPERATORS:
            raise ValueError(f"Unsafe or non-causal condition: {condition}")
        series = frame[column]
        mask &= {"eq": series.eq, "ge": series.ge, "le": series.le, "gt": series.gt, "lt": series.lt}[operator](value)
    return frame.loc[mask].copy()


def evaluate(frame: pd.DataFrame, hypothesis: dict, seed: int = 20261013) -> dict:
    if hypothesis.get("causal_at_signal_time") is not True:
        raise ValueError("Hypothesis must attest features are causal at signal time")
    outcome = hypothesis.get("outcome")
    if outcome != "directional_advantage":
        raise ValueError("Only the predeclared paired directional_advantage outcome is supported")
    selected = _select(frame, hypothesis.get("conditions", []))
    selected = selected.loc[selected.follow_PnL.notna() & selected.invert_PnL.notna()].copy()
    sign = int(hypothesis.get("expected_sign", 0))
    if sign not in (-1, 1):
        raise ValueError("expected_sign must be -1 or 1")
    counts = {side: int(selected.follow_side.eq(side).sum()) for side in ("BUY", "SELL")}
    minimum = hypothesis.get("minimum_support", {})
    intended_side = hypothesis.get("signal_side")
    required_n = int(minimum.get("intended_side", minimum.get("overall", 0)))
    values = selected.directional_advantage.to_numpy(dtype=float)
    mean = float(values.mean()) if len(values) else None
    ci = _bootstrap_ci(selected, "directional_advantage", seed) if len(values) else [None, None]
    enough = len(values) >= int(minimum.get("overall", 0)) and counts.get(intended_side, 0) >= required_n
    survives = bool(enough and mean is not None and sign * ci[0] > 0 and
                    selected.follow_PnL.mean() > selected.invert_PnL.mean())
    opposite = bool(enough and mean is not None and sign * ci[1] < 0)
    status = "SURVIVES_VALIDATION" if survives else ("REJECTED" if opposite else "INCONCLUSIVE")
    return {
        "hypothesis_id": hypothesis["hypothesis_id"], "status": status,
        "n_paired": len(values), "n_by_signal_side": counts,
        "mean_directional_advantage": mean,
        "median_directional_advantage": float(np.median(values)) if len(values) else None,
        "mean_follow_pnl": float(selected.follow_PnL.mean()) if len(values) else None,
        "mean_invert_pnl": float(selected.invert_PnL.mean()) if len(values) else None,
        "directional_advantage_ci95_week_cluster_bootstrap": ci,
        "bootstrap_seed": seed, "bootstrap_repetitions": 4000,
        "missing_rows_excluded": int(frame.loc[_select(frame, hypothesis.get("conditions", [])).index,
                                                 ["follow_PnL", "invert_PnL"]].isna().any(axis=1).sum()),
        "follow_win_rate": float((selected.follow_PnL > 0).mean()) if len(values) else None,
        "invert_win_rate": float((selected.invert_PnL > 0).mean()) if len(values) else None,
        "sell_out_of_scope_for_side_specific_hypothesis": intended_side == "BUY",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("validation", type=Path, help="Must be the purged DISCOVERY_VALIDATION Parquet")
    parser.add_argument("hypotheses", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20261013)
    args = parser.parse_args()
    try:
        if "final_test" in str(args.validation).lower() or args.validation.name.lower().startswith("final"):
            raise ValueError("FINAL_TEST paths are categorically refused")
        frame = read_dataset(args.validation)
        errors = validate(frame)
        if errors:
            raise ValueError("Validation dataset failed contract: " + "; ".join(errors))
        args.output.mkdir(parents=True, exist_ok=False)
        results = []
        for path in args.hypotheses:
            raw = path.read_bytes()
            hypothesis = json.loads(raw)
            result = evaluate(frame, hypothesis, args.seed)
            result["hypothesis_sha256"] = hashlib.sha256(raw).hexdigest()
            results.append(result)
        (args.output / "results.json").write_text(json.dumps(results, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        manifest = {"partition": "DISCOVERY_VALIDATION", "rows": len(frame),
                    "validation_file_sha256": hashlib.sha256(args.validation.read_bytes()).hexdigest(),
                    "hypotheses": [{"path": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in args.hypotheses],
                    "final_test_accessed": False}
        (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(results, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"Hypothesis evaluation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
