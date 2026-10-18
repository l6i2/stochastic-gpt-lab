import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from train_event_source import read_events_for_ids


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


if __name__ == "__main__":
    unittest.main()
