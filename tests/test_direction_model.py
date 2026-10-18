import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "tests"))
from train_direction_model import (feature_list, run, _policy_stats, make_models,
    add_round2_interactions, ROUND2_INTERACTIONS)
from fixtures import dataset


class DirectionModelSafetyTests(unittest.TestCase):
    def test_feature_list_has_only_causal_numeric_features(self):
        frame = dataset(10)
        features = feature_list(frame)
        self.assertIn("ha_direction", features)
        self.assertNotIn("follow_PnL", features)
        self.assertNotIn("exit_price", features)
        self.assertNotIn("directional_advantage", features)

    def test_final_test_path_is_refused_before_any_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "protected split path"):
                run(root / "train.parquet", root / "final_test.parquet", root / "out", False)
            self.assertFalse((root / "out").exists())

    def test_model_policy_has_the_same_rows_as_fixed_baselines(self):
        frame = dataset(20)
        model = _policy_stats(frame, frame.directional_advantage.gt(0).to_numpy(), "m", "validation")
        follow = _policy_stats(frame, [True] * len(frame), "FOLLOW_ALWAYS", "validation")
        invert = _policy_stats(frame, [False] * len(frame), "INVERT_ALWAYS", "validation")
        self.assertEqual(model["signals"], follow["signals"])
        self.assertEqual(model["signals"], invert["signals"])

    def test_round_two_has_calibrated_logistic_with_ordered_cv(self):
        from sklearn.calibration import CalibratedClassifierCV
        from sklearn.model_selection import TimeSeriesSplit
        models = make_models()
        self.assertIn("calibrated_logistic", models)
        calibrated = models["calibrated_logistic"]
        self.assertIsInstance(calibrated, CalibratedClassifierCV)
        self.assertIsInstance(calibrated.cv, TimeSeriesSplit)

    def test_round_two_interactions_are_fixed_causal_and_side_aligned(self):
        frame = dataset(20)
        frame["ha_direction"] = [1 if value == "BUY" else -1 for value in frame.follow_side]
        frame["relative_volume_20"] = 2.0
        frame["ha_changed_to_bullish"] = 1
        frame["ha_changed_to_bearish"] = 0
        frame["exit_speed_from_zone"] = 0.5
        frame["ha_body_expansion"] = 1.2
        frame["bull_alignment"] = 1
        frame["bear_alignment"] = 0
        frame["ATR_percentile_20"] = 0.8
        frame["vp_session_distance_price_to_POC"] = 2.0
        frame["vp_session_distance_price_to_VAH"] = -1.0
        frame["vp_session_distance_price_to_VAL"] = 5.0
        result = add_round2_interactions(frame)
        expected = {"r2_ha_alignment", "r2_volume_x_ha_alignment", "r2_volume_x_ha_transition",
                    "r2_stoch_exit_speed_x_volume", "r2_ha_body_expansion_x_volume",
                    "r2_trend_alignment_x_ha", "r2_atr_percentile_x_volume",
                    "r2_price_to_poc_x_side", "r2_price_to_vah_x_side", "r2_price_to_val_x_side"}
        self.assertEqual(ROUND2_INTERACTIONS, expected)
        self.assertTrue(expected.issubset(result.columns))
        aligned = result.ha_direction * result.follow_side.map({"BUY": 1.0, "SELL": -1.0})
        self.assertTrue(result.r2_ha_alignment.equals(aligned))
        self.assertTrue(ROUND2_INTERACTIONS.isdisjoint({"follow_PnL", "MFE", "MAE", "exit_price"}))
        round2_features = feature_list(result, round2=True)
        self.assertTrue(ROUND2_INTERACTIONS.issubset(round2_features))
        self.assertLess(len(round2_features), len(feature_list(frame)))


if __name__ == "__main__":
    unittest.main()
