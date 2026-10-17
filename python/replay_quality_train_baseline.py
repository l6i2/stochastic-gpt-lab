"""Recheck frozen FOLLOW/INVERT baseline parity for quality-v1 TRAIN only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from parquet_io import read_parquet
from quote_replay import replay_memmap_window
from validate_bar_path import QUOTE_DTYPE, open_quotes

ROOT = Path(__file__).resolve().parents[1]
BLOCKS = ("2023", "2024", "2025", "2026")
MODES = ("FOLLOW", "INVERT")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _float_equal(left: float, right: float) -> bool:
    return bool(np.isclose(left, right, rtol=0.0, atol=1e-7))


def run(root: Path = ROOT, *, output: Path | None = None) -> dict:
    root = Path(root)
    quality_dir = root / "outputs/bar_controller/research/quality_v1"
    quality_manifest_path = quality_dir / "tick_quality_manifest.json"
    quality = json.loads(quality_manifest_path.read_text(encoding="utf-8"))
    if quality.get("status") != "PASS_INHERITED_VALIDATION" or quality.get("final_test_accessed") is not False:
        raise ValueError("Quality-v1 provenance is not accepted")
    if sha256(quality_dir / "stochastic_events.csv") != quality["output_sha256"]["stochastic_events.csv"]:
        raise ValueError("Quality event hash mismatch")

    train_ids = set(read_parquet(root / "outputs/splits/train.parquet", columns=["signal_id"])
                    .signal_id.astype(str))
    excluded = set(pd.read_csv(quality_dir / "excluded_signal_ids.csv", dtype=str).signal_id)
    train_ids -= excluded
    sources = pd.read_csv(quality_dir / "signal_source_blocks.csv",
                          dtype={"signal_id": str, "source_block": str})
    source_map = dict(zip(sources.signal_id, sources.source_block))
    event_columns = ["signal_id", "schema_version", "follow_PnL", "follow_exit_time",
                     "follow_exit_reason", "invert_PnL", "invert_exit_time", "invert_exit_reason"]
    events = pd.read_csv(quality_dir / "stochastic_events.csv", usecols=event_columns,
                         dtype={"signal_id": str, "schema_version": str})
    event_map = events.set_index("signal_id").to_dict(orient="index")
    if not set(event_map) <= set(source_map):
        raise ValueError("Invalid event/source mapping")
    if not train_ids <= set(event_map) or not train_ids <= set(source_map):
        raise ValueError("Frozen TRAIN event membership is missing quality rows or source blocks")
    if events.schema_version.ne("1.1").any():
        raise ValueError("Event table schema changed; expected EA schema 1.1")

    split_manifest = json.loads((root / "outputs/splits/split_manifest.json").read_text(encoding="utf-8"))
    allowed_end = int(split_manifest["boundaries"]["final_test_start_signal_time_msc"])
    source_proofs = {item["block"]: item for item in quality["blocks"]}
    results = {block: {"trades": 0, "matched": 0} for block in BLOCKS}
    run_hashes = {}

    for block_name in BLOCKS:
        block_ids = {signal for signal in train_ids if source_map[signal] == block_name}
        if not block_ids:
            continue
        block = root / "outputs/bar_controller/validated_blocks" / block_name
        manifest_path = block / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        proof = source_proofs[block_name]
        if (sha256(manifest_path) != proof["manifest_sha256"]
                or proof["source_validation"].get("status") != "PASS"
                or proof["source_validation"].get("schema_version") != "3.0"):
            raise ValueError(f"Source block proof mismatch: {block_name}")
        quote_path = block / "bar_quote_path.bin"
        trade_path = block / "bar_trade_index.csv"
        quote_key = f"{manifest['run_id']}_bar_quote_path.bin"
        if sha256(quote_path) != manifest["source_artifact_hashes"][quote_key]:
            raise ValueError(f"Quote tape hash mismatch: {block_name}")
        tape = open_quotes(quote_path, allowed_end)
        found = set()
        with trade_path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                signal_id, mode = row["signal_id"], row["virtual_mode"]
                if signal_id not in block_ids:
                    continue
                if mode not in MODES or (signal_id, mode) in found:
                    raise ValueError(f"Duplicate or unknown TRAIN virtual trade: {signal_id}/{mode}")
                found.add((signal_id, mode))
                side = 1 if row["virtual_side"] == "BUY" else -1 if row["virtual_side"] == "SELL" else 0
                if side == 0:
                    raise ValueError(f"Invalid virtual side: {signal_id}/{mode}")
                entry_index, exit_index = int(row["entry_quote_index"]), int(row["exit_quote_index"])
                replay = replay_memmap_window(
                    tape, entry_index, exit_index, side,
                    allowed_end_exclusive=allowed_end, coverage_verified=True)
                event = event_map[signal_id]
                prefix = mode.lower()
                if (replay["status"] != "COMPLETE"
                        or replay["reason"] != row["exit_reason"]
                        or replay["reason"] != event[f"{prefix}_exit_reason"]
                        or replay["exit_sequence"] != exit_index
                        or replay["exit_time_msc"] != int(event[f"{prefix}_exit_time"])
                        or not _float_equal(replay["pnl"], float(event[f"{prefix}_PnL"]))):
                    raise ValueError(f"HOLD baseline replay parity failure: {signal_id}/{mode}")
                results[block_name]["trades"] += 1
                results[block_name]["matched"] += 1
        expected = {(signal, mode) for signal in block_ids for mode in MODES}
        if found != expected:
            raise ValueError(f"TRAIN trade index coverage mismatch in {block_name}: "
                             f"missing={len(expected - found)}, extra={len(found - expected)}")
        run_hashes[block_name] = {
            "run_id": manifest["run_id"],
            "block_manifest_sha256": sha256(manifest_path),
            "quote_tape_sha256": sha256(quote_path),
        }

    total = sum(item["trades"] for item in results.values())
    if total != 2 * len(train_ids) or any(item["matched"] != item["trades"] for item in results.values()):
        raise ValueError("TRAIN replay did not cover both frozen virtual modes")
    summary = {
        "status": "TRAIN_HOLD_BASELINE_REPLAY_PASS",
        "scope": "QUALITY_V1_TRAIN_ONLY",
        "train_signals": len(train_ids),
        "virtual_trades": total,
        "matched_trades": total,
        "modes": {"FOLLOW": len(train_ids), "INVERT": len(train_ids)},
        "blocks": results,
        "source_runs": run_hashes,
        "quality_manifest_sha256": sha256(quality_manifest_path),
        "train_membership_sha256": sha256(root / "outputs/splits/train.parquet"),
        "split_manifest_sha256": sha256(root / "outputs/splits/split_manifest.json"),
        "quality_event_sha256": sha256(quality_dir / "stochastic_events.csv"),
        "decision_latency_msc": None,
        "final_test_accessed": False,
        "validation_accessed": False,
        "candidate_selected": False,
        "demo_execution": False,
        "live_trading": False,
    }
    if output is not None:
        output = Path(output)
        if "final_test" in output.as_posix().lower() or output.exists():
            raise ValueError("Refusing protected or existing replay output path")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path,
                        default=Path("outputs/bar_controller/research/train_hold_replay.json"))
    args = parser.parse_args()
    root = args.root if args.root.is_absolute() else ROOT / args.root
    output = args.output if args.output.is_absolute() else root / args.output
    print(json.dumps(run(root, output=output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
