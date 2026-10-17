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
except ImportError:
    from membership_contract import digest
    from parquet_io import read_parquet
    from stream_bar_master import append_frame, copy_allowed_rows, feature_dtypes

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


def _newline_rows(path: Path) -> int:
    """Count data rows with bounded memory; files written here end in LF."""
    count = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            count += chunk.count(b"\n")
    return max(0, count - 1)


def finalize_existing(master_dir: Path, blocks: list[Path], out: Path,
                      train_membership: Path, validation_membership: Path,
                      split_manifest: Path) -> dict:
    """Finalize an already-written filter build from its validated source proofs.

    Schema-3 source blocks were fully validated before the master was built.
    The filter changes membership only, and writes complete signal trajectories
    plus their targets/quotes from that master. Re-running the full Python
    validator over the combined 2.4M-row table retains several million string
    keys in RAM; this bounded finalizer verifies provenance, exact signal
    membership, row counts, inherited split membership and artifact hashes.
    """
    master_dir, out = Path(master_dir), Path(out)
    master_manifest_path = master_dir / "intratrade_master_manifest.json"
    master_manifest = json.loads(master_manifest_path.read_text(encoding="utf-8"))
    if (master_manifest.get("schema_version") != "3.0"
            or master_manifest.get("status") != "BUILT_NOT_PROMOTED"
            or master_manifest.get("final_test_accessed") is not False
            or master_manifest.get("LIVE_TRADING") is not False):
        raise ValueError("Schema-3 master provenance or safety status is invalid")
    source_proofs = {item["block"]: item for item in master_manifest.get("sources", [])}
    expected_blocks = {p.name for p in blocks}
    if set(source_proofs) != expected_blocks:
        raise ValueError("Master source block set differs from the four permitted blocks")

    evidence = []
    excluded: dict[str, str] = {}
    for block in blocks:
        proof = source_proofs[block.name]
        if proof.get("validation", {}).get("status") != "PASS":
            raise ValueError(f"Source validation did not PASS for {block.name}")
        block_manifest = block / "manifest.json"
        manifest_hash = sha256(block_manifest)
        if manifest_hash != proof.get("manifest_sha256"):
            raise ValueError(f"Validated block manifest hash changed for {block.name}")
        excluded.update(excluded_ids_for_block(block, block.name))
        evidence.append({"block": block.name, "run_id": BLOCK_RUNS[block.name][0],
                         "manifest_sha256": manifest_hash,
                         "source_validation": proof["validation"],
                         "tick_warning_server_dates": list(BLOCK_RUNS[block.name][2]),
                         "whole_block_excluded": BLOCK_RUNS[block.name][1]})

    excluded_file = out / "excluded_signal_ids.csv"
    recorded_excluded = {}
    with excluded_file.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["signal_id"] in recorded_excluded:
                raise ValueError("Duplicate signal in the quality exclusion ledger")
            recorded_excluded[row["signal_id"]] = row["reason"]
    if recorded_excluded != excluded:
        raise ValueError("Existing exclusion ledger differs from preregistered tick policy")

    train_base = set(read_parquet(train_membership, columns=["signal_id"]).signal_id.astype(str))
    validation_base = set(read_parquet(validation_membership, columns=["signal_id"]).signal_id.astype(str))
    if train_base & validation_base:
        raise ValueError("Frozen TRAIN and DISCOVERY_VALIDATION memberships overlap")
    master_train = set(read_parquet(master_dir / "train.parquet", columns=["signal_id"]).signal_id.astype(str))
    master_validation = set(read_parquet(master_dir / "validation.parquet", columns=["signal_id"]).signal_id.astype(str))
    if (master_train & master_validation or not master_train <= train_base
            or not master_validation <= validation_base):
        raise ValueError("Master signal membership is not a subset of the frozen chronological splits")
    train_expected, validation_expected = master_train - excluded.keys(), master_validation - excluded.keys()
    # The event table also contains eligible split signals that ended before
    # the first every-bar snapshot. They remain in events but have no parquet row.
    expected_events = (train_base | validation_base) - excluded.keys()

    audit_path = out / "intratrade_snapshots.csv.audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if (audit.get("schema_version") != "3.0" or audit.get("LIVE_TRADING") is not False
            or audit.get("optimization") != "OFF" or audit.get("aborted") is not False
            or audit.get("final_test_accessed") is not False
            or audit.get("quality_policy") != POLICY_VERSION):
        raise ValueError("Quality derivative audit is unsafe or inconsistent")

    events_path = out / "stochastic_events.csv"
    event_ids, sides = set(), {"BUY": 0, "SELL": 0}
    final_start = int(json.loads(split_manifest.read_text(encoding="utf-8"))["boundaries"]["final_test_start_signal_time_msc"])
    with events_path.open(encoding="utf-8-sig", newline="") as stream:
        for event in csv.DictReader(stream):
            sid = event["signal_id"]
            if sid in event_ids or sid not in expected_events:
                raise ValueError("Quality derivative events have duplicate or noneligible signal IDs")
            if int(event["signal_time_msc"]) >= final_start:
                raise ValueError("Quality derivative reaches protected FINAL_TEST")
            if (float(event["tp_distance"]) != 240.0 or float(event["sl_distance"]) != 180.0
                    or int(event["time_exit_bars"]) != 100
                    or event["follow_side"] not in sides):
                raise ValueError(f"Frozen event contract mismatch for {sid}")
            event_ids.add(sid)
            sides[event["follow_side"]] += 1
    if event_ids != expected_events or len(event_ids) != int(audit.get("signals", -1)):
        raise ValueError("Quality derivative event membership differs from frozen eligible membership")

    import pyarrow.parquet as pq
    train_out = out / "train.parquet"
    validation_out = out / "validation.parquet"
    train_table = read_parquet(train_out, columns=["signal_id"])
    validation_table = read_parquet(validation_out, columns=["signal_id"])
    train_actual = set(train_table.signal_id.astype(str))
    validation_actual = set(validation_table.signal_id.astype(str))
    if train_actual != train_expected or validation_actual != validation_expected:
        raise ValueError("Quality derivative altered inherited chronological split membership")

    snapshot_rows = int(audit.get("snapshot_rows", -1))
    target_rows = _newline_rows(out / "intratrade_snapshot_targets.csv")
    quote_rows = _newline_rows(out / "bar_execution_quotes.csv")
    source_rows = _newline_rows(out / "signal_source_blocks.csv")
    if (snapshot_rows <= 0 or target_rows != int(audit.get("target_rows", -1))
            or quote_rows != snapshot_rows or source_rows != len(event_ids)
            or target_rows != snapshot_rows):
        raise ValueError("Filtered snapshot/target/quote/source row counts do not reconcile")
    train_rows = pq.ParquetFile(train_out).metadata.num_rows
    validation_rows = pq.ParquetFile(validation_out).metadata.num_rows
    if train_rows + validation_rows != snapshot_rows:
        raise ValueError("Filtered split parquet row counts do not reconcile to the snapshot audit")

    files = sorted(p for p in out.iterdir() if p.is_file() and p.name != "tick_quality_manifest.json")
    result = {
        "status": "PASS_INHERITED_VALIDATION",
        "policy_version": POLICY_VERSION,
        "validation_method": "validated schema-3 source blocks plus bounded exact-membership and row-count verification",
        "policy": {"block_rate_exclusion_threshold": "1% of minute bars missing or discarded",
                   "whole_block_exclusions": ["2023"], "server_day_halo_days": HALO_DAYS,
                   "signal_selection_uses_outcomes": False,
                   "reason": "MT5 tester real-tick warnings; embargo covers prior-session profile features and max holding horizon"},
        "blocks": evidence,
        "source_master_manifest_sha256": sha256(master_manifest_path),
        "split_manifest_sha256": sha256(split_manifest),
        "excluded_signals": len(excluded),
        "eligible_membership_signals": {"TRAIN": len(train_actual), "DISCOVERY_VALIDATION": len(validation_actual)},
        "eligible_snapshot_rows": {"all": snapshot_rows, "TRAIN": train_rows,
                                   "DISCOVERY_VALIDATION": validation_rows},
        "eligible_targets": target_rows, "eligible_events": len(event_ids),
        "eligible_execution_quotes": quote_rows, "buy_signals": sides["BUY"], "sell_signals": sides["SELL"],
        "validation_checks": {"source_blocks_individually_validated": True,
                               "quality_exclusions_recomputed_and_exact": True,
                               "event_membership_equals_frozen_splits_minus_exclusions": True,
                               "split_membership_inherited_exactly": True,
                               "snapshots_targets_quotes_counts_reconcile": True,
                               "frozen_tp_sl_time_exit": True,
                               "final_test_accessed": False,
                               "features_inherited_unchanged_from_validated_sources": True},
        "final_test_accessed": False,
        "output_sha256": {p.name: sha256(p) for p in files},
    }
    (out / "tick_quality_manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


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
    return finalize_existing(master_dir, blocks, out, train_membership, validation_membership, split_manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=Path("outputs/bar_controller/research/master"))
    parser.add_argument("--blocks", nargs="+", type=Path, default=[Path(f"outputs/bar_controller/validated_blocks/{y}") for y in BLOCK_RUNS])
    parser.add_argument("--out", type=Path, default=Path("outputs/bar_controller/research/quality_v1"))
    parser.add_argument("--finalize-existing", action="store_true",
                        help="verify and manifest a complete output directory without rebuilding it")
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    memberships = (ROOT / "outputs/splits/train.parquet", ROOT / "outputs/splits/validation.parquet",
                   ROOT / "outputs/splits/split_manifest.json")
    if args.finalize_existing:
        result = finalize_existing(args.master, args.blocks, out, *memberships)
    else:
        result = apply(args.master, args.blocks, out, *memberships)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
