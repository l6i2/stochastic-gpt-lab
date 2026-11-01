import unittest
from unittest.mock import Mock,patch
from tools.prospective_pipeline import read_collector_status


class StatusReadRetryTests(unittest.TestCase):
    def test_transient_access_error_retries_same_status_only(self):
        path=Mock();path.read_text.side_effect=[PermissionError(),PermissionError(),'{"status":"ACTIVE_QUARANTINED"}']
        with patch('tools.prospective_pipeline.time.sleep') as sleep:
            self.assertEqual(read_collector_status(path)['status'],'ACTIVE_QUARANTINED')
        self.assertEqual(path.read_text.call_count,3);self.assertEqual(sleep.call_count,2)

    def test_persistent_access_error_remains_fail_closed(self):
        path=Mock();path.read_text.side_effect=PermissionError()
        with patch('tools.prospective_pipeline.time.sleep'),self.assertRaises(PermissionError):read_collector_status(path)
        self.assertEqual(path.read_text.call_count,5)

    def test_malformed_or_missing_file_never_becomes_cached_pass(self):
        path=Mock();path.read_text.return_value='not json'
        with self.assertRaises(ValueError):read_collector_status(path)
        path.read_text.side_effect=FileNotFoundError()
        with self.assertRaises(FileNotFoundError):read_collector_status(path)


if __name__=='__main__':unittest.main()
