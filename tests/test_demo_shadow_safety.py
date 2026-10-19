from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from demo_safety import DemoLimits, RuntimeState, authorize_demo_decision
from shadow_mode import ShadowRecorder


class DemoShadowSafetyTests(unittest.TestCase):
    def setUp(self):
        self.limits = DemoLimits(0.1, 1, 100.0, 3, 5.0, 2.0, 4)
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
        ]
        for state, expected in cases:
            self.assertEqual(authorize_demo_decision(state, self.limits, set()), (False, expected))
        self.assertEqual(authorize_demo_decision(self.state, self.limits, {"s1"}),
                         (False, "DUPLICATE_OR_EMPTY_SIGNAL"))
        allowed, reason = authorize_demo_decision(self.state, self.limits, set())
        self.assertTrue(allowed)
        self.assertEqual(reason, "GATES_PASS_NO_ORDER_SENT")

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


if __name__ == "__main__":
    unittest.main()
