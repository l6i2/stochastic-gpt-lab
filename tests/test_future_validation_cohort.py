from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from future_validation_collector import (  # noqa: E402
    COHORT_ID, START_UTC, _collect_day, _load_manifest, _mt5_query_with_retry,
    collect_once, health, prepare_cohort, status,
)


class _FakeMT5:
    COPY_TICKS_ALL = 0
    TIMEFRAME_M5 = 5
    ACCOUNT_TRADE_MODE_DEMO = 0

    tick_dtype = np.dtype([
        ("time", "i8"), ("time_msc", "i8"), ("bid", "f8"), ("ask", "f8"),
        ("last", "f8"), ("volume", "u8"), ("volume_real", "f8"), ("flags", "u4"),
    ])
    bar_dtype = np.dtype([
        ("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"),
        ("close", "f8"), ("tick_volume", "u8"), ("spread", "u4"), ("real_volume", "u8"),
    ])

    def __init__(self, data_path: Path):
        self.data_path = data_path
        self.initialized = False
        self.shutdown_called = False

    def initialize(self, **kwargs):
        self.initialized = True
        return True

    def terminal_info(self):
        return type("Terminal", (), {"data_path": str(self.data_path)})()

    def account_info(self):
        return type("Account", (), {"trade_mode": 0})()

    def symbol_info(self, symbol):
        return object() if symbol == "US30Cash" else None

    def copy_ticks_range(self, symbol, start, end, flags):
        stamp = int(start.timestamp() * 1000)
        return np.array([(stamp // 1000, stamp, 40000.0, 40000.5, 0.0, 0, 0.0, 1)], dtype=self.tick_dtype)

    def copy_rates_range(self, symbol, timeframe, start, end):
        stamp = int(start.timestamp())
        return np.array([(stamp, 40000.0, 40001.0, 39999.0, 40000.5, 15, 2, 0)], dtype=self.bar_dtype)

    @staticmethod
    def last_error():
        return (0, "ok")

    def shutdown(self):
        self.shutdown_called = True


class FutureValidationCohortTests(unittest.TestCase):
    def test_start_rule_is_future_only_and_has_no_override(self):
        self.assertEqual(START_UTC, datetime(2026, 10, 19, tzinfo=timezone.utc))
        self.assertEqual(COHORT_ID, "us30cash_m5_future_20261019_v1")

    def test_before_start_returns_without_mt5_or_filesystem_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cohort"
            result = collect_once(now=datetime(2026, 10, 18, 23, 59, tzinfo=timezone.utc),
                                  cohort_root=root,
                                  environment_status=lambda: self.fail("MT5 must not be contacted"))
            self.assertEqual(result["status"], "WAITING_FOR_FUTURE_START")
            self.assertFalse(root.exists())

    def test_open_cohort_day_waits_before_mt5_or_environment_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cohort"
            prepare_cohort(root, ROOT / "configs/future_validation_cohort_manifest.template.json")

            class ForbiddenMT5:
                def initialize(self, **kwargs):
                    raise AssertionError("MT5 must not initialize before a closed cohort day exists")

            def forbidden_environment():
                raise AssertionError("Environment probe must not run before the cutoff")

            result = collect_once(
                now=datetime(2026, 10, 19, 17, tzinfo=timezone.utc), cohort_root=root,
                environment_status=forbidden_environment, mt5_module=ForbiddenMT5())
            self.assertEqual(result["status"], "CAUGHT_UP_WAITING_FOR_CLOSED_DAY")
            self.assertEqual(result["collected"], 0)
            self.assertEqual(result["next_cursor_utc"], "2026-10-19T00:00:00Z")

    def test_collector_writes_separate_hashed_read_only_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cohort = tmp_path / "future-cohort"
            mt5 = _FakeMT5(tmp_path / "terminal-data")
            result = collect_once(
                now=datetime(2026, 10, 21, 3, tzinfo=timezone.utc),
                cohort_root=cohort,
                environment_status=lambda: {
                    "SAFE_FOR_RESEARCH": True, "ACCOUNT_MODE": "DEMO", "XM_ACTIVE": True,
                    "CONNECTED": True, "US30Cash_AVAILABLE": True,
                    "TERMINAL_PATH": "unused", "DATA_FOLDER": str(mt5.data_path),
                },
                mt5_module=mt5,
            )
            self.assertEqual(result["status"], "COLLECTION_UPDATED")
            self.assertEqual(result["days_added"], 2)
            self.assertTrue(mt5.shutdown_called)
            manifest = _load_manifest(cohort, ROOT / "configs/future_validation_cohort_manifest.template.json")
            self.assertEqual(len(manifest["segments"]), 2)
            self.assertFalse(manifest["train_access_allowed"])
            self.assertFalse(manifest["evaluation_authorized"])
            self.assertFalse(manifest["live_trading"])
            self.assertTrue(all(item["ticks_rows"] > 0 and item["bars_rows"] == 1
                                for item in manifest["segments"]))
            repeat = collect_once(
                now=datetime(2026, 10, 21, 3, tzinfo=timezone.utc), cohort_root=cohort,
                environment_status=lambda: {
                    "SAFE_FOR_RESEARCH": True, "ACCOUNT_MODE": "DEMO", "XM_ACTIVE": True,
                    "CONNECTED": True, "US30Cash_AVAILABLE": True,
                    "TERMINAL_PATH": "unused", "DATA_FOLDER": str(mt5.data_path),
                }, mt5_module=mt5)
            self.assertEqual(repeat["status"], "CAUGHT_UP_WAITING_FOR_CLOSED_DAY")
            self.assertEqual(len(_load_manifest(cohort, ROOT / "configs/future_validation_cohort_manifest.template.json")["segments"]), 2)

    def test_manifest_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cohort"
            root.mkdir()
            manifest_path = root / "cohort_manifest.json"
            manifest_path.write_text(json.dumps({"cohort_id": "tampered"}), encoding="utf-8")
            (root / "cohort_manifest.sha256").write_text("bad\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "hash"):
                _load_manifest(root, ROOT / "configs/future_validation_cohort_manifest.template.json")

    def test_prepare_creates_hashed_manifest_without_mt5(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cohort"
            result = prepare_cohort(root, ROOT / "configs/future_validation_cohort_manifest.template.json")
            self.assertEqual(result["status"], "SEALED_WAITING_FOR_START")
            self.assertFalse(result["train_access_allowed"])
            self.assertFalse(result["evaluation_authorized"])
            self.assertTrue((root / "cohort_manifest.sha256").is_file())

    @unittest.skipUnless(os.name == "nt", "Windows Task Scheduler is unavailable")
    def test_status_reports_registered_task(self):
        with patch("future_validation_collector.subprocess.run") as run:
            run.return_value.returncode = 0
            self.assertTrue(status()["collector_scheduled"])
            run.assert_called_once()

    def test_transient_mt5_query_failure_retries_with_backoff(self):
        class Query:
            calls = 0

            @staticmethod
            def last_error():
                return (-1, "temporary")

            def copy_ticks_range(self):
                self.calls += 1
                return None if self.calls < 3 else np.array([], dtype=_FakeMT5.tick_dtype)

        query = Query()
        with patch("future_validation_collector.time_module.sleep") as pause:
            result = _mt5_query_with_retry(query, "copy_ticks_range")
        self.assertEqual(result.size, 0)
        self.assertEqual(query.calls, 3)
        self.assertEqual([call.args[0] for call in pause.call_args_list], [1, 2])

    def test_completed_orphan_day_is_recovered_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cohort = base / "future-cohort"
            prepare_cohort(cohort, ROOT / "configs/future_validation_cohort_manifest.template.json")
            mt5 = _FakeMT5(base / "terminal-data")
            day_start = START_UTC
            _collect_day(mt5, day_start, day_start + timedelta(days=1), cohort / "raw")
            result = collect_once(
                now=datetime(2026, 10, 21, 3, tzinfo=timezone.utc), cohort_root=cohort,
                environment_status=lambda: {
                    "SAFE_FOR_RESEARCH": True, "ACCOUNT_MODE": "DEMO", "XM_ACTIVE": True,
                    "CONNECTED": True, "US30Cash_AVAILABLE": True,
                    "TERMINAL_PATH": "unused", "DATA_FOLDER": str(mt5.data_path),
                }, mt5_module=mt5)
            self.assertEqual(result["days_added"], 2)
            manifest = _load_manifest(cohort, ROOT / "configs/future_validation_cohort_manifest.template.json")
            self.assertTrue(manifest["segments"][0]["recovered_after_restart"])

    def test_health_reports_no_capture_and_blocked_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            cohort = Path(tmp) / "cohort"
            prepare_cohort(cohort, ROOT / "configs/future_validation_cohort_manifest.template.json")
            with patch("future_validation_collector.subprocess.run") as run:
                run.return_value.returncode = 0
                result = health(cohort, now=datetime(2026, 10, 20, tzinfo=timezone.utc),
                                environment_status=lambda: {
                                    "CONNECTED": False, "ACCOUNT_MODE": "UNKNOWN",
                                    "US30Cash_AVAILABLE": None,
                                })
            self.assertEqual(result["collector_status"], "WAITING_FIRST_CAPTURE")
            self.assertEqual(result["ticks_rows"], 0)
            self.assertFalse(result["mt5_connected"])


if __name__ == "__main__":
    unittest.main()
