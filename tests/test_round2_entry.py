import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from round2_entry_research import hypotheses
from research import FEATURE_COLUMNS


class RoundTwoEntryTests(unittest.TestCase):
    def test_fixed_family_has_ten_causal_non_skip_hypotheses(self):
        items = hypotheses()
        self.assertEqual(len(items), 10)
        self.assertEqual(sum(x["signal_side"] == "BUY" for x in items), 5)
        self.assertEqual(sum(x["signal_side"] == "SELL" for x in items), 5)
        for item in items:
            self.assertTrue(item["conditions"])
            self.assertLessEqual(len(item["conditions"]) - 1, 2)
            for condition in item["conditions"]:
                self.assertIn(condition["column"], set(FEATURE_COLUMNS) | {"follow_side"})
                self.assertNotIn("PnL", condition["column"])
                self.assertNotIn("MFE", condition["column"])
                self.assertNotIn("MAE", condition["column"])
                self.assertNotIn("exit", condition["column"])
        self.assertFalse(any("skip" in x["hypothesis_id"].lower() for x in items))

    def test_conditions_always_scope_to_signal_side(self):
        for item in hypotheses():
            self.assertEqual(item["conditions"][0], {
                "column": "follow_side", "operator": "eq", "value": item["signal_side"]})


if __name__ == "__main__":
    unittest.main()
