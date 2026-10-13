import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "tests"))
from train_direction_model import feature_list, run, _policy_stats
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
            with self.assertRaisesRegex(ValueError, "FINAL_TEST paths are categorically refused"):
                run(root / "train.parquet", root / "final_test.parquet", root / "out", False)
            self.assertFalse((root / "out").exists())

    def test_model_policy_has_the_same_rows_as_fixed_baselines(self):
        frame = dataset(20)
        model = _policy_stats(frame, frame.directional_advantage.gt(0).to_numpy(), "m", "validation")
        follow = _policy_stats(frame, [True] * len(frame), "FOLLOW_ALWAYS", "validation")
        invert = _policy_stats(frame, [False] * len(frame), "INVERT_ALWAYS", "validation")
        self.assertEqual(model["signals"], follow["signals"])
        self.assertEqual(model["signals"], invert["signals"])


if __name__ == "__main__":
    unittest.main()
