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
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
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


def _collect_day(mt5, day_start: datetime, day_end: datetime, data_dir: Path) -> dict[str, Any]:
    day_name = day_start.strftime("%Y%m%d")
    final_day_dir = data_dir / day_name
    if final_day_dir.exists():
        raise FileExistsError(f"Refusing to overwrite a cohort day already on disk: {day_name}")
    data_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{day_name}.pending-", dir=data_dir))
    ticks_path = staging / f"ticks_{day_name}.csv.gz"
    bars_path = staging / f"bars_{day_name}.csv.gz"
    tick_count = 0
    tick_min = None
    tick_max = None
    try:
        with gzip.open(ticks_path, "wt", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=TICK_FIELDS, extrasaction="ignore")
            writer.writeheader()
            cursor = day_start
            while cursor < day_end:
                end = min(cursor + TICK_QUERY_CHUNK, day_end)
                inclusive_end = end - timedelta(milliseconds=1)
                ticks = mt5.copy_ticks_range(SYMBOL, cursor, inclusive_end, mt5.COPY_TICKS_ALL)
                if ticks is None:
                    raise RuntimeError(f"copy_ticks_range failed: {mt5.last_error()}")
                names = getattr(getattr(ticks, "dtype", None), "names", None)
                if ticks.size and (not names or not set(TICK_FIELDS).issubset(names)):
                    raise ValueError("MT5 tick response is missing required quote fields")
                for row in ticks:
                    stamp = int(_scalar(row["time_msc"]))
                    if not (_ms(cursor) <= stamp < _ms(end)):
                        raise ValueError("MT5 tick outside requested UTC partition")
                    writer.writerow({key: _scalar(row[key]) for key in TICK_FIELDS})
                    tick_count += 1
                    tick_min = stamp if tick_min is None else min(tick_min, stamp)
                    tick_max = stamp if tick_max is None else max(tick_max, stamp)
                cursor = end
        with ticks_path.open("r+b") as stream:
            os.fsync(stream.fileno())

        rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M5, day_start,
                                     day_end - timedelta(milliseconds=1))
        if rates is None:
            raise RuntimeError(f"copy_rates_range failed: {mt5.last_error()}")
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
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError("Collector already running or stale lock requires review") from exc
    try:
        os.write(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
        os.close(descriptor)
        manifest = _load_manifest(cohort_root, template_path)
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
            cursor = datetime.fromisoformat(manifest["next_cursor_utc"].replace("Z", "+00:00"))
            end = _closed_day_boundary(now)
            if cursor < START_UTC or cursor != datetime.combine(cursor.date(), time.min, timezone.utc):
                raise ValueError("Cohort cursor is not an aligned UTC day at or after the frozen start")
            if end <= cursor:
                return {"status": "CAUGHT_UP_WAITING_FOR_CLOSED_DAY", "collected": 0,
                        "next_cursor_utc": manifest["next_cursor_utc"], "live_trading": False}
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
    parser.add_argument("command", choices=("status", "prepare", "collect"))
    args = parser.parse_args()
    if args.command == "status":
        result = status()
    elif args.command == "prepare":
        result = prepare_cohort()
    else:
        result = collect_once()
    print(json.dumps(result, indent=2))
    return 0 if not str(result.get("status", "")).startswith("BLOCKED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
