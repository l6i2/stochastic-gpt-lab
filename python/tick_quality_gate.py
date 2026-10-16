"""Apply a preregistered, outcome-blind MT5 real-tick quality screen to schema 3.

Raw validated blocks and the frozen TRAIN/VALIDATION membership remain intact.
This script creates a separately hashed research-eligible derivative only.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import pandas as pd

try:
    from .membership_contract import digest
    from .parquet_io import read_parquet
    from .stream_bar_master import append_frame, copy_allowed_rows, feature_dtypes
    from .validate_intratrade_dataset import validate
except ImportError:
    from membership_contract import digest
    from parquet_io import read_parquet
    from stream_bar_master import append_frame, copy_allowed_rows, feature_dtypes
    from validate_intratrade_dataset import validate

ROOT = Path(__file__).resolve().parents[1]
POLICY_VERSION = "tick_quality_v1"
HALO_DAYS = 2
BLOCK_RUNS = {
    "2023": ("r20261016T155454_92027a5b", True, ()),
    "2024": ("r20261016T155802_b5bf64eb", False,
             ("2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08", "2024-07-19")),
    "2025": ("r20261016T165620_b7a3933a", False, ()),
    "2026": ("r20261016T174747_38d1ddfb", False, ()),
}


def expanded_server_day_windows(days: tuple[str, ...], halo_days: int = HALO_DAYS):
    """Return merged half-open pseudo-UTC windows for broker server calendar dates."""
    intervals = []
    for value in days:
        day = date.fromisoformat(value)
        start = datetime.combine(day - timedelta(days=halo_days), time.min, timezone.utc)
        end = datetime.combine(day + timedelta(days=halo_days + 1), time.min, timezone.utc)
        intervals.append((int(start.timestamp() * 1000), int(end.timestamp() * 1000)))
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def overlaps(start_msc: int, end_msc: int, windows) -> bool:
    return any(int(start_msc) < end and int(end_msc) >= start for start, end in windows)


def event_server_time_msc(row: dict[str, str]) -> int:
    value = row.get("server_time", "")
    if value:
        parsed = datetime.strptime(value, "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return int(parsed.timestamp() * 1000)
    return int(row["signal_time_msc"])


def excluded_ids_for_block(block: Path, block_id: str):
    """Exclude only contaminated dates/episodes, never using PnL or target values."""
    expected_run, whole_block, bad_days = BLOCK_RUNS[block_id]
    manifest = json.loads((block / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("run_id") != expected_run or manifest.get("producer_schema") != "3.0":
        raise ValueError(f"Unexpected accepted source identity for block {block_id}")
    if whole_block:
        with (block / "stochastic_events.csv").open(encoding="utf-8-sig", newline="") as stream:
            return {row["signal_id"]: "block_failed_real_tick_coverage_threshold" for row in csv.DictReader(stream)}

    windows = expanded_server_day_windows(bad_days)
    excluded: dict[str, str] = {}
    with (block / "stochastic_events.csv").open(encoding="utf-8-sig", newline="") as stream:
        for event in csv.DictReader(stream):
            signal_id = event["signal_id"]
            signal_time = event_server_time_msc(event)
            # The two-day halo covers the producer's prior-session profile window,
            # 100-bar indicators and the full 100-bar virtual holding horizon.
            if overlaps(signal_time, signal_time, windows):
                excluded[signal_id] = "feature_or_trade_window_overlaps_tick_warning_embargo"

    # Also inspect actual virtual episode bounds. This is a temporal quality check;
    # no exit price, reason, excursion, or PnL is read.
    index_path = block / "bar_trade_index.csv"
    if windows and index_path.exists():
        with index_path.open(encoding="utf-8-sig", newline="") as stream:
            for trade in csv.DictReader(stream):
                if overlaps(int(trade["entry_time_msc"]), int(trade["exit_time_msc"]), windows):
                    excluded[trade["signal_id"]] = "open_trade_quote_path_overlaps_tick_warning_embargo"
    return excluded


def sha256(path: Path) -> str:
    return digest(path)


def apply(master_dir: Path, blocks: list[Path], out: Path,
          train_membership: Path, validation_membership: Path,
          split_manifest: Path) -> dict:
    master_dir, out = Path(master_dir), Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError("Refusing to overwrite an existing quality-gated research build")
    if not (master_dir / "intratrade_master.csv").is_file():
        raise FileNotFoundError("Schema 3 master must be built before applying the quality gate")
    blocks = list(map(Path, blocks))
    if len(blocks) != 4:
        raise ValueError("The complete four-block permitted history is required")

    excluded: dict[str, str] = {}
    block_evidence = []
    for block in blocks:
        block_id = block.name
        if block_id not in BLOCK_RUNS:
            raise ValueError(f"Unrecognized block identity: {block_id}")
        values = excluded_ids_for_block(block, block_id)
        overlap = excluded.keys() & values.keys()
        if overlap:
            raise ValueError("Signal identity is duplicated across quality-screen blocks")
        excluded.update(values)
        run_id = BLOCK_RUNS[block_id][0]
        run_dir = ROOT / "outputs/bar_controller/runs" / run_id
        log = run_dir / "agent_0.log"
        block_evidence.append({
            "block": block_id, "run_id": run_id,
            "run_manifest_sha256": sha256(run_dir / "run_manifest.json"),
            "agent_log_sha256": sha256(log),
            "whole_block_excluded": BLOCK_RUNS[block_id][1],
            "tick_warning_server_dates": list(BLOCK_RUNS[block_id][2]),
            "excluded_signal_count": len(values),
        })

    out.mkdir(parents=True, exist_ok=True)
    exclusions_path = out / "excluded_signal_ids.csv"
    with exclusions_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("signal_id", "reason"))
        writer.writerows(sorted(excluded.items()))
    excluded_ids = set(excluded)
    train_ids = set(read_parquet(train_membership, columns=["signal_id"]).signal_id.astype(str))
    validation_ids = set(read_parquet(validation_membership, columns=["signal_id"]).signal_id.astype(str))
    if train_ids & validation_ids:
        raise ValueError("Frozen TRAIN and VALIDATION memberships overlap")
    train_eligible = train_ids - excluded_ids
    validation_eligible = validation_ids - excluded_ids
    eligible = train_eligible | validation_eligible

    master_csv = master_dir / "intratrade_master.csv"
    with master_csv.open(encoding="utf-8-sig", newline="") as stream:
        columns = next(csv.reader(stream))
    counts = {"all": 0, "TRAIN": 0, "DISCOVERY_VALIDATION": 0}
    seen = {"TRAIN": set(), "DISCOVERY_VALIDATION": set()}
    snapshots_out = out / "intratrade_snapshots.csv"
    for frame in pd.read_csv(master_csv, dtype=feature_dtypes(columns), float_precision="round_trip",
                             keep_default_na=False, na_values=[""], chunksize=5000):
        frame = frame.loc[frame.signal_id.astype(str).isin(eligible)].copy()
        if frame.empty:
            continue
        frame.to_csv(snapshots_out, mode="a", header=not snapshots_out.exists(), index=False,
                     float_format="%.17g")
        counts["all"] += len(frame)
        for label, ids in (("TRAIN", train_eligible), ("DISCOVERY_VALIDATION", validation_eligible)):
            partition = frame.loc[frame.signal_id.astype(str).isin(ids)]
            if partition.empty:
                continue
            append_frame(partition, out / ("train.parquet" if label == "TRAIN" else "validation.parquet"))
            counts[label] += len(partition)
            seen[label].update(partition.signal_id.astype(str))

    targets = copy_allowed_rows([master_dir / "intratrade_targets.csv"],
                                out / "intratrade_snapshot_targets.csv", eligible)
    events = copy_allowed_rows([master_dir / "all_allowed_events.csv"],
                               out / "stochastic_events.csv", eligible)
    quotes = copy_allowed_rows([master_dir / "bar_execution_quotes.csv"],
                               out / "bar_execution_quotes.csv", eligible)
    source_map = copy_allowed_rows([master_dir / "signal_source_blocks.csv"],
                                   out / "signal_source_blocks.csv", eligible)
    if quotes != counts["all"]:
        raise ValueError("Quality-gated execution-quote coverage differs from snapshots")
    if source_map != events:
        raise ValueError("Quality-gated quote-tape source map and events disagree")
    if not counts["TRAIN"] or not counts["DISCOVERY_VALIDATION"]:
        raise ValueError("Quality gate left an empty inherited research partition")
    if events != len(eligible):
        raise ValueError("Quality-eligible split membership and event rows disagree")

    audit = {"schema_version": "3.0", "target_schema_version": "1.0", "symbol": "US30Cash",
             "timeframe": "M5", "optimization": "OFF", "LIVE_TRADING": False,
             "aborted": False, "snapshot_schedule": ",".join(map(str, range(1, 101))),
             "signals": events, "snapshot_rows": counts["all"], "target_rows": targets,
             "final_test_accessed": False, "quality_policy": POLICY_VERSION}
    audit_path = out / "intratrade_snapshots.csv.audit.json"
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    validation = validate(snapshots_out, audit_path, out / "intratrade_snapshot_targets.csv",
                          out / "train.parquet", out / "validation.parquet",
                          out / "stochastic_events.csv", split_manifest,
                          out / "bar_execution_quotes.csv")
    if validation.get("status") != "PASS":
        raise ValueError("Quality-gated dataset validation did not pass")

    result = {
        "status": "PASS", "policy_version": POLICY_VERSION,
        "policy": {"block_rate_exclusion_threshold": "1% of minute bars missing or discarded",
                   "whole_block_exclusions": ["2023"], "server_day_halo_days": HALO_DAYS,
                   "signal_selection_uses_outcomes": False,
                   "reason": "MT5 tester real-tick warnings; embargo covers prior-session profile features and max holding horizon"},
        "blocks": block_evidence, "excluded_signals": len(excluded),
        "eligible_membership_signals": {"TRAIN": len(train_eligible),
                                        "DISCOVERY_VALIDATION": len(validation_eligible)},
        "eligible_snapshot_rows": counts, "eligible_targets": targets,
        "eligible_events": events, "eligible_execution_quotes": quotes,
        "eligible_quote_tape_source_map": source_map,
        "validation": validation, "final_test_accessed": False,
        "input_sha256": {p.name: sha256(p) for p in (master_csv, master_dir / "intratrade_targets.csv",
                                                       master_dir / "all_allowed_events.csv",
                                                       master_dir / "bar_execution_quotes.csv",
                                                       master_dir / "signal_source_blocks.csv")},
        "output_sha256": {p.name: sha256(p) for p in out.iterdir() if p.is_file()},
    }
    (out / "tick_quality_manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=Path("outputs/bar_controller/research/master"))
    parser.add_argument("--blocks", nargs="+", type=Path, default=[Path(f"outputs/bar_controller/validated_blocks/{y}") for y in BLOCK_RUNS])
    parser.add_argument("--out", type=Path, default=Path("outputs/bar_controller/research/quality_v1"))
    args = parser.parse_args()
    result = apply(args.master, args.blocks,
                   args.out if args.out.is_absolute() else ROOT / args.out,
                   ROOT / "outputs/splits/train.parquet", ROOT / "outputs/splits/validation.parquet",
                   ROOT / "outputs/splits/split_manifest.json")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
