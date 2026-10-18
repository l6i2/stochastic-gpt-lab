"""Execute a frozen, bounded TRAIN-only family of dynamic-exit hypotheses.

Only causal every-bar snapshot features and verified ordered quote tapes are
read. The runner never opens Discovery Validation or FINAL_TEST.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from fastparquet import ParquetFile

from explore_train_intratrade_exits import _join_trigger_arrivals, _load_inputs
from train_event_source import assert_train_only_source_path
from quote_replay import Decision, replay_memmap_scenarios
from validate_bar_path import QUOTE_DTYPE

ROOT = Path(__file__).resolve().parents[1]
LATENCIES = (0, 250, 500)
FEATURES = (
    "snapshot_id", "signal_id", "virtual_mode", "virtual_side", "snapshot_bar",
    "snapshot_time_msc", "feature_max_time_msc", "mark_time_msc",
    "current_unrealized_pnl", "distance_to_sl", "current_mfe_so_far",
    "stoch_k_prev", "stoch_k", "relative_volume_20", "ATR_percentile_20",
    "return_1", "ha_changed_to_bullish", "ha_changed_to_bearish",
    "vp_60m_distance_price_to_VAH", "vp_60m_distance_price_to_VAL", "NY_time",
    "current_mae_so_far", "distance_to_tp", "vp_60m_distance_price_to_POC",
    "ema_bull_alignment", "ema_bear_alignment", "recent_low_break", "recent_high_break",
    "bars_open", "rolling_std_20", "rolling_std_50",
)


def sha256(path: Path) -> str:
    path = assert_train_only_source_path(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _num(value) -> float:
    try:
        value = float(value)
        return value if math.isfinite(value) else math.nan
    except (TypeError, ValueError):
        return math.nan


def triggers(row: dict, round_id: str = "R2", previous_poc: float | None = None) -> dict[str, bool]:
    side = 1 if row["virtual_side"] == "BUY" else -1
    pnl, mfe, sl = (_num(row[k]) for k in ("current_unrealized_pnl", "current_mfe_so_far", "distance_to_sl"))
    kprev, k = (_num(row[n]) for n in ("stoch_k_prev", "stoch_k"))
    relvol, atrpct, ret = (_num(row[n]) for n in ("relative_volume_20", "ATR_percentile_20", "return_1"))
    vah, val = (_num(row[n]) for n in (
        "vp_60m_distance_price_to_VAH", "vp_60m_distance_price_to_VAL"))
    ny_time = str(row["NY_time"])
    ha_up, ha_down = _num(row["ha_changed_to_bullish"]), _num(row["ha_changed_to_bearish"])
    if round_id == "R4":
        pnl = _num(row["current_unrealized_pnl"])
        bull, bear = _num(row["ema_bull_alignment"]), _num(row["ema_bear_alignment"])
        low_break, high_break = _num(row["recent_low_break"]), _num(row["recent_high_break"])
        bars = _num(row["bars_open"])
        std20, std50 = _num(row["rolling_std_20"]), _num(row["rolling_std_50"])
        vol_ratio = std20 / std50 if math.isfinite(std20) and math.isfinite(std50) and std50 > 0 else math.nan
        return {
            "HYP-20261018-R4-001": math.isfinite(pnl) and pnl < 0 and
                ((side > 0 and bear == 1) or (side < 0 and bull == 1)),
            "HYP-20261018-R4-002": math.isfinite(pnl) and pnl < 0 and
                ((side > 0 and low_break == 1) or (side < 0 and high_break == 1)),
            "HYP-20261018-R4-003": math.isfinite(bars) and math.isfinite(pnl) and bars >= 50 and pnl < 0,
            "HYP-20261018-R4-004": math.isfinite(vol_ratio) and math.isfinite(pnl) and
                vol_ratio <= 0.75 and pnl > 0,
        }
    if round_id == "R3":
        mae, distance_tp = _num(row["current_mae_so_far"]), _num(row["distance_to_tp"])
        poc = _num(row["vp_60m_distance_price_to_POC"])
        pnl = _num(row["current_unrealized_pnl"])
        return {
            "HYP-20261018-R3-001": math.isfinite(mae) and math.isfinite(pnl) and mae >= 120 and pnl >= -60,
            "HYP-20261018-R3-002": math.isfinite(distance_tp) and math.isfinite(pnl) and distance_tp <= 60 and pnl > 0,
            "HYP-20261018-R3-003": math.isfinite(mfe) and math.isfinite(pnl) and math.isfinite(relvol)
                and mfe >= 60 and pnl > 0 and relvol <= 0.75,
            "HYP-20261018-R3-004": math.isfinite(pnl) and pnl > 0 and math.isfinite(poc)
                and previous_poc is not None and math.isfinite(previous_poc)
                and ((side > 0 and previous_poc > 0 and poc <= 0)
                     or (side < 0 and previous_poc < 0 and poc >= 0)),
        }
    if round_id != "R2":
        raise ValueError(f"Unsupported hypothesis round: {round_id}")
    return {
        "HYP-20261018-R2-001": math.isfinite(mfe) and math.isfinite(pnl) and mfe >= 120 and pnl <= mfe - 120,
        "HYP-20261018-R2-002": math.isfinite(mfe) and math.isfinite(pnl) and mfe >= 120 and pnl <= 0,
        "HYP-20261018-R2-003": math.isfinite(sl) and math.isfinite(pnl) and sl <= 30 and pnl < 0,
        "HYP-20261018-R2-004": math.isfinite(kprev) and math.isfinite(k) and
            ((side > 0 and kprev >= 80 and k < 80) or (side < 0 and kprev <= 20 and k > 20)),
        "HYP-20261018-R2-005": math.isfinite(relvol) and relvol >= 1.25 and
            ((side > 0 and ha_down == 1) or (side < 0 and ha_up == 1)),
        "HYP-20261018-R2-006": math.isfinite(atrpct) and math.isfinite(ret) and math.isfinite(pnl) and
            atrpct >= 0.80 and ret * side < 0 and pnl < 0,
        "HYP-20261018-R2-007": math.isfinite(pnl) and pnl > 0 and
            ((side > 0 and math.isfinite(vah) and -20 <= vah <= 0) or
             (side < 0 and math.isfinite(val) and 0 <= val <= 20)),
        "HYP-20261018-R2-008": len(ny_time) >= 16 and ny_time[11:16] >= "15:30" and
            math.isfinite(pnl) and pnl > 0,
    }


def run(root: Path = ROOT, output: Path | None = None, round_id: str = "R2") -> dict:
    root = Path(root)
    if output is not None and (output.exists() or "final_test" in output.as_posix().lower()):
        raise ValueError("Refusing existing/protected output")
    if output is not None:
        assert_train_only_source_path(output)
    qdir, quality_path, quality, train_ids, source_map, event_map = _load_inputs(root)
    rule_files = tuple(sorted((root / "research/hypotheses").glob(f"HYP-20261018-{round_id}-*.json")))
    if not 1 <= len(rule_files) <= 10:
        raise ValueError(f"Expected 1..10 frozen hypotheses, found {len(rule_files)}")
    hypotheses = [json.loads(assert_train_only_source_path(path).read_text(encoding="utf-8")) for path in rule_files]
    hyp_hashes = {h["hypothesis_id"]: sha256(p) for h, p in zip(hypotheses, rule_files)}
    for h in hypotheses:
        if h.get("status_before_evaluation") != "FROZEN_TRAIN_WALK_FORWARD_PENDING":
            raise ValueError(f"Hypothesis not frozen before evaluation: {h['hypothesis_id']}")

    parquet = ParquetFile(assert_train_only_source_path(qdir / "train.parquet"))
    missing = set(FEATURES) - set(parquet.columns)
    if missing:
        raise ValueError(f"Missing frozen causal feature columns: {sorted(missing)}")
    last_bar: dict[tuple[str, str], int] = {}
    previous_poc: dict[tuple[str, str], float] = {}
    decisions: dict[tuple[str, str, str], dict] = {}
    snapshot_count = 0
    print("Scanning frozen quality-v1 TRAIN snapshots...", flush=True)
    for group in parquet.iter_row_groups(columns=list(FEATURES)):
        for raw in group.itertuples(index=False, name=None):
            row = dict(zip(FEATURES, raw))
            sid = str(row["signal_id"])
            mode = str(row["virtual_mode"])
            if sid not in train_ids or mode not in ("FOLLOW", "INVERT"):
                raise ValueError("Unexpected row outside frozen TRAIN/mode contract")
            if int(row["feature_max_time_msc"]) > int(row["snapshot_time_msc"]):
                raise ValueError(f"Feature timestamp after snapshot: {row['snapshot_id']}")
            if int(row["mark_time_msc"]) > int(row["snapshot_time_msc"]):
                raise ValueError(f"Mark timestamp after snapshot: {row['snapshot_id']}")
            key = (sid, mode)
            bar = int(row["snapshot_bar"])
            if bar <= last_bar.get(key, 0):
                raise ValueError(f"Nonmonotone snapshots: {key}")
            last_bar[key] = bar
            # Policies are defined only for FOLLOW; INVERT is never altered.
            if mode == "FOLLOW":
                prior_poc = previous_poc.get(key)
                for hyp_id, hit in triggers(row, round_id, prior_poc).items():
                    dkey = (sid, mode, hyp_id)
                    if hit and dkey not in decisions:
                        decisions[dkey] = {
                            "snapshot_id": str(row["snapshot_id"]), "signal_id": sid,
                            "mode": mode, "policy": hyp_id,
                            "side": str(row["virtual_side"]),
                            "snapshot_time": int(row["snapshot_time_msc"]),
                            "feature_time": int(row["feature_max_time_msc"]),
                            "mark_time": int(row["mark_time_msc"]),
                        }
                previous_poc[key] = _num(row["vp_60m_distance_price_to_POC"])
            snapshot_count += 1
    print(f"Scanned {snapshot_count:,} rows; {len(decisions):,} first triggers.", flush=True)
    arrivals = _join_trigger_arrivals(qdir, decisions)
    split_path = assert_train_only_source_path(root / "outputs/splits/split_manifest.json")
    split = json.loads(split_path.read_text(encoding="utf-8"))
    boundary = int(split["boundaries"]["final_test_start_signal_time_msc"])
    proof_path = assert_train_only_source_path(root / "outputs/bar_controller/research/train_hold_replay.json")
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    if proof.get("status") != "TRAIN_HOLD_BASELINE_REPLAY_PASS" or proof.get("final_test_accessed") is not False:
        raise ValueError("Verified HOLD replay proof required")
    block_proofs = {b["block"]: b for b in quality["blocks"]}
    tapes, trade_indices = {}, {}
    for block in ("2024", "2025", "2026"):
        ids = {sid for sid in train_ids if source_map[sid] == block}
        if not ids:
            continue
        bdir = root / "outputs/bar_controller/validated_blocks" / block
        manifest_path = assert_train_only_source_path(bdir / "manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if sha256(manifest_path) != block_proofs[block]["manifest_sha256"]:
            raise ValueError(f"Source manifest changed: {block}")
        tape_path = assert_train_only_source_path(bdir / "bar_quote_path.bin")
        if tape_path.stat().st_size % QUOTE_DTYPE.itemsize:
            raise ValueError(f"Partial quote tape: {block}")
        tapes[block] = np.memmap(tape_path, dtype=QUOTE_DTYPE, mode="r")
        trade_index_path = assert_train_only_source_path(bdir / "bar_trade_index.csv")
        with trade_index_path.open(encoding="utf-8-sig", newline="") as stream:
            for tr in csv.DictReader(stream):
                if tr["signal_id"] in ids and tr["virtual_mode"] == "FOLLOW":
                    if tr["signal_id"] in trade_indices:
                        raise ValueError(f"Duplicate FOLLOW trade index: {tr['signal_id']}")
                    trade_indices[tr["signal_id"]] = tr
    if set(trade_indices) != train_ids:
        raise ValueError("Missing/extra FOLLOW quote paths for frozen TRAIN")

    # Authenticate each arrival quote against the precise timestamp and side prices in tape.
    for key, d in decisions.items():
        a = arrivals[d["snapshot_id"]]
        if (a["signal_id"] != d["signal_id"] or a["mode"] != "FOLLOW" or
            d["feature_time"] > a["cutoff"] or d["mark_time"] > a["cutoff"] or
            d["snapshot_time"] > a["cutoff"] or a["execution_time"] <= a["cutoff"]):
            raise ValueError(f"Causality/arrival mismatch: {d['snapshot_id']}")
        tape = tapes[source_map[d["signal_id"]]]
        qi = a["quote_index"]
        if (qi <= 0 or qi >= len(tape) or int(tape[qi]["time_msc"]) != a["execution_time"] or
            not np.isclose(float(tape[qi]["bid"]), a["bid"], rtol=0, atol=1e-8) or
            not np.isclose(float(tape[qi]["ask"]), a["ask"], rtol=0, atol=1e-8)):
            raise ValueError(f"Arrival quote/tape mismatch: {d['snapshot_id']}")
        d["decision"] = Decision(cutoff_msc=a["cutoff"], feature_max_time_msc=d["feature_time"],
                                  mark_time_msc=d["mark_time"], action="EXIT",
                                  available_sequence=qi, latency_msc=0)

    if output is None:
        output = root / f"outputs/bar_controller/research/round{round_id[-1]}/train_intratrade_round{round_id[-1]}.json"
    detail_path = output.with_name(output.stem + "_trades.csv")
    if output.exists() or detail_path.exists():
        raise ValueError("Refusing to overwrite round output")
    assert_train_only_source_path(output)
    assert_train_only_source_path(detail_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    import tempfile
    tmp = tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", dir=output.parent,
                                     delete=False, prefix="r2_trades_", suffix=".tmp")
    detail_tmp = Path(tmp.name)
    writer = csv.writer(tmp)
    writer.writerow(["signal_id", "signal_time_msc", "label_end_msc", "source_block",
                     "virtual_side", "policy", "latency_msc", "baseline_pnl", "policy_pnl",
                     "paired_delta", "triggered", "policy_exit_fill", "exit_reason"])
    event_cols = {sid: ev for sid, ev in event_map.items()}
    trigger_counts = {h["hypothesis_id"]: 0 for h in hypotheses}
    for d in decisions.values():
        trigger_counts[d["policy"]] += 1
    print("Replaying frozen policies against ordered quote tapes...", flush=True)
    try:
        for sid in sorted(train_ids, key=lambda s: int(event_cols[s]["signal_time_msc"])):
            tr = trade_indices[sid]
            side = 1 if tr["virtual_side"] == "BUY" else -1
            base = float(event_cols[sid]["follow_PnL"])
            active = {h["hypothesis_id"]: decisions[(sid, "FOLLOW", h["hypothesis_id"])]["decision"]
                      for h in hypotheses if (sid, "FOLLOW", h["hypothesis_id"]) in decisions}
            got = {}
            if active:
                _, got = replay_memmap_scenarios(
                    tapes[source_map[sid]], int(tr["entry_quote_index"]),
                    int(tr["exit_quote_index"]), side, decisions=active,
                    latencies_msc=LATENCIES, allowed_end_exclusive=boundary,
                    coverage_verified=True)
            for h in hypotheses:
                hid = h["hypothesis_id"]
                decision = active.get(hid)
                for latency in LATENCIES:
                    triggered = decision is not None
                    if triggered:
                        result = got[(hid, latency)]
                        if result["status"] != "COMPLETE":
                            raise ValueError(f"Incomplete replay for {sid}/{hid}")
                        pnl, reason = float(result["pnl"]), result["reason"]
                    else:
                        pnl, reason = base, tr["exit_reason"]
                    writer.writerow([sid, int(event_cols[sid]["signal_time_msc"]),
                                     max(int(event_cols[sid]["follow_exit_time"]), int(event_cols[sid]["invert_exit_time"])),
                                     source_map[sid], tr["virtual_side"], hid, latency, base, pnl,
                                     pnl-base, int(triggered), int(reason == "POLICY_EXIT"), reason])
        tmp.flush()
        import os
        os.fsync(tmp.fileno())
        tmp.close()
        detail_tmp.rename(detail_path)
    except BaseException:
        tmp.close()
        raise

    report = {
        "status": f"ROUND{round_id[-1]}_TRAIN_ONLY_REPLAY_COMPLETE_PENDING_WALK_FORWARD",
        "round": round_id,
        "scope": "QUALITY_V1_TRAIN_ONLY", "train_signals": len(train_ids),
        "snapshots_scanned": snapshot_count, "latencies_msc": list(LATENCIES),
        "primary_latency_msc": 250, "hypothesis_count": len(hypotheses),
        "hypothesis_hashes": hyp_hashes, "trigger_counts": trigger_counts,
        "trade_results_file": detail_path.name, "trade_results_sha256": sha256(detail_path),
        "quality_manifest_sha256": sha256(quality_path),
        "train_membership_sha256": sha256(root / "outputs/splits/train.parquet"),
        "split_manifest_sha256": sha256(root / "outputs/splits/split_manifest.json"),
        "hold_replay_proof_sha256": sha256(root / "outputs/bar_controller/research/train_hold_replay.json"),
        "validation_accessed": False, "final_test_accessed": False,
        "candidate_selected": False, "demo_execution": False, "live_trading": False,
    }
    report["runner_sha256"] = sha256(Path(__file__).resolve())
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--round-id", choices=("R2", "R3", "R4"), default="R2")
    args = parser.parse_args()
    result = run(args.root, output=args.output, round_id=args.round_id)
    print(json.dumps({"status": result["status"], "hypotheses": result["hypothesis_count"],
                      "triggers": result["trigger_counts"], "validation_accessed": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
