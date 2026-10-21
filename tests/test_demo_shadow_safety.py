from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from demo_safety import DemoLimits, RuntimeState, authorize_demo_decision
from shadow_mode import ShadowRecorder
from demo_mock_executor import MockShadowExecutor


class DemoShadowSafetyTests(unittest.TestCase):
    def setUp(self):
        self.limits = DemoLimits(0.1, 1, 100.0, 3, 5.0, 2.0, 4, 150.0)
        self.state = RuntimeState("DEMO", "US30Cash", True, False, 1, 1, 0, 0, 0, 1, 0, "s1", 0.1, 0.0)

    def test_real_unknown_account_and_disabled_mode_fail_closed(self):
        for mode in ("REAL", "UNKNOWN"):
            state = RuntimeState(**{**self.state.__dict__, "account_mode": mode})
            self.assertEqual(authorize_demo_decision(state, self.limits, set()), (False, "ACCOUNT_MODE_NOT_DEMO"))
        disabled = RuntimeState(**{**self.state.__dict__, "demo_trading_allowed": False})
        self.assertEqual(authorize_demo_decision(disabled, self.limits, set()), (False, "DEMO_DISABLED"))

    def test_kill_switch_duplicates_staleness_and_risk_limits(self):
        cases = [
            (RuntimeState(**{**self.state.__dict__, "kill_switch": True}), "KILL_SWITCH"),
            (RuntimeState(**{**self.state.__dict__, "quote_age_seconds": 99}), "STALE_QUOTE"),
            (RuntimeState(**{**self.state.__dict__, "heartbeat_age_seconds": 99}), "STALE_HEARTBEAT"),
            (RuntimeState(**{**self.state.__dict__, "open_positions": 1}), "POSITION_LIMIT"),
            (RuntimeState(**{**self.state.__dict__, "requested_lot": 0.2}), "LOT_LIMIT"),
            (RuntimeState(**{**self.state.__dict__, "observed_slippage": 3}), "SLIPPAGE_LIMIT"),
            (RuntimeState(**{**self.state.__dict__, "equity_drawdown": 150.0}), "EQUITY_DRAWDOWN_LIMIT"),
            (RuntimeState(**{**self.state.__dict__, "reconnect_pending": True}), "RECONNECT_RECONCILIATION_REQUIRED"),
            (RuntimeState(**{**self.state.__dict__, "persistent_state_valid": False}), "PERSISTENT_STATE_UNAVAILABLE"),
            (RuntimeState(**{**self.state.__dict__, "audit_log_writable": False}), "AUDIT_LOG_UNAVAILABLE"),
            (RuntimeState(**{**self.state.__dict__, "spread": float("nan")}), "INVALID_RUNTIME_STATE"),
        ]
        for state, expected in cases:
            self.assertEqual(authorize_demo_decision(state, self.limits, set()), (False, expected))
        self.assertEqual(authorize_demo_decision(self.state, self.limits, {"s1"}),
                         (False, "DUPLICATE_OR_EMPTY_SIGNAL"))
        allowed, reason = authorize_demo_decision(self.state, self.limits, set())
        self.assertTrue(allowed)
        self.assertEqual(reason, "GATES_PASS_NO_ORDER_SENT")

    def test_equity_drawdown_limit_must_be_configured(self):
        limits = DemoLimits(0.1, 1, 100.0, 3, 5.0, 2.0, 4)
        self.assertEqual(authorize_demo_decision(self.state, limits, set()),
                         (False, "INVALID_RISK_LIMIT"))

    def test_shadow_recorder_writes_hypothetical_event_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "shadow.jsonl"
            ShadowRecorder(path).record({
                "timestamp_utc": "2026-10-19T00:00:00Z", "signal_id": "s1",
                "candidate_sha256": "abc", "decision": "NO_DECISION", "reason": "stale",
            })
            record = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(record["decision"], "NO_DECISION")
            self.assertFalse(any("order" in key.casefold() for key in record))
            with self.assertRaises(ValueError):
                ShadowRecorder(path).record({"decision": "TRADE"})

    def test_mock_adapter_is_disabled_by_default_and_never_emits_orders(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = MockShadowExecutor(Path(tmp) / "mock.sqlite3")
            payload = executor.record(
                self.state, self.limits, decision="FOLLOW", candidate_sha256="a" * 64)
            self.assertEqual(payload["status"], "DISABLED")
            self.assertTrue(payload["mock_only"])
            self.assertEqual(payload["orders_sent"], 0)
            connection = sqlite3.connect(Path(tmp) / "mock.sqlite3")
            try:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0], 1)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM processed_signals").fetchone()[0], 0)
            finally:
                connection.close()

    def test_mock_adapter_hard_fails_real_and_unknown_accounts(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = MockShadowExecutor(Path(tmp) / "mock.sqlite3", enabled=True)
            for mode in ("REAL", "UNKNOWN"):
                state = RuntimeState(**{**self.state.__dict__, "account_mode": mode})
                payload = executor.record(state, self.limits, decision="INVERT",
                                          candidate_sha256="b" * 64)
                self.assertEqual(payload["status"], "BLOCKED")
                self.assertEqual(payload["reason"], "ACCOUNT_MODE_NOT_DEMO")
                self.assertEqual(payload["orders_sent"], 0)

    def test_mock_adapter_persists_duplicate_protection_and_stale_data_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "mock.sqlite3"
            first = MockShadowExecutor(database, enabled=True)
            accepted = first.record(self.state, self.limits, decision="FOLLOW",
                                    candidate_sha256="c" * 64)
            self.assertEqual(accepted["status"], "MOCK_ONLY_ACCEPTED")
            second = MockShadowExecutor(database, enabled=True)
            duplicate = second.record(self.state, self.limits, decision="FOLLOW",
                                      candidate_sha256="c" * 64)
            self.assertEqual((duplicate["status"], duplicate["reason"]),
                             ("BLOCKED", "DUPLICATE_OR_EMPTY_SIGNAL"))
            stale = RuntimeState(**{**self.state.__dict__, "signal_key": "s2", "quote_age_seconds": 60})
            rejected = second.record(stale, self.limits, decision="INVERT",
                                     candidate_sha256="c" * 64)
            self.assertEqual((rejected["status"], rejected["reason"]), ("BLOCKED", "STALE_QUOTE"))
            connection = sqlite3.connect(database)
            try:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM processed_signals").fetchone()[0], 1)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0], 3)
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
