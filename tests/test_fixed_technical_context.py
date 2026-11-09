import unittest

from tools.audit_fixed_technical_context import closed_context


class ClosedContextTests(unittest.TestCase):
    def test_bucket_is_visible_only_after_close(self):
        bar = dict(open=1, close=2, high=3, low=0)
        bars = {stamp: bar for stamp in (900, 1200, 1500)}
        self.assertIsNone(closed_context(bars, 1799999, 900))
        self.assertEqual(closed_context(bars, 1800000, 900)['available_native_msc'], 1800000)

    def test_rejects_missing_constituent(self):
        bar = dict(open=1, close=2, high=3, low=0)
        self.assertIsNone(closed_context({900: bar, 1500: bar}, 1800000, 900))

    def test_future_bar_mutation_does_not_change_context(self):
        bar = dict(open=1, close=2, high=3, low=0)
        bars = {stamp: bar for stamp in (900, 1200, 1500, 1800)}
        before = closed_context(bars, 1800123, 900)
        bars[1800] = dict(open=3, close=9, high=10, low=-1)
        self.assertEqual(before, closed_context(bars, 1800123, 900))
