import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "tests"))
from build_master_dataset import build
from fixtures import audit, dataset


class MasterBuildTests(unittest.TestCase):
    def _block(self, root: Path, safe=True):
        block = root / "block"
        block.mkdir()
        frame = dataset(30)
        frame.to_csv(block / "stochastic_events.csv", index=False, float_format="%.17g")
        (block / "stochastic_events.csv.audit.json").write_text(json.dumps(audit(30)))
        manifest = {
            "period": "2024-01-01..2024-01-01", "validator": "PASS",
            "LIVE_TRADING": not safe, "optimization": "OFF",
            "model": "Every tick based on real ticks", "code_HEAD_SHA": "test-sha",
            "tester_warnings": [],
        }
        (block / "manifest.json").write_text(json.dumps(manifest))
        return block

    def test_master_writes_only_train_and_validation_splits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            block = self._block(root)
            result = build([block], root / "master", root / "splits")
            self.assertEqual(result["signals"], 30)
            self.assertTrue((root / "master/stochastic_master.parquet").is_file())
            self.assertTrue((root / "splits/train.parquet").is_file())
            self.assertTrue((root / "splits/validation.parquet").is_file())
            self.assertFalse((root / "splits/final_test.parquet").exists())
            split = json.loads((root / "splits/split_manifest.json").read_text())
            self.assertFalse(split["final_test_parquet_written"])

    def test_master_refuses_live_trading_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            block = self._block(root, safe=False)
            with self.assertRaisesRegex(ValueError, "Unsafe or optimized"):
                build([block], root / "master", root / "splits")


if __name__ == "__main__":
    unittest.main()
