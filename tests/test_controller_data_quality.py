import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from controller.data_quality import summarize_snapshots, tick_warnings
from controller.progress import last_event_time


class QualityTests(unittest.TestCase):
    def test_progress_ignores_partial_rows_and_locked_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'events.csv'
            path.write_text('signal_id,signal_time_msc\na,1000\nb,2000\nc,30')
            self.assertEqual(last_event_time(path), 2000)
            with patch.object(Path, 'open', side_effect=PermissionError):
                self.assertIsNone(last_event_time(path))

    def test_streaming_counts_missing_and_duplicate_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'snapshots.csv'
            path.write_text('snapshot_id,snapshot_bar,session,original_signal,virtual_mode,ATR\n'
                            'a,1,Asia,BUY,FOLLOW,2\na,1,Asia,BUY,FOLLOW,4\n'
                            'b,2,London,SELL,INVERT,\n')
            result = summarize_snapshots(path)
            self.assertEqual(result['duplicate_ids'], 1)
            self.assertEqual(result['statistics']['ATR']['mean'], 3)
            self.assertEqual(result['missing']['ATR']['n'], 1)
            self.assertEqual(result['counts']['session']['Asia'], 2)

    def test_tick_warning_absence_does_not_assert_zero_substitution(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            result = tick_warnings(folder)
            self.assertIsNone(result['generated_tick_substitution_count'])
            (folder/'tester.log').write_text('183 minutes real ticks discarded\n'
                                            'real ticks discarded for 1230 minutes of 9635 total minute bars\n')
            result = tick_warnings(folder)
            self.assertEqual(result['severity'], 'HIGH')
            self.assertEqual(result['discarded_minute_counts_reported'], [183, 1230])
