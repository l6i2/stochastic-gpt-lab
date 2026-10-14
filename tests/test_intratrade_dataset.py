from __future__ import annotations

import csv
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import pandas as pd
from python.parquet_io import write_parquet

from python.validate_intratrade_dataset import REQUIRED_FEATURE_COLUMNS, validate


class IntratradeDatasetTests(unittest.TestCase):
    def test_endpoint_quarantine_uses_entry_clock_not_previous_bar_cutoff(self):
        train, validation = self.root/'train.parquet', self.root/'validation.parquet'
        write_parquet(pd.DataFrame({'signal_id':['train']}),train)
        write_parquet(pd.DataFrame({'signal_id':['validation']}),validation)
        events=self.root/'events.csv'
        events.write_text('signal_id,signal_time_msc,entry_time_msc,tp_distance,sl_distance,time_exit_bars,follow_side,invert_side,follow_exit_reason,invert_exit_reason,follow_exit_time,invert_exit_time\n'
                          'sig,1000,1001,240,180,100,BUY,SELL,END_OF_DATA,END_OF_DATA,2500,2500\n')
        self.snapshots.write_text(self.snapshots.read_text().replace('1500','1001'))
        split=self.root/'split.json'
        split.write_text(json.dumps({'boundaries':{'validation_start_signal_time_msc':3000,
                                                  'final_test_start_signal_time_msc':5000}}))
        contract=self.root/'contract.json';contract.write_text('{}')
        with patch('python.membership_contract.quarantine_windows',return_value=[(1001,1501)]):
            result=validate(self.snapshots,self.audit,self.targets,train,validation,events,split,
                            quarantine_manifest=contract)
        self.assertEqual(result['quarantined_noncanonical_signals'],1)
        self.assertEqual(result['purged_signals_excluded_from_splits'],0)

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
                    "mark_time_msc": "1999", "bars_open": "1", "current_ask": "2",
                    "distance_to_tp": "239", "distance_to_sl": "181"})
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

    def test_unscoped_pass_does_not_claim_final_test_was_not_accessed(self):
        result = validate(self.snapshots, self.audit, self.targets)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["split_membership_verified"])
        self.assertIsNone(result["final_test_accessed"])

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

    def test_accepts_only_known_pre_final_purged_signals(self):
        train, validation = self.root / "train.parquet", self.root / "validation.parquet"
        write_parquet(pd.DataFrame({"signal_id": ["train"]}), train)
        write_parquet(pd.DataFrame({"signal_id": ["validation"]}), validation)
        events = self.root / "stochastic_events.csv"
        events.write_text("signal_id,signal_time_msc,tp_distance,sl_distance,time_exit_bars,follow_side,invert_side,follow_exit_reason,invert_exit_reason,follow_exit_time,invert_exit_time\n"
                          "sig,1000,240,180,100,BUY,SELL,END_OF_DATA,END_OF_DATA,3500,3500\n", encoding="utf-8")
        boundary = self.root / "split_manifest.json"
        boundary.write_text(json.dumps({"boundaries": {"validation_start_signal_time_msc": 3000,
                                                       "final_test_start_signal_time_msc": 5000}}), encoding="utf-8")
        result = validate(self.snapshots, self.audit, self.targets, train, validation, events, boundary)
        self.assertEqual(result["purged_signals_excluded_from_splits"], 1)
        self.assertFalse(result["final_test_accessed"])
        events.write_text(events.read_text().replace(',3500,3500', ',2500,2500'))
        with self.assertRaisesRegex(ValueError, "not explained by chronological boundary purging"):
            validate(self.snapshots, self.audit, self.targets, train, validation, events, boundary)

    def test_rejects_signal_id_absent_from_safe_event_source(self):
        train, validation = self.root / "train.parquet", self.root / "validation.parquet"
        write_parquet(pd.DataFrame({"signal_id": ["train"]}), train)
        write_parquet(pd.DataFrame({"signal_id": ["validation"]}), validation)
        events = self.root / "stochastic_events.csv"
        events.write_text("signal_id,signal_time_msc,tp_distance,sl_distance,time_exit_bars,follow_side,invert_side,follow_exit_reason,invert_exit_reason\n"
                          "other,1000,240,180,100,BUY,SELL,END_OF_DATA,END_OF_DATA\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "absent from block event source"):
            validate(self.snapshots, self.audit, self.targets, train, validation, events)

    def test_rejects_live_trading_manifest(self):
        data = json.loads(self.audit.read_text(encoding="utf-8"))
        data["LIVE_TRADING"] = True
        self.audit.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            validate(self.snapshots, self.audit, self.targets)

    def test_nan_cannot_bypass_execution_bounds(self):
        with self.snapshots.open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        rows[0]['current_mfe_so_far'] = 'nan'
        with self.snapshots.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=self.feature_fields)
            writer.writeheader(); writer.writerows(rows)
        with self.assertRaisesRegex(ValueError, 'Nonfinite'):
            validate(self.snapshots, self.audit, self.targets)

    def test_every_bar_schema_requires_complete_post_decision_execution_quotes(self):
        data = json.loads(self.audit.read_text())
        data.update(schema_version='3.0', snapshot_schedule=','.join(map(str, range(1, 101))))
        self.audit.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'separate execution quote'):
            validate(self.snapshots, self.audit, self.targets)
        execution = self.root/'execution.csv'
        execution.write_text('snapshot_id,signal_id,virtual_mode,snapshot_bar,decision_cutoff_msc,execution_time_msc,execution_bid,execution_ask\n'
                             'sig_FOLLOW_1,sig,FOLLOW,1,2000,2001,1,2\n')
        result = validate(self.snapshots, self.audit, self.targets, execution_quotes_csv=execution)
        self.assertEqual(result['execution_quote_rows'], 1)
        execution.write_text(execution.read_text().replace(',2001,', ',2000,'))
        with self.assertRaisesRegex(ValueError, 'Noncausal'):
            validate(self.snapshots, self.audit, self.targets, execution_quotes_csv=execution)

    def test_known_train_id_still_requires_past_only_label_horizon(self):
        train, validation = self.root/'train.parquet', self.root/'validation.parquet'
        write_parquet(pd.DataFrame({'signal_id': ['sig']}), train)
        write_parquet(pd.DataFrame({'signal_id': ['other']}), validation)
        events = self.root/'events.csv'
        events.write_text('signal_id,signal_time_msc,tp_distance,sl_distance,time_exit_bars,follow_side,invert_side,follow_exit_reason,invert_exit_reason,follow_exit_time,invert_exit_time\n'
                          'sig,1000,240,180,100,BUY,SELL,END_OF_DATA,END_OF_DATA,3500,3500\n')
        split = self.root/'split.json'
        split.write_text(json.dumps({'boundaries': {'validation_start_signal_time_msc': 3000,
                                                   'final_test_start_signal_time_msc': 5000}}))
        with self.assertRaisesRegex(ValueError, 'horizon crossing'):
            validate(self.snapshots, self.audit, self.targets, train, validation, events, split)
        events.write_text(events.read_text().replace(',3500,3500', ',2500,2500'))
        self.assertTrue(validate(self.snapshots, self.audit, self.targets, train, validation, events, split)
                        ['split_membership_verified'])


if __name__ == "__main__":
    unittest.main()
