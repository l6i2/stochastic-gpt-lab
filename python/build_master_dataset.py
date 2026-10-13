"""Validate chronological MT5 blocks, freeze a master dataset, and make purged splits."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from parquet_io import write_parquet
from research import chronological_split, purge_at_boundary, read_dataset, validate


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dataframe_hash(frame: pd.DataFrame) -> str:
    # Normalize CSV/Parquet dtype differences while preserving exact numeric
    # values and null positions. This hash is for round-trip parity only.
    normalized = frame.copy()
    for column in normalized:
        if pd.api.types.is_numeric_dtype(normalized[column]):
            normalized[column] = pd.to_numeric(normalized[column]).astype("float64")
        else:
            normalized[column] = normalized[column].astype("string").fillna("<NULL>")
    values = pd.util.hash_pandas_object(normalized, index=False).to_numpy().tobytes()
    return hashlib.sha256(values).hexdigest()


def block_period(manifest: dict) -> tuple[datetime, datetime]:
    start, end = manifest["period"].split("..", 1)
    return (datetime.fromisoformat(start).replace(tzinfo=timezone.utc),
            datetime.fromisoformat(end).replace(tzinfo=timezone.utc))


def _equal_rows(frame: pd.DataFrame) -> bool:
    normalized = frame.reset_index(drop=True)
    return all(normalized.iloc[0].equals(normalized.iloc[i]) for i in range(1, len(normalized)))


def assemble_blocks(block_dirs: list[Path]) -> tuple[pd.DataFrame, list[dict], int]:
    """Read and validate each block; drop only byte-equivalent boundary rows."""
    if not block_dirs:
        raise ValueError("At least one validated block is required")
    blocks = []
    reference = None
    reference_manifest = None
    for block_dir in block_dirs:
        csv_path = block_dir / "stochastic_events.csv"
        audit_path = Path(str(csv_path) + ".audit.json")
        manifest_path = block_dir / "manifest.json"
        if not all(path.is_file() for path in (csv_path, audit_path, manifest_path)):
            raise ValueError(f"Incomplete block artifacts in {block_dir}")
        audit = json.loads(audit_path.read_text(encoding="utf-8-sig"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        frame = read_dataset(csv_path)
        errors = validate(frame, audit)
        if errors:
            raise ValueError(f"Block {block_dir} failed validation: {'; '.join(errors)}")
        if manifest.get("validator") != "PASS":
            raise ValueError(f"Block manifest does not record validator PASS: {block_dir}")
        if manifest.get("LIVE_TRADING") is not False or manifest.get("optimization") != "OFF":
            raise ValueError(f"Unsafe or optimized block configuration: {block_dir}")
        if manifest.get("model") != "Every tick based on real ticks":
            raise ValueError(f"Unexpected tick model in {block_dir}")
        start, end = block_period(manifest)
        server_dates = pd.to_datetime(frame.server_time, format="%Y.%m.%d %H:%M:%S", errors="coerce", utc=True)
        if server_dates.isna().any() or (server_dates < start).any() or (server_dates >= end + pd.Timedelta(days=1)).any():
            raise ValueError(f"Signals fall outside the declared inclusive block period: {block_dir}")
        signature = {
            "columns": list(frame.columns),
            "schema_version": str(frame.schema_version.iloc[0]),
            "symbol": str(frame.symbol.iloc[0]),
            "code_HEAD_SHA": manifest.get("code_HEAD_SHA"),
            "strategy": {key: int(frame[key].iloc[0]) if key.endswith("period") or key == "time_exit_bars"
                         else float(frame[key].iloc[0])
                         for key in ("stoch_k_period", "stoch_d_period", "stoch_slowing",
                                     "tp_distance", "sl_distance", "time_exit_bars")},
            "trigger_line": str(frame.trigger_line.iloc[0]),
            "simulation_mode": str(frame.simulation_mode.iloc[0]),
            "server_utc_offset_seconds": int(frame.server_utc_offset_seconds.iloc[0]),
        }
        if reference is None:
            reference, reference_manifest = signature, manifest
        elif signature != reference:
            raise ValueError(f"Block schema or run metadata differs: {block_dir}")
        frame = frame.copy()
        frame["_source_block"] = str(block_dir)
        blocks.append({"frame": frame, "manifest": manifest, "range": (start, end), "path": block_dir})

    blocks.sort(key=lambda block: block["range"][0])
    for left, right in zip(blocks, blocks[1:]):
        if left["range"][1] >= right["range"][0]:
            # Inclusive ranges may share one boundary date only. On that date,
            # require identical rows in both exports before dropping duplicates.
            overlap_start = max(left["range"][0], right["range"][0])
            overlap_end = min(left["range"][1], right["range"][1])
            if overlap_start != overlap_end:
                raise ValueError(f"Block periods overlap by more than one boundary day: {left['path']} and {right['path']}")
            def rows_on_day(block):
                dates = pd.to_datetime(block["frame"].server_time, format="%Y.%m.%d %H:%M:%S", utc=True).dt.date
                return block["frame"].loc[dates == overlap_start.date()].drop(columns="_source_block")
            left_rows, right_rows = rows_on_day(left), rows_on_day(right)
            if left_rows.empty or right_rows.empty or len(left_rows) != len(right_rows):
                raise ValueError(f"Shared boundary day is incomplete in one block: {left['path']} and {right['path']}")
            if not left_rows.reset_index(drop=True).equals(right_rows.reset_index(drop=True)):
                raise ValueError(f"Shared boundary rows differ: {left['path']} and {right['path']}")

    combined = pd.concat([block["frame"] for block in blocks], ignore_index=True)
    exact_duplicates_removed = 0
    dupes = combined[combined.signal_id.duplicated(keep=False)]
    for signal_id, group in dupes.groupby("signal_id", sort=False):
        sources = group._source_block.unique()
        if len(group) != 2 or len(sources) != 2 or not _equal_rows(group.drop(columns="_source_block")):
            raise ValueError(f"Inconsistent or non-boundary duplicate signal_id: {signal_id}")
        source_positions = [next(i for i, block in enumerate(blocks) if str(block["path"]) == src)
                            for src in sources]
        if abs(source_positions[0] - source_positions[1]) != 1:
            raise ValueError(f"Duplicate does not belong to adjacent blocks: {signal_id}")
        timestamp = int(group.signal_time_msc.iloc[0]) / 1000
        signal_date = datetime.fromtimestamp(timestamp, timezone.utc)
        neighboring = [blocks[i]["range"][1] for i in source_positions]
        starts = [blocks[i]["range"][0] for i in source_positions]
        if min(min(abs((signal_date - t).total_seconds()) for t in neighboring + starts), default=0) > 86400:
            raise ValueError(f"Duplicate is not at a block boundary: {signal_id}")
        exact_duplicates_removed += len(group) - 1
    if exact_duplicates_removed:
        combined = combined.drop_duplicates(subset="signal_id", keep="first")

    combined = combined.drop(columns="_source_block").sort_values("signal_time_msc", kind="stable").reset_index(drop=True)
    if combined.signal_id.duplicated().any() or combined.signal_time_msc.duplicated().any():
        raise ValueError("Master contains duplicate signal identifiers or timestamps")
    if not combined.signal_time_msc.is_monotonic_increasing:
        raise ValueError("Master timestamps are not monotonic")
    errors = validate(combined)
    if errors:
        raise ValueError("Combined master failed validation: " + "; ".join(errors))
    return combined, [block["manifest"] for block in blocks], exact_duplicates_removed


def build(block_dirs: list[Path], master_dir: Path, splits_dir: Path) -> dict:
    if master_dir.exists() or splits_dir.exists():
        raise ValueError("Refusing to overwrite an existing master or split directory")
    frame, manifests, duplicates_removed = assemble_blocks(block_dirs)
    parts = chronological_split(frame, 0.6, 0.2)
    validation_boundary = int(parts["DISCOVERY_VALIDATION"].signal_time_msc.iloc[0])
    final_boundary = int(parts["FINAL_TEST"].signal_time_msc.iloc[0])
    train, purged_train = purge_at_boundary(parts["TRAIN"], validation_boundary)
    validation, purged_validation = purge_at_boundary(parts["DISCOVERY_VALIDATION"], final_boundary)
    if train.empty or validation.empty:
        raise ValueError("Chronological TRAIN/VALIDATION is empty after purging")

    master_dir.mkdir(parents=True)
    splits_dir.mkdir(parents=True)
    csv_path = master_dir / "stochastic_master.csv"
    parquet_path = master_dir / "stochastic_master.parquet"
    frame.to_csv(csv_path, index=False, float_format="%.17g")
    write_parquet(frame, parquet_path, index=False)

    split_train_path = splits_dir / "train.parquet"
    split_validation_path = splits_dir / "validation.parquet"
    write_parquet(train, split_train_path, index=False)
    write_parquet(validation, split_validation_path, index=False)

    # Verify the written master in both formats before freezing it.
    csv_check = read_dataset(csv_path)
    parquet_check = read_dataset(parquet_path)
    for name, checked in (("CSV", csv_check), ("Parquet", parquet_check)):
        errors = validate(checked)
        if errors or len(checked) != len(frame):
            raise ValueError(f"Written master {name} failed round-trip validation: {'; '.join(errors)}")
    if dataframe_hash(csv_check) != dataframe_hash(parquet_check):
        raise ValueError("CSV and Parquet round trips differ")

    dataset_sha = sha256(parquet_path)
    code_sha = manifests[0].get("code_HEAD_SHA")
    split_info = {
        "dataset_sha256": dataset_sha,
        "fractions": {"TRAIN": 0.6, "DISCOVERY_VALIDATION": 0.2, "FINAL_TEST": 0.2},
        "boundaries": {
            "validation_start_signal_time_msc": validation_boundary,
            "final_test_start_signal_time_msc": final_boundary,
        },
        "counts_before_purge": {name: len(part) for name, part in parts.items()},
        "counts_written": {"TRAIN": len(train), "DISCOVERY_VALIDATION": len(validation),
                           "FINAL_TEST_PROTECTED": len(parts["FINAL_TEST"])},
        "purged": {"TRAIN": purged_train, "DISCOVERY_VALIDATION": purged_validation},
        "train_parquet_sha256": sha256(split_train_path),
        "validation_parquet_sha256": sha256(split_validation_path),
        "final_test_parquet_written": False,
        "final_test_in_master_is_protected_by_process": True,
    }
    (splits_dir / "split_manifest.json").write_text(json.dumps(split_info, indent=2) + "\n", encoding="utf-8")

    all_warnings = [warning for manifest in manifests for warning in manifest.get("tester_warnings", [])]
    audit = {
        "signals": len(frame),
        "rows_written": len(frame),
        "aborted": False,
        "schema_version": str(frame.schema_version.iloc[0]),
        "exact_boundary_duplicates_removed": duplicates_removed,
        "warnings_preserved": all_warnings,
        "censored_rows": int((frame.follow_exit_reason.eq("END_OF_DATA") |
                               frame.invert_exit_reason.eq("END_OF_DATA")).sum()),
    }
    (master_dir / "master_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "dataset_version": "stochastic_master_v1",
        "dataset_hash": dataset_sha,
        "schema_version": str(frame.schema_version.iloc[0]),
        "code_HEAD_SHA": code_sha,
        "broker": "XM Global Limited",
        "symbol": str(frame.symbol.iloc[0]),
        "coverage_first_signal_server_time": str(frame.server_time.iloc[0]),
        "coverage_last_signal_server_time": str(frame.server_time.iloc[-1]),
        "signals": len(frame),
        "exact_boundary_duplicates_removed": duplicates_removed,
        "source_blocks": [m["period"] for m in manifests],
        "source_block_manifest_hashes": [hashlib.sha256(json.dumps(m, sort_keys=True).encode()).hexdigest()
                                          for m in manifests],
        "source_code_HEAD_SHAs": sorted({m.get("code_HEAD_SHA") for m in manifests}),
        "known_tester_warnings": all_warnings,
        "csv_sha256": sha256(csv_path),
        "parquet_sha256": dataset_sha,
        "final_test_status": "NOT_EVALUATED",
    }
    (master_dir / "master_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"signals": len(frame), "duplicates_removed": duplicates_removed,
            "master_dir": str(master_dir), "splits_dir": str(splits_dir), "dataset_hash": dataset_sha}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("blocks", nargs="+", type=Path, help="Directories with validated block artifacts")
    parser.add_argument("--master", type=Path, default=Path("outputs/master"))
    parser.add_argument("--splits", type=Path, default=Path("outputs/splits"))
    args = parser.parse_args()
    try:
        result = build(args.blocks, args.master, args.splits)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, ImportError, TypeError) as exc:
        print(f"Master build failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
