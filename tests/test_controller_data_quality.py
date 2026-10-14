import tempfile
import unittest
from pathlib import Path

from controller.data_quality import summarize_snapshots, tick_warnings


class QualityTests(unittest.TestCase):
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
            (folder/'tester.log').write_text('183 minutes real ticks discarded\n')
            result = tick_warnings(folder)
            self.assertEqual(result['severity'], 'HIGH')
            self.assertEqual(result['discarded_minute_counts_reported'], [183])
