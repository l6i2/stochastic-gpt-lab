import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from volume_forensics import compare_quotes


def row(ms, flags=6):
    return dict(time=ms//1000, time_msc=ms, bid=1., ask=1.01, last=0., volume=0, volume_real=0., flags=flags)


class VolumeForensicsTests(unittest.TestCase):
    def test_missing_payload_multiplicity_is_coverage_failure(self):
        result = compare_quotes([row(1000)], [row(1000), row(1000)], 2)
        self.assertEqual(result['added_payload_multiplicity'], 1)
        self.assertTrue(result['coverage_affected'])
        self.assertFalse(result['event_causality_proven'])

    def test_bar_tick_inconsistency_is_not_hidden_by_undercoverage(self):
        result = compare_quotes([row(1000)], [row(1000), row(1100)], 3)
        self.assertEqual(result['remaining_native_bar_tick_difference'], 1)
        self.assertFalse(result['native_bar_tick_reference_consistent'])

    def test_revision_and_flag_only_changes_are_distinguished(self):
        revised = compare_quotes([row(1000)], [row(1100)], 1)
        self.assertIn('REVISION', revised['classification'])
        flags = compare_quotes([row(1000, 1254)], [row(1000, 1126)], 1)
        self.assertFalse(flags['flag_sensitive_equal'])
        self.assertFalse(flags['coverage_affected'])

    def test_csv_numeric_spelling_does_not_invent_revision(self):
        first = row(1000)
        csv = {k:str(v) for k,v in first.items()}
        self.assertEqual(compare_quotes([first], [csv], 1)['added_payload_multiplicity'], 0)


if __name__ == '__main__': unittest.main()
