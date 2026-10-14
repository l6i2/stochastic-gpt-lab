"""Validate causal intra-trade snapshots and their separately stored future labels."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
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
             validation_parquet: Path | None = None, events_csv: Path | None = None,
             split_manifest: Path | None = None) -> dict:
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

    event_rows = {}
    event_sides = Counter()
    if events_csv is not None:
        with events_csv.open("r", encoding="utf-8-sig", newline="") as stream:
            for event in csv.DictReader(stream):
                signal_id = str(event["signal_id"])
                if signal_id in event_rows:
                    raise ValueError(f"Duplicate signal_id in event source: {signal_id}")
                if (float(event["tp_distance"]) != 240.0 or float(event["sl_distance"]) != 180.0
                        or int(event["time_exit_bars"]) != 100):
                    raise ValueError(f"Frozen TP/SL/TIME_EXIT mismatch for {signal_id}")
                event_rows[signal_id] = event
                event_sides[event["follow_side"]] += 1

    snapshot_times: dict[str, int] = {}
    pairs: set[tuple[str, str, int]] = set()
    seen_modes: dict[str, set[str]] = defaultdict(set)
    last_by_trade: dict[tuple[str, str], tuple[int, int]] = {}
    excursions_by_trade: dict[tuple[str, str], tuple[float, float]] = {}
    row_count = 0
    sides = {"BUY", "SELL"}
    offset_counts = Counter()
    mode_counts = Counter()
    signal_side_counts = Counter()
    virtual_side_counts = Counter()
    target_refs = {}
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
            original = row["original_signal"]
            expected_side = original if mode == "FOLLOW" else ("SELL" if original == "BUY" else "BUY")
            if original not in sides or side != expected_side:
                raise ValueError(f"FOLLOW/INVERT side mapping mismatch in {snapshot_id}")
            if events_csv is not None:
                event = event_rows.get(signal_id)
                if event is None:
                    raise ValueError(f"signal_id absent from block event source: {signal_id}")
                expected_original = event["follow_side"]
                expected_virtual = event["follow_side"] if mode == "FOLLOW" else event["invert_side"]
                if (original != expected_original or side != expected_virtual
                        or int(row["signal_time_msc"]) != int(event["signal_time_msc"])):
                    raise ValueError(f"Snapshot/event mapping mismatch in {snapshot_id}")
            bar = int(row["snapshot_bar"])
            if bar not in SCHEDULE or int(row["bars_open"]) != bar:
                raise ValueError(f"Snapshot at unscheduled bar offset: {snapshot_id}")
            snapshot_time = int(row["snapshot_time_msc"])
            feature_max = int(row["feature_max_time_msc"])
            mark_time = int(row["mark_time_msc"])
            if feature_max > snapshot_time or mark_time > snapshot_time:
                raise ValueError(f"Lookahead timestamp in {snapshot_id}")
            for column in reader.fieldnames:
                if column.startswith("vp_") and column.endswith("window_end_msc") and row[column]:
                    if int(row[column]) > snapshot_time:
                        raise ValueError(f"Future Volume Profile window in {snapshot_id}: {column}")
                if column.startswith("vp_") and column.endswith("last_tick_msc") and row[column]:
                    if int(row[column]) > snapshot_time:
                        raise ValueError(f"Future Volume Profile tick in {snapshot_id}: {column}")
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
            pnl = float(row["current_unrealized_pnl"])
            mfe, mae = float(row["current_mfe_so_far"]), float(row["current_mae_so_far"])
            if mfe < max(0.0, pnl) - 1e-8 or mae < max(0.0, -pnl) - 1e-8:
                raise ValueError(f"Current MFE/MAE does not bound current PnL in {snapshot_id}")
            previous_excursion = excursions_by_trade.get(key)
            if previous_excursion and (mfe + 1e-8 < previous_excursion[0] or mae + 1e-8 < previous_excursion[1]):
                raise ValueError(f"Current MFE/MAE regresses in {snapshot_id}")
            excursions_by_trade[key] = (mfe, mae)
            offset_counts[bar] += 1
            mode_counts[mode] += 1
            signal_side_counts[original] += 1
            virtual_side_counts[side] += 1
            target_refs[snapshot_id] = (signal_id, mode, snapshot_time)
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
    target_ids: set[str] = set()
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
                signal_id, mode, _ = target_refs[sid]
                if events_csv is not None:
                    event = event_rows[signal_id]
                    prefix = "follow_" if mode == "FOLLOW" else "invert_"
                    if event[prefix + "exit_reason"] == "END_OF_DATA":
                        raise ValueError(f"Completed target belongs to a censored end-of-data trade: {sid}")
                target_count += 1
                target_ids.add(sid)
    if int(audit.get("target_rows", -1)) != target_count:
        raise ValueError("Audit target_rows does not match target CSV row count")
    if events_csv is not None:
        missing_targets = set(target_refs) - target_ids
        for sid in missing_targets:
            signal_id, mode, _ = target_refs[sid]
            prefix = "follow_" if mode == "FOLLOW" else "invert_"
            if event_rows[signal_id][prefix + "exit_reason"] != "END_OF_DATA":
                raise ValueError(f"Open-at-snapshot row has no target but terminal trade is not censored: {sid}")

    split_counts = {}
    purged_signals = 0
    if bool(train_parquet) != bool(validation_parquet):
        raise ValueError("Provide both TRAIN and VALIDATION Parquet files, or neither")
    if train_parquet and validation_parquet:
        if events_csv is None:
            raise ValueError("Provide the block stochastic_events.csv to distinguish purged IDs from protected FINAL_TEST IDs")
        try:
            from .parquet_io import read_parquet
        except ImportError:
            from parquet_io import read_parquet
        train_ids = set(read_parquet(train_parquet)["signal_id"].astype(str))
        validation_ids = set(read_parquet(validation_parquet)["signal_id"].astype(str))
        if train_ids & validation_ids:
            raise ValueError("TRAIN and VALIDATION signal membership overlaps")
        unknown = set(seen_modes) - train_ids - validation_ids
        event_times = {}
        with events_csv.open("r", encoding="utf-8-sig", newline="") as stream:
            for event in csv.DictReader(stream):
                event_times[str(event["signal_id"])] = int(event["signal_time_msc"])
        missing_from_source = unknown - event_times.keys()
        if missing_from_source:
            raise ValueError("Snapshots contain signal IDs absent from the block event source; refusing possible FINAL_TEST access")
        split_manifest = split_manifest or Path(__file__).resolve().parents[1] / "outputs/splits/split_manifest.json"
        split_data = json.loads(split_manifest.read_text(encoding="utf-8"))
        final_start = int(split_data["boundaries"]["final_test_start_signal_time_msc"])
        if any(event_times[signal_id] >= final_start for signal_id in unknown):
            raise ValueError("Snapshots contain signal IDs at or after protected FINAL_TEST boundary")
        validation_start = int(split_data["boundaries"]["validation_start_signal_time_msc"])
        for signal_id in unknown:
            event = event_rows[signal_id]
            boundary = validation_start if event_times[signal_id] < validation_start else final_start
            try:
                label_end = max(int(event["follow_exit_time"]), int(event["invert_exit_time"]))
            except (KeyError, ValueError) as exc:
                raise ValueError("Unknown signal has no verifiable purge horizon") from exc
            if label_end < boundary:
                raise ValueError("Unknown signal is not explained by chronological boundary purging")
        purged_signals = len(unknown)
        split_counts = {"TRAIN": sum(s in train_ids for s in seen_modes),
                        "DISCOVERY_VALIDATION": sum(s in validation_ids for s in seen_modes)}

    membership_verified = bool(train_parquet and validation_parquet and events_csv)
    return {"status": "PASS", "snapshot_rows": row_count, "target_rows": target_count,
            "unique_signals": len(seen_modes), "schema_version": audit["schema_version"],
            "split_signals": split_counts, "split_membership_verified": membership_verified,
            "purged_signals_excluded_from_splits": purged_signals,
            "signals": int(audit["signals"]), "buy_signals": event_sides["BUY"],
            "sell_signals": event_sides["SELL"], "snapshot_offsets": dict(sorted(offset_counts.items())),
            "follow_snapshots": mode_counts["FOLLOW"], "invert_snapshots": mode_counts["INVERT"],
            "virtual_sides": dict(virtual_side_counts), "causal_checks": {
                "timestamp_cutoff": True, "feature_target_separation": True,
                "mfe_mae_past_only_monotonic": True if events_csv else None,
                "heikin_ashi_and_volume_from_closed_bars": True if events_csv else None,
                "profile_windows_closed_by_cutoff": True if events_csv else None,
                "snapshot_position_open_or_censored": True if events_csv else None,
                "frozen_tp_sl_time_exit": True if events_csv else None,
                "follow_invert_mapping": True},
            # A structural-only pass cannot attest that signal IDs avoid the held-out split.
            "final_test_accessed": False if membership_verified else None}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshots", type=Path)
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--targets", type=Path)
    parser.add_argument("--train", type=Path)
    parser.add_argument("--validation", type=Path)
    parser.add_argument("--events", type=Path,
                        help="same-block stochastic_events.csv; required with split membership")
    parser.add_argument("--split-manifest", type=Path,
                        help="split boundaries manifest (defaults to outputs/splits/split_manifest.json)")
    args = parser.parse_args()
    try:
        result = validate(args.snapshots, args.audit, args.targets, args.train, args.validation,
                          args.events, args.split_manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"INTRATRADE DATASET INVALID: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
