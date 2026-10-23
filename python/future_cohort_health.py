"""Integrity and eligibility metadata for the sealed future cohort only.

This module intentionally has no outcome, PnL, win-rate, ranking, or tuning
code. It reads raw tick/bar segments, calculates only frozen signal-support
metadata, and fails maturity closed when an official session calendar or
frozen candidate package is absent.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
from datetime import date, datetime, time, timedelta, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "python") not in sys.path:
    sys.path.insert(0, str(ROOT / "python"))

from future_validation_collector import (  # noqa: E402
    BAR_FIELDS, COHORT_ROOT, START_UTC, TICK_FIELDS, _load_manifest, _sha256,
)

SESSION_CALENDAR = ROOT / "configs/xm_us30cash_sessions_utc.json"
HEALTH_PROTOCOL = ROOT / "configs/future_cohort_metadata_spec.json"
HEALTH_NAME = "cohort_health_report.json"


def _read_spec() -> dict[str, Any]:
    return json.loads(HEALTH_PROTOCOL.read_text(encoding="utf-8"))


def _nth_weekday(year: int, month: int, weekday: int, occurrence: int) -> date:
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (occurrence - 1))


def _ny_wall_time(utc_dt: datetime) -> datetime:
    """Convert UTC to New York with the US DST rule, without optional packages."""
    dt = utc_dt.astimezone(timezone.utc)
    year = dt.year
    # Since 2007: DST starts 02:00 local standard time (07:00 UTC) on the
    # second Sunday in March and ends 02:00 local daylight time (06:00 UTC) on
    # the first Sunday in November.
    start = datetime.combine(_nth_weekday(year, 3, 6, 2), time(7), timezone.utc)
    end = datetime.combine(_nth_weekday(year, 11, 6, 1), time(6), timezone.utc)
    offset = timedelta(hours=-4 if start <= dt < end else -5)
    return (dt + offset).replace(tzinfo=None)


def _session(utc_dt: datetime) -> str:
    local = _ny_wall_time(utc_dt)
    minute = local.hour * 60 + local.minute
    if minute >= 19 * 60 or minute < 3 * 60:
        return "Asia"
    if minute < 8 * 60:
        return "London"
    if minute < 17 * 60:
        return "New_York"
    return "Other"


def _manifest_days(manifest: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    segments = sorted(manifest.get("segments", []), key=lambda item: item["day_utc"])
    days = [str(item["day_utc"]) for item in segments]
    if len(days) != len(set(days)):
        raise ValueError("duplicate UTC-day segment")
    return days, segments


def _complete_period_counts(day_names: list[str], start: date, end: date) -> tuple[int, int]:
    covered = {date.fromisoformat(f"{x[:4]}-{x[4:6]}-{x[6:8]}") for x in day_names}
    week_keys: set[tuple[int, int]] = set()
    month_keys: set[tuple[int, int]] = set()
    cursor = start
    while cursor <= end:
        year, week, _ = cursor.isocalendar()
        week_start = cursor - timedelta(days=cursor.weekday())
        week_end = week_start + timedelta(days=6)
        if week_start >= start and week_end <= end and all(
                week_start + timedelta(days=i) in covered for i in range(7)):
            week_keys.add((year, week))
        month_start = cursor.replace(day=1)
        next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        month_end = next_month - timedelta(days=1)
        if month_start >= start and month_end <= end and all(
                month_start + timedelta(days=i) in covered for i in range((month_end-month_start).days + 1)):
            month_keys.add((month_start.year, month_start.month))
        cursor += timedelta(days=1)
    return len(week_keys), len(month_keys)


def _manifest_chain_status(cohort_root: Path, current_hash: str) -> tuple[str, bool]:
    history = Path(cohort_root) / "manifest_history"
    ledger = history / "chain.jsonl"
    if not ledger.is_file():
        return "NO_SNAPSHOT_HISTORY", False
    try:
        records = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not records:
            return "EMPTY_SNAPSHOT_HISTORY", False
        previous_hash = None
        full = True
        for index, record in enumerate(records):
            snapshot = history / record["snapshot"]
            if not snapshot.is_file() or _sha256(snapshot) != record.get("sha256"):
                return "SNAPSHOT_HASH_MISMATCH", False
            snapshot_obj = json.loads(snapshot.read_text(encoding="utf-8"))
            parent = record.get("previous_manifest_sha256")
            if snapshot_obj.get("previous_manifest_sha256") != parent:
                return "SNAPSHOT_PARENT_MISMATCH", False
            if index == 0:
                if parent is not None:
                    full = False  # An audit anchor cannot prove the earlier overwritten version.
            elif parent != previous_hash:
                return "CHAIN_LINK_MISMATCH", False
            previous_hash = record["sha256"]
        if previous_hash != current_hash:
            return "CURRENT_MANIFEST_NOT_LATEST_ARCHIVE", False
        if not full:
            return "BASELINE_ANCHORED_PREFIX_UNVERIFIED", False
        return "FULL_CHAIN_VERIFIED", True
    except (OSError, KeyError, ValueError, json.JSONDecodeError):
        return "INVALID_SNAPSHOT_HISTORY", False


def _bar_feature_rows(segments: list[dict[str, Any]], cohort_root: Path):
    """Yield causal signal and health metadata from closed M5 OHLC rows."""
    highs: deque[float] = deque(maxlen=50)
    lows: deque[float] = deque(maxlen=50)
    closes: deque[float] = deque(maxlen=50)
    true_ranges: deque[float] = deque(maxlen=14)
    fastks: deque[float] = deque(maxlen=3)
    atr_history: deque[float] = deque(maxlen=288)
    ema50_history: deque[float] = deque(maxlen=13)
    ema20 = ema50 = previous_close = previous_ema50 = previous_k = None
    previous_msc = None
    bars_count = 0
    bad_bars = 0
    bar_count_mismatches = []
    max_gap_minutes = 0.0
    for segment in segments:
        segment_bars = 0
        path = cohort_root / segment["bars_file"]
        with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
            import csv
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != BAR_FIELDS:
                raise ValueError(f"M5 schema mismatch: {segment['bars_file']}")
            for row in reader:
                stamp_s = int(row["time"])
                stamp_msc = stamp_s * 1000
                segment_bars += 1
                values = [float(row[key]) for key in ("open", "high", "low", "close")]
                op, hi, lo, close = values
                bars_count += 1
                if not (all(math.isfinite(v) and v > 0 for v in values)
                        and hi >= max(op, close, lo) and lo <= min(op, close, hi)):
                    bad_bars += 1
                    yield {"_bar_time": stamp_s}
                    continue
                yield {"_bar_time": stamp_s}
                if previous_msc is not None and stamp_msc > previous_msc:
                    max_gap_minutes = max(max_gap_minutes, (stamp_msc - previous_msc) / 60000 - 5)
                previous_msc = stamp_msc

                tr = hi - lo if previous_close is None else max(
                    hi - lo, abs(hi - previous_close), abs(lo - previous_close))
                true_ranges.append(tr)
                atr = sum(true_ranges) / len(true_ranges)
                highs.append(hi); lows.append(lo); closes.append(close)
                alpha20, alpha50 = 2.0 / 21.0, 2.0 / 51.0
                ema20 = close if ema20 is None else alpha20 * close + (1 - alpha20) * ema20
                ema50 = close if ema50 is None else alpha50 * close + (1 - alpha50) * ema50
                ema50_history.append(ema50)

                if len(highs) >= 5:
                    highest, lowest = max(list(highs)[-5:]), min(list(lows)[-5:])
                    fastk = 50.0 if highest == lowest else 100.0 * (close - lowest) / (highest - lowest)
                    fastks.append(fastk)
                else:
                    fastk = None
                main_k = sum(fastks) / 3.0 if len(fastks) == 3 else None
                event_time = datetime.fromtimestamp(stamp_s + 300, timezone.utc)
                side = None
                if main_k is not None and previous_k is not None:
                    if previous_k <= 20.0 and main_k > 20.0:
                        side = "BUY"
                    elif previous_k >= 80.0 and main_k < 80.0:
                        side = "SELL"
                if side:
                    regime = "UNKNOWN"
                    volatility = "UNKNOWN"
                    if len(closes) >= 20 and len(true_ranges) == 14 and len(ema50_history) == 13:
                        slope = (ema50 - ema50_history[0]) / max(atr, 1e-12)
                        separation = (ema20 - ema50) / max(atr, 1e-12)
                        range_width = (max(list(highs)[-20:]) - min(list(lows)[-20:])) / max(atr, 1e-12)
                        if separation > 0 and slope > 0.1:
                            regime = "uptrend"
                        elif separation < 0 and slope < -0.1:
                            regime = "downtrend"
                        elif abs(separation) <= 0.1 and range_width <= 3.0:
                            regime = "range"
                        else:
                            regime = "transition"
                        baseline_atr = statistics.median(atr_history) if atr_history else None
                        if baseline_atr is not None and baseline_atr > 0:
                            ratio = atr / baseline_atr
                            volatility = "low" if ratio < 0.8 else "high" if ratio > 1.25 else "medium"
                    yield {"side": side, "session": _session(event_time), "regime": regime,
                           "volatility": volatility, "time_utc": event_time.isoformat().replace("+00:00", "Z")}
                previous_k = main_k
                previous_close = close
                previous_ema50 = ema50
                atr_history.append(atr)
        if segment_bars != int(segment.get("bars_rows", -1)):
            bar_count_mismatches.append(segment["day_utc"] + ":bars")
    yield {"_audit": {"bars_rows_scanned": bars_count, "invalid_bars": bad_bars,
                      "max_observed_bar_gap_minutes": max(0.0, max_gap_minutes),
                      "bar_count_mismatches": bar_count_mismatches}}


def build_health_report(*, cohort_root: Path = COHORT_ROOT,
                        now: datetime | None = None,
                        session_calendar_path: Path = SESSION_CALENDAR,
                        frozen_candidate_path: Path | None = None,
                        causality_audit_path: Path | None = None) -> dict[str, Any]:
    """Verify only capture integrity and frozen metadata maturity; never outcomes."""
    from future_validation_collector import TEMPLATE_PATH
    cohort_root = Path(cohort_root).resolve()
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    manifest = _load_manifest(cohort_root, TEMPLATE_PATH)
    manifest_hash = _sha256(cohort_root / "cohort_manifest.json")
    chain_status, chain_pass = _manifest_chain_status(cohort_root, manifest_hash)
    metadata_sidecar = HEALTH_PROTOCOL.with_name(HEALTH_PROTOCOL.name + ".sha256")
    metadata_spec_frozen = (metadata_sidecar.is_file()
                            and metadata_sidecar.read_text(encoding="ascii").split()[0] == _sha256(HEALTH_PROTOCOL))
    day_names, segments = _manifest_days(manifest)
    tick_rows = bars_rows = invalid_ticks = duplicate_tick_msc = invalid_time_rows = 0
    first_tick = last_tick = None
    spread_hist = Counter()
    previous_tick = None
    segment_count_mismatches = []
    for segment in segments:
        tick_path = cohort_root / segment["ticks_file"]
        actual_tick_rows = 0
        with gzip.open(tick_path, "rt", encoding="utf-8", newline="") as stream:
            import csv
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != TICK_FIELDS:
                raise ValueError(f"tick schema mismatch: {segment['ticks_file']}")
            for row in reader:
                tick_rows += 1
                actual_tick_rows += 1
                stamp = int(row["time_msc"])
                if abs(int(row["time"]) * 1000 - stamp) > 999:
                    invalid_time_rows += 1
                bid, ask = float(row["bid"]), float(row["ask"])
                if previous_tick is not None:
                    if stamp < previous_tick:
                        raise ValueError("tick timestamps are not monotonic")
                    duplicate_tick_msc += stamp == previous_tick
                previous_tick = stamp
                first_tick = stamp if first_tick is None else min(first_tick, stamp)
                last_tick = stamp if last_tick is None else max(last_tick, stamp)
                if not (math.isfinite(bid) and math.isfinite(ask) and 0 < bid <= ask):
                    invalid_ticks += 1
                else:
                    spread = ask - bid
                    bucket = "0-1" if spread < 1 else "1-2" if spread < 2 else "2-5" if spread < 5 else "5+"
                    spread_hist[bucket] += 1
        if actual_tick_rows != int(segment.get("ticks_rows", -1)):
            segment_count_mismatches.append(segment["day_utc"] + ":ticks")
        bars_rows += int(segment.get("bars_rows", 0))

    signal_counts = Counter()
    session_counts = Counter()
    side_session_counts = Counter()
    regime_counts = Counter()
    volatility_counts = Counter()
    side_regime_counts = Counter()
    side_volatility_counts = Counter()
    observed_bar_times: set[int] = set()
    for item in _bar_feature_rows(segments, cohort_root):
        if "_bar_time" in item:
            observed_bar_times.add(int(item["_bar_time"]))
            continue
        if "_audit" in item:
            bars_audit = item["_audit"]
            continue
        signal_counts[item["side"]] += 1
        session_counts[item["session"]] += 1
        side_session_counts[(item["session"], item["side"])] += 1
        regime_counts[item["regime"]] += 1
        volatility_counts[item["volatility"]] += 1
        side_regime_counts[(item["regime"], item["side"])] += 1
        side_volatility_counts[(item["volatility"], item["side"])] += 1
    bars_audit = locals().get("bars_audit", {"bars_rows_scanned": 0, "invalid_bars": 0,
                                               "max_observed_bar_gap_minutes": 0.0,
                                               "bar_count_mismatches": []})

    covered_dates = [date.fromisoformat(f"{x[:4]}-{x[4:6]}-{x[6:8]}") for x in day_names]
    complete_days = [d for d in covered_dates if datetime.combine(d + timedelta(days=1), time.min, timezone.utc) <= now]
    complete_weeks, complete_months = _complete_period_counts(
        day_names, START_UTC.date(), max(covered_dates, default=START_UTC.date()))
    expected_days = []
    cursor = START_UTC.date()
    for d in covered_dates:
        while cursor < d:
            expected_days.append(cursor.strftime("%Y%m%d")); cursor += timedelta(days=1)
        cursor = d + timedelta(days=1)
    gaps = expected_days
    calendar_path = Path(session_calendar_path)
    calendar_exists = calendar_path.is_file()
    calendar_hash = _sha256(calendar_path) if calendar_exists else None
    calendar_sidecar = calendar_path.with_name(calendar_path.name + ".sha256")
    calendar_config_frozen = (calendar_hash is not None and calendar_sidecar.is_file()
                              and calendar_sidecar.read_text(encoding="ascii").split()[0] == calendar_hash)
    calendar_valid = False
    if calendar_exists:
        try:
            calendar = json.loads(calendar_path.read_text(encoding="utf-8"))
            calendar_valid = (calendar_config_frozen and calendar.get("verified") is True
                              and bool(calendar.get("source_sha256"))
                              and bool(calendar.get("weekly_sessions_utc"))
                              and bool(calendar.get("daily_exceptions_utc") is not None))
        except (OSError, json.JSONDecodeError):
            calendar_valid = False
    expected_bar_times: set[int] = set()
    if calendar_valid:
        covered_from = START_UTC.date()
        covered_to = max(covered_dates, default=covered_from)
        day = covered_from
        while day <= covered_to:
            day_key = day.isoformat()
            exception = calendar.get("daily_exceptions_utc", {}).get(day_key)
            periods = exception if exception is not None else None
            if periods is None:
                weekday = day.weekday()
                for schedule in calendar["weekly_sessions_utc"]:
                    first = date.fromisoformat(schedule["effective_from_utc"])
                    last = date.fromisoformat(schedule["effective_to_utc"])
                    if first <= day <= last:
                        periods = schedule["weekdays"].get(str(weekday), [])
                        break
            for period in periods or []:
                start_h, start_m = map(int, period["start"].split(":"))
                end_h, end_m = map(int, period["end"].split(":"))
                t = datetime(day.year, day.month, day.day, start_h, start_m, tzinfo=timezone.utc)
                end_dt = datetime(day.year, day.month, day.day, end_h, end_m, tzinfo=timezone.utc)
                while t < end_dt:
                    expected_bar_times.add(int(t.timestamp()))
                    t += timedelta(minutes=5)
            day += timedelta(days=1)
    missing_bar_times = sorted(expected_bar_times - observed_bar_times) if calendar_valid else []
    missing_bar_pct = (100.0 * len(missing_bar_times) / len(expected_bar_times)
                       if expected_bar_times else None)
    longest_missing_run = run = 0
    previous_missing = None
    for stamp in missing_bar_times:
        run = run + 1 if previous_missing is not None and stamp - previous_missing == 300 else 1
        longest_missing_run = max(longest_missing_run, run)
        previous_missing = stamp
    candidate_frozen = False
    candidate_hash = None
    if frozen_candidate_path is not None and Path(frozen_candidate_path).is_file():
        candidate_path = Path(frozen_candidate_path)
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        candidate_hash = _sha256(candidate_path)
        candidate_sidecar = candidate_path.with_name(candidate_path.name + ".sha256")
        candidate_frozen = (candidate.get("status") == "FROZEN"
                            and candidate_sidecar.is_file()
                            and candidate_sidecar.read_text(encoding="ascii").split()[0] == candidate_hash)
    causality_audit_pass = False
    causality_audit_hash = None
    if causality_audit_path is not None and Path(causality_audit_path).is_file():
        audit_path = Path(causality_audit_path)
        audit_sidecar = audit_path.with_name(audit_path.name + ".sha256")
        audit_hash_valid = (audit_sidecar.is_file()
                            and audit_sidecar.read_text(encoding="ascii").split()[0] == _sha256(audit_path))
        causality_audit_hash = _sha256(audit_path) if audit_hash_valid else None
        audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_hash_valid else {}
        causality_audit_pass = (audit_hash_valid and audit.get("status") == "PASS"
                                and audit.get("cohort_manifest_sha256") == manifest_hash
                                and audit.get("metadata_spec_sha256") == _sha256(HEALTH_PROTOCOL)
                                and audit.get("pnl_read") is False
                                and audit.get("labels_read") is False)
    total_signals = signal_counts["BUY"] + signal_counts["SELL"]
    mature_gates = {
        "signals_total": total_signals >= 300,
        "signals_buy": signal_counts["BUY"] >= 120,
        "signals_sell": signal_counts["SELL"] >= 120,
        "complete_utc_weeks": complete_weeks >= 16,
        "complete_utc_months": complete_months >= 4,
        "session_support": all(session_counts[s] >= 30 for s in ("Asia", "London", "New_York"))
                           and all(side_session_counts[(s, side)] >= 10
                                   for s in ("Asia", "London", "New_York")
                                   for side in ("BUY", "SELL")),
        "regime_support": all(regime_counts[r] >= 25 for r in ("uptrend", "downtrend", "range", "transition")),
        "volatility_support": all(volatility_counts[v] >= 30 for v in ("low", "medium", "high")),
        "tick_quality_100_percent": tick_rows > 0 and invalid_ticks == 0 and invalid_time_rows == 0,
        "bar_quality": bars_rows > 0 and bars_audit["invalid_bars"] == 0
                       and bars_audit["bars_rows_scanned"] == bars_rows,
        "m5_gaps_pass": calendar_valid and missing_bar_pct is not None
                        and missing_bar_pct < 1.0 and longest_missing_run * 5 <= 60,
        "manifest_row_counts_match": not segment_count_mismatches,
        "bar_segment_counts_match": not bars_audit["bar_count_mismatches"],
        "manifest_chain_verified": chain_pass,
        "metadata_spec_frozen": metadata_spec_frozen,
        "session_calendar_config_frozen": calendar_config_frozen,
        "session_calendar_verified": calendar_valid,
        "candidate_frozen": candidate_frozen,
        "causality_audit_pass": causality_audit_pass,
        "no_utc_day_gaps": not gaps,
    }
    # Side/session minimums from the frozen readiness rule.
    # The side-by-session counts are calculated in the second counter below.
    report = {
        "protocol": "prospective-evaluation/1.0",
        "generated_utc": now.isoformat().replace("+00:00", "Z"),
        "cohort_id": manifest["cohort_id"],
        "cohort_manifest_sha256": manifest_hash,
        "metadata_spec_sha256": _sha256(HEALTH_PROTOCOL),
        "session_calendar_config_sha256": calendar_hash,
        "session_calendar_config_frozen": calendar_config_frozen,
        "metadata_spec_frozen": metadata_spec_frozen,
        "health_code_sha256": _sha256(Path(__file__).resolve()),
        "cohort_start_utc": manifest["cohort_start_utc"],
        "first_tick_utc": datetime.fromtimestamp(first_tick / 1000, timezone.utc).isoformat().replace("+00:00", "Z") if first_tick is not None else None,
        "latest_tick_utc": datetime.fromtimestamp(last_tick / 1000, timezone.utc).isoformat().replace("+00:00", "Z") if last_tick is not None else None,
        "cohort_days": len(complete_days), "cohort_rows": tick_rows, "m5_bars": bars_rows,
        "buy_count_metadata": signal_counts["BUY"], "sell_count_metadata": signal_counts["SELL"],
        "session_coverage_metadata": dict(session_counts),
        "side_session_coverage_metadata": {f"{s}:{side}": side_session_counts[(s, side)]
                                            for s in ("Asia", "London", "New_York")
                                            for side in ("BUY", "SELL")},
        "regime_coverage_metadata": dict(regime_counts),
        "volatility_coverage_metadata": dict(volatility_counts),
        "side_regime_coverage_metadata": {f"{state}:{side}": side_regime_counts[(state, side)]
                                           for state in ("uptrend", "downtrend", "range", "transition")
                                           for side in ("BUY", "SELL")},
        "side_volatility_coverage_metadata": {f"{state}:{side}": side_volatility_counts[(state, side)]
                                               for state in ("low", "medium", "high")
                                               for side in ("BUY", "SELL")},
        "spread_distribution_metadata": dict(spread_hist),
        "latency_distribution_metadata": {},
        "invalid_ticks": invalid_ticks, "invalid_time_rows": invalid_time_rows,
        "duplicate_tick_msc": duplicate_tick_msc,
        "invalid_bars": bars_audit["invalid_bars"], "missing_utc_days": gaps,
        "segment_count_mismatches": segment_count_mismatches,
        "bar_segment_count_mismatches": bars_audit["bar_count_mismatches"],
        "manifest_chain_status": chain_status,
        "max_observed_bar_gap_minutes": bars_audit["max_observed_bar_gap_minutes"],
        "missing_expected_m5_bar_pct": missing_bar_pct,
        "longest_missing_open_session_minutes": longest_missing_run * 5,
        "session_calendar_verified": calendar_valid,
        "m5_gaps_pass": calendar_valid and missing_bar_pct is not None
                        and missing_bar_pct < 1.0 and longest_missing_run * 5 <= 60,
        "candidate_frozen": candidate_frozen,
        "candidate_sha256": candidate_hash,
        "causality_audit_sha256": causality_audit_hash,
        "causality_audit_pass": causality_audit_pass,
        "maturity_gates": mature_gates,
        "cohort_mature": all(mature_gates.values()),
        "collector_train_access_allowed": False,
        "scoring_performed": False, "pnl_read": False, "labels_read": False,
        "FINAL_TEST": "LOCKED", "DEMO": "DISABLED", "LIVE_TRADING": False,
    }
    report["status"] = ("WAITING_PROSPECTIVE_EVALUATION_AUTHORIZATION" if report["cohort_mature"]
                        else "NOT_MATURE")
    return report


def write_health_report(report: dict[str, Any], cohort_root: Path = COHORT_ROOT) -> tuple[Path, str]:
    path = Path(cohort_root) / HEALTH_NAME
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    temp.replace(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    path.with_name(path.name + ".sha256").write_text(digest + "\n", encoding="ascii")
    return path, digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", type=Path, default=COHORT_ROOT)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--causality-audit", type=Path)
    args = parser.parse_args()
    report = build_health_report(cohort_root=args.cohort, frozen_candidate_path=args.candidate,
                                 causality_audit_path=args.causality_audit)
    path, digest = write_health_report(report, args.cohort)
    print(json.dumps({**report, "health_report": str(path), "health_sha256": digest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
