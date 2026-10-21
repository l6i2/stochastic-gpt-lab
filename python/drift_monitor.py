"""Feature-only distribution drift checks; no labels or performance inputs."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

FORBIDDEN = {"pnl", "profit", "win_rate", "profit_factor", "mfe", "mae", "exit_price",
             "exit_reason", "target", "label", "candidate_pnl", "follow_pnl", "invert_pnl"}


def _validate_feature_names(names: list[str], whitelist: set[str]) -> None:
    if not set(names).issubset(whitelist):
        raise ValueError("Input contains columns outside the frozen feature whitelist")
    for name in names:
        parts = name.casefold().replace("-", "_").split("_")
        if any(part in FORBIDDEN for part in parts):
            raise ValueError(f"Forbidden outcome/label field: {name}")


def summarize_feature_csv(path: Path, *, whitelist: set[str], bins: dict[str, list[float]]) -> dict[str, Any]:
    """Summarize a feature-only matrix against fixed bins from a prior baseline."""
    path = Path(path)
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        if not fields:
            raise ValueError("Feature matrix has no header")
        _validate_feature_names(fields, whitelist)
        if set(fields) != set(bins):
            raise ValueError("Every feature requires a frozen baseline bin definition")
        counts = {name: [0] * (len(bins[name]) + 1) for name in fields}
        missing = {name: 0 for name in fields}
        rows = 0
        for row in reader:
            rows += 1
            for name in fields:
                value = row.get(name, "")
                if value in (None, ""):
                    missing[name] += 1
                    continue
                try:
                    numeric = float(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Non-numeric feature value: {name}") from exc
                if not math.isfinite(numeric):
                    missing[name] += 1
                    continue
                edges = bins[name]
                if any(not math.isfinite(float(edge)) for edge in edges) or sorted(edges) != edges:
                    raise ValueError(f"Invalid frozen bin edges for {name}")
                index = 0
                while index < len(edges) and numeric > edges[index]:
                    index += 1
                counts[name][index] += 1
    if rows == 0:
        raise ValueError("Feature matrix is empty")
    return {"rows": rows, "feature_only": True, "labels_read": False, "pnl_read": False,
            "features": {name: {"counts": counts[name], "missing": missing[name],
                                "missing_rate": missing[name] / rows}
                          for name in fields}}


def compare_drift(baseline: dict[str, Any], current: dict[str, Any], *, psi_limit: float = 0.25,
                  missing_rate_delta_limit: float = 0.10) -> dict[str, Any]:
    if baseline.get("feature_only") is not True or current.get("feature_only") is not True:
        raise ValueError("Drift monitor accepts feature-only summaries")
    results = {}
    for name, now in current["features"].items():
        if name not in baseline.get("features", {}):
            raise ValueError(f"Feature missing from frozen baseline: {name}")
        ref = baseline["features"][name]
        if len(now["counts"]) != len(ref["counts"]):
            raise ValueError(f"Frozen bin count changed for {name}")
        smoothing = 1e-6
        ref_total, now_total = sum(ref["counts"]), sum(now["counts"])
        psi = 0.0
        for a, b in zip(ref["counts"], now["counts"]):
            p = (a + smoothing) / (ref_total + smoothing * len(ref["counts"]))
            q = (b + smoothing) / (now_total + smoothing * len(now["counts"]))
            psi += (q - p) * math.log(q / p)
        missing_delta = abs(float(now["missing_rate"]) - float(ref["missing_rate"]))
        results[name] = {"psi": psi, "missing_rate_delta": missing_delta,
                         "psi_alert": psi > psi_limit,
                         "missingness_alert": missing_delta > missing_rate_delta_limit}
    return {"features": results, "drift_only": True, "labels_read": False, "pnl_read": False,
            "candidate_scored": False, "threshold_tuning": False}


def _count_psi(reference: dict[str, int], current: dict[str, int]) -> float:
    categories = sorted(set(reference) | set(current))
    if not categories or sum(reference.values()) == 0 or sum(current.values()) == 0:
        return 0.0
    smoothing = 1e-6
    ref_total, now_total = sum(reference.values()), sum(current.values())
    score = 0.0
    for key in categories:
        p = (reference.get(key, 0) + smoothing) / (ref_total + smoothing * len(categories))
        q = (current.get(key, 0) + smoothing) / (now_total + smoothing * len(categories))
        score += (q - p) * math.log(q / p)
    return score


def compare_health_metadata(baseline: dict[str, Any], current: dict[str, Any], *,
                            psi_limit: float = 0.25) -> dict[str, Any]:
    """Compare only predeclared distribution/coverage metadata, never outcomes."""
    keys = ("spread_distribution_metadata", "session_coverage_metadata",
            "regime_coverage_metadata", "volatility_coverage_metadata",
            "latency_distribution_metadata")
    distributions = {}
    for key in keys:
        ref, now = baseline.get(key), current.get(key)
        if ref is None and now is None:
            continue
        if not isinstance(ref, dict) or not isinstance(now, dict):
            raise ValueError(f"Drift metadata pair missing for {key}")
        psi = _count_psi(ref, now)
        distributions[key] = {"psi": psi, "alert": psi > psi_limit,
                              "baseline_total": sum(ref.values()), "current_total": sum(now.values())}
    quality = {
        "missing_utc_days_changed": baseline.get("missing_utc_days") != current.get("missing_utc_days"),
        "invalid_ticks_changed": baseline.get("invalid_ticks") != current.get("invalid_ticks"),
        "invalid_bars_changed": baseline.get("invalid_bars") != current.get("invalid_bars"),
        "tick_quality_current": "PASS" if current.get("invalid_ticks") == 0 else "FAIL",
        "session_calendar_verified": current.get("session_calendar_verified") is True,
    }
    return {"metadata_distributions": distributions, "quality_and_gaps": quality,
            "drift_only": True, "labels_read": False, "pnl_read": False,
            "candidate_scored": False, "threshold_tuning": False}


def summarize_shadow_latency(path: Path, *, edges_ms: list[float]) -> dict[str, int]:
    """Count decision latencies from shadow logs; no decision outcomes are read."""
    if sorted(edges_ms) != edges_ms or any(not math.isfinite(float(v)) for v in edges_ms):
        raise ValueError("Latency edges must be finite and ascending")
    counts = {f"bin_{i}": 0 for i in range(len(edges_ms) + 1)}
    with Path(path).open("r", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            value = float(row["latency_ms"])
            if not math.isfinite(value) or value < 0:
                raise ValueError("Shadow latency must be finite and nonnegative")
            bucket = 0
            while bucket < len(edges_ms) and value > edges_ms[bucket]:
                bucket += 1
            counts[f"bin_{bucket}"] += 1
    return counts


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("features", type=Path)
    parser.add_argument("--whitelist", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    whitelist_data = json.loads(args.whitelist.read_text(encoding="utf-8"))
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    bins = {name: item["edges"] for name, item in baseline["features"].items()}
    current = summarize_feature_csv(args.features, whitelist=set(whitelist_data["features"]), bins=bins)
    report = compare_drift(baseline, current)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "DRIFT_REPORT_WRITTEN", "output": str(args.output), **report}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
