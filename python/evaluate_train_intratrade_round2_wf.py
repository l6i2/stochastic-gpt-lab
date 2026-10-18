"""Score frozen round-2 exit rules on expanding purged quality-v1 TRAIN folds."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from fastparquet import ParquetFile

from evaluate_train_exit_walkforward import build_folds
from explore_train_intratrade_round2 import FEATURES, ROOT, sha256, triggers
from train_event_source import read_events_for_ids


def _stats(values):
    a = np.asarray(values, dtype=float)
    if not len(a):
        return {"n": 0, "mean": None, "max_drawdown_proxy": None}
    curve = np.cumsum(a)
    dd = curve - np.maximum.accumulate(np.r_[0.0, curve])[1:]
    return {"n": int(len(a)), "mean": float(a.mean()),
            "max_drawdown_proxy": float(dd.min())}


def _session(ny_time: str) -> str:
    if len(ny_time) < 16:
        return "MISSING"
    hour, minute = int(ny_time[11:13]), int(ny_time[14:16])
    minutes = hour * 60 + minute
    if minutes >= 19 * 60 or minutes < 3 * 60:
        return "ASIA"
    if minutes < 8 * 60:
        return "LONDON"
    if minutes < 17 * 60:
        return "NEW_YORK"
    return "OTHER"


def _first_trigger_metadata(root: Path, train_ids: set[str], round_id: str) -> dict:
    qdir = root / "outputs/bar_controller/research/quality_v1"
    pf = ParquetFile(qdir / "train.parquet")
    output = {}
    last_bar = {}
    previous_poc = {}
    for group in pf.iter_row_groups(columns=list(FEATURES)):
        for raw in group.itertuples(index=False, name=None):
            r = dict(zip(FEATURES, raw))
            sid, mode = str(r["signal_id"]), str(r["virtual_mode"])
            if sid not in train_ids or mode != "FOLLOW":
                continue
            key = (sid, mode)
            bar = int(r["snapshot_bar"])
            if bar <= last_bar.get(key, 0):
                raise ValueError(f"Nonmonotone snapshot path: {key}")
            last_bar[key] = bar
            prior = previous_poc.get(key)
            for hid, hit in triggers(r, round_id, prior).items():
                trigger_key = (sid, hid)
                if hit and trigger_key not in output:
                    output[trigger_key] = {"ny_session": _session(str(r["NY_time"])),
                                           "snapshot_id": str(r["snapshot_id"])}
            previous_poc[key] = float(r["vp_60m_distance_price_to_POC"])
    return output


def evaluate(root: Path = ROOT, *, replay_path: Path | None = None,
             output: Path | None = None, round_id: str = "R2") -> dict:
    root = Path(root)
    replay_path = replay_path or root / f"outputs/bar_controller/research/round{round_id[-1]}/train_intratrade_round{round_id[-1]}.json"
    trade_path = replay_path.with_name(replay_path.stem + "_trades.csv")
    run = json.loads(replay_path.read_text(encoding="utf-8"))
    if (run.get("scope") != "QUALITY_V1_TRAIN_ONLY" or run.get("validation_accessed") is not False
            or run.get("final_test_accessed") is not False or sha256(trade_path) != run["trade_results_sha256"]):
        raise ValueError("Frozen TRAIN replay provenance/hash failed")
    quality_path = root / "outputs/bar_controller/research/quality_v1/tick_quality_manifest.json"
    if sha256(quality_path) != run["quality_manifest_sha256"]:
        raise ValueError("Quality manifest changed after replay")
    split_path = root / "outputs/splits/split_manifest.json"
    split = json.loads(split_path.read_text(encoding="utf-8"))
    hold_proof = json.loads((root / "outputs/bar_controller/research/train_hold_replay.json").read_text(encoding="utf-8"))
    if (sha256(split_path) != run["split_manifest_sha256"] or
            sha256(split_path) != hold_proof.get("split_manifest_sha256") or
            int(split["boundaries"]["final_test_start_signal_time_msc"]) <= 0):
        raise ValueError("Pinned split manifest/protected boundary mismatch")
    qdir = root / "outputs/bar_controller/research/quality_v1"
    train_ids = set(pd.read_parquet(root / "outputs/splits/train.parquet", columns=["signal_id"],
                                    engine="fastparquet").signal_id.astype(str))
    exclusions = set(pd.read_csv(qdir / "excluded_signal_ids.csv", dtype=str).signal_id)
    train_ids -= exclusions
    event_cols = ["signal_id", "signal_time_msc", "follow_exit_time", "invert_exit_time",
                  "follow_PnL", "invert_PnL"]
    events = read_events_for_ids(qdir / "stochastic_events.csv", event_cols, train_ids)
    if set(events.signal_id) != train_ids:
        raise ValueError("Events do not match exact quality-v1 TRAIN membership")
    invert_pnl = dict(zip(events.signal_id.astype(str), events.invert_PnL.astype(float)))
    events["label_end_msc"] = events[["follow_exit_time", "invert_exit_time"]].max(axis=1)
    folds = build_folds(events)
    if len(folds) != 4:
        raise ValueError(f"Expected four frozen folds, got {len(folds)}")

    by_policy = {h: {} for h in run["hypothesis_hashes"]}
    with trade_path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            hid, sid, latency = row["policy"], row["signal_id"], int(row["latency_msc"])
            if hid not in by_policy or sid not in train_ids:
                raise ValueError("Unexpected hypothesis or non-TRAIN trade row")
            key = (latency, sid)
            if key in by_policy[hid]:
                raise ValueError(f"Duplicate policy outcome: {hid}/{key}")
            by_policy[hid][key] = {
                "pnl": float(row["policy_pnl"]), "base": float(row["baseline_pnl"]),
                "delta": float(row["paired_delta"]), "triggered": bool(int(row["triggered"])),
                "side": row["virtual_side"], "block": row["source_block"],
                "signal_time_msc": int(row["signal_time_msc"]),
            }
    expected = len(train_ids) * 3
    for hid, rows in by_policy.items():
        if len(rows) != expected:
            raise ValueError(f"Incomplete policy rows for {hid}: {len(rows)} != {expected}")

    metadata = _first_trigger_metadata(root, train_ids, round_id)
    expected_trigger_keys = set()
    for hid, rows in by_policy.items():
        for (latency, sid), row in rows.items():
            if latency == 250 and row["triggered"]:
                expected_trigger_keys.add((sid, hid))
    if expected_trigger_keys != set(metadata):
        raise ValueError(f"Trigger/session membership mismatch: {len(expected_trigger_keys)} vs {len(metadata)}")

    results = {}
    for hid, rows in by_policy.items():
        hyp_results = {"folds": [], "latency": {}, "by_source_block": {}, "by_session": {}}
        for fold in folds:
            eval_ids = fold["eval_ids"]
            fold_res = {"fold": fold["fold"], "n": len(eval_ids), "side": {}, "latencies": {}}
            for latency in (0, 250, 500):
                current = [rows[(latency, sid)] for sid in eval_ids]
                pnl, base, invert, delta = [], [], [], []
                for sid in sorted(eval_ids, key=lambda s: rows[(latency, s)]["signal_time_msc"]):
                    r = rows[(latency, sid)]
                    pnl.append(r["pnl"]); base.append(r["base"]); delta.append(r["delta"])
                    # INVERT HOLD outcome is loaded from the same event row, never policy-selected.
                    invert.append(invert_pnl[sid])
                lat_stats = {"policy": _stats(pnl), "FOLLOW_HOLD": _stats(base), "INVERT_HOLD": _stats(invert),
                             "paired_delta_mean": float(np.mean(delta))}
                fold_res["latencies"][str(latency)] = lat_stats
                if latency == 250:
                    for side in ("BUY", "SELL"):
                        side_rows = [rows[(latency, sid)] for sid in eval_ids if rows[(latency, sid)]["side"] == side]
                        triggered = [r for r in side_rows if r["triggered"]]
                        fold_res["side"][side] = {
                            "n": len(side_rows), "triggered_n": len(triggered),
                            "trigger_rate": len(triggered) / len(side_rows) if side_rows else 0.0,
                            "mean_paired_delta": float(np.mean([r["delta"] for r in side_rows])) if side_rows else None,
                        }
            hyp_results["folds"].append(fold_res)

        for latency in (0, 250, 500):
            seq = sorted((r for (lat, _), r in rows.items() if lat == latency), key=lambda r: r["signal_time_msc"])
            base_stats = _stats([r["base"] for r in seq])
            policy_stats = _stats([r["pnl"] for r in seq])
            inv_seq = [invert_pnl[sid] for sid in sorted(
                (sid for (lat, sid) in rows if lat == latency),
                key=lambda sid: rows[(latency, sid)]["signal_time_msc"])]
            hyp_results["latency"][str(latency)] = {
                "paired_delta_mean": float(np.mean([r["delta"] for r in seq])),
                "policy_follow_portfolio": policy_stats, "FOLLOW_HOLD": base_stats,
                "INVERT_HOLD": _stats(inv_seq),
            }
        for block in ("2024", "2025", "2026"):
            subset = [r for (lat, _), r in rows.items() if lat == 250 and r["block"] == block]
            changed = [r for r in subset if r["triggered"]]
            hyp_results["by_source_block"][block] = {
                "n": len(subset), "triggered_n": len(changed),
                "mean_paired_delta": float(np.mean([r["delta"] for r in subset])) if subset else None,
                "triggered_mean_delta": float(np.mean([r["delta"] for r in changed])) if changed else None,
            }
        sessions = defaultdict(list)
        for (lat, sid), row in rows.items():
            if lat == 250 and row["triggered"]:
                sessions[metadata[(sid, hid)]["ny_session"]].append(row["delta"])
        for session, values in sessions.items():
            hyp_results["by_session"][session] = {"triggered_n": len(values), "mean_delta": float(np.mean(values)),
                                                   "total_delta": float(np.sum(values))}

        primary = hyp_results["latency"]["250"]["paired_delta_mean"]
        latency_effects = {lat: hyp_results["latency"][lat]["paired_delta_mean"] for lat in ("0", "250", "500")}
        all250 = [r for (lat, _), r in rows.items() if lat == 250]
        total_trigger = sum(r["triggered"] for r in all250)
        side_gates, fold_sides = {}, {}
        for side in ("BUY", "SELL"):
            sr = [r for r in all250 if r["side"] == side]
            st = sum(r["triggered"] for r in sr)
            side_folds = [f["side"][side] for f in hyp_results["folds"]]
            effs = [f["mean_paired_delta"] for f in side_folds]
            poss = [e for e in effs if e is not None and e > 0]
            cshare = max(poss) / sum(poss) if poss and sum(poss) > 0 else 1.0
            fold_sides[side] = {"positive_fraction": sum(e > 0 for e in effs if e is not None) / len(effs),
                                "positive_concentration": cshare,
                                "triggered_total": st,
                                "min_triggered_per_fold": min(x["triggered_n"] for x in side_folds),
                                "trigger_rate": st / len(sr) if sr else 0.0}
            side_gates[side] = (st >= 200 and min(x["triggered_n"] for x in side_folds) >= 100 and
                                st / len(sr) >= 0.05 and fold_sides[side]["positive_fraction"] >= 0.70 and
                                cshare <= 0.50)
        fold_effects = [f["latencies"]["250"]["paired_delta_mean"] for f in hyp_results["folds"]]
        positive = [x for x in fold_effects if x > 0]
        concentration = max(positive) / sum(positive) if positive and sum(positive) > 0 else 1.0
        latency_tol = max(1.0, 0.25 * abs(primary))
        latency_pass = primary > 0 and all(v > 0 and abs(v-primary) <= latency_tol for v in latency_effects.values())
        overall_positive = sum(x > 0 for x in fold_effects) / len(fold_effects) >= 0.70 and concentration <= 0.50
        dd_candidate = hyp_results["latency"]["250"]["policy_follow_portfolio"]["max_drawdown_proxy"]
        dd_base = hyp_results["latency"]["250"]["FOLLOW_HOLD"]["max_drawdown_proxy"]
        dd_pass = dd_candidate >= dd_base * 1.20
        blocks = [v for v in hyp_results["by_source_block"].values() if v["triggered_n"] >= 100]
        block_pass = sum(v["triggered_mean_delta"] > 0 for v in blocks) >= 2
        sessions_eligible = [v for v in hyp_results["by_session"].values() if v["triggered_n"] >= 100]
        session_positive = [v for v in sessions_eligible if v["mean_delta"] > 0]
        session_sum = sum(v["total_delta"] for v in session_positive)
        session_share = max((v["total_delta"] / session_sum for v in session_positive), default=1.0)
        session_pass = len(session_positive) >= 2 and session_share <= 0.50
        support_pass = total_trigger >= 500 and all(fold_sides[s]["triggered_total"] >= 200 for s in ("BUY", "SELL"))
        overall_rate = total_trigger / len(all250)
        prevalence_pass = overall_rate >= 0.05 and all(fold_sides[s]["trigger_rate"] >= 0.05 for s in ("BUY", "SELL"))
        gates = {"support": support_pass, "prevalence": prevalence_pass,
                 "overall_walk_forward": overall_positive, "both_sides_walk_forward": all(side_gates.values()),
                 "latency_robustness": latency_pass, "drawdown": dd_pass,
                 "multi_block": block_pass, "multi_session": session_pass}
        hyp_results["triggered_total"] = total_trigger
        hyp_results["trigger_rate"] = overall_rate
        hyp_results["side_walk_forward"] = fold_sides
        hyp_results["fold_concentration"] = concentration
        hyp_results["latency_sensitivity_tolerance"] = latency_tol
        hyp_results["robustness_gates"] = gates
        hyp_results["train_gate_pass"] = all(gates.values())
        results[hid] = hyp_results

    survivors = [hid for hid, res in results.items() if res["train_gate_pass"]]
    survivors.sort(key=lambda hid: (-np.mean([f["latencies"]["250"]["paired_delta_mean"]
                                              for f in results[hid]["folds"]]), hid))
    selected = survivors[0] if survivors else None
    output = output or root / f"outputs/bar_controller/research/round{round_id[-1]}/train_intratrade_round{round_id[-1]}_walkforward.json"
    if output.exists():
        raise ValueError("Refusing to overwrite walk-forward report")
    protocol_path = root / f"docs/INTRATRADE_{round_id}_PROTOCOL.md"
    report = {"status": f"TRAIN_{round_id}_WALK_FORWARD_COMPLETE", "round": round_id,
              "scope": "QUALITY_V1_TRAIN_ONLY", "hypotheses": results,
              "hypotheses_created": len(results), "train_survivors": survivors,
              "selected_for_single_discovery_validation": selected,
              "selection_rule": "Highest mean purged walk-forward portfolio delta at 250 ms, ties ascending hypothesis ID.",
              "replay_sha256": sha256(replay_path), "trades_sha256": sha256(trade_path),
              "protocol_sha256": sha256(protocol_path), "split_manifest_sha256": sha256(split_path),
              "validation_accessed": False, "final_test_accessed": False,
              "demo_execution": False, "live_trading": False}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--round-id", choices=("R2", "R3", "R4"), default="R2")
    args = parser.parse_args()
    report = evaluate(args.root, output=args.output, round_id=args.round_id)
    print(json.dumps({"status": report["status"], "survivors": report["train_survivors"],
                      "selected": report["selected_for_single_discovery_validation"],
                      "validation_accessed": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
