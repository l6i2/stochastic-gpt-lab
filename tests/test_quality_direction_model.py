import unittest
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from python.train_direction_model import ROUND2_BASE_FEATURES, add_round2_interactions, feature_list
from python.train_direction_model import _target_rows


class QualityDirectionModelTests(unittest.TestCase):
    def test_fixed_signal_feature_whitelist_excludes_outcomes(self):
        required = {
            "follow_side", "ha_direction", "relative_volume_20",
            "ha_changed_to_bullish", "ha_changed_to_bearish",
            "exit_speed_from_zone", "ha_body_expansion", "bull_alignment",
            "bear_alignment", "ATR_percentile_20",
            "vp_session_distance_price_to_POC",
            "vp_session_distance_price_to_VAH",
            "vp_session_distance_price_to_VAL",
        }
        columns = set(ROUND2_BASE_FEATURES) | required
        frame = pd.DataFrame({name: [1.0, 2.0] for name in columns})
        frame["follow_side"] = ["BUY", "SELL"]
        frame["follow_PnL"] = [100.0, -100.0]
        frame["invert_PnL"] = [-100.0, 100.0]
        frame["directional_advantage"] = [200.0, -200.0]
        featured = add_round2_interactions(frame)
        features = feature_list(featured, round2=True)
        self.assertGreaterEqual(len(features), 10)
        self.assertTrue(set(features).issubset(featured.columns))
        self.assertFalse(any(token in name for name in features
                             for token in ("PnL", "exit_price", "exit_reason", "MFE", "MAE",
                                           "directional_advantage")))

    def test_censored_directional_labels_are_counted_but_not_fitted(self):
        frame = pd.DataFrame({
            "follow_PnL": [10.0, np.nan, -5.0],
            "invert_PnL": [0.0, np.nan, -3.0],
            "directional_advantage": [10.0, np.nan, -2.0],
        })
        rows, target = _target_rows(frame)
        self.assertEqual(len(frame) - len(rows), 1)
        self.assertEqual(target.tolist(), [1, 0])


if __name__ == "__main__":
    unittest.main()
