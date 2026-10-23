from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from runtime_session_guard import RuntimeSessionGuard, SessionObservation
from demo_safety import DemoLimits, RuntimeState, authorize_demo_decision
from shadow_mode import ReadOnlyMT5Adapter, ShadowMode, ShadowRecorder, sha256_bytes
from demo_mock_executor import MockShadowExecutor


class DemoShadowSafetyTests(unittest.TestCase):
    def setUp(self):
        self.limits = DemoLimits(0.1, 1, 100.0, 3, 5.0, 2.0, 4, 150.0)
        self.state = RuntimeState("DEMO", "US30Cash", True, False, 1, 1, 0, 0, 0, 1, 0, "s1", 0.1, 0.0, session_guard_pass=True)

    def test_real_unknown_account_and_disabled_mode_fail_closed(self):
        for mode in ("REAL", "UNKNOWN"):
            state = RuntimeState(**{**self.state.__dict__, "account_mode": mode})
            self.assertEqual(authorize_demo_decision(state, self.limits, set()), (False, "ACCOUNT_MODE_NOT_DEMO"))
        disabled = RuntimeState(**{**self.state.__dict__, "demo_trading_allowed": False})
        self.assertEqual(authorize_demo_decision(disabled, self.limits, set()), (False, "DEMO_DISABLED"))

    def test_kill_switch_duplicates_staleness_and_risk_limits(self):
        cases = [
            (RuntimeState(**{**self.state.__dict__, "session_guard_pass": False}), "SESSION_GUARD_REQUIRED"),
            (RuntimeState(**{**self.state.__dict__, "kill_switch": True}), "KILL_SWITCH"),
            (RuntimeState(**{**self.state.__dict__, "quote_age_seconds": 99}), "STALE_QUOTE"),
            (RuntimeState(**{**self.state.__dict__, "heartbeat_age_seconds": 99}), "STALE_HEARTBEAT"),
            (RuntimeState(**{**self.state.__dict__, "open_positions": 1}), "POSITION_LIMIT"),
            (RuntimeState(**{**self.state.__dict__, "requested_lot": 0.2}), "LOT_LIMIT"),
            (RuntimeState(**{**self.state.__dict__, "daily_loss": 100.0}), "DAILY_LOSS_LIMIT"),
            (RuntimeState(**{**self.state.__dict__, "consecutive_losses": 3}), "CONSECUTIVE_LOSS_LIMIT"),
            (RuntimeState(**{**self.state.__dict__, "trades_today": 4}), "DAILY_TRADE_LIMIT"),
            (RuntimeState(**{**self.state.__dict__, "symbol": "US30"}), "SYMBOL_NOT_ALLOWED"),
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
                "candidate_sha256": "a" * 64, "decision": "NO_DECISION", "reason": "stale",
                "features": {"x": 1}, "feature_sha256": sha256_bytes(b'{"x":1}'),
                "quote_time_utc": "2026-10-19T00:00:00Z", "spread": 0.5,
                "feature_max_time_utc": "2026-10-19T00:00:00Z", "latency_ms": 0,
                "policy_version": "fixture-v1", "baseline_decision": "FOLLOW",
            })
            record = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(record["decision"], "NO_DECISION")
            self.assertEqual(record["orders_sent"], 0)
            with self.assertRaises(ValueError):
                ShadowRecorder(path).record({"decision": "TRADE"})

    def test_shadow_pipeline_is_disabled_by_default_and_zero_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "shadow.jsonl"
            disabled = ShadowMode(ShadowRecorder(path))
            self.assertEqual(disabled.observe(signal={}, quote={}, candidate_sha256="",
                policy_version="v1", decision_fn=lambda _: "FOLLOW")["status"], "DISABLED")
            self.assertFalse(path.exists())
            mode = ShadowMode(ShadowRecorder(path), enabled=True, session_guard=RuntimeSessionGuard())
            signal = {"signal_id": "s1", "symbol": "US30Cash",
                      "signal_time_utc": "2026-10-23T07:00:08Z",
                      "feature_max_time_utc": "2026-10-23T07:00:05Z", "features": {"k": 22}}
            quote = {"symbol": "US30Cash", "time_utc": "2026-10-23T07:00:09Z",
                     "bid": 40000.0, "ask": 40000.5}
            result = mode.observe(signal=signal, quote=quote, candidate_sha256="c" * 64,
                policy_version="candidate-v1", decision_fn=lambda _: "FOLLOW",
                session_observation=SessionObservation(datetime(2026, 10, 23, 7, 0, 10, tzinfo=timezone.utc),
                    datetime(2026, 10, 23, 7, 0, 9, tzinfo=timezone.utc), True, "DEMO", "XMGlobal-MT5 10",
                    "US30Cash", 40000, 40001, 7200, True, True, "NORMAL", "OPEN"),
                now_utc=datetime(2026, 10, 23, 7, 0, 10, tzinfo=timezone.utc))
            self.assertEqual(result["decision"], "FOLLOW")
            self.assertEqual(result["orders_sent"], 0)
            event = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(event["order_count"], 0)
            self.assertEqual(event["spread"], 0.5)
            stale_quote = {**quote, "time_utc": "2026-10-23T07:00:00Z"}
            stale = mode.observe(signal=signal, quote=stale_quote, candidate_sha256="c" * 64,
                policy_version="candidate-v1", decision_fn=lambda _: "INVERT",
                now_utc=datetime(2026, 10, 23, 7, 0, 10, tzinfo=timezone.utc))
            self.assertEqual(stale["decision"], "NO_DECISION")
            self.assertEqual(mode.order_count, 0)
            no_candidate = mode.observe(
                signal={**signal, "signal_id": "s2"}, quote=quote, candidate_sha256=None,
                policy_version="NO_CANDIDATE", decision_fn=lambda _: self.fail("policy must not run without a candidate"),
                now_utc=datetime(2026, 10, 23, 7, 0, 10, tzinfo=timezone.utc))
            self.assertEqual(no_candidate["status"], "NO_FROZEN_CANDIDATE")
            self.assertEqual(no_candidate["orders_sent"], 0)

    def test_shadow_refuses_missing_ambiguous_and_closed_sessions_before_policy(self):
        now = datetime(2026, 10, 23, 8, 0, tzinfo=timezone.utc)
        signal = {"signal_id": "guard-fixture", "symbol": "US30Cash",
                  "signal_time_utc": "2026-10-23T08:00:00Z", "feature_max_time_utc": "2026-10-23T07:59:59Z",
                  "features": {"x": 1}}
        quote = {"symbol": "US30Cash", "time_utc": "2026-10-23T08:00:00Z", "bid": 40000, "ask": 40001}
        observation = SessionObservation(now, now, True, "DEMO", "XMGlobal-MT5 10", "US30Cash",
                                         40000, 40001, 7200, True, True, "NORMAL", "CLOSED")
        with tempfile.TemporaryDirectory() as tmp:
            for guard, context, reason in (
                    (None, None, "SESSION_GUARD_UNAVAILABLE"),
                    (RuntimeSessionGuard(), None, "SESSION_RUNTIME_MISSING"),
                    (RuntimeSessionGuard(), observation, "BROKER_MARKET_CLOSED")):
                mode = ShadowMode(ShadowRecorder(Path(tmp) / "shadow.jsonl"), enabled=True, session_guard=guard)
                result = mode.observe(signal=signal, quote=quote, candidate_sha256="a" * 64,
                    policy_version="fixture-only", now_utc=now, session_observation=context,
                    decision_fn=lambda _: self.fail("policy must not execute behind a failed session gate"))
                self.assertEqual(result["status"], reason)
                self.assertEqual(result["decision"], "NO_DECISION")
                self.assertEqual(result["orders_sent"], 0)

    def test_read_only_mt5_adapter_exposes_no_order_methods(self):
        class FakeMT5:
            def symbol_info_tick(self, symbol):
                return symbol
            def order_send(self, request):
                raise AssertionError("must never be callable")

        adapter = ReadOnlyMT5Adapter(FakeMT5())
        self.assertEqual(adapter.symbol_info_tick("US30Cash"), "US30Cash")
        with self.assertRaisesRegex(AttributeError, "refuses method"):
            adapter.order_send

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
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM order_intents").fetchone()[0], 1)
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
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM order_intents").fetchone()[0], 2)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0], 3)
            finally:
                connection.close()

    def test_blocked_intent_is_idempotent_across_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "state.sqlite3"
            state = RuntimeState(**{**self.state.__dict__, "signal_key": "daily-loss", "daily_loss": 100.0})
            first = MockShadowExecutor(db, enabled=True)
            result = first.record(state, self.limits, decision="FOLLOW", candidate_sha256="d" * 64)
            self.assertEqual(result["reason"], "DAILY_LOSS_LIMIT")
            restarted = MockShadowExecutor(db, enabled=True)
            self.assertEqual(restarted.load_runtime_snapshot()["signal_key"], "daily-loss")
            duplicate = restarted.record(state, self.limits, decision="FOLLOW", candidate_sha256="d" * 64)
            self.assertEqual(duplicate["reason"], "DUPLICATE_OR_EMPTY_SIGNAL")
            self.assertEqual(duplicate["orders_sent"], 0)


if __name__ == "__main__":
    unittest.main()
