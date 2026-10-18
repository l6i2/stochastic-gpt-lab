import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from explore_train_intratrade_round2 import FEATURES, triggers


def row(**changes):
    base = {name: 0.0 for name in FEATURES}
    base.update({"virtual_side": "BUY", "current_unrealized_pnl": 10.0,
                 "current_mfe_so_far": 140.0, "distance_to_sl": 100.0,
                 "stoch_k_prev": 85.0, "stoch_k": 79.0,
                 "relative_volume_20": 1.4, "ATR_percentile_20": 0.9,
                 "return_1": -1.0, "ha_changed_to_bullish": 0.0,
                 "ha_changed_to_bearish": 1.0,
                 "vp_60m_distance_price_to_VAH": -10.0,
                 "vp_60m_distance_price_to_VAL": -30.0,
                 "NY_time": "2024.01.10 15:30:00"})
    base.update(changes)
    return base


class TrainIntratradeRound2Tests(unittest.TestCase):
    def test_frozen_conditions_trigger_as_defined(self):
        result = triggers(row())
        self.assertTrue(result["HYP-20261018-R2-001"])  # 10 units of giveback after 140 MFE
        self.assertFalse(result["HYP-20261018-R2-002"])
        self.assertFalse(result["HYP-20261018-R2-003"])
        self.assertTrue(result["HYP-20261018-R2-004"])
        self.assertTrue(result["HYP-20261018-R2-005"])
        self.assertFalse(result["HYP-20261018-R2-006"])
        self.assertTrue(result["HYP-20261018-R2-007"])
        self.assertTrue(result["HYP-20261018-R2-008"])

    def test_sell_side_mappings_are_mirrored(self):
        r = row(virtual_side="SELL", current_unrealized_pnl=12.0,
               stoch_k_prev=15.0, stoch_k=21.0,
               ha_changed_to_bullish=1.0, ha_changed_to_bearish=0.0,
               vp_60m_distance_price_to_VAH=25.0,
               vp_60m_distance_price_to_VAL=12.0, return_1=1.0)
        result = triggers(r)
        self.assertTrue(result["HYP-20261018-R2-004"])
        self.assertTrue(result["HYP-20261018-R2-005"])
        self.assertTrue(result["HYP-20261018-R2-007"])

    def test_missing_values_do_not_trigger(self):
        r = row(current_unrealized_pnl=math.nan, current_mfe_so_far=math.nan,
                distance_to_sl=math.nan, stoch_k_prev=math.nan, stoch_k=math.nan,
                relative_volume_20=math.nan, ATR_percentile_20=math.nan,
                return_1=math.nan, vp_60m_distance_price_to_VAH=math.nan,
                vp_60m_distance_price_to_VAL=math.nan, NY_time="",
                ha_changed_to_bullish=math.nan, ha_changed_to_bearish=math.nan)
        self.assertFalse(any(triggers(r).values()))

    def test_session_cutoff_is_1530_new_york(self):
        self.assertFalse(triggers(row(NY_time="2024.01.10 15:29:00"))["HYP-20261018-R2-008"])
        self.assertTrue(triggers(row(NY_time="2024.01.10 15:30:00"))["HYP-20261018-R2-008"])

    def test_round3_new_families_and_poc_crossing(self):
        r = row(current_mae_so_far=130, current_unrealized_pnl=-50,
                distance_to_tp=50, current_mfe_so_far=70,
                relative_volume_20=0.5, vp_60m_distance_price_to_POC=0.0)
        result = triggers(r, "R3", previous_poc=1.0)
        self.assertTrue(result["HYP-20261018-R3-001"])
        self.assertFalse(result["HYP-20261018-R3-002"])
        self.assertFalse(result["HYP-20261018-R3-003"])
        r.update(current_unrealized_pnl=10.0)
        result = triggers(r, "R3", previous_poc=1.0)
        self.assertTrue(result["HYP-20261018-R3-002"])
        self.assertTrue(result["HYP-20261018-R3-003"])
        self.assertTrue(result["HYP-20261018-R3-004"])

    def test_round4_new_families(self):
        r = row(current_unrealized_pnl=-20.0, ema_bear_alignment=1.0,
                ema_bull_alignment=0.0, recent_low_break=1.0,
                recent_high_break=0.0, bars_open=50,
                rolling_std_20=0.5, rolling_std_50=1.0)
        result = triggers(r, "R4")
        self.assertTrue(result["HYP-20261018-R4-001"])
        self.assertTrue(result["HYP-20261018-R4-002"])
        self.assertTrue(result["HYP-20261018-R4-003"])
        self.assertFalse(result["HYP-20261018-R4-004"])
        r["current_unrealized_pnl"] = 20.0
        result = triggers(r, "R4")
        self.assertTrue(result["HYP-20261018-R4-004"])


if __name__ == "__main__":
    unittest.main()
