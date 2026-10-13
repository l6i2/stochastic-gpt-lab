from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from python.parquet_io import write_parquet

from python.validate_intratrade_dataset import REQUIRED_FEATURE_COLUMNS, validate


class IntratradeDatasetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.snapshots = self.root / "intratrade_snapshots.csv"
        self.audit = self.root / "intratrade_snapshots.csv.audit.json"
        self.targets = self.root / "intratrade_snapshot_targets.csv"
        self.feature_fields = sorted(REQUIRED_FEATURE_COLUMNS)
        row = {name: "1" for name in self.feature_fields}
        row.update({"snapshot_id": "sig_FOLLOW_1", "signal_id": "sig", "symbol": "US30Cash",
                    "signal_time_msc": "1000", "original_signal": "BUY", "virtual_mode": "FOLLOW",
                    "virtual_side": "BUY", "entry_time_msc": "1500", "snapshot_bar": "1",
                    "snapshot_time_msc": "2000", "feature_max_time_msc": "2000",
                    "mark_time_msc": "1999", "bars_open": "1"})
        with self.snapshots.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=self.feature_fields)
            writer.writeheader()
            writer.writerow(row)
        self.audit.write_text(json.dumps({"schema_version": "2.0", "LIVE_TRADING": False,
            "optimization": "OFF", "aborted": False, "snapshot_schedule": "1,2,3,5,10,15,20,30,50",
            "snapshot_rows": 1, "target_rows": 0, "signals": 1}), encoding="utf-8")
        self.targets.write_text("", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_causal_snapshot_passes_without_targets_for_censored_trade(self):
        result = validate(self.snapshots, self.audit, self.targets)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["final_test_accessed"])

    def test_rejects_feature_timestamp_after_snapshot(self):
        with self.snapshots.open("r", newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        rows[0]["feature_max_time_msc"] = "2001"
        with self.snapshots.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=self.feature_fields)
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaisesRegex(ValueError, "Lookahead"):
            validate(self.snapshots, self.audit, self.targets)

    def test_rejects_outcome_columns_in_feature_table(self):
        fields = self.feature_fields + ["future_pnl_to_exit"]
        with self.snapshots.open("r", newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        with self.snapshots.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerow({**rows[0], "future_pnl_to_exit": "999"})
        with self.assertRaisesRegex(ValueError, "leaked"):
            validate(self.snapshots, self.audit, self.targets)

    def test_rejects_signal_not_in_train_or_validation(self):
        train, validation = self.root / "train.parquet", self.root / "validation.parquet"
        write_parquet(pd.DataFrame({"signal_id": ["train"]}), train)
        write_parquet(pd.DataFrame({"signal_id": ["validation"]}), validation)
        with self.assertRaisesRegex(ValueError, "FINAL_TEST"):
            validate(self.snapshots, self.audit, self.targets, train, validation)

    def test_rejects_live_trading_manifest(self):
        data = json.loads(self.audit.read_text(encoding="utf-8"))
        data["LIVE_TRADING"] = True
        self.audit.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            validate(self.snapshots, self.audit, self.targets)


if __name__ == "__main__":
    unittest.main()
