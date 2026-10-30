"""Offline audit of the already-approved fixed diagnostic; no MT5 invocation.

Only the pinned 2024-01-02 artifacts are opened. No arbitrary data path or date
is accepted. The report checks native arrival chronology, not physical UTC or
the values of every historical feature. No authorization artifact is created.
"""
import csv
import hashlib
import json
from pathlib import Path
import struct

from .availability import Position, check_availability, training_readiness

ROOT = Path(__file__).resolve().parents[2]
RUN = "diag_fd4e5bf3d468"
START, END = 1704153600000, 1704240000000


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_existing():
    evidence = ROOT / "configs/pc_a_native_tester_evidence_20261030"
    seals = json.loads((evidence / "hashes.json").read_text())
    native_runs = evidence / "native_runs.json"
    if digest(native_runs) != seals["native_runs.json"]:
        raise ValueError("PUBLISHED_RUN_MANIFEST_MISMATCH")
    runs = json.loads(native_runs.read_text())["runs"]
    hashes = next(r for r in runs if r["run_id"] == RUN)["artifact_sha256"]
    folder = ROOT / "outputs/pc_a_certification/native_tester/runs" / RUN

    def pinned(suffix):
        name = RUN + "_" + suffix
        path = folder / name
        if digest(path) != hashes[name]:
            raise ValueError("ORIGINAL_ARTIFACT_MISMATCH_" + suffix)
        return path

    tape = pinned("bar_quote_path.bin").read_bytes()
    if not tape or len(tape) % 28:
        raise ValueError("INVALID_TAPE_LENGTH")
    times = [row[0] for row in struct.iter_unpack("<qddi", tape)]
    if any(not START <= t < END for t in times) or any(
            b < a for a, b in zip(times, times[1:])):
        raise ValueError("UNSAFE_FIXED_NATIVE_RANGE_OR_ORDER")
    first = {}
    for index, time in enumerate(times):
        first.setdefault(time // 300000, index)

    def rows(suffix):
        with pinned(suffix).open(encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))

    events = {e["signal_id"]: e for e in rows("stochastic_events.csv")}
    snapshots = {s["snapshot_id"]: s for s in rows("intratrade_snapshots.csv")}
    delays = []

    def arrival(cutoff, feature_max, index, stamp):
        if index < 0 or index >= len(times) or times[index] != stamp:
            raise ValueError("ARRIVAL_NOT_IN_TAPE")
        if first[stamp // 300000] != index:
            raise ValueError("NOT_FIRST_OBSERVED_NEXT_BAR_QUOTE")
        bar_open = cutoff - 299999
        check_availability(bar_open_ms=bar_open, feature_max_ms=feature_max,
                           arrival_ms=stamp, quote_ms=stamp,
                           feature_ready=Position(index, 1),
                           decision=Position(index, 2), domain="XM_NATIVE_ORDER")
        delays.append(stamp - cutoff)

    trades = rows("bar_trade_index.csv")
    for trade in trades:
        event = events[trade["signal_id"]]
        arrival(int(event["signal_time_msc"]), int(event["feature_max_time_msc"]),
                int(trade["entry_quote_index"]), int(trade["entry_time_msc"]))
    executions = rows("bar_execution_quotes.csv")
    for execution in executions:
        snapshot = snapshots[execution["snapshot_id"]]
        arrival(int(execution["decision_cutoff_msc"]),
                int(snapshot["feature_max_time_msc"]),
                int(execution["decision_quote_index"]),
                int(execution["execution_time_msc"]))
    return dict(training_readiness(), fixed_native_date="2024-01-02",
                source_run=RUN, quotes=len(times), signals=len(events),
                virtual_entries_checked=len(trades), snapshots_checked=len(executions),
                arrival_chronology="PASS_NATIVE_ORDER_THIS_DIAGNOSTIC",
                cutoff_to_callback_native_label_delta_ms=dict(min=min(delays), max=max(delays)),
                delta_is_network_or_compute_latency=False,
                source_stages="INFERRED_FROM_FROZEN_ON_TICK_CODE_NOT_CPU_INSTRUMENTATION",
                feature_values_all_prefix_invariant="NOT_PROVEN_BY_THIS_CHECK",
                historical_data_vintage="UNVERIFIED",
                independent_utc_generation_time="BLOCKED",
                split_membership="UNVERIFIED_NOT_ADMITTED",
                baseline_fill="UNCHANGED_SAME_TRIGGERING_QUOTE_VIRTUAL_ASSUMPTION",
                CAUSAL_AUDIT="FAIL_GLOBAL_UNCHANGED")


if __name__ == "__main__":
    print(json.dumps(audit_existing(), indent=2, sort_keys=True))
