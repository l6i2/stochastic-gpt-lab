import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from explore_train_intratrade_exits import policy_triggers


class IntratradeExitExplorationTests(unittest.TestCase):
    def test_buy_opposition_rules(self):
        self.assertEqual(policy_triggers(1, -1, 20, 30), {
            "HA_OPPOSITE": True,
            "STOCH_KD_OPPOSITE": True,
            "HA_AND_STOCH_OPPOSITE": True,
        })
        self.assertEqual(policy_triggers(1, 1, 30, 20), {
            "HA_OPPOSITE": False,
            "STOCH_KD_OPPOSITE": False,
            "HA_AND_STOCH_OPPOSITE": False,
        })

    def test_sell_opposition_rules_and_missing_values(self):
        self.assertEqual(policy_triggers(-1, 1, 30, 20), {
            "HA_OPPOSITE": True,
            "STOCH_KD_OPPOSITE": True,
            "HA_AND_STOCH_OPPOSITE": True,
        })
        self.assertEqual(policy_triggers(-1, float("nan"), 20, 30), {
            "HA_OPPOSITE": False,
            "STOCH_KD_OPPOSITE": False,
            "HA_AND_STOCH_OPPOSITE": False,
        })


if __name__ == "__main__":
    unittest.main()
