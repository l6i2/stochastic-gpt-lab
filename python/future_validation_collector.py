"""Read-only MT5 collector for the physically isolated future cohort.

This module records broker-delivered US30Cash M5 bars and all quote ticks.
It has no order APIs, does not read legacy Validation/FINAL_TEST files, and
does not produce hypotheses, features, labels, or scores.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, time, timedelta, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time as time_module
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
COHORT_ROOT = ROOT / "outputs/future_validation_cohort/cohort_20261019"
TEMPLATE_PATH = ROOT / "configs/future_validation_cohort_manifest.template.json"
COHORT_ID = "us30cash_m5_future_20261019_v1"
SYMBOL = "US30Cash"
TIMEFRAME_NAME = "M5"
START_UTC = datetime(2026, 10, 19, tzinfo=timezone.utc)
SETTLEMENT_LAG = timedelta(hours=2)
TICK_QUERY_CHUNK = timedelta(hours=1)
TICK_FIELDS = ("time", "time_msc", "bid", "ask", "last", "volume", "volume_real", "flags")
BAR_FIELDS = ("time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume")
MAX_QUERY_ATTEMPTS = 4


def _mt5_query_with_retry(mt5, function_name: str, *args):
    function = getattr(mt5, function_name)
    for attempt in range(MAX_QUERY_ATTEMPTS):
        result = function(*args)
        if result is not None:
            return result
        if attempt + 1 < MAX_QUERY_ATTEMPTS:
            time_module.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f"{function_name} failed after {MAX_QUERY_ATTEMPTS} attempts: {mt5.last_error()}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iso(msc: int) -> str:
    return datetime.fromtimestamp(msc / 1000, timezone.utc).isoformat().replace("+00:00", "Z")


def _ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def _json_write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8")
    os.replace(temp, path)


def _new_manifest(template_path: Path) -> dict[str, Any]:
    template = json.loads(template_path.read_text(encoding="utf-8"))
    expected = {"cohort_id": COHORT_ID, "symbol": SYMBOL, "timeframe": TIMEFRAME_NAME,
                "cohort_start_utc": START_UTC.isoformat().replace("+00:00", "Z")}
    if any(template.get(key) != value for key, value in expected.items()):
        raise ValueError("Cohort template identity or fixed start rule changed")
    return {**template, "cohort_template_sha256": _sha256(template_path),
            "collector_code_sha256": _sha256(Path(__file__).resolve()),
            "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "SEALED_WAITING_FOR_START", "next_cursor_utc": expected["cohort_start_utc"],
            "segments": [], "previous_manifest_sha256": None,
            "evaluation_authorized": False, "train_access_allowed": False,
            "legacy_validation_accessed": False, "legacy_final_test_accessed": False,
            "live_trading": False}


def _load_manifest(cohort_root: Path, template_path: Path) -> dict[str, Any]:
    manifest_path = cohort_root / "cohort_manifest.json"
    sha_path = cohort_root / "cohort_manifest.sha256"
    if not manifest_path.exists():
        manifest = _new_manifest(template_path)
        _save_manifest(cohort_root, manifest, previous_hash=None)
        return manifest
    if not sha_path.is_file() or _sha256(manifest_path) != sha_path.read_text(encoding="ascii").strip():
        raise ValueError("Cohort manifest hash is missing or does not match; refusing collection")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("cohort_id") != COHORT_ID or manifest.get("symbol") != SYMBOL
            or manifest.get("timeframe") != TIMEFRAME_NAME
            or manifest.get("cohort_start_utc") != START_UTC.isoformat().replace("+00:00", "Z")
            or manifest.get("cohort_template_sha256") != _sha256(template_path)
            or manifest.get("collector_code_sha256") != _sha256(Path(__file__).resolve())
            or manifest.get("train_access_allowed") is not False
            or manifest.get("evaluation_authorized") is not False
            or manifest.get("live_trading") is not False):
        raise ValueError("Cohort manifest violates its frozen identity or access policy")
    for segment in manifest.get("segments", []):
        for field in ("ticks_file", "bars_file"):
            relative = segment.get(field)
            if relative:
                file_path = (cohort_root / relative).resolve()
                if cohort_root.resolve() not in file_path.parents or not file_path.is_file():
                    raise ValueError(f"Missing or escaped cohort artifact: {relative}")
                if _sha256(file_path) != segment[field.replace("file", "sha256")]:
                    raise ValueError(f"Cohort artifact hash mismatch: {relative}")
    return manifest


def _save_manifest(cohort_root: Path, manifest: dict[str, Any], previous_hash: str | None) -> str:
    manifest["previous_manifest_sha256"] = previous_hash
    path = cohort_root / "cohort_manifest.json"
    _json_write_atomic(path, manifest)
    digest = _sha256(path)
    temp = cohort_root / "cohort_manifest.sha256.tmp"
    temp.write_text(digest + "\n", encoding="ascii")
    os.replace(temp, cohort_root / "cohort_manifest.sha256")
    return digest


def _date_from_ms(msc: int) -> datetime:
    return datetime.fromtimestamp(msc / 1000, timezone.utc)


def _scalar(value: Any) -> Any:
    return value.item() if hasattr(value, "item") else value


def _write_gzip_csv(path: Path, fields: tuple[str, ...], rows) -> tuple[int, str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    temp_path = path.with_name(path.name + ".tmp")
    with gzip.open(temp_path, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _scalar(row[key]) for key in fields})
            count += 1
    with temp_path.open("r+b") as stream:
        os.fsync(stream.fileno())
    os.replace(temp_path, path)
    return count, _sha256(path), path.stat().st_size


def _recover_orphan_day(final_day_dir: Path, day_start: datetime, day_end: datetime,
                        data_dir: Path) -> dict[str, Any]:
    """Adopt a fully written day directory left between atomic rename and manifest update."""
    day_name = day_start.strftime("%Y%m%d")
    ticks_path = final_day_dir / f"ticks_{day_name}.csv.gz"
    bars_path = final_day_dir / f"bars_{day_name}.csv.gz"
    if not ticks_path.is_file() or not bars_path.is_file():
        raise FileExistsError(f"Incomplete orphan day directory; refusing overwrite: {day_name}")

    tick_count = 0
    tick_min = tick_max = previous_tick = None
    with gzip.open(ticks_path, "rt", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != TICK_FIELDS:
            raise ValueError(f"Orphan tick schema mismatch: {day_name}")
        for row in reader:
            stamp = int(row["time_msc"])
            if not (_ms(day_start) <= stamp < _ms(day_end)) or (previous_tick is not None and stamp < previous_tick):
                raise ValueError(f"Orphan tick interval/order error: {day_name}")
            tick_count += 1
            tick_min = stamp if tick_min is None else min(tick_min, stamp)
            tick_max = stamp if tick_max is None else max(tick_max, stamp)
            previous_tick = stamp

    bar_count = 0
    first_bar = last_bar = previous_bar = None
    with gzip.open(bars_path, "rt", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != BAR_FIELDS:
            raise ValueError(f"Orphan M5 bar schema mismatch: {day_name}")
        for row in reader:
            stamp = int(row["time"])
            if (not (_ms(day_start) <= stamp * 1000 < _ms(day_end))
                    or (previous_bar is not None and stamp <= previous_bar)):
                raise ValueError(f"Orphan M5 bar interval/order error: {day_name}")
            first_bar = stamp if first_bar is None else first_bar
            last_bar = previous_bar = stamp
            bar_count += 1

    return {
        "day_utc": day_name,
        "range_start_utc": day_start.isoformat().replace("+00:00", "Z"),
        "range_end_exclusive_utc": day_end.isoformat().replace("+00:00", "Z"),
        "ticks_file": str(ticks_path.relative_to(data_dir.parent)).replace("\\", "/"),
        "ticks_sha256": _sha256(ticks_path), "ticks_bytes": ticks_path.stat().st_size,
        "ticks_rows": tick_count, "first_tick_msc": tick_min, "last_tick_msc": tick_max,
        "bars_file": str(bars_path.relative_to(data_dir.parent)).replace("\\", "/"),
        "bars_sha256": _sha256(bars_path), "bars_bytes": bars_path.stat().st_size,
        "bars_rows": bar_count,
        "first_bar_time_utc": datetime.fromtimestamp(first_bar, timezone.utc).isoformat().replace("+00:00", "Z") if first_bar is not None else None,
        "last_bar_time_utc": datetime.fromtimestamp(last_bar, timezone.utc).isoformat().replace("+00:00", "Z") if last_bar is not None else None,
        "empty_day": tick_count == 0 and bar_count == 0,
        "recovered_after_restart": True,
    }


def _collect_day(mt5, day_start: datetime, day_end: datetime, data_dir: Path) -> dict[str, Any]:
    day_name = day_start.strftime("%Y%m%d")
    final_day_dir = data_dir / day_name
    if final_day_dir.exists():
        return _recover_orphan_day(final_day_dir, day_start, day_end, data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{day_name}.pending-", dir=data_dir))
    ticks_path = staging / f"ticks_{day_name}.csv.gz"
    bars_path = staging / f"bars_{day_name}.csv.gz"
    tick_count = 0
    tick_min = None
    tick_max = None
    previous_tick = None
    try:
        with gzip.open(ticks_path, "wt", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=TICK_FIELDS, extrasaction="ignore")
            writer.writeheader()
            cursor = day_start
            while cursor < day_end:
                end = min(cursor + TICK_QUERY_CHUNK, day_end)
                inclusive_end = end - timedelta(milliseconds=1)
                ticks = _mt5_query_with_retry(mt5, "copy_ticks_range", SYMBOL, cursor,
                                              inclusive_end, mt5.COPY_TICKS_ALL)
                names = getattr(getattr(ticks, "dtype", None), "names", None)
                if ticks.size and (not names or not set(TICK_FIELDS).issubset(names)):
                    raise ValueError("MT5 tick response is missing required quote fields")
                for row in ticks:
                    stamp = int(_scalar(row["time_msc"]))
                    if not (_ms(cursor) <= stamp < _ms(end)):
                        raise ValueError("MT5 tick outside requested UTC partition")
                    if previous_tick is not None and stamp < previous_tick:
                        raise ValueError("MT5 ticks are not ordered by UTC milliseconds")
                    writer.writerow({key: _scalar(row[key]) for key in TICK_FIELDS})
                    tick_count += 1
                    tick_min = stamp if tick_min is None else min(tick_min, stamp)
                    tick_max = stamp if tick_max is None else max(tick_max, stamp)
                    previous_tick = stamp
                cursor = end
        with ticks_path.open("r+b") as stream:
            os.fsync(stream.fileno())

        rates = _mt5_query_with_retry(mt5, "copy_rates_range", SYMBOL,
                                      mt5.TIMEFRAME_M5, day_start,
                                      day_end - timedelta(milliseconds=1))
        names = getattr(getattr(rates, "dtype", None), "names", None)
        if rates.size and (not names or not set(BAR_FIELDS).issubset(names)):
            raise ValueError("MT5 M5 response is missing required OHLC/volume fields")
        bar_rows = []
        previous_bar = None
        for row in rates:
            stamp = int(_scalar(row["time"]))
            if not (_ms(day_start) <= stamp * 1000 < _ms(day_end)):
                raise ValueError("MT5 M5 bar outside requested UTC partition")
            if previous_bar is not None and stamp <= previous_bar:
                raise ValueError("MT5 M5 bars are not strictly ordered")
            previous_bar = stamp
            bar_rows.append(row)
        bar_count, bars_hash, bars_size = _write_gzip_csv(bars_path, BAR_FIELDS, bar_rows)
        ticks_hash = _sha256(ticks_path)
        ticks_size = ticks_path.stat().st_size
        os.replace(staging, final_day_dir)
        ticks_path = final_day_dir / ticks_path.name
        bars_path = final_day_dir / bars_path.name
        return {
            "day_utc": day_name,
            "range_start_utc": day_start.isoformat().replace("+00:00", "Z"),
            "range_end_exclusive_utc": day_end.isoformat().replace("+00:00", "Z"),
            "ticks_file": str(ticks_path.relative_to(data_dir.parent)).replace("\\", "/"),
            "ticks_sha256": ticks_hash, "ticks_bytes": ticks_size, "ticks_rows": tick_count,
            "first_tick_msc": tick_min, "last_tick_msc": tick_max,
            "first_bar_time_utc": datetime.fromtimestamp(bar_rows[0]["time"], timezone.utc).isoformat().replace("+00:00", "Z") if bar_rows else None,
            "last_bar_time_utc": datetime.fromtimestamp(bar_rows[-1]["time"], timezone.utc).isoformat().replace("+00:00", "Z") if bar_rows else None,
            "bars_file": str(bars_path.relative_to(data_dir.parent)).replace("\\", "/"),
            "bars_sha256": bars_hash, "bars_bytes": bars_size, "bars_rows": bar_count,
            "empty_day": tick_count == 0 and bar_count == 0,
        }
    except BaseException:
        # Keep any completed temp/segment as forensic evidence; never replace an existing artifact.
        raise


def _closed_day_boundary(now: datetime) -> datetime:
    safe = now.astimezone(timezone.utc) - SETTLEMENT_LAG
    return datetime.combine(safe.date(), time.min, timezone.utc)


def _acquire_lock(lock: Path) -> int:
    try:
        return os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        try:
            content = lock.read_text(encoding="ascii")
            pid = int(content.splitlines()[0].removeprefix("pid="))
            age = time_module.time() - lock.stat().st_mtime
            os.kill(pid, 0)
            alive = True
        except ProcessLookupError:
            alive = False
        except (OSError, ValueError, IndexError):
            alive = True
            age = 0
        if not alive and age > 2 * 60 * 60:
            lock.unlink(missing_ok=True)
            try:
                return os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError as retry_exc:
                raise RuntimeError("Collector lock was reclaimed concurrently; retry next schedule") from retry_exc
        raise RuntimeError("Collector already running or lock needs review; refusing concurrent collection") from exc


def collect_once(*, now: datetime | None = None, cohort_root: Path = COHORT_ROOT,
                 template_path: Path = TEMPLATE_PATH, mt5_module=None,
                 environment_status=None) -> dict[str, Any]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cohort_root = Path(cohort_root)
    if now < START_UTC:
        return {"status": "WAITING_FOR_FUTURE_START", "start_utc": START_UTC.isoformat(),
                "collected": 0, "mt5_connected": False}

    cohort_root.mkdir(parents=True, exist_ok=True)
    lock = cohort_root / ".collector.lock"
    descriptor = _acquire_lock(lock)
    try:
        os.write(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
        os.close(descriptor)
        manifest = _load_manifest(cohort_root, template_path)
        cursor = datetime.fromisoformat(manifest["next_cursor_utc"].replace("Z", "+00:00"))
        if cursor < START_UTC or cursor != datetime.combine(cursor.date(), time.min, timezone.utc):
            raise ValueError("Cohort cursor is not an aligned UTC day at or after the frozen start")
        end = _closed_day_boundary(now)
        # Avoid initializing MT5 when no complete, settled cohort day exists.
        if end <= cursor:
            return {"status": "CAUGHT_UP_WAITING_FOR_CLOSED_DAY", "collected": 0,
                    "next_cursor_utc": manifest["next_cursor_utc"], "live_trading": False}
        if environment_status is None:
            from controller.mt5_env import status as environment_status
        environment = environment_status()
        if (not environment.get("SAFE_FOR_RESEARCH") or environment.get("ACCOUNT_MODE") != "DEMO"
                or not environment.get("XM_ACTIVE") or not environment.get("CONNECTED")
                or not environment.get("US30Cash_AVAILABLE")):
            return {"status": "BLOCKED_MT5_XM_DEMO_NOT_VERIFIED", "collected": 0,
                    "live_trading": False}
        if mt5_module is None:
            import MetaTrader5 as mt5_module
        if not mt5_module.initialize(path=environment["TERMINAL_PATH"], timeout=5000):
            raise RuntimeError(f"Could not attach to verified MT5 terminal: {mt5_module.last_error()}")
        try:
            terminal = mt5_module.terminal_info()
            account = mt5_module.account_info()
            symbol = mt5_module.symbol_info(SYMBOL)
            if (not terminal or Path(terminal.data_path).resolve() != Path(environment["DATA_FOLDER"]).resolve()
                    or not account or account.trade_mode != mt5_module.ACCOUNT_TRADE_MODE_DEMO
                    or not symbol):
                raise RuntimeError("MT5 attachment, XM data-folder, DEMO mode, or exact symbol check failed")
            previous_hash = _sha256(cohort_root / "cohort_manifest.json")
            manifest["status"] = "COLLECTING"
            manifest["collector_last_attempt_utc"] = now.isoformat().replace("+00:00", "Z")
            data_dir = cohort_root / "raw"
            added = 0
            while cursor < end:
                day_end = cursor + timedelta(days=1)
                segment = _collect_day(mt5_module, cursor, day_end, data_dir)
                manifest["segments"].append(segment)
                cursor = day_end
                manifest["next_cursor_utc"] = cursor.isoformat().replace("+00:00", "Z")
                manifest["updated_utc"] = now.isoformat().replace("+00:00", "Z")
                manifest["status"] = "COLLECTING_SEALED_SEGMENTS"
                manifest["access_policy"]["train_access_allowed"] = False
                manifest["access_policy"]["evaluation_authorized"] = False
                previous_hash = _save_manifest(cohort_root, manifest, previous_hash)
                added += 1
            return {"status": "COLLECTION_UPDATED", "days_added": added,
                    "next_cursor_utc": manifest["next_cursor_utc"],
                    "manifest_sha256": previous_hash, "live_trading": False}
        finally:
            mt5_module.shutdown()
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def status(cohort_root: Path = COHORT_ROOT) -> dict[str, Any]:
    cohort_root = Path(cohort_root)
    manifest = cohort_root / "cohort_manifest.json"
    scheduled = False
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["schtasks.exe", "/Query", "/TN", "StochasticGptLabFutureValidationCollector", "/FO", "LIST"],
                capture_output=True, text=True, timeout=10, check=False)
            scheduled = result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            scheduled = False
    return {
        "cohort_id": COHORT_ID, "cohort_root": str(cohort_root),
        "start_utc": START_UTC.isoformat().replace("+00:00", "Z"),
        "manifest_exists": manifest.is_file(), "collector_scheduled": scheduled,
        "train_access_allowed": False, "evaluation_authorized": False,
        "legacy_discovery_validation_used": False, "legacy_final_test_used": False,
        "LIVE_TRADING": False,
    }


def health(cohort_root: Path = COHORT_ROOT, *, now: datetime | None = None,
           environment_status=None) -> dict[str, Any]:
    """Return operational health without exposing credentials or market rows."""
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cohort_root = Path(cohort_root)
    basic = status(cohort_root)
    manifest_path = cohort_root / "cohort_manifest.json"
    scheduler_log = cohort_root / "scheduler.log"
    latest_attempt = None
    last_exit = None
    last_error = None
    if scheduler_log.is_file():
        try:
            lines = [line for line in scheduler_log.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
            if lines:
                latest_attempt = json.loads(lines[-1])
                last_exit = latest_attempt.get("exit_code")
                if last_exit != 0:
                    last_error = str(latest_attempt.get("output", "collector returned nonzero"))[-2000:]
        except (OSError, json.JSONDecodeError):
            last_error = "scheduler.log is unreadable or contains malformed JSON"

    if environment_status is None:
        try:
            from controller.mt5_env import status as environment_status
        except ImportError:
            environment_status = lambda: {}
    try:
        environment = environment_status()
    except Exception as exc:  # health should report a failed probe, never crash a status query
        environment = {}
        last_error = f"MT5 environment probe failed: {type(exc).__name__}"

    result = {
        **basic,
        "collector_status": "WAITING_FIRST_CAPTURE",
        "last_success_utc": None,
        "last_attempt_utc": latest_attempt.get("started_utc") if latest_attempt else None,
        "ticks_rows": 0, "bars_rows": 0, "latest_timestamp_utc": None,
        "errors": [last_error] if last_error else [],
        "mt5_connected": environment.get("CONNECTED") is True,
        "account_mode": environment.get("ACCOUNT_MODE", "UNKNOWN"),
        "symbol_status": "AVAILABLE" if environment.get("US30Cash_AVAILABLE") is True
                        else "UNAVAILABLE" if environment.get("US30Cash_AVAILABLE") is False else "UNKNOWN",
        "duplicate_day_segments": False, "missing_utc_days": [],
        "manifest_sha256": None,
    }
    if not manifest_path.is_file():
        result["collector_status"] = "MANIFEST_MISSING"
        return result
    try:
        manifest = _load_manifest(cohort_root, TEMPLATE_PATH)
        result["manifest_sha256"] = _sha256(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result["collector_status"] = "MANIFEST_OR_SEGMENT_INVALID"
        result["errors"].append(str(exc))
        return result

    segments = manifest.get("segments", [])
    days = [str(item.get("day_utc", "")) for item in segments]
    result["duplicate_day_segments"] = len(days) != len(set(days))
    result["ticks_rows"] = sum(int(item.get("ticks_rows", 0)) for item in segments)
    result["bars_rows"] = sum(int(item.get("bars_rows", 0)) for item in segments)
    cursors = [item.get("last_tick_msc") for item in segments if item.get("last_tick_msc") is not None]
    bar_times = [item.get("last_bar_time_utc") for item in segments if item.get("last_bar_time_utc")]
    latest_values = ([datetime.fromtimestamp(max(cursors) / 1000, timezone.utc)] if cursors else [])
    latest_values.extend(datetime.fromisoformat(value.replace("Z", "+00:00")) for value in bar_times)
    if latest_values:
        result["latest_timestamp_utc"] = max(latest_values).isoformat().replace("+00:00", "Z")
    result["last_success_utc"] = manifest.get("updated_utc")
    result["last_attempt_utc"] = manifest.get("collector_last_attempt_utc") or result["last_attempt_utc"]

    cursor = datetime.fromisoformat(manifest["next_cursor_utc"].replace("Z", "+00:00"))
    expected = set()
    day = START_UTC.date()
    while day < cursor.date():
        expected.add(day.strftime("%Y%m%d"))
        day += timedelta(days=1)
    result["missing_utc_days"] = sorted(expected - set(days))
    if result["duplicate_day_segments"] or result["missing_utc_days"]:
        result["collector_status"] = "SEGMENT_COVERAGE_INVALID"
        result["errors"].append("UTC-day segment sequence has duplicates or gaps")
    elif not segments:
        if last_exit not in (None, 0):
            result["collector_status"] = "BLOCKED_OR_FAILED_BEFORE_FIRST_CAPTURE"
    else:
        updated = manifest.get("updated_utc")
        age_hours = (now - datetime.fromisoformat(updated.replace("Z", "+00:00"))).total_seconds() / 3600 if updated else float("inf")
        result["collector_status"] = "STALE" if age_hours > 26 else "HEALTHY"
    return result


def prepare_cohort(cohort_root: Path = COHORT_ROOT,
                   template_path: Path = TEMPLATE_PATH) -> dict[str, Any]:
    cohort_root = Path(cohort_root)
    cohort_root.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest(cohort_root, template_path)
    return {"status": manifest["status"], "cohort_id": COHORT_ID,
            "manifest_sha256": _sha256(cohort_root / "cohort_manifest.json"),
            "next_cursor_utc": manifest["next_cursor_utc"],
            "train_access_allowed": False, "evaluation_authorized": False,
            "live_trading": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "health", "prepare", "collect"))
    args = parser.parse_args()
    if args.command == "status":
        result = status()
    elif args.command == "health":
        result = health()
    elif args.command == "prepare":
        result = prepare_cohort()
    else:
        result = collect_once()
    print(json.dumps(result, indent=2))
    return 0 if not str(result.get("status", "")).startswith("BLOCKED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
