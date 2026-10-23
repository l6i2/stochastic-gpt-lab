"""Feature-only distribution drift checks; no labels or performance inputs."""
from __future__ import annotations

import csv
import hashlib
import re
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


def _validate_edges(edges: list[float], name: str) -> None:
    if (not isinstance(edges, list)
            or any(isinstance(edge, bool) or not isinstance(edge, (int, float))
                   or not math.isfinite(edge) for edge in edges)
            or any(a >= b for a, b in zip(edges, edges[1:]))):
        raise ValueError(f"Invalid frozen bin edges for {name}")


def _validate_summary(summary: dict[str, Any]) -> None:
    if summary.get("feature_only") is not True:
        raise ValueError("Drift monitor accepts feature-only summaries")
    for key in ("feature_definition_sha256", "feature_producer_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", str(summary.get(key, ""))):
            raise ValueError("Drift summary requires hash-bound feature definitions and producer")
    rows = summary.get("rows")
    features = summary.get("features")
    if type(rows) is not int or rows <= 0 or not isinstance(features, dict) or not features:
        raise ValueError("Summary requires positive row count and features")
    _validate_feature_names(list(features), set(features))
    for name, item in features.items():
        edges = item.get("edges")
        _validate_edges(edges, name)
        counts, missing = item.get("counts"), item.get("missing")
        if (not isinstance(counts, list) or len(counts) != len(edges) + 1
                or any(type(n) is not int or n < 0 for n in counts)
                or type(missing) is not int or missing < 0
                or sum(counts) + missing != rows):
            raise ValueError(f"Invalid summary counts for {name}")
        rate = item.get("missing_rate")
        if (isinstance(rate, bool) or not isinstance(rate, (int, float))
                or not math.isfinite(rate) or not math.isclose(rate, missing / rows, abs_tol=1e-12)):
            raise ValueError(f"Invalid missing rate for {name}")


def summarize_feature_csv(path: Path, *, whitelist: set[str], bins: dict[str, list[float]],
                          feature_definition_sha256: str | None = None,
                          feature_producer_sha256: str | None = None) -> dict[str, Any]:
    """Summarize a feature-only matrix against fixed bins from a prior baseline."""
    path = Path(path)
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        if not fields:
            raise ValueError("Feature matrix has no header")
        if len(set(fields)) != len(fields):
            raise ValueError("Duplicate feature columns")
        _validate_feature_names(fields, whitelist)
        for name, edges in bins.items():
            _validate_edges(edges, name)
        if set(fields) != set(bins):
            raise ValueError("Every feature requires a frozen baseline bin definition")
        counts = {name: [0] * (len(bins[name]) + 1) for name in fields}
        missing = {name: 0 for name in fields}
        rows = 0
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Feature row does not match header width")
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
                index = 0
                while index < len(edges) and numeric > edges[index]:
                    index += 1
                counts[name][index] += 1
    if rows == 0:
        raise ValueError("Feature matrix is empty")
    return {"rows": rows, "feature_definition_sha256": feature_definition_sha256,
            "feature_producer_sha256": feature_producer_sha256, "feature_only": True, "labels_read": False, "pnl_read": False,
            "features": {name: {"edges": list(bins[name]), "counts": counts[name], "missing": missing[name],
                                "missing_rate": missing[name] / rows}
                          for name in fields}}


def compare_drift(baseline: dict[str, Any], current: dict[str, Any], *, psi_limit: float = 0.25,
                  missing_rate_delta_limit: float = 0.10) -> dict[str, Any]:
    _validate_summary(baseline)
    _validate_summary(current)
    for key in ("feature_definition_sha256", "feature_producer_sha256"):
        if baseline[key] != current[key]:
            raise ValueError("Feature definitions or producer changed from frozen baseline")
    if set(baseline["features"]) != set(current["features"]):
        raise ValueError("Feature set changed from frozen baseline")
    for limit in (psi_limit, missing_rate_delta_limit):
        if not math.isfinite(limit) or limit < 0:
            raise ValueError("Drift alert limits must be finite and nonnegative")
    results = {}
    for name, now in current["features"].items():
        if name not in baseline.get("features", {}):
            raise ValueError(f"Feature missing from frozen baseline: {name}")
        ref = baseline["features"][name]
        if now["edges"] != ref["edges"]:
            raise ValueError(f"Frozen bin definition changed for {name}")
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
    parser.add_argument("--feature-definition", type=Path, required=True)
    parser.add_argument("--producer-source", type=Path, required=True)
    args = parser.parse_args()
    whitelist_data = json.loads(args.whitelist.read_text(encoding="utf-8"))
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    bins = {name: item["edges"] for name, item in baseline["features"].items()}
    definition_raw = args.feature_definition.read_bytes()
    definition_hash = hashlib.sha256(definition_raw).hexdigest()
    sidecar = args.feature_definition.with_name(args.feature_definition.name + ".sha256")
    if not sidecar.is_file() or sidecar.read_text(encoding="ascii").split()[0] != definition_hash:
        raise ValueError("Feature definition requires a frozen SHA-256 sidecar")
    definition = json.loads(definition_raw)
    producer_hash = hashlib.sha256(args.producer_source.read_bytes()).hexdigest()
    if (definition.get("producer_sha256") != producer_hash
            or set(definition.get("features", [])) != set(bins)):
        raise ValueError("Feature producer/schema does not match frozen definition")
    current = summarize_feature_csv(args.features, whitelist=set(whitelist_data["features"]), bins=bins,
                                    feature_definition_sha256=definition_hash,
                                    feature_producer_sha256=producer_hash)
    report = compare_drift(baseline, current)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "DRIFT_REPORT_WRITTEN", "output": str(args.output), **report}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
