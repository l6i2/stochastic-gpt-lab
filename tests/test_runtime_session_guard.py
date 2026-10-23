from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from runtime_session_guard import EVIDENCE, RuntimeSessionGuard, SessionObservation, eu_expected_offset_seconds


def utc(day, hour=0, minute=0, second=0, month=10):
    return datetime(2026, month, day, hour, minute, second, tzinfo=timezone.utc)


def observation(now, **changes):
    return replace(SessionObservation(now, now - timedelta(seconds=1), True, "DEMO",
        "XMGlobal-MT5 10", "US30Cash", 40000, 40001, 7200, True, True, "NORMAL", "OPEN"), **changes)


class SessionGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        data = json.loads(EVIDENCE.read_text())
        data["records"][1] = "XM_SESSION_PROBE|CLOCK|server_time=2026.10.19 02:00:00|utc_time=2026.10.19 00:00:00|offset_seconds=7200"
        self.path = Path(self.temp.name) / "evidence.json"
        self._save(data)
        self.guard = RuntimeSessionGuard(self.path)

    def _save(self, data):
        self.path.write_text(json.dumps(data))
        self.path.with_name(self.path.name + ".sha256").write_text(hashlib.sha256(self.path.read_bytes()).hexdigest())

    def check(self, now, **changes):
        return self.guard.check(observation(now, **changes), now_utc=now)

    def test_eu_dst_transitions_are_diagnostic_not_broker_attestation(self):
        self.assertEqual(eu_expected_offset_seconds(utc(29, 0, 59, 59, month=3)), 7200)
        self.assertEqual(eu_expected_offset_seconds(utc(29, 1, month=3)), 10800)
        self.assertEqual(eu_expected_offset_seconds(utc(25, 0, 59, 59)), 10800)
        self.assertEqual(eu_expected_offset_seconds(utc(25, 1)), 7200)
        self.assertEqual(self.check(utc(23, 8), clock_verified=False).reason, "CLOCK_OR_CALENDAR_AMBIGUOUS")
        self.assertEqual(self.check(utc(23, 8), calendar_reconciled=False).reason, "CLOCK_OR_CALENDAR_AMBIGUOUS")

    def test_dst_change_requires_new_reconciled_snapshot(self):
        self.assertEqual(self.check(utc(25, 2)).reason, "DST_TRANSITION_REFRESH_REQUIRED")
        self.assertEqual(self.check(utc(23, 8), offset_seconds=10800).reason, "OFFSET_CHANGED_REFRESH_REQUIRED")

    def test_weekday_differences_and_daily_breaks(self):
        for day in (19, 20, 21):
            self.assertTrue(self.check(utc(day, 20, 54)).allowed)  # server 22:54
            self.assertFalse(self.check(utc(day, 20, 55)).allowed)
            if day < 21:
                self.assertTrue(self.check(utc(day, 22, 5)).allowed)  # next server day 00:05
        self.assertFalse(self.check(utc(21, 22, 5)).allowed)  # Thursday opens 01:05
        self.assertTrue(self.check(utc(21, 23, 5)).allowed)
        self.assertTrue(self.check(utc(22, 21, 54)).allowed)
        self.assertFalse(self.check(utc(22, 21, 55)).allowed)

    def test_friday_close_and_weekend(self):
        self.assertTrue(self.check(utc(23, 21, 49, 59)).allowed)
        self.assertEqual(self.check(utc(23, 21, 50)).reason, "OUTSIDE_OBSERVED_TRADE_SESSION")
        self.assertFalse(self.check(utc(23, 22, 0)).allowed)  # server Saturday even though UTC Friday
        self.assertFalse(self.check(utc(24, 12)).allowed)
        self.assertFalse(self.check(utc(25, 0)).allowed)

    def test_holiday_unknown_or_closed_and_runtime_closed_block_even_with_fresh_quotes(self):
        now = utc(23, 8)
        self.assertEqual(self.check(now, holiday_status="UNKNOWN").reason, "HOLIDAY_UNKNOWN_REQUIRE_RUNTIME_GUARD")
        self.assertEqual(self.check(now, holiday_status="CLOSED").reason, "HOLIDAY_CLOSED")
        self.assertEqual(self.check(now, broker_market_state="CLOSED").reason, "BROKER_MARKET_CLOSED")
        self.assertEqual(self.check(now, broker_market_state="UNKNOWN").reason, "BROKER_MARKET_STATE_UNKNOWN")
        self.assertFalse(self.check(now, connected=False).allowed)
        self.assertFalse(self.check(now, account_mode="REAL").allowed)

    def test_missing_stale_future_malformed_quote_and_observation_fail_closed(self):
        now = utc(23, 8)
        self.assertFalse(self.guard.check(None, now_utc=now).allowed)
        for changed in ({"checked_at_utc": now-timedelta(seconds=6)},
                        {"checked_at_utc": now+timedelta(seconds=1)},
                        {"quote_time_utc": now-timedelta(seconds=6)},
                        {"quote_time_utc": now+timedelta(seconds=1)},
                        {"bid": float("nan")}, {"ask": -1}, {"bid": "bad"},
                        {"server": "OTHER"}, {"symbol": "US30"}):
            with self.subTest(changed=changed):
                self.assertFalse(self.check(now, **changed).allowed)

    def test_snapshot_expiry_and_evidence_tampering(self):
        self.assertEqual(self.check(utc(27, 8)).reason, "SESSION_SNAPSHOT_EXPIRED")
        self.path.write_text("{}")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            RuntimeSessionGuard(self.path)

    def test_real_published_evidence_can_be_loaded_without_rerunning_probe(self):
        guard = RuntimeSessionGuard()
        self.assertEqual(guard.offset_seconds, 7200)
        self.assertEqual(guard.sessions["TRADE"]["FRIDAY"], [(3900, 85800)])
        self.assertEqual(guard.sessions["QUOTE"]["FRIDAY"], [(3600, 86400)])
        result = guard.check(observation(utc(23, 8)), now_utc=utc(23, 8))
        self.assertTrue(result.allowed)
        self.assertEqual(result.orders_sent, 0)


if __name__ == "__main__":
    unittest.main()
