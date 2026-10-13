from __future__ import annotations

import unittest

import pandas as pd

from python.train_intratrade_models import FEATURES, _policy_report, _temporal_group_folds


class IntratradeModelSafetyTests(unittest.TestCase):
    def test_feature_whitelist_excludes_future_targets_and_identifiers(self):
        forbidden = {"future_pnl_to_exit", "reversal_event", "exit_time_msc", "snapshot_id",
                     "signal_id", "snapshot_time_msc", "feature_max_time_msc"}
        self.assertFalse(forbidden.intersection(FEATURES))
        self.assertFalse(any(token in feature.lower() for feature in FEATURES
                             for token in ("future_", "final_", "exit_", "target", "label")))

    def test_temporal_calibration_folds_keep_each_signal_together(self):
        rows = []
        for signal in range(20):
            for bar in (1, 3, 5):
                rows.append({"signal_id": f"s{signal}", "signal_time_msc": signal,
                             "snapshot_bar": bar})
        frame = pd.DataFrame(rows)
        for train_idx, test_idx in _temporal_group_folds(frame):
            train_ids = set(frame.iloc[train_idx].signal_id)
            test_ids = set(frame.iloc[test_idx].signal_id)
            self.assertFalse(train_ids & test_ids)
            self.assertLess(frame.iloc[train_idx].signal_time_msc.max(),
                            frame.iloc[test_idx].signal_time_msc.min())

    def test_policy_report_freezes_bar_and_does_not_simulate_reverse(self):
        frame = pd.DataFrame([
            {"snapshot_bar": 3, "signal_id": "s1", "virtual_mode": "FOLLOW", "signal_time_msc": 1,
             "current_unrealized_pnl": 80.0, "future_pnl_to_exit": -40.0},
            {"snapshot_bar": 3, "signal_id": "s1", "virtual_mode": "INVERT", "signal_time_msc": 1,
             "current_unrealized_pnl": -10.0, "future_pnl_to_exit": 20.0},
        ])
        probabilities = {"fixed_model": pd.Series([0.8, 0.1], index=frame.index)}
        result = _policy_report(frame, probabilities)
        self.assertEqual(result["status"], "SIMULATED_AT_FIXED_BAR_3_ONLY")
        self.assertEqual(result["thresholds_frozen"]["model_early_exit_probability"], 0.7)
        self.assertEqual(result["model_early_exit"]["fixed_model"]["mean_pnl"], 45.0)
        self.assertEqual(result["REVERSE_DIRECTION"]["status"], "NOT_SIMULATED_MISSING_POST_SNAPSHOT_QUOTE_PATH")


if __name__ == "__main__":
    unittest.main()
