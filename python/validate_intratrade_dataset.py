"""Validate causal intra-trade snapshots and their separately stored future labels."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

SCHEDULE = (1, 2, 3, 5, 10, 15, 20, 30, 50)
REQUIRED_FEATURE_COLUMNS = {
    "snapshot_id", "signal_id", "symbol", "signal_time_msc", "original_signal",
    "virtual_mode", "virtual_side", "entry_time_msc", "snapshot_bar",
    "snapshot_time_msc", "feature_max_time_msc", "mark_time_msc",
    "current_bid", "current_ask", "spread", "current_unrealized_pnl",
    "distance_to_tp", "distance_to_sl", "current_mfe_so_far",
    "current_mae_so_far", "bars_open",
}
REQUIRED_TARGET_COLUMNS = {
    "snapshot_id", "signal_id", "virtual_mode", "snapshot_bar", "exit_time_msc",
    "label_status", "tp_before_sl_after_snapshot", "sl_before_tp_after_snapshot",
    "future_pnl_to_exit", "future_max_favorable_move", "future_max_adverse_move",
    "profit_erosion", "recovery_after_drawdown", "continuation_score", "reversal_event",
}
FORBIDDEN_FEATURE_TOKENS = ("future_", "final_", "exit_", "target", "label", "reversal_event")


def validate(snapshot_csv: Path, audit_path: Path | None = None,
             targets_csv: Path | None = None, train_parquet: Path | None = None,
             validation_parquet: Path | None = None) -> dict:
    snapshot_csv = snapshot_csv.resolve()
    audit_path = (audit_path or Path(str(snapshot_csv) + ".audit.json")).resolve()
    targets_csv = targets_csv.resolve() if targets_csv else None
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("schema_version") != "2.0":
        raise ValueError("Expected intratrade schema_version 2.0")
    if audit.get("LIVE_TRADING") is not False or audit.get("optimization") != "OFF":
        raise ValueError("Unsafe source manifest: LIVE_TRADING must be false and optimization OFF")
    if audit.get("aborted") is not False:
        raise ValueError("Snapshot run is aborted or incomplete")
    if tuple(map(int, audit.get("snapshot_schedule", "").split(","))) != SCHEDULE:
        raise ValueError("Snapshot schedule does not match the frozen schedule")

    snapshot_times: dict[str, int] = {}
    pairs: set[tuple[str, str, int]] = set()
    seen_modes: dict[str, set[str]] = defaultdict(set)
    last_by_trade: dict[tuple[str, str], tuple[int, int]] = {}
    row_count = 0
    sides = {"BUY", "SELL"}
    with snapshot_csv.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError("Snapshot CSV has no header")
        fields = set(reader.fieldnames)
        missing = REQUIRED_FEATURE_COLUMNS - fields
        if missing:
            raise ValueError(f"Missing required snapshot columns: {sorted(missing)}")
        bad = [name for name in fields if any(token in name.lower() for token in FORBIDDEN_FEATURE_TOKENS)]
        if bad:
            raise ValueError(f"Future/outcome columns leaked into feature CSV: {sorted(bad)}")
        for row in reader:
            if not row.get("snapshot_id"):
                raise ValueError("Snapshot row missing snapshot_id")
            snapshot_id = row["snapshot_id"]
            signal_id = row["signal_id"]
            mode = row["virtual_mode"]
            side = row["virtual_side"]
            if mode not in {"FOLLOW", "INVERT"} or side not in sides:
                raise ValueError(f"Invalid virtual mode/side in {snapshot_id}")
            bar = int(row["snapshot_bar"])
            if bar not in SCHEDULE or int(row["bars_open"]) != bar:
                raise ValueError(f"Snapshot at unscheduled bar offset: {snapshot_id}")
            snapshot_time = int(row["snapshot_time_msc"])
            feature_max = int(row["feature_max_time_msc"])
            mark_time = int(row["mark_time_msc"])
            if feature_max > snapshot_time or mark_time > snapshot_time:
                raise ValueError(f"Lookahead timestamp in {snapshot_id}")
            if int(row["signal_time_msc"]) >= snapshot_time or int(row["entry_time_msc"]) > snapshot_time:
                raise ValueError(f"Snapshot is not after its signal/entry: {snapshot_id}")
            if snapshot_id in snapshot_times:
                raise ValueError(f"Duplicate snapshot_id: {snapshot_id}")
            pair = (signal_id, mode, bar)
            if pair in pairs:
                raise ValueError(f"Duplicate (signal_id, virtual_mode, snapshot_bar): {pair}")
            key = (signal_id, mode)
            previous = last_by_trade.get(key)
            if previous and (bar <= previous[0] or snapshot_time <= previous[1]):
                raise ValueError(f"Non-monotone snapshots for {key}")
            last_by_trade[key] = (bar, snapshot_time)
            snapshot_times[snapshot_id] = snapshot_time
            pairs.add(pair)
            seen_modes[signal_id].add(mode)
            row_count += 1

    if row_count != int(audit.get("snapshot_rows", -1)):
        raise ValueError("Audit snapshot_rows does not match CSV row count")
    for key in ("signals",):
        if int(audit.get(key, -1)) < 0:
            raise ValueError(f"Audit missing {key}")

    target_count = 0
    if targets_csv and targets_csv.exists() and targets_csv.stat().st_size:
        with targets_csv.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            target_fields = set(reader.fieldnames or ())
            missing = REQUIRED_TARGET_COLUMNS - target_fields
            if missing:
                raise ValueError(f"Missing required target columns: {sorted(missing)}")
            target_ids: set[str] = set()
            for row in reader:
                sid = row["snapshot_id"]
                if sid not in snapshot_times:
                    raise ValueError(f"Target has no matching snapshot: {sid}")
                if sid in target_ids:
                    raise ValueError(f"Duplicate target row: {sid}")
                target_ids.add(sid)
                if int(row["exit_time_msc"]) <= snapshot_times[sid]:
                    raise ValueError(f"Target exit is not after snapshot: {sid}")
                if row["label_status"] != "COMPLETE":
                    raise ValueError(f"Unexpected target status for {sid}")
                target_count += 1
    if int(audit.get("target_rows", -1)) != target_count:
        raise ValueError("Audit target_rows does not match target CSV row count")

    split_counts = {}
    if bool(train_parquet) != bool(validation_parquet):
        raise ValueError("Provide both TRAIN and VALIDATION Parquet files, or neither")
    if train_parquet and validation_parquet:
        try:
            from .parquet_io import read_parquet
        except ImportError:
            from parquet_io import read_parquet
        train_ids = set(read_parquet(train_parquet)["signal_id"].astype(str))
        validation_ids = set(read_parquet(validation_parquet)["signal_id"].astype(str))
        if train_ids & validation_ids:
            raise ValueError("TRAIN and VALIDATION signal membership overlaps")
        unknown = set(seen_modes) - train_ids - validation_ids
        if unknown:
            raise ValueError("Snapshots contain signal IDs outside TRAIN/VALIDATION; refusing possible FINAL_TEST access")
        split_counts = {"TRAIN": sum(s in train_ids for s in seen_modes),
                        "DISCOVERY_VALIDATION": sum(s in validation_ids for s in seen_modes)}

    membership_verified = bool(train_parquet and validation_parquet)
    return {"status": "PASS", "snapshot_rows": row_count, "target_rows": target_count,
            "unique_signals": len(seen_modes), "schema_version": audit["schema_version"],
            "split_signals": split_counts, "split_membership_verified": membership_verified,
            # A structural-only pass cannot attest that signal IDs avoid the held-out split.
            "final_test_accessed": False if membership_verified else None}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshots", type=Path)
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--targets", type=Path)
    parser.add_argument("--train", type=Path)
    parser.add_argument("--validation", type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.snapshots, args.audit, args.targets, args.train, args.validation)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"INTRATRADE DATASET INVALID: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
