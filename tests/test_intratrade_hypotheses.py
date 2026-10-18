from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from python.intratrade_hypotheses import evaluate, freeze
from python.parquet_io import write_parquet


class IntratradeHypothesisTests(unittest.TestCase):
    def test_freezes_train_rules_but_blocks_contaminated_discovery_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            train_path, validation_path, targets_path = (root / "train.parquet", root / "validation.parquet",
                                                          root / "targets.csv")

            def snapshots(prefix, count):
                rows = []
                for i in range(count):
                    rows.append({"snapshot_id": f"{prefix}_{i}", "signal_id": f"{prefix}_signal_{i}",
                                 "snapshot_bar": 3, "virtual_mode": "FOLLOW", "virtual_side": "BUY",
                                 "original_signal": "BUY", "signal_time_msc": 100000 + i,
                                 "ha_direction": -1 if i < 110 else 1,
                                 "stoch_direction_change": i % 2, "vp_30m_inside_value_area": i % 2,
                                 "current_unrealized_pnl": 80 if i < 30 else 10})
                return pd.DataFrame(rows)

            train = snapshots("train", 120)
            validation = snapshots("validation", 120)
            write_parquet(train, train_path)
            write_parquet(validation, validation_path)
            target_rows = []
            for frame in (train, validation):
                for row in frame.itertuples():
                    target_rows.append({"snapshot_id": row.snapshot_id, "signal_id": row.signal_id,
                                        "snapshot_bar": row.snapshot_bar, "virtual_mode": row.virtual_mode,
                                        "reversal_event": int(row.ha_direction == -1)})
            pd.DataFrame(target_rows).to_csv(targets_path, index=False)
            frozen_dir = root / "hypotheses"
            manifest = freeze(train_path, targets_path, frozen_dir)
            self.assertFalse(manifest["final_test_accessed"])
            self.assertEqual(len(manifest["hypotheses"]), 4)
            with self.assertRaises(FileExistsError):
                freeze(train_path, targets_path, frozen_dir)
            results_path = root / "results"
            with self.assertRaisesRegex(ValueError, "protected split path"):
                evaluate(validation_path, targets_path, frozen_dir, results_path)
            self.assertFalse(results_path.exists())

    def test_final_test_named_inputs_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "protected split path"):
            freeze(Path("final_test.parquet"), Path("targets.csv"), Path("hypotheses"))


if __name__ == "__main__":
    unittest.main()
