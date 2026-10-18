"""Explore fixed causal EXIT rules on quality-v1 TRAIN using ordered ticks only.

This discovery tool never loads Discovery Validation or FINAL_TEST. It uses the
already verified TRAIN HOLD replay to authenticate source tapes and replays
only the first trigger per trade, not every possible snapshot as a separate
counterfactual.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from parquet_io import read_parquet
from train_event_source import read_events_for_ids
from quote_replay import Decision, replay_memmap_scenarios
from validate_bar_path import QUOTE_DTYPE

ROOT = Path(__file__).resolve().parents[1]
LATENCIES_MSC = (0, 250, 500)
POLICIES = ("HA_OPPOSITE", "STOCH_KD_OPPOSITE", "HA_AND_STOCH_OPPOSITE")
SNAPSHOT_COLUMNS = [
    "snapshot_id", "signal_id", "virtual_mode", "virtual_side", "snapshot_bar",
    "snapshot_time_msc", "feature_max_time_msc", "mark_time_msc", "ha_direction",
    "stoch_k", "stoch_d",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def policy_triggers(side: int, ha_direction, k, d) -> dict[str, bool]:
    ha = math.isfinite(float(ha_direction)) and float(ha_direction) * side < 0
    stoch = math.isfinite(float(k)) and math.isfinite(float(d)) and (float(k) - float(d)) * side < 0
    return {"HA_OPPOSITE": ha, "STOCH_KD_OPPOSITE": stoch,
            "HA_AND_STOCH_OPPOSITE": ha and stoch}


class Stats:
    def __init__(self):
        self.values = defaultdict(list)

    def add(self, policy, latency, mode, side, pnl, baseline, reason, triggered):
        for subset in ("ALL", side):
            self.values[(policy, latency, mode, subset)].append(
                (pnl, baseline, reason == "POLICY_EXIT", triggered))

    def records(self):
        output = []
        for (policy, latency, mode, subset), rows in sorted(self.values.items()):
            pnl = np.asarray([r[0] for r in rows], dtype=float)
            baseline = np.asarray([r[1] for r in rows], dtype=float)
            gains, losses = pnl[pnl > 0], pnl[pnl < 0]
            output.append({
                "policy": policy, "latency_msc": latency, "virtual_mode": mode,
                "side": subset, "n": len(rows), "triggered": sum(r[3] for r in rows),
                "policy_exit_fills": sum(r[2] for r in rows),
                "mean_pnl": float(pnl.mean()), "baseline_mean_pnl": float(baseline.mean()),
                "mean_paired_delta": float((pnl-baseline).mean()),
                "win_rate": float((pnl > 0).mean()),
                "profit_factor": float(gains.sum() / -losses.sum()) if len(losses) else None,
            })
        return output


def _load_inputs(root: Path):
    qdir = root / "outputs/bar_controller/research/quality_v1"
    quality_path = qdir / "tick_quality_manifest.json"
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    if quality.get("status") != "PASS_INHERITED_VALIDATION" or quality.get("final_test_accessed") is not False:
        raise ValueError("Quality-v1 provenance is not accepted")
    events_path = qdir / "stochastic_events.csv"
    if sha256(events_path) != quality["output_sha256"]["stochastic_events.csv"]:
        raise ValueError("Quality-v1 event hash mismatch")
    train_ids = set(read_parquet(root / "outputs/splits/train.parquet", columns=["signal_id"])
                    .signal_id.astype(str))
    train_ids -= set(pd.read_csv(qdir / "excluded_signal_ids.csv", dtype=str).signal_id)
    source = pd.read_csv(qdir / "signal_source_blocks.csv",
                         dtype={"signal_id": str, "source_block": str})
    source_map = dict(zip(source.signal_id, source.source_block))
    event_columns = ["signal_id", "signal_time_msc", "follow_exit_time", "invert_exit_time",
                     "follow_PnL", "invert_PnL"]
    events = read_events_for_ids(events_path, event_columns, train_ids)
    event_map = events.set_index("signal_id").to_dict(orient="index")
    if not train_ids <= set(source_map) or not train_ids <= set(event_map):
        raise ValueError("Frozen TRAIN membership is missing a source or event record")
    return qdir, quality_path, quality, train_ids, source_map, event_map


def _read_first_triggers(qdir: Path, train_ids: set[str]):
    from fastparquet import ParquetFile

    parquet = ParquetFile(qdir / "train.parquet")
    missing = set(SNAPSHOT_COLUMNS) - set(parquet.columns)
    if missing:
        raise ValueError(f"Training snapshot schema is missing {sorted(missing)}")
    last_bar: dict[tuple[str, str], int] = {}
    decisions: dict[tuple[str, str, str], dict] = {}
    snapshot_count = 0
    print("Reading causal TRAIN snapshots and finding first fixed-rule triggers...", flush=True)
    for group in parquet.iter_row_groups(columns=SNAPSHOT_COLUMNS):
        if group.empty:
            continue
        for row in group.itertuples(index=False, name=None):
            (snapshot_id, signal_id, mode, side_name, snapshot_bar, snapshot_time,
             feature_time, mark_time, ha, k, d) = row
            signal_id, mode, snapshot_id = str(signal_id), str(mode), str(snapshot_id)
            if signal_id not in train_ids or mode not in ("FOLLOW", "INVERT"):
                raise ValueError("Unexpected row in frozen TRAIN snapshots")
            side = 1 if side_name == "BUY" else -1 if side_name == "SELL" else 0
            if not side:
                raise ValueError("Unknown virtual side in TRAIN snapshot")
            if int(feature_time) > int(snapshot_time) or int(mark_time) > int(snapshot_time):
                raise ValueError(f"Future feature/mark timestamp in {snapshot_id}")
            key = (signal_id, mode)
            bar = int(snapshot_bar)
            if bar <= last_bar.get(key, 0):
                raise ValueError(f"Non-increasing snapshot bars in {signal_id}/{mode}")
            last_bar[key] = bar
            triggers = policy_triggers(side, ha, k, d)
            for policy, triggered in triggers.items():
                decision_key = (signal_id, mode, policy)
                if triggered and decision_key not in decisions:
                    decisions[decision_key] = {
                        "snapshot_id": snapshot_id, "signal_id": signal_id,
                        "mode": mode, "policy": policy, "side": side,
                        "snapshot_time": int(snapshot_time),
                        "feature_time": int(feature_time), "mark_time": int(mark_time),
                    }
            snapshot_count += 1
    print(f"TRAIN snapshots scanned: {snapshot_count:,}; first triggers: {len(decisions):,}", flush=True)
    return snapshot_count, decisions


def _join_trigger_arrivals(qdir: Path, decisions: dict) -> dict:
    wanted = {row["snapshot_id"] for row in decisions.values()}
    arrivals = {}
    print(f"Joining {len(wanted):,} trigger snapshots to arrival quotes...", flush=True)
    with (qdir / "bar_execution_quotes.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            snapshot_id = row["snapshot_id"]
            if snapshot_id in wanted:
                if snapshot_id in arrivals:
                    raise ValueError(f"Duplicate quote arrival for {snapshot_id}")
                arrivals[snapshot_id] = {
                    "signal_id": row["signal_id"], "mode": row["virtual_mode"],
                    "cutoff": int(row["decision_cutoff_msc"]),
                    "execution_time": int(row["execution_time_msc"]),
                    "bid": float(row["execution_bid"]), "ask": float(row["execution_ask"]),
                    "quote_index": int(row["decision_quote_index"]),
                }
    if set(arrivals) != wanted:
        raise ValueError(f"Missing trigger arrival rows: {len(wanted - arrivals.keys())}")
    print(f"Arrival quotes joined: {len(arrivals):,}", flush=True)
    return arrivals


def run(root: Path = ROOT, *, output: Path | None = None) -> dict:
    root = Path(root)
    detail_path = Path(output).with_name(Path(output).stem + "_trades.csv") if output is not None else None
    if output is not None and ("final_test" in Path(output).as_posix().lower() or Path(output).exists()
                               or detail_path.exists()):
        raise ValueError("Refusing protected or existing output path")
    qdir, quality_path, quality, train_ids, source_map, event_map = _load_inputs(root)
    split = json.loads((root / "outputs/splits/split_manifest.json").read_text(encoding="utf-8"))
    boundary = int(split["boundaries"]["final_test_start_signal_time_msc"])
    hold_proof_path = root / "outputs/bar_controller/research/train_hold_replay.json"
    hold_proof = json.loads(hold_proof_path.read_text(encoding="utf-8"))
    if (hold_proof.get("status") != "TRAIN_HOLD_BASELINE_REPLAY_PASS"
            or hold_proof.get("final_test_accessed") is not False
            or hold_proof.get("validation_accessed") is not False):
        raise ValueError("A passing TRAIN-only quote replay proof is required")
    source_proofs = {item["block"]: item for item in quality["blocks"]}
    tapes, manifests, trades = {}, {}, {}
    for block_name in ("2024", "2025"):
        block_ids = {sid for sid in train_ids if source_map[sid] == block_name}
        if not block_ids:
            continue
        block = root / "outputs/bar_controller/validated_blocks" / block_name
        manifest_path = block / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        proof = source_proofs[block_name]
        if (sha256(manifest_path) != proof["manifest_sha256"]
                or proof["source_validation"].get("status") != "PASS"
                or proof["source_validation"].get("schema_version") != "3.0"):
            raise ValueError(f"Unaccepted quote source block: {block_name}")
        expected_tape_hash = manifest["source_artifact_hashes"][f"{manifest['run_id']}_bar_quote_path.bin"]
        prior_tape_hash = hold_proof["source_runs"][block_name]["quote_tape_sha256"]
        if prior_tape_hash != expected_tape_hash:
            raise ValueError(f"TRAIN replay proof and source tape disagree: {block_name}")
        quote_path = block / "bar_quote_path.bin"
        if quote_path.stat().st_size % QUOTE_DTYPE.itemsize:
            raise ValueError(f"Partial quote record in {block_name}")
        tapes[block_name] = np.memmap(quote_path, dtype=QUOTE_DTYPE, mode="r")
        manifests[block_name] = manifest
        with (block / "bar_trade_index.csv").open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row["signal_id"] in block_ids:
                    key = (row["signal_id"], row["virtual_mode"])
                    if key in trades:
                        raise ValueError(f"Duplicate virtual trade path: {key}")
                    trades[key] = row
    if len(trades) != 2 * len(train_ids):
        raise ValueError("TRAIN does not have complete FOLLOW/INVERT quote paths")

    snapshot_count, decisions = _read_first_triggers(qdir, train_ids)
    arrivals = _join_trigger_arrivals(qdir, decisions)
    for key, row in decisions.items():
        arrival = arrivals[row["snapshot_id"]]
        if (arrival["signal_id"] != row["signal_id"] or arrival["mode"] != row["mode"]
                or row["feature_time"] > arrival["cutoff"]
                or row["mark_time"] > arrival["cutoff"]
                or row["snapshot_time"] > arrival["cutoff"]
                or arrival["execution_time"] <= arrival["cutoff"]):
            raise ValueError(f"Noncausal or mismatched arrival: {row['snapshot_id']}")
        block_name = source_map[row["signal_id"]]
        tape = tapes[block_name]
        quote_index = arrival["quote_index"]
        if (quote_index <= 0 or quote_index >= len(tape)
                or int(tape[quote_index]["time_msc"]) != arrival["execution_time"]
                or not np.isclose(float(tape[quote_index]["bid"]), arrival["bid"], rtol=0, atol=1e-8)
                or not np.isclose(float(tape[quote_index]["ask"]), arrival["ask"], rtol=0, atol=1e-8)):
            raise ValueError(f"Trigger arrival does not match ordered quote tape: {row['snapshot_id']}")
        row["decision"] = Decision(
            cutoff_msc=arrival["cutoff"], feature_max_time_msc=row["feature_time"],
            mark_time_msc=row["mark_time"], action="EXIT",
            available_sequence=quote_index, latency_msc=0)

    stats = Stats()
    if output is not None:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        temp_file = tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8",
                                                dir=Path(output).parent, delete=False,
                                                prefix="train_exit_trades_", suffix=".tmp")
        detail_temp = Path(temp_file.name)
        detail_writer = csv.writer(temp_file)
        detail_writer.writerow(["signal_id", "signal_time_msc", "label_end_msc", "source_block",
                                "virtual_mode", "virtual_side", "policy", "latency_msc",
                                "baseline_pnl", "policy_pnl", "paired_delta", "triggered",
                                "policy_exit_fill", "exit_reason"])
    else:
        temp_file = None
        detail_temp = None
        detail_writer = None
    try:
      for (signal_id, mode), trade in trades.items():
        side_name = trade["virtual_side"]
        side = 1 if side_name == "BUY" else -1 if side_name == "SELL" else 0
        if not side:
            raise ValueError("Unknown virtual side in quote trade index")
        event = event_map[signal_id]
        baseline_pnl = float(event[f"{mode.lower()}_PnL"])
        state_rows = {policy: decisions.get((signal_id, mode, policy)) for policy in POLICIES}
        active = {policy: row["decision"] for policy, row in state_rows.items() if row is not None}
        scenarios = {}
        if active:
            _, scenarios = replay_memmap_scenarios(
                tapes[source_map[signal_id]], int(trade["entry_quote_index"]),
                int(trade["exit_quote_index"]), side, decisions=active,
                latencies_msc=LATENCIES_MSC, allowed_end_exclusive=boundary,
                coverage_verified=True)
        for policy, row in state_rows.items():
            for latency in LATENCIES_MSC:
                if row is None:
                    pnl, reason, triggered = baseline_pnl, trade["exit_reason"], False
                else:
                    replay = scenarios[(policy, latency)]
                    if replay["status"] != "COMPLETE":
                        raise ValueError(f"Unexpected censored replay: {signal_id}/{mode}")
                    pnl, reason, triggered = float(replay["pnl"]), replay["reason"], True
                stats.add(policy, latency, mode, side_name, pnl, baseline_pnl, reason, triggered)
                if detail_writer is not None:
                    detail_writer.writerow([
                        signal_id, int(event["signal_time_msc"]),
                        max(int(event["follow_exit_time"]), int(event["invert_exit_time"])),
                        source_map[signal_id], mode, side_name, policy, latency,
                        baseline_pnl, pnl, pnl-baseline_pnl, int(triggered),
                        int(reason == "POLICY_EXIT"), reason,
                    ])
      if temp_file is not None:
          temp_file.flush()
          os.fsync(temp_file.fileno())
          temp_file.close()
    except BaseException:
      if temp_file is not None:
          temp_file.close()
      raise

    if detail_temp is not None:
        if detail_path.exists():
            raise ValueError("Refusing to overwrite an existing trade detail file")
        detail_temp.rename(detail_path)

    report = {
        "status": "TRAIN_EXIT_RULES_EXPLORED_NOT_PROMOTED",
        "scope": "QUALITY_V1_TRAIN_ONLY", "train_signals": len(train_ids),
        "snapshots": snapshot_count, "trigger_decisions": len(decisions),
        "virtual_trades": len(trades), "policies": {
            "HA_OPPOSITE": "first snapshot with ha_direction * virtual_side < 0",
            "STOCH_KD_OPPOSITE": "first snapshot with (stoch_k - stoch_d) * virtual_side < 0",
            "HA_AND_STOCH_OPPOSITE": "first snapshot where both component rules are true",
        },
        "latencies_msc": list(LATENCIES_MSC), "latency_primary_msc": 250,
        "metric_rows": stats.records(),
        "trade_results_file": detail_path.name if detail_path is not None else None,
        "trade_results_sha256": sha256(detail_path) if detail_path is not None else None,
        "source_runs": {block: manifest["run_id"] for block, manifest in manifests.items()},
        "quality_manifest_sha256": sha256(quality_path),
        "quality_events_sha256": sha256(qdir / "stochastic_events.csv"),
        "train_membership_sha256": sha256(root / "outputs/splits/train.parquet"),
        "split_manifest_sha256": sha256(root / "outputs/splits/split_manifest.json"),
        "hold_replay_proof_sha256": sha256(hold_proof_path),
        "runner_sha256": sha256(Path(__file__).resolve()),
        "decision_execution": "strictly after arrival quote, then selected latency; barriers take precedence",
        "random_shuffle": False, "validation_accessed": False,
        "final_test_accessed": False, "candidate_selected": False,
        "demo_execution": False, "live_trading": False,
    }
    if output is not None:
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path,
                        default=Path("outputs/bar_controller/research/train_exit_exploration_v2.json"))
    args = parser.parse_args()
    root = args.root if args.root.is_absolute() else ROOT / args.root
    output = args.output if args.output.is_absolute() else root / args.output
    result = run(root, output=output)
    print(json.dumps({"status": result["status"], "train_signals": result["train_signals"],
                      "snapshots": result["snapshots"], "trigger_decisions": result["trigger_decisions"],
                      "virtual_trades": result["virtual_trades"], "latencies_msc": result["latencies_msc"],
                      "validation_accessed": result["validation_accessed"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
