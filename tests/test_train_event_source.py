import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from train_event_source import assert_train_only_source_path, read_events_for_ids
import evaluate_train_intratrade_round2_wf as train_wf
import explore_train_intratrade_exits as train_exits
import explore_train_intratrade_round2 as train_round


class TrainEventSourceTests(unittest.TestCase):
    def test_stream_retains_only_frozen_train_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.csv"
            path.write_text("signal_id,follow_PnL\ntrain-a,1\nvalidation-secret,999999\ntrain-b,-2\n", encoding="utf-8")
            result = read_events_for_ids(path, ["signal_id", "follow_PnL"], {"train-a", "train-b"}, chunksize=1)
            self.assertEqual(set(result.signal_id), {"train-a", "train-b"})
            self.assertEqual(set(result.follow_PnL), {1, -2})

    def test_missing_or_duplicate_train_ids_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.csv"
            path.write_text("signal_id,follow_PnL\ntrain-a,1\ntrain-a,2\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_events_for_ids(path, ["signal_id", "follow_PnL"], {"train-a", "train-b"}, chunksize=1)

    def test_validation_path_is_rejected_before_csv_is_opened(self):
        path = Path("outputs/splits/DISCOVERY_VALIDATION.parquet")
        with patch("train_event_source.pd.read_csv") as read_csv:
            with self.assertRaisesRegex(ValueError, "protected split path"):
                read_events_for_ids(path, ["signal_id", "follow_PnL"], {"train-a"})
            read_csv.assert_not_called()

    def test_validation_directory_and_final_test_names_are_rejected(self):
        for path in (Path("outputs/validation/events.csv"),
                     Path("outputs/splits/final_test.parquet"),
                     Path("outputs/discovery-validation/rows.csv")):
            with self.subTest(path=path), self.assertRaises(ValueError):
                assert_train_only_source_path(path)

    def test_combined_source_is_allowed_but_only_frozen_train_ids_are_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stochastic_events.csv"
            path.write_text("signal_id,follow_PnL\ntrain-a,1\nvalidation-b,999999\n", encoding="utf-8")
            result = read_events_for_ids(path, ["signal_id", "follow_PnL"], {"train-a"}, chunksize=1)
            self.assertEqual(result.signal_id.tolist(), ["train-a"])

    def test_train_runner_entrypoints_refuse_validation_root_before_data_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "DISCOVERY_VALIDATION"
            with patch("pandas.read_csv") as read_csv, patch("pandas.read_parquet") as read_parquet:
                with self.assertRaises(ValueError):
                    train_exits.run(root, output=root / "replay.json")
                with self.assertRaises(ValueError):
                    train_round.run(root, output=root / "replay.json")
                with self.assertRaises(ValueError):
                    train_wf.evaluate(root, output=root / "walkforward.json")
                read_csv.assert_not_called()
                read_parquet.assert_not_called()


if __name__ == "__main__":
    unittest.main()
