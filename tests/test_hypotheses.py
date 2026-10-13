import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "tests"))
from evaluate_hypotheses import evaluate, _select
from fixtures import dataset


class HypothesisEvaluationTests(unittest.TestCase):
    def test_cluster_bootstrap_is_reproducible_and_reports_both_sides(self):
        frame = dataset(120)
        frame["signal_utc_epoch"] = [1704067200 + i * 7 * 86400 for i in range(len(frame))]
        frame["ha_direction"] = 1
        hypothesis = {
            "hypothesis_id": "TEST-1", "causal_at_signal_time": True,
            "outcome": "directional_advantage", "expected_sign": 1,
            "signal_side": "BUY", "conditions": [
                {"column": "follow_side", "operator": "eq", "value": "BUY"},
                {"column": "ha_direction", "operator": "eq", "value": 1}],
            "minimum_support": {"overall": 500, "intended_side": 500},
        }
        first = evaluate(frame, hypothesis, seed=17)
        second = evaluate(frame, hypothesis, seed=17)
        self.assertEqual(first, second)
        self.assertEqual(first["n_by_signal_side"]["SELL"], 0)
        self.assertEqual(first["status"], "INCONCLUSIVE")
        self.assertEqual(len(first["directional_advantage_ci95_week_cluster_bootstrap"]), 2)

    def test_future_outcome_cannot_be_used_as_a_filter(self):
        frame = dataset(10)
        with self.assertRaisesRegex(ValueError, "Unsafe or non-causal"):
            _select(frame, [{"column": "follow_PnL", "operator": "gt", "value": 0}])

    def test_uncertain_effect_is_inconclusive_not_rejected(self):
        frame = dataset(100)
        frame["signal_utc_epoch"] = [1704067200 + i * 7 * 86400 for i in range(len(frame))]
        frame["follow_side"] = "BUY"
        frame["ha_direction"] = 1
        frame["directional_advantage"] = [1 if i % 2 else -1 for i in range(len(frame))]
        frame["follow_PnL"] = frame.directional_advantage
        frame["invert_PnL"] = 0.0
        hypothesis = {
            "hypothesis_id": "TEST-UNCERTAIN", "causal_at_signal_time": True,
            "outcome": "directional_advantage", "expected_sign": 1,
            "signal_side": "BUY", "conditions": [
                {"column": "follow_side", "operator": "eq", "value": "BUY"},
                {"column": "ha_direction", "operator": "eq", "value": 1}],
            "minimum_support": {"overall": 50, "intended_side": 50},
        }
        result = evaluate(frame, hypothesis, seed=42)
        self.assertEqual(result["status"], "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
