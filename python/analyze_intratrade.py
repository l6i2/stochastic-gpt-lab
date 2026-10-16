"""TRAIN-only descriptive reports for validated intra-trade snapshots."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

try:
    from .parquet_io import read_parquet
except ImportError:
    from parquet_io import read_parquet


def analyze(train_path: Path, targets_path: Path, out: Path) -> dict:
    # This legacy descriptive checkpoint does not need the 257-column frame
    # resident in memory. Exhaustive causal research uses the versioned path.
    import fastparquet
    available=set(fastparquet.ParquetFile(train_path).columns)
    requested={'snapshot_id','signal_id','snapshot_bar','original_signal','virtual_mode',
               'virtual_side','ha_direction','stoch_direction_change',
               'vp_30m_inside_value_area','vp_30m_above_value_area',
               'vp_30m_below_value_area','volume_expansion',
               'current_unrealized_pnl','mfe_so_far','mae_so_far','stoch_k',
               'atr_14','signal_time_msc','snapshot_time_msc'}
    train = read_parquet(train_path,columns=sorted(available & requested))
    train_ids=set(train.signal_id.astype(str))
    targets=pd.concat([chunk.loc[chunk.signal_id.astype(str).isin(train_ids)]
                       for chunk in pd.read_csv(targets_path,chunksize=10000)],ignore_index=True)
    if train["signal_id"].nunique() == 0:
        raise ValueError("TRAIN snapshots are empty")
    data = train.merge(targets, on=["snapshot_id", "signal_id", "virtual_mode", "snapshot_bar"],
                       how="left", validate="one_to_one", suffixes=("", "_target"))
    if len(data) != len(train):
        raise ValueError("Target join changed TRAIN row count")
    if data["reversal_event"].notna().sum() == 0:
        raise ValueError("TRAIN has no completed labels to analyze")
    out.mkdir(parents=True, exist_ok=True)
    label_cols = ["reversal_event", "tp_before_sl_after_snapshot", "sl_before_tp_after_snapshot",
                  "future_pnl_to_exit", "future_max_favorable_move", "future_max_adverse_move", "profit_erosion"]
    grouped = data.groupby(["snapshot_bar", "original_signal", "virtual_mode"], dropna=False)
    rows = []
    for keys, frame in grouped:
        row = dict(zip(("snapshot_bar", "original_signal", "virtual_mode"), keys))
        row["n_snapshots"] = int(len(frame))
        for label in label_cols:
            if label not in frame:
                continue
            values = pd.to_numeric(frame[label], errors="coerce")
            row[f"{label}_n"] = int(values.notna().sum())
            row[f"{label}_mean"] = float(values.mean()) if values.notna().any() else None
        rows.append(row)
    pd.DataFrame(rows).to_csv(out / "summary.csv", index=False)

    groups = []
    feature_groups = {
        "ha_direction": ["ha_direction"], "stoch_direction_change": ["stoch_direction_change"],
        "vp_30m_inside_value_area": ["vp_30m_inside_value_area"],
        "vp_30m_above_value_area": ["vp_30m_above_value_area"],
        "vp_30m_below_value_area": ["vp_30m_below_value_area"],
    }
    data["ha_aligned_with_virtual_side"] = (
        (pd.to_numeric(data.get("ha_direction"), errors="coerce") == 1) & (data["virtual_side"] == "BUY")
    ) | ((pd.to_numeric(data.get("ha_direction"), errors="coerce") == -1) & (data["virtual_side"] == "SELL"))
    feature_groups["ha_aligned_with_virtual_side"] = ["ha_aligned_with_virtual_side"]
    if "volume_expansion" in data:
        values = pd.to_numeric(data["volume_expansion"], errors="coerce")
        data["volume_expansion_train_decile"] = pd.qcut(values, 10, labels=False, duplicates="drop")
        feature_groups["volume_expansion_train_decile"] = ["volume_expansion_train_decile"]
    for name, cols in feature_groups.items():
        col = cols[0]
        if col not in data:
            continue
        for (bar, side, mode, value), frame in data.groupby(
                ["snapshot_bar", "original_signal", "virtual_mode", col], dropna=False):
            row = {"feature": name, "value": str(value), "snapshot_bar": int(bar),
                   "original_signal": side, "virtual_mode": mode, "n": int(len(frame))}
            for label in label_cols:
                if label in frame:
                    vals = pd.to_numeric(frame[label], errors="coerce")
                    row[f"{label}_mean"] = float(vals.mean()) if vals.notna().any() else None
            groups.append(row)
    pd.DataFrame(groups).to_csv(out / "groups.csv", index=False)

    future_targets = set(label_cols) | {"recovery_after_drawdown", "continuation_score", "exit_time_msc"}
    excluded = future_targets | {"snapshot_id", "signal_id", "symbol", "original_signal", "virtual_mode",
                                 "virtual_side", "snapshot_time_msc", "feature_max_time_msc", "mark_time_msc",
                                 "signal_time_msc", "entry_time_msc"}
    numeric_features = [c for c in train.columns if c not in excluded and pd.api.types.is_numeric_dtype(train[c])]
    corr_rows = []
    for feature in numeric_features:
        vals = pd.to_numeric(data[feature], errors="coerce")
        target = pd.to_numeric(data["future_pnl_to_exit"], errors="coerce")
        pair = pd.concat([vals.rename("feature"), target.rename("target")], axis=1).dropna()
        if len(pair) >= 3 and pair["feature"].nunique() > 1:
            corr_rows.append({"feature": feature, "target": "future_pnl_to_exit",
                              "n": int(len(pair)), "pearson": float(pair.corr().iloc[0, 1])})
    pd.DataFrame(corr_rows).sort_values("feature").to_csv(out / "correlations.csv", index=False)
    data[list(train.columns)].isna().mean().rename("missing_fraction").to_csv(out / "missingness.csv", header=True)
    summary = {"status": "TRAIN_DESCRIPTIVE_ONLY", "rows": len(train),
               "analysis_scope": "PROJECTED_LEGACY_DESCRIPTIVE_FEATURES_NOT_PROMOTION",
               "projected_columns": sorted(train.columns),
               "legacy_future_excursions": "EXCLUDED_FROM_PROMOTION",
               "signals": int(train.signal_id.nunique()), "labeled_snapshots": int(data.reversal_event.notna().sum()),
               "final_test_accessed": False, "feature_count_numeric_descriptive": len(numeric_features),
               "artifacts": ["summary.csv", "groups.csv", "correlations.csv", "missingness.csv"]}
    (out / "manifest.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, default=Path("outputs/intratrade/splits/train.parquet"))
    parser.add_argument("--targets", type=Path, default=Path("outputs/intratrade/master/intratrade_targets.csv"))
    parser.add_argument("--output", type=Path, default=Path("outputs/intratrade/analysis/train"))
    args = parser.parse_args()
    from pathlib import Path as P
    root = P(__file__).resolve().parents[1]
    result = analyze(*(p if p.is_absolute() else root / p for p in (args.train, args.targets, args.output)))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
