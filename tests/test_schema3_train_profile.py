import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from python.analyze_schema3_train import FEATURES, GROUPS, analyze


class Schema3TrainProfileTests(unittest.TestCase):
    def test_final_test_path_is_rejected_before_reading(self):
        with self.assertRaisesRegex(ValueError, "protected split path"):
            analyze(Path("outputs/final_test/private.parquet"), Path("unused"), Path("unused"))

    def test_profile_reads_only_features_and_hash_pinned_train(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            train = root / "train.parquet"
            frame = pd.DataFrame({
                "signal_id": ["s1", "s1", "s2"],
                "original_signal": ["BUY", "BUY", "SELL"],
                "virtual_mode": ["FOLLOW", "FOLLOW", "INVERT"],
                "snapshot_bar": [1, 2, 1],
                **{name: [1.0, 2.0, 3.0] for name in FEATURES},
            })
            frame.to_parquet(train, engine="fastparquet", index=False)
            digest = hashlib.sha256(train.read_bytes()).hexdigest()
            quality = root / "quality.json"
            quality.write_text(json.dumps({
                "status": "PASS_INHERITED_VALIDATION", "final_test_accessed": False,
                "policy_version": "tick_quality_v1", "output_sha256": {"train.parquet": digest},
            }), encoding="utf-8")
            result = analyze(train, root / "profile", quality)
            self.assertEqual(result["status"], "TRAIN_DESCRIPTIVE_PROFILE_ONLY")
            self.assertEqual(result["rows"], 3)
            self.assertEqual(result["unique_signals"], 2)
            self.assertFalse(result["final_test_accessed"])
            self.assertFalse(result["discovery_validation_accessed"])
            self.assertEqual(set(GROUPS), {"original_signal", "virtual_mode", "snapshot_bar"})


if __name__ == "__main__":
    unittest.main()
