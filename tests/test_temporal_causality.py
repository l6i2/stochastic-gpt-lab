from datetime import datetime,timedelta,timezone
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from temporal_causality import utc_milliseconds,validate_decision_times,validate_execution_times
from runtime_session_guard import eu_expected_offset_seconds


class TemporalCausalityTests(unittest.TestCase):
    def test_equality_is_allowed_and_one_millisecond_future_is_rejected(self):
        for feature,quote,expected in ((10000,10000,'TEMPORAL_CAUSALITY_PASS'),(10001,10000,'FEATURE_LOOKAHEAD'),(10000,10001,'FUTURE_QUOTE'),(10000,4999,'STALE_QUOTE'),(10000,5000,'TEMPORAL_CAUSALITY_PASS')):
            with self.subTest(feature=feature,quote=quote):
                self.assertEqual(validate_decision_times(feature_max_time_msc=feature,decision_time_msc=10000,quote_time_msc=quote)[1],expected)

    def test_explicit_local_server_offsets_normalize_same_instant_without_guessing(self):
        utc=datetime(2026,10,23,10,0,0,123000,tzinfo=timezone.utc)
        for offset in (-6,-5,2,3):
            wall=utc.astimezone(timezone(timedelta(hours=offset)))
            self.assertEqual(utc_milliseconds(wall),utc_milliseconds(utc))
        with self.assertRaises(ValueError):utc_milliseconds(utc.replace(tzinfo=None))
        self.assertEqual(utc_milliseconds(utc+timedelta(milliseconds=1))-utc_milliseconds(utc),1)

    def test_dst_does_not_reorder_utc_or_millisecond_causality(self):
        for before in (datetime(2026,3,29,0,59,59,999000,tzinfo=timezone.utc),datetime(2026,10,25,0,59,59,999000,tzinfo=timezone.utc)):
            after=before+timedelta(milliseconds=1)
            self.assertNotEqual(eu_expected_offset_seconds(before),eu_expected_offset_seconds(after))
            self.assertEqual(utc_milliseconds(after)-utc_milliseconds(before),1)
            self.assertFalse(validate_decision_times(feature_max_time_msc=utc_milliseconds(after),decision_time_msc=utc_milliseconds(before),quote_time_msc=utc_milliseconds(before))[0])

    def test_replay_fill_uses_later_sequence_and_latency_not_live_quote_rule(self):
        params=dict(decision_cutoff_msc=999,arrival_time_msc=1000,arrival_sequence=10,fill_time_msc=1000,fill_sequence=11,latency_msc=0)
        self.assertTrue(validate_execution_times(**params)[0])
        for changes,reason in (({'arrival_time_msc':999},'ARRIVAL_NOT_AFTER_CUTOFF'),({'fill_sequence':10},'FILL_NOT_AFTER_ARRIVAL_SEQUENCE'),({'latency_msc':1},'FILL_BEFORE_LATENCY')):
            self.assertEqual(validate_execution_times(**{**params,**changes})[1],reason)
        self.assertTrue(validate_execution_times(**{**params,'fill_time_msc':1250,'latency_msc':250})[0])
