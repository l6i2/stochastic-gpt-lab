"""Create a bounded-memory, outcome-free descriptive profile of schema-3 TRAIN."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FEATURES = (
    "current_unrealized_pnl", "current_mfe_so_far", "current_mae_so_far",
    "stoch_k", "stoch_d", "relative_volume_20", "volume_zscore_20",
    "ha_direction", "ha_body_percent", "vp_30m_inside_value_area",
    "vp_30m_distance_price_to_POC", "ATR", "spread", "tick_volume", "NY_hour",
)
GROUPS = ("original_signal", "virtual_mode", "snapshot_bar")


def analyze(train_path: Path, output: Path, quality_manifest: Path) -> dict:
    train_path, output = Path(train_path), Path(output)
    if "final_test" in train_path.as_posix().lower():
        raise ValueError("FINAL_TEST input is forbidden")
    quality = json.loads(Path(quality_manifest).read_text(encoding="utf-8"))
    if (quality.get("status") != "PASS_INHERITED_VALIDATION"
            or quality.get("final_test_accessed") is not False):
        raise ValueError("TRAIN data-quality manifest is not accepted")
    quality_manifest_hash = hashlib.sha256(Path(quality_manifest).read_bytes()).hexdigest()
    expected_hash = quality.get("output_sha256", {}).get("train.parquet")
    if not expected_hash:
        raise ValueError("Quality manifest does not pin the TRAIN partition")

    h = hashlib.sha256()
    with train_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    if h.hexdigest() != expected_hash:
        raise ValueError("TRAIN partition hash differs from accepted quality manifest")

    from fastparquet import ParquetFile
    parquet = ParquetFile(train_path)
    available = set(parquet.columns)
    missing_columns = (set(GROUPS) | set(FEATURES)) - available
    if missing_columns:
        raise ValueError(f"TRAIN schema misses expected fields: {sorted(missing_columns)}")
    columns = ["signal_id", *GROUPS, *FEATURES]
    group_rows: dict[tuple[str, str, int], int] = Counter()
    stats = defaultdict(lambda: {"n": 0, "missing": 0, "sum": 0.0, "sum_sq": 0.0,
                                 "min": None, "max": None})
    interactions = Counter()
    signal_ids = set()
    rows = 0
    for frame in parquet.iter_row_groups(columns=columns):
        rows += len(frame)
        signal_ids.update(frame.signal_id.astype(str).unique())
        for key, group in frame.groupby(list(GROUPS), sort=False, dropna=False):
            group_rows[(str(key[0]), str(key[1]), int(key[2]))] += len(group)
        vol = np.asarray(frame["relative_volume_20"], dtype=float)
        ha = np.asarray(frame["ha_direction"], dtype=float)
        side = frame["original_signal"].astype(str).to_numpy()
        mode = frame["virtual_mode"].astype(str).to_numpy()
        vol_bin = np.full(len(frame), "MISSING", dtype=object)
        good = np.isfinite(vol)
        vol_bin[good & (vol < 0.5)] = "LT_0.5"
        vol_bin[good & (vol >= 0.5) & (vol < 1.0)] = "0.5_TO_LT_1"
        vol_bin[good & (vol >= 1.0) & (vol < 2.0)] = "1_TO_LT_2"
        vol_bin[good & (vol >= 2.0)] = "GE_2"
        ha_bin = np.where(np.isfinite(ha), ha.astype(str), "MISSING")
        for s, m, vb, hb in zip(side, mode, vol_bin, ha_bin):
            interactions[(s, m, vb, hb)] += 1
        for feature in FEATURES:
            values = np.asarray(frame[feature], dtype=float)
            finite = values[np.isfinite(values)]
            item = stats[feature]
            item["n"] += len(values)
            item["missing"] += len(values) - len(finite)
            if len(finite):
                item["sum"] += float(finite.sum(dtype=np.float64))
                item["sum_sq"] += float(np.square(finite, dtype=np.float64).sum(dtype=np.float64))
                minimum, maximum = float(finite.min()), float(finite.max())
                item["min"] = minimum if item["min"] is None else min(item["min"], minimum)
                item["max"] = maximum if item["max"] is None else max(item["max"], maximum)

    summaries = {}
    for feature, item in stats.items():
        n = item["n"] - item["missing"]
        mean = item["sum"] / n if n else None
        variance = max(0.0, item["sum_sq"] / n - mean * mean) if n else None
        summaries[feature] = {"rows": item["n"], "nonmissing": n, "missing": item["missing"],
                              "missing_rate": item["missing"] / item["n"] if item["n"] else None,
                              "mean": mean, "std_population": variance ** 0.5 if variance is not None else None,
                              "min": item["min"], "max": item["max"]}
    output.mkdir(parents=True, exist_ok=False)
    try:
        source_label = train_path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        source_label = train_path.name
    result = {
        "status": "TRAIN_DESCRIPTIVE_PROFILE_ONLY",
        "source": source_label,
        "train_sha256": expected_hash,
        "quality_manifest_sha256": quality_manifest_hash,
        "quality_policy": quality["policy_version"],
        "rows": rows,
        "unique_signals": len(signal_ids),
        "snapshot_rows_by_signal_mode_offset": [
            {"original_signal": k[0], "virtual_mode": k[1], "snapshot_bar": k[2], "rows": n}
            for k, n in sorted(group_rows.items())
        ],
        "feature_summary": summaries,
        "descriptive_volume_x_heikin_ashi_counts": [
            {"original_signal": k[0], "virtual_mode": k[1], "relative_volume_20_bin": k[2],
             "ha_direction": k[3], "snapshot_rows": n}
            for k, n in sorted(interactions.items())
        ],
        "interpretation_limits": [
            "This is a snapshot-row description; repeated states within a signal are dependent.",
            "No target, exit outcome, PnL label, Discovery Validation, or FINAL_TEST data was read.",
            "No statistical significance, policy effect, or candidate is claimed.",
        ],
        "final_test_accessed": False,
        "discovery_validation_accessed": False,
        "candidate_promoted": False,
    }
    (output / "train_descriptive_profile.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    report = ["# Schema 3 TRAIN descriptive profile", "",
              f"Rows: {rows:,}; distinct signal IDs: {len(signal_ids):,}.",
              "This report is feature-only and descriptive. Repeated snapshots within a signal are dependent.",
              "No targets, outcomes, Discovery Validation, or FINAL_TEST were read.", "",
              "| Feature | Nonmissing | Missing % | Mean | Population SD | Min | Max |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for feature, item in summaries.items():
        fmt = lambda x: "" if x is None else f"{x:.6g}"
        report.append(f"| {feature} | {item['nonmissing']:,} | {item['missing_rate']:.3%} | "
                      f"{fmt(item['mean'])} | {fmt(item['std_population'])} | {fmt(item['min'])} | {fmt(item['max'])} |")
    (output / "TRAIN_PROFILE.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    package_docs = {
        "PACKAGE_PROTOCOL.md": """# Schema 3 TRAIN package protocol\n\nThis package is generated from the quality-v1 TRAIN partition only. It contains aggregate feature summaries, not event rows or outcomes. Repeated snapshot rows from one signal are dependent; treat signal_id, not a snapshot, as the independent sampling unit.\n\nThe source blocks passed full schema-3 causal and baseline validators. The quality derivative uses `PASS_INHERITED_VALIDATION`: exact membership, partition, parameter, count and hash checks over unchanged rows. A separate monolithic row-by-row validation of the merged 2.4M rows did not finish because its Python maps caused sustained paging. Do not describe that aggregate pass as independent.\n\nThis profile did not read future targets, Discovery Validation, or FINAL_TEST. It is descriptive only; no hypothesis, policy effect, model, or candidate is established.\n""",
        "STRATEGY_SPEC.md": """# Frozen entry strategy\n\nInstrument: US30Cash, M5. Stochastic parameters: K=5, D=3, Slowing=3, oversold=20, overbought=80; trigger MAIN_K. BUY when previous K <= 20 and current K > 20; SELL when previous K >= 80 and current K < 80. Entry is the next candle. TP=240, SL=180, TIME_EXIT=100 observed M5 bars. FOLLOW preserves signal direction; INVERT takes the opposite virtual side.\n\nThis package does not modify or optimize these rules. The rows describe the open virtual position at completed-bar offsets; current state features are causal and targets are not included.\n""",
        "DATA_DICTIONARY.md": """# TRAIN feature profile dictionary\n\nThe full producer schema is pinned by the quality-v1 manifest and the schema-3 validator. This package profiles these causal fields only:\n\n- `current_unrealized_pnl`, `current_mfe_so_far`, `current_mae_so_far`: virtual state through the snapshot cutoff.\n- `stoch_k`, `stoch_d`: Stochastic values at the latest closed bar.\n- `relative_volume_20`, `volume_zscore_20`, `tick_volume`: causal tick-activity measures; they are not broker real-trade volume.\n- `ha_direction`, `ha_body_percent`: Heikin Ashi direction and candle body share.\n- `vp_30m_inside_value_area`, `vp_30m_distance_price_to_POC`: prior-window profile state; missing/profile coverage limitations remain as in source.\n- `ATR`: causal Average True Range.\n- `spread`: bid/ask spread at the snapshot.\n- `NY_hour`: server-to-New-York mapped hour.\n\nStatistics are snapshot-row summaries. Repeated states within a signal are correlated; they are not inferential sample sizes.\n""",
        "GPT_RESEARCH_PROMPT.md": """# GPT instructions for the supplied TRAIN profile\n\nAct as a skeptical research assistant. Use only the supplied profile and do not request or infer access to Discovery Validation or FINAL_TEST. The supplied artifact contains aggregate, feature-only TRAIN summaries, not targets or trade rows. Do not claim feature/outcome relationships, significance, predictive power, or trading edge from marginal distributions.\n\nDescribe data coverage, missingness, and broad feature distributions. State that repeated snapshots from a signal are dependent. Propose no executable rule from this profile alone. Any future hypothesis must use causal fields, a frozen definition and a separate bounded-memory ordered-quote evaluator that first reproduces HOLD; its validation protocol and latency assumptions must be frozen before looking at validation results. Do not alter the Stochastic strategy or promote a candidate.\n""",
    }
    for name, contents in package_docs.items():
        (output / name).write_text(contents, encoding="utf-8")
    package_manifest = {
        "status": "TRAIN_PROFILE_ONLY",
        "dataset_hash": expected_hash,
        "quality_manifest_sha256": quality_manifest_hash,
        "source_master_manifest_sha256": quality.get("source_master_manifest_sha256"),
        "train_rows": rows,
        "train_signals": len(signal_ids),
        "targets_read": False,
        "discovery_validation_read": False,
        "final_test_accessed": False,
        "candidate_promoted": False,
    }
    package_files = sorted(p for p in output.iterdir() if p.is_file())
    package_manifest["files_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in package_files}
    (output / "package_manifest.json").write_text(json.dumps(package_manifest, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, default=Path("outputs/bar_controller/research/quality_v1/train.parquet"))
    parser.add_argument("--quality-manifest", type=Path,
                        default=Path("outputs/bar_controller/research/quality_v1/tick_quality_manifest.json"))
    parser.add_argument("--out", type=Path,
                        default=Path("outputs/gpt_research/train_schema3_quality_v1"))
    args = parser.parse_args()
    absolute = lambda p: p if p.is_absolute() else ROOT / p
    result = analyze(absolute(args.train), absolute(args.out), absolute(args.quality_manifest))
    print(json.dumps({k: result[k] for k in ("status", "rows", "unique_signals", "final_test_accessed")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
