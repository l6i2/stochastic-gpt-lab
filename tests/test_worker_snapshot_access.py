import unittest
from unittest.mock import Mock,patch
from tools.prospective_pipeline import read_snapshot_json


class SnapshotAccess(unittest.TestCase):
    def test_access_recovers_without_stale_fallback(self):
        p=Mock();p.read_text.side_effect=[PermissionError('sharing'),'{"rows":42}']
        with patch('tools.prospective_pipeline.time.sleep') as sleep:
            self.assertEqual(read_snapshot_json(p),{'rows':42});sleep.assert_called_once_with(.02)
        self.assertEqual(p.read_text.call_count,2)

    def test_permanent_denial_remains_fail_closed(self):
        p=Mock();p.read_text.side_effect=PermissionError('access')
        with patch('tools.prospective_pipeline.time.sleep') as sleep:
            with self.assertRaises(PermissionError):read_snapshot_json(p)
        self.assertEqual(p.read_text.call_count,5);self.assertEqual(sleep.call_count,4)

    def test_corruption_and_missing_file_are_not_hidden(self):
        for problem in ('{',FileNotFoundError('missing')):
            p=Mock()
            if isinstance(problem,Exception):p.read_text.side_effect=problem
            else:p.read_text.return_value=problem
            with patch('tools.prospective_pipeline.time.sleep') as sleep:
                with self.assertRaises((ValueError,FileNotFoundError)):read_snapshot_json(p)
                sleep.assert_not_called()


if __name__=='__main__':unittest.main()
