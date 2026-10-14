"""Build a TRAIN + DISCOVERY_VALIDATION intra-trade master; FINAL_TEST is rejected."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

try:
    from .parquet_io import read_parquet, write_parquet
    from .validate_intratrade_dataset import validate
except ImportError:
    from parquet_io import read_parquet, write_parquet
    from validate_intratrade_dataset import validate

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(blocks: list[Path], out: Path, train_path: Path, validation_path: Path) -> dict:
    split_manifest_path = ROOT / "outputs/splits/split_manifest.json"
    split_manifest = json.loads(split_manifest_path.read_text(encoding="utf-8"))
    final_start = int(split_manifest["boundaries"]["final_test_start_signal_time_msc"])
    train = read_parquet(train_path)
    validation = read_parquet(validation_path)
    train_ids = set(train["signal_id"].astype(str))
    validation_ids = set(validation["signal_id"].astype(str))
    if train_ids & validation_ids:
        raise ValueError("TRAIN and DISCOVERY_VALIDATION signal IDs overlap")

    snapshots: list[pd.DataFrame] = []
    targets: list[pd.DataFrame] = []
    source_manifests: list[dict] = []
    purged_signal_ids: set[str] = set()
    purged_snapshot_rows = 0
    for block in blocks:
        manifest_path = block / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("LIVE_TRADING") is not False or manifest.get("optimization") != "OFF":
            raise ValueError(f"Unsafe block manifest: {manifest_path}")
        if manifest.get("symbol") != "US30Cash" or manifest.get("timeframe") != "M5":
            raise ValueError(f"Unexpected symbol/timeframe: {manifest_path}")
        if manifest.get("model") != "Every tick based on real ticks":
            raise ValueError(f"Unexpected tester model: {manifest_path}")
        max_signal = manifest.get("max_signal_time_msc")
        if max_signal is None or int(max_signal) >= final_start:
            raise ValueError(f"Block period reaches protected FINAL_TEST boundary: {manifest_path}")
        snapshot_path = block / "intratrade_snapshots.csv"
        target_path = block / "intratrade_snapshot_targets.csv"
        audit_path = block / "intratrade_snapshots.csv.audit.json"
        events_path = block / "stochastic_events.csv"
        validation = validate(snapshot_path, audit_path, target_path, train_path, validation_path,
                              events_path, split_manifest_path)
        snapshot = pd.read_csv(snapshot_path)
        target = pd.read_csv(target_path) if target_path.exists() and target_path.stat().st_size else pd.DataFrame()
        unknown = set(snapshot["signal_id"].astype(str)) - train_ids - validation_ids
        if len(unknown) != int(validation["purged_signals_excluded_from_splits"]):
            raise ValueError("Split membership and independently validated purged signal IDs disagree")
        purged_signal_ids.update(unknown)
        purged_snapshot_rows += int(snapshot["signal_id"].astype(str).isin(unknown).sum())
        snapshot = snapshot[~snapshot["signal_id"].astype(str).isin(unknown)].copy()
        if not target.empty:
            target = target[target["signal_id"].astype(str).isin(train_ids | validation_ids)].copy()
        snapshots.append(snapshot)
        if not target.empty:
            targets.append(target)
        source_manifests.append({"path": str(manifest_path.relative_to(ROOT)), "sha256": sha256(manifest_path),
                                 "period": manifest.get("period"), "max_signal_time_msc": int(max_signal),
                                 "purged_signals": len(unknown),
                                 "source_event_sha256": sha256(events_path)})

    if not snapshots:
        raise ValueError("No validated intra-trade blocks were supplied")
    schemas = [tuple(frame.columns) for frame in snapshots]
    if any(schema != schemas[0] for schema in schemas[1:]):
        raise ValueError("Snapshot schema differs between historical blocks")
    frame = pd.concat(snapshots, ignore_index=True)
    key = ["signal_id", "virtual_mode", "snapshot_bar"]
    duplicates = frame.duplicated(key, keep=False)
    if duplicates.any():
        dup = frame.loc[duplicates]
        for _, group in dup.groupby(key, sort=False):
            if len(group.drop_duplicates()) != 1:
                raise ValueError("Conflicting duplicate snapshot at a block boundary")
        frame = frame.drop_duplicates()
    if frame["snapshot_id"].duplicated().any():
        raise ValueError("snapshot_id is not unique after exact-boundary deduplication")
    frame = frame.sort_values(["signal_time_msc", "snapshot_time_msc", "signal_id", "virtual_mode"], kind="stable")
    train_frame = frame[frame["signal_id"].astype(str).isin(train_ids)].copy()
    validation_frame = frame[frame["signal_id"].astype(str).isin(validation_ids)].copy()
    if set(train_frame["signal_id"]) & set(validation_frame["signal_id"]):
        raise ValueError("A signal appears in more than one inherited split")

    if targets and any(tuple(frame.columns) != tuple(targets[0].columns) for frame in targets[1:]):
        raise ValueError("Target schema differs between historical blocks")
    target_frame = pd.concat(targets, ignore_index=True) if targets else pd.DataFrame()
    if not target_frame.empty:
        if target_frame["snapshot_id"].duplicated().any():
            raise ValueError("Duplicate target across source blocks")
        target_frame = target_frame[target_frame["snapshot_id"].isin(set(frame["snapshot_id"]))]
    out.mkdir(parents=True, exist_ok=True)
    all_csv, all_parquet = out / "intratrade_master.csv", out / "intratrade_master.parquet"
    train_out, val_out = out.parent / "splits" / "train.parquet", out.parent / "splits" / "validation.parquet"
    targets_out = out / "intratrade_targets.csv"
    frame.to_csv(all_csv, index=False)
    write_parquet(frame, all_parquet, index=False)
    train_out.parent.mkdir(parents=True, exist_ok=True)
    write_parquet(train_frame, train_out, index=False)
    write_parquet(validation_frame, val_out, index=False)
    target_frame.to_csv(targets_out, index=False)
    result = {"schema_version": "2.0", "status": "BUILT_TRAIN_AND_VALIDATION_ONLY",
              "final_test_accessed": False, "train_rows": len(train_frame),
              "validation_rows": len(validation_frame), "master_rows": len(frame),
              "target_rows": len(target_frame), "train_signals": int(train_frame.signal_id.nunique()),
              "validation_signals": int(validation_frame.signal_id.nunique()),
              "purged_signal_ids": len(purged_signal_ids), "purged_snapshot_rows": purged_snapshot_rows,
              "source_blocks": source_manifests,
              "sha256": {p.name: sha256(p) for p in (all_csv, all_parquet, train_out, val_out, targets_out)}}
    (out / "intratrade_master_audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (out / "intratrade_master_manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("blocks", nargs="+", type=Path, help="validated raw block directories")
    parser.add_argument("--out", type=Path, default=Path("outputs/intratrade/master"))
    parser.add_argument("--train", type=Path, default=Path("outputs/splits/train.parquet"))
    parser.add_argument("--validation", type=Path, default=Path("outputs/splits/validation.parquet"))
    args = parser.parse_args()
    try:
        result = build([p if p.is_absolute() else ROOT / p for p in args.blocks],
                       args.out if args.out.is_absolute() else ROOT / args.out,
                       args.train if args.train.is_absolute() else ROOT / args.train,
                       args.validation if args.validation.is_absolute() else ROOT / args.validation)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"INTRATRADE MASTER BUILD BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
