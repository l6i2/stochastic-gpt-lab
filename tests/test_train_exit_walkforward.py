import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from evaluate_train_exit_walkforward import build_folds


class TrainExitWalkForwardTests(unittest.TestCase):
    def test_folds_are_chronological_and_purge_crossing_eval_labels(self):
        frame = pd.DataFrame({
            "signal_id": [f"s{i}" for i in range(10)],
            "signal_time_msc": [i * 100 for i in range(10)],
            "label_end_msc": [i * 100 + 20 for i in range(10)],
        })
        frame.loc[4, "label_end_msc"] = 750
        folds = build_folds(frame, initial=4, step=3)
        self.assertEqual([f["fold"] for f in folds], [1, 2])
        self.assertEqual(folds[0]["eval_rows_before_purge"], 3)
        self.assertEqual(folds[0]["eval_rows_after_purge"], 2)
        self.assertEqual(folds[0]["purged_eval_ids"], 1)
        self.assertLess(max(int(i[1:]) for i in folds[0]["train_ids"]),
                        min(int(i[1:]) for i in folds[0]["eval_ids"]))
        self.assertTrue(folds[1]["eval_ids"])


if __name__ == "__main__":
    unittest.main()
