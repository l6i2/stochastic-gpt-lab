"""Evaluate the frozen entry spread/ATR router on quality-v1 TRAIN only.

The execution arrival is the first Tester quote at the next-bar entry. A fill
must use a strictly later quote whose time is at least arrival + latency.
Only quote records before the frozen Discovery Validation boundary are mapped
for evaluation; Validation rows, cohort data, and FINAL_TEST are never read.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from numba import njit

from evaluate_train_exit_walkforward import build_folds
from parquet_io import read_parquet
from train_event_source import assert_train_only_source_path
from validate_bar_path import QUOTE_DTYPE

ROOT = Path(__file__).resolve().parents[1]
LATENCIES = (0, 250, 500)
MIN_CELL_SIGNALS = 100
BLOCKS = ("2023", "2024", "2025", "2026")
QUOTE_CHUNK_SIZE = 8192


@njit(cache=True)
def _price_block_extrema(bid, ask, chunk_size):
    """Build compact exact min/max indexes in one sequential quote pass."""
    count = (len(bid) + chunk_size - 1) // chunk_size
    bid_min = np.empty(count, dtype=np.float64)
    bid_max = np.empty(count, dtype=np.float64)
    ask_min = np.empty(count, dtype=np.float64)
    ask_max = np.empty(count, dtype=np.float64)
    for block in range(count):
        start = block * chunk_size
        end = min(len(bid), start + chunk_size)
        bmin, bmax, amin, amax = bid[start], bid[start], ask[start], ask[start]
        for i in range(start + 1, end):
            bmin = min(bmin, bid[i])
            bmax = max(bmax, bid[i])
            amin = min(amin, ask[i])
            amax = max(amax, ask[i])
        bid_min[block], bid_max[block] = bmin, bmax
        ask_min[block], ask_max[block] = amin, amax
    return bid_min, bid_max, ask_min, ask_max


@njit(cache=True)
def _first_exit_indexed(time_msc, bar_index, bid, ask, fill, side, entry,
                        stop, chunk_size, bid_min, bid_max, ask_min, ask_max):
    """Skip quote blocks whose extrema cannot hit either fixed barrier."""
    first_block = fill // chunk_size
    last_block = (stop - 1) // chunk_size
    for block in range(first_block, last_block + 1):
        start = max(fill, block * chunk_size)
        end = min(stop, (block + 1) * chunk_size)
        if side > 0:
            possible = bid_min[block] <= entry - 180.0 or bid_max[block] >= entry + 240.0
        else:
            possible = ask_max[block] >= entry + 180.0 or ask_min[block] <= entry - 240.0
        if possible:
            for i in range(start, end):
                price = bid[i] if side > 0 else ask[i]
                pnl = side * (price - entry)
                if pnl <= -180.0:
                    return 1, i, pnl
                if pnl >= 240.0:
                    return 2, i, 240.0
    return 0, -1, 0.0


def sha256(path: Path) -> str:
    path = assert_train_only_source_path(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _regime(value: float, q1: float, q2: float) -> str:
    if not math.isfinite(value):
        return "MISSING"
    return "LOW" if value <= q1 else "MID" if value <= q2 else "HIGH"


def _select_policy(train_rows: pd.DataFrame, outcomes: dict, qlo: float,
                   qhi: float) -> dict:
    ratios = train_rows.spread_to_atr.to_numpy(dtype=float)
    finite = ratios[np.isfinite(ratios)]
    if not len(finite):
        return {"q1": None, "q2": None, "mode": {}}
    q1, q2 = (float(np.quantile(finite, qlo)), float(np.quantile(finite, qhi)))
    assignment = {str(row.signal_id): _regime(float(row.spread_to_atr), q1, q2)
                  for row in train_rows.itertuples()}
    policy = {}
    for side in ("BUY", "SELL"):
        for regime in ("LOW", "MID", "HIGH"):
            ids = [sid for sid, value in assignment.items()
                   if value == regime and outcomes[sid]["side"] == side]
            if len(ids) < MIN_CELL_SIGNALS:
                policy[(side, regime)] = "FOLLOW"
                continue
            follow = float(np.mean([outcomes[sid]["pnl"][250]["FOLLOW"] for sid in ids]))
            invert = float(np.mean([outcomes[sid]["pnl"][250]["INVERT"] for sid in ids]))
            policy[(side, regime)] = "INVERT" if invert > follow else "FOLLOW"
    return {"q1": q1, "q2": q2, "mode": policy}


def _max_drawdown(values: list[float]) -> float:
    curve = np.cumsum(np.asarray(values, dtype=float))
    if not len(curve):
        return 0.0
    return float(np.min(curve - np.maximum.accumulate(np.r_[0.0, curve])[1:]))


def _mean_ci(values: list[float], seed: int) -> list[float] | None:
    if not values:
        return None
    data = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    means = np.empty(2000, dtype=float)
    for i in range(len(means)):
        means[i] = rng.choice(data, size=len(data), replace=True).mean()
    return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


def _load_train(root: Path):
    train_path = assert_train_only_source_path(root / "outputs/splits/train.parquet")
    excluded_path = assert_train_only_source_path(
        root / "outputs/bar_controller/research/quality_v1/excluded_signal_ids.csv")
    split_path = assert_train_only_source_path(root / "outputs/splits/split_manifest.json")
    quality_path = assert_train_only_source_path(
        root / "outputs/bar_controller/research/quality_v1/tick_quality_manifest.json")
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    if quality.get("status") != "PASS_INHERITED_VALIDATION" or quality.get("final_test_accessed") is not False:
        raise ValueError("Quality-v1 source proof is not accepted")
    split = json.loads(split_path.read_text(encoding="utf-8"))
    boundary = int(split["boundaries"]["validation_start_signal_time_msc"])
    excluded = set(pd.read_csv(excluded_path, dtype=str).signal_id)
    columns = ["signal_id", "signal_time_msc", "feature_max_time_msc", "spread", "ATR", "direction", "session"]
    events = read_parquet(train_path, columns=columns)
    events["signal_id"] = events.signal_id.astype(str)
    events = events[~events.signal_id.isin(excluded)].copy()
    if events.signal_id.duplicated().any() or events.signal_id.isna().any():
        raise ValueError("Quality-v1 TRAIN signal identities are duplicated or missing")
    if (events.feature_max_time_msc > events.signal_time_msc).any():
        raise ValueError("TRAIN signal features are not causal")
    events["spread"] = pd.to_numeric(events.spread, errors="coerce")
    events["ATR"] = pd.to_numeric(events.ATR, errors="coerce")
    events["spread_to_atr"] = events.spread / events.ATR.where(events.ATR > 0)
    events = events.sort_values("signal_time_msc", kind="stable").reset_index(drop=True)
    events = events[events.signal_time_msc < boundary].reset_index(drop=True)
    if len(events) != 11714:
        raise ValueError(f"Frozen quality-v1 TRAIN membership changed: {len(events)}")
    source_path = assert_train_only_source_path(
        root / "outputs/bar_controller/research/quality_v1/signal_source_blocks.csv")
    sources = pd.read_csv(source_path, dtype={"signal_id": str, "source_block": str})
    train_ids = set(events.signal_id)
    sources = sources[sources.signal_id.isin(train_ids)]
    source_map = dict(zip(sources.signal_id, sources.source_block))
    if set(source_map) != train_ids or len(source_map) != len(train_ids):
        raise ValueError("Quality-v1 TRAIN source-block mapping is incomplete or duplicated")
    events["source_block"] = events.signal_id.map(source_map)
    return events, boundary, quality, split


def _read_train_trade_index(path: Path, wanted: set[str]) -> dict:
    path = assert_train_only_source_path(path)
    result = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            sid = row["signal_id"]
            if sid not in wanted:
                continue
            mode = row["virtual_mode"]
            if mode not in ("FOLLOW", "INVERT") or (sid, mode) in result:
                raise ValueError(f"Duplicate/unknown TRAIN quote pair: {sid}/{mode}")
            result[(sid, mode)] = {
                "side": row["virtual_side"], "entry": int(row["entry_quote_index"]),
                "exit": int(row["exit_quote_index"]),
                "entry_time": int(row["entry_time_msc"]), "exit_time": int(row["exit_time_msc"]),
                "exit_reason": row["exit_reason"],
                "entry_price": float(row["entry_price"]), "exit_price": float(row["exit_price"]),
            }
    expected = {(sid, mode) for sid in wanted for mode in ("FOLLOW", "INVERT")}
    if set(result) != expected:
        raise ValueError(f"TRAIN quote-index coverage mismatch: missing={len(expected-set(result))}, "
                         f"extra={len(set(result)-expected)}")
    return result


def _prefix_quotes(path: Path, boundary: int):
    """Expose only the TRAIN quote prefix from an already hash-validated tape.

    The immutable source-block validation and TRAIN replay proof certify tape
    ordering and quote validity. Rechecking every byte here would scan protected
    periods and duplicate a complete validation pass; only a binary-search
    boundary lookup is needed to construct the TRAIN-only memmap view.
    """
    path = assert_train_only_source_path(path)
    if path.stat().st_size == 0 or path.stat().st_size % QUOTE_DTYPE.itemsize:
        raise ValueError("Incomplete source quote tape")
    full = np.memmap(path, dtype=QUOTE_DTYPE, mode="r")
    # Binary search the ordered timestamp field; no quote price after the
    # boundary enters the returned view or any metric.
    count = int(np.searchsorted(full["time_msc"], boundary, side="left"))
    if not count:
        raise ValueError("No quote observations in TRAIN prefix")
    tape = full[:count]
    if int(tape["time_msc"][-1]) >= boundary:
        raise ValueError("TRAIN quote prefix crosses its frozen boundary")
    return tape


def _replay_entry_latency(tape, extrema, record: dict, latency: int, boundary: int) -> dict:
    arrival = record["entry"]
    if not 0 <= arrival < len(tape) or int(tape[arrival]["time_msc"]) != record["entry_time"]:
        raise ValueError("TRAIN entry quote does not match its trade index")
    target = int(tape[arrival]["time_msc"]) + latency
    fill = arrival + 1 + int(np.searchsorted(tape["time_msc"][arrival + 1:], target, side="left"))
    if fill >= len(tape) or int(tape[fill]["time_msc"]) >= boundary:
        return {"complete": False, "reason": "TRAIN_BOUNDARY", "exit_time": boundary}
    side_text = record["side"]
    side = 1 if side_text == "BUY" else -1 if side_text == "SELL" else 0
    if side == 0:
        raise ValueError("Invalid TRAIN virtual side")
    entry = float(tape[fill]["ask" if side > 0 else "bid"])
    entry_bar = int(tape[fill]["bar_index"])
    # Use only the TRAIN-prefix slice. The first quote at bar+100 is the
    # project's frozen TIME_EXIT point.
    timeout_index = int(np.searchsorted(tape["bar_index"], entry_bar + 100,
                                        side="left"))
    has_timeout = timeout_index < len(tape) and int(tape["bar_index"][timeout_index]) == entry_bar + 100
    if timeout_index < len(tape) and int(tape["bar_index"][timeout_index]) > entry_bar + 100:
        raise ValueError("TRAIN quote tape skipped a TIME_EXIT bar")
    stop = min(len(tape), timeout_index + 1) if has_timeout else len(tape)
    if fill >= stop:
        return {"complete": False, "reason": "TRAIN_BOUNDARY", "exit_time": boundary}
    code, pos, pnl_value = _first_exit_indexed(
        tape["time_msc"], tape["bar_index"], tape["bid"], tape["ask"],
        fill, side, entry, stop, QUOTE_CHUNK_SIZE, *extrema)
    if code == 0:
        if not has_timeout:
            return {"complete": False, "reason": "TRAIN_BOUNDARY", "exit_time": boundary}
        pos, code = timeout_index, 3
        price = float(tape["bid" if side > 0 else "ask"][pos])
        pnl_value = side * (price - entry)
    reason = "SL" if code == 1 else "TP" if code == 2 else "TIME_EXIT"
    return {"complete": True, "reason": reason, "exit_time": int(tape["time_msc"][pos]),
            "pnl": pnl_value, "entry_time": int(tape[fill]["time_msc"]),
            "entry_index": fill, "fill_latency_msc": latency}


def _collect_outcomes(root: Path, events: pd.DataFrame, boundary: int,
                      quality: dict, split: dict) -> dict:
    ids = set(events.signal_id)
    source_path = assert_train_only_source_path(
        root / "outputs/bar_controller/research/quality_v1/signal_source_blocks.csv")
    sources = pd.read_csv(source_path, dtype={"signal_id": str, "source_block": str})
    sources = sources[sources.signal_id.isin(ids)]
    source_map = dict(zip(sources.signal_id, sources.source_block))
    direction = dict(zip(events.signal_id.astype(str), events.direction.astype(int)))
    by_id = {sid: {"side": "BUY" if direction[sid] > 0 else "SELL",
                   "pnl": {lat: {} for lat in LATENCIES}, "exit_times": [],
                   "baseline_exit_times": []}
             for sid in ids}
    # Reuse the previously completed exact baseline replay only when its proof
    # still binds every TRAIN input and quote tape byte-for-byte. This preserves
    # replay consistency without rescanning 23k long paths in Python.
    proof_path = assert_train_only_source_path(
        root / "outputs/bar_controller/research/train_hold_replay.json")
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    quality_path = assert_train_only_source_path(
        root / "outputs/bar_controller/research/quality_v1/tick_quality_manifest.json")
    events_path = assert_train_only_source_path(
        root / "outputs/bar_controller/research/quality_v1/stochastic_events.csv")
    train_path = assert_train_only_source_path(root / "outputs/splits/train.parquet")
    split_path = assert_train_only_source_path(root / "outputs/splits/split_manifest.json")
    if (proof.get("status") != "TRAIN_HOLD_BASELINE_REPLAY_PASS"
            or proof.get("scope") != "QUALITY_V1_TRAIN_ONLY"
            or proof.get("matched_trades") != len(ids) * 2
            or proof.get("final_test_accessed") is not False
            or proof.get("validation_accessed") is not False
            or proof.get("candidate_selected") is not False
            or proof.get("quality_manifest_sha256") != sha256(quality_path)
            or proof.get("quality_event_sha256") != sha256(events_path)
            or proof.get("train_membership_sha256") != sha256(train_path)
            or proof.get("split_manifest_sha256") != sha256(split_path)):
        raise ValueError("Existing TRAIN baseline replay proof is stale or incomplete")
    # direction is reconstructed from FOLLOW side in the trade index below;
    # this value is overwritten once its per-mode records are loaded.
    for block_name in BLOCKS:
        wanted = {sid for sid in ids if source_map[sid] == block_name}
        if not wanted:
            continue
        block = root / "outputs/bar_controller/validated_blocks" / block_name
        manifest_path = assert_train_only_source_path(block / "manifest.json")
        quote_path = assert_train_only_source_path(block / "bar_quote_path.bin")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        quote_key = f"{manifest['run_id']}_bar_quote_path.bin"
        source_proof = next(item for item in quality["blocks"] if item["block"] == block_name)
        run_proof = proof.get("source_runs", {}).get(block_name, {})
        if (sha256(manifest_path) != source_proof.get("manifest_sha256")
                or manifest.get("source_artifact_hashes", {}).get(quote_key)
                   != run_proof.get("quote_tape_sha256")):
            raise ValueError(f"TRAIN replay source hash mismatch: {block_name}")
        index = _read_train_trade_index(block / "bar_trade_index.csv", wanted)
        tape = _prefix_quotes(quote_path, boundary)
        extrema = _price_block_extrema(tape["bid"], tape["ask"], QUOTE_CHUNK_SIZE)
        ordered_ids = sorted(wanted, key=lambda sid: index[(sid, "FOLLOW")]["entry"])
        for sid in ordered_ids:
            modes = {}
            for mode in ("FOLLOW", "INVERT"):
                record = index[(sid, mode)]
                if record["exit"] >= len(tape) or int(tape[record["exit"]]["time_msc"]) != record["exit_time"]:
                    raise ValueError("TRAIN exit quote does not match its trade index")
                side = 1 if record["side"] == "BUY" else -1 if record["side"] == "SELL" else 0
                if (side == 0 or record["entry"] >= len(tape)
                        or int(tape[record["entry"]]["time_msc"]) != record["entry_time"]):
                    raise ValueError("TRAIN entry quote/side does not match its trade index")
                modes[mode] = record
                by_id[sid]["baseline_exit_times"].append(record["exit_time"])
                if mode == "FOLLOW":
                    by_id[sid]["side"] = record["side"]
            for latency in LATENCIES:
                for mode, record in modes.items():
                    outcome = _replay_entry_latency(tape, extrema, record, latency, boundary)
                    if not outcome["complete"]:
                        raise ValueError(f"Incomplete TRAIN latency replay: {sid}/{mode}/{latency}")
                    by_id[sid]["pnl"][latency][mode] = outcome["pnl"]
                    by_id[sid]["exit_times"].append(outcome["exit_time"])
    if any(len(data["exit_times"]) != 6 or len(data["baseline_exit_times"]) != 2
           for data in by_id.values()):
        raise ValueError("TRAIN replay omitted one or more mode/latency outcomes")
    return by_id


def _assign(rows: pd.DataFrame, policy: dict) -> dict[str, str]:
    q1, q2 = policy["q1"], policy["q2"]
    if q1 is None or q2 is None:
        return {str(row.signal_id): "FOLLOW" for row in rows.itertuples()}
    return {str(row.signal_id): policy["mode"].get(
                ("BUY" if int(row.direction) > 0 else "SELL", _regime(float(row.spread_to_atr), q1, q2)),
                "FOLLOW") for row in rows.itertuples()}


def _summarize_fold(eval_rows: pd.DataFrame, outcomes: dict, modes: dict,
                    fixed_modes: dict, latency: int, fold: int,
                    threshold_label: str) -> dict:
    result = {"fold": fold, "threshold": threshold_label, "latency_msc": latency,
              "overall": {}, "by_side": {}, "by_source_block": {}, "by_session": {}}
    selected = []
    for row in eval_rows.itertuples():
        sid = str(row.signal_id)
        side = "BUY" if int(row.direction) > 0 else "SELL"
        mode = modes[sid]
        values = outcomes[sid]["pnl"][latency]
        fixed = fixed_modes[side]
        delta = values[mode] - values[fixed]
        selected.append((sid, side, mode, delta, outcomes[sid]["pnl"][latency],
                         str(row.source_block), str(row.session)))
    sides = ("BUY", "SELL")
    for side in (*sides, "ALL"):
        subset = selected if side == "ALL" else [item for item in selected if item[1] == side]
        deltas = [item[3] for item in subset]
        policy_pnl = [item[4][item[2]] for item in subset]
        follow = [item[4]["FOLLOW"] for item in subset]
        invert = [item[4]["INVERT"] for item in subset]
        baseline_mode = fixed_modes.get(side, "FOLLOW")
        all_deltas_follow = [item[4][item[2]] - item[4]["FOLLOW"] for item in subset]
        all_deltas_invert = [item[4][item[2]] - item[4]["INVERT"] for item in subset]
        result["overall" if side == "ALL" else "by_side"][side] = {
            "n": len(subset), "fixed_baseline_mode": baseline_mode if side != "ALL" else "SIDE_SPECIFIC_TRAIN_SELECTED",
            "mean_delta_vs_best_fixed": float(np.mean(deltas)) if deltas else None,
            "mean_delta_vs_follow": float(np.mean(all_deltas_follow)) if deltas else None,
            "mean_delta_vs_invert": float(np.mean(all_deltas_invert)) if deltas else None,
            "median_delta_vs_best_fixed": float(np.median(deltas)) if deltas else None,
            "mean_pnl": float(np.mean(policy_pnl)) if policy_pnl else None,
            "mean_follow_pnl": float(np.mean(follow)) if follow else None,
            "mean_invert_pnl": float(np.mean(invert)) if invert else None,
            "win_rate": float(np.mean(np.asarray(policy_pnl) > 0)) if policy_pnl else None,
            "profit_factor": (float(np.asarray(policy_pnl)[np.asarray(policy_pnl) > 0].sum()
                                   / -np.asarray(policy_pnl)[np.asarray(policy_pnl) < 0].sum())
                              if np.any(np.asarray(policy_pnl) < 0) else None),
            "drawdown_proxy": _max_drawdown(policy_pnl),
        }
        if side == "ALL":
            for dimension in ("block", "session"):
                grouped = {}
                idx = 5 if dimension == "block" else 6
                for item in selected:
                    group = item[idx]
                    delta = item[3]
                    grouped[group] = grouped.get(group, 0.0) + delta
                result["by_source_block" if dimension == "block" else "by_session"] = {
                    key: float(value) for key, value in grouped.items()}
    return result


def run(root: Path = ROOT, output: Path | None = None) -> dict:
    root = Path(root)
    if output is not None:
        output = assert_train_only_source_path(output)
        if output.exists():
            raise ValueError("Refusing to overwrite existing TRAIN research output")
    events, boundary, quality, split = _load_train(root)
    outcomes = _collect_outcomes(root, events, boundary, quality, split)
    events["label_end_msc"] = events.signal_id.map(
        {sid: max(value["baseline_exit_times"]) for sid,value in outcomes.items()})
    raw_folds = build_folds(events)
    if len(raw_folds) != 4:
        raise ValueError(f"Frozen quality-v1 TRAIN requires four folds, got {len(raw_folds)}")
    # Fixed fold index ranges from the preregistered expanding design. Re-purge
    # against latency-adjusted full horizons, using the same eligible IDs at
    # all three latencies.
    rows_by_id = events.set_index("signal_id", drop=False)
    max_exit = {sid: max(value["exit_times"]) for sid, value in outcomes.items()}
    fold_ranges = []
    for f in raw_folds:
        eval_ids = set(f["eval_ids"])
        eval_start = int(f["eval_start_msc"])
        later_starts = [int(item["eval_start_msc"]) for item in raw_folds if item["eval_start_msc"] > eval_start]
        eval_end = min(later_starts) if later_starts else boundary
        eval_ids = {sid for sid in eval_ids if max_exit[sid] < eval_end}
        train_ids = {sid for sid in f["train_ids"] if max_exit[sid] < eval_start}
        fold_ranges.append((f, train_ids, eval_ids))
    fold_results = []
    latency_rows = {lat: {side: [] for side in ("BUY", "SELL")} for lat in LATENCIES}
    sensitivity_rows = {lat: {side: [] for side in ("BUY", "SELL")} for lat in LATENCIES}
    selected_rows = {side: [] for side in ("BUY", "SELL")}
    dd_policy, dd_fixed = [], []
    for f, train_ids, eval_ids in fold_ranges:
        training = rows_by_id.loc[sorted(train_ids)].reset_index(drop=True)
        evaluation = rows_by_id.loc[sorted(eval_ids)].sort_values("signal_time_msc", kind="stable")
        if not len(training) or not len(evaluation):
            raise ValueError(f"Empty purged TRAIN fold {f['fold']}")
        primary = _select_policy(training, outcomes, 1/3, 2/3)
        sensitivity = _select_policy(training, outcomes, 0.25, 0.75)
        fixed_modes = {}
        for side in ("BUY", "SELL"):
            side_train = [sid for sid in train_ids if outcomes[sid]["side"] == side]
            if not side_train:
                fixed_modes[side] = "FOLLOW"
            else:
                fixed_modes[side] = ("INVERT" if np.mean(
                    [outcomes[sid]["pnl"][250]["INVERT"] for sid in side_train]) > np.mean(
                    [outcomes[sid]["pnl"][250]["FOLLOW"] for sid in side_train]) else "FOLLOW")
        primary_modes = _assign(evaluation, primary)
        sensitivity_modes = _assign(evaluation, sensitivity)
        for latency in LATENCIES:
            metrics = _summarize_fold(evaluation, outcomes, primary_modes, fixed_modes,
                                      latency, f["fold"], "33/67")
            fold_results.append(metrics)
            robust = _summarize_fold(evaluation, outcomes, sensitivity_modes, fixed_modes,
                                     latency, f["fold"], "25/75")
            fold_results.append(robust)
            for row in evaluation.itertuples():
                sid = str(row.signal_id)
                side = "BUY" if int(row.direction) > 0 else "SELL"
                p_mode, r_mode = primary_modes[sid], sensitivity_modes[sid]
                fixed = fixed_modes[side]
                latency_rows[latency][side].append(
                    outcomes[sid]["pnl"][latency][p_mode] - outcomes[sid]["pnl"][latency][fixed])
                sensitivity_rows[latency][side].append(
                    outcomes[sid]["pnl"][latency][r_mode] - outcomes[sid]["pnl"][latency][fixed])
                if latency == 250:
                    picked = outcomes[sid]["pnl"][latency][p_mode]
                    baseline = outcomes[sid]["pnl"][latency][fixed]
                    selected_rows[side].append({"delta": picked-baseline,
                                                "block": row.source_block,
                                                "session": row.session,
                                                "time": int(row.signal_time_msc)})
                    dd_policy.append((int(row.signal_time_msc), picked))
                    dd_fixed.append((int(row.signal_time_msc), baseline))
    side_gates = {}
    for side in ("BUY", "SELL"):
        primary = [r["by_side"][side]["mean_delta_vs_best_fixed"] for r in fold_results
                   if r["threshold"] == "33/67" and r["latency_msc"] == 250]
        robust = [r["by_side"][side]["mean_delta_vs_best_fixed"] for r in fold_results
                  if r["threshold"] == "25/75" and r["latency_msc"] == 250]
        latency_effects = [float(np.mean(latency_rows[lat][side])) for lat in LATENCIES]
        positive_folds = sum(value is not None and value > 0 for value in primary)
        threshold_stable = all((a is None and b is None) or (a is not None and b is not None and a*b > 0)
                               for a,b in zip(primary, robust))
        latency_stable = (latency_effects[1] != 0 and all(v*latency_effects[1] > 0 for v in latency_effects)
                          and max(abs(v-latency_effects[1]) for v in latency_effects)
                          <= 0.5*abs(latency_effects[1]))
        side_n = sum(r["by_side"][side]["n"] for r in fold_results
                     if r["threshold"] == "33/67" and r["latency_msc"] == 250)
        side_gates[side] = {
            "n": side_n, "positive_folds": positive_folds, "folds": len(primary),
            "positive_fold_fraction": positive_folds/len(primary) if primary else 0,
            "latency_effect_means_0_250_500": latency_effects,
            "latency_stable": latency_stable, "threshold_sign_stable": threshold_stable,
            "support_pass": side_n >= 80 and len(primary) >= 3,
            "fold_pass": positive_folds/len(primary) >= 0.70 if primary else False,
        }
        sizes = [r["by_side"][side]["n"] for r in fold_results
                 if r["threshold"] == "33/67" and r["latency_msc"] == 250]
        positive_effect_by_fold = [max(0.0, float(effect) * n)
                                   for effect, n in zip(primary, sizes)]
        positive_total = sum(positive_effect_by_fold)
        fold_share = max(positive_effect_by_fold, default=0.0) / positive_total if positive_total else 1.0
        side_gates[side]["max_positive_fold_share"] = fold_share
        side_gates[side]["fold_concentration_pass"] = positive_total > 0 and fold_share <= 0.50
        for dimension in ("block", "session"):
            grouped = {}
            for item in selected_rows[side]:
                grouped[item[dimension]] = grouped.get(item[dimension], 0.0) + item["delta"]
            positive_total = sum(max(0.0, value) for value in grouped.values())
            positive_groups = [value for value in grouped.values() if value > 0]
            side_gates[side][f"{dimension}_positive_groups"] = len(positive_groups)
            side_gates[side][f"{dimension}_max_positive_share"] = (
                max(positive_groups)/positive_total if positive_total else 1.0)
            side_gates[side][f"{dimension}_pass"] = (len(positive_groups) >= 2 and positive_total > 0
                and side_gates[side][f"{dimension}_max_positive_share"] <= 0.50)
    total_n = sum(side_gates[s]["n"] for s in ("BUY", "SELL"))
    dd_policy_values = [x[1] for x in sorted(dd_policy)]
    dd_fixed_values = [x[1] for x in sorted(dd_fixed)]
    policy_dd = _max_drawdown(dd_policy_values)
    fixed_dd = _max_drawdown(dd_fixed_values)
    drawdown_pass = abs(policy_dd) <= abs(fixed_dd) * 1.20 if fixed_dd < 0 else policy_dd >= 0
    survive = (total_n >= 200 and all(v["support_pass"] and v["fold_pass"]
                                       and v["latency_stable"] and v["threshold_sign_stable"]
                                       and v["block_pass"] and v["session_pass"]
                                       and v["fold_concentration_pass"]
                                       for v in side_gates.values()))
    survive = survive and drawdown_pass
    summary = {
        "status": "TRAIN_ROUTER_SURVIVES" if survive else "TRAIN_ROUTER_REJECTED",
        "scope": "QUALITY_V1_TRAIN_ONLY", "hypothesis_id": "HV2_ENTRY_SPREAD_ATR_ROUTER",
        "train_signals": len(events), "folds": len(raw_folds),
        "missing_spread_atr_rows": int(events.spread_to_atr.isna().sum()),
        "fold_support": [{"fold": f["fold"], "train_n": len(t), "eval_n": len(e)}
                         for f,t,e in fold_ranges],
        "latencies_msc": list(LATENCIES), "primary_latency_msc": 250,
        "side_gates": side_gates, "fold_results": fold_results,
        "drawdown_proxy": {"router": policy_dd, "best_fixed": fixed_dd,
                           "pass": drawdown_pass, "account_level": False},
        "confidence_intervals": {
            side: _mean_ci(latency_rows[250][side], 7200 + i)
            for i,side in enumerate(("BUY","SELL"))},
        "threshold_sensitivity": "25/75 diagnostic; never selected",
        "baseline_comparisons": ["FOLLOW_ALWAYS", "INVERT_ALWAYS"],
        "train_membership_sha256": sha256(root / "outputs/splits/train.parquet"),
        "quality_manifest_sha256": sha256(root / "outputs/bar_controller/research/quality_v1/tick_quality_manifest.json"),
        "split_manifest_sha256": sha256(root / "outputs/splits/split_manifest.json"),
        "runner_sha256": sha256(root / "python/train_entry_spread_atr_router.py"),
        "replay_kernel_sha256": sha256(root / "python/validate_bar_path.py"),
        "validation_accessed": False, "final_test_accessed": False,
        "future_cohort_accessed": False, "demo_execution": False, "live_trading": False,
    }
    if survive:
        final_policy = _select_policy(events, outcomes, 1/3, 2/3)
        policy_doc = {
            "hypothesis_id": "HV2_ENTRY_SPREAD_ATR_ROUTER",
            "feature": "signal_time_spread / signal_time_ATR",
            "missing_policy": "FOLLOW",
            "fixed_policy": {f"{key[0]}:{key[1]}": value for key,value in final_policy["mode"].items()},
            "q33": final_policy["q1"], "q67": final_policy["q2"],
            "primary_latency_msc": 250, "sensitivity_latency_msc": [0, 500],
            "entry_fill": "strictly post next-bar arrival quote, at or after arrival plus latency",
            "failure_criteria": "docs/RESEARCH_PROTOCOL_V2.md",
            "train_signals": len(events),
            "train_membership_sha256": summary["train_membership_sha256"],
            "feature_sha256": hashlib.sha256(
                b"spread/ATR@signal_time; missing=>FOLLOW; thresholds=TRAIN-fold-quantiles").hexdigest(),
            "quality_manifest_sha256": summary["quality_manifest_sha256"],
            "split_manifest_sha256": summary["split_manifest_sha256"],
            "runner_sha256": summary["runner_sha256"],
            "replay_kernel_sha256": summary["replay_kernel_sha256"],
            "validation_accessed": False, "final_test_accessed": False,
            "future_cohort_accessed": False, "demo_execution": False, "live_trading": False,
        }
        encoded = json.dumps(policy_doc, sort_keys=True, separators=(",", ":")).encode()
        summary["candidate_provisional"] = {
            "status": "FROZEN_PROVISIONAL_TRAIN_ONLY",
            "policy_sha256": hashlib.sha256(encoded).hexdigest(),
            "model_sha256": hashlib.sha256(encoded).hexdigest(), "policy": policy_doc,
        }
    else:
        summary["candidate_provisional"] = None
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path,
                        default=Path("outputs/bar_controller/research/train_entry_spread_atr_router.json"))
    args = parser.parse_args()
    root = args.root if args.root.is_absolute() else ROOT / args.root
    output = args.output if args.output.is_absolute() else root / args.output
    print(json.dumps(run(root, output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
