import unittest

from python.quote_replay import Quote, Decision, replay


class ReplayTests(unittest.TestCase):
    def run_path(self, quotes, side=1, decisions=()):
        return replay(quotes, side, decisions, allowed_end_exclusive=10000, coverage_verified=True)

    def test_fill_uses_first_strictly_post_decision_quote_and_spread(self):
        quotes = [Quote(10, 0, 0, 100, 102), Quote(20, 1, 0, 110, 112),
                  Quote(20, 2, 0, 111, 113), Quote(21, 3, 0, 108, 111)]
        decision = [Decision(20, 20, 20, 'EXIT')]
        buy = self.run_path(quotes, decisions=decision)
        sell = self.run_path(quotes, side=-1, decisions=decision)
        self.assertEqual((buy['exit_time_msc'], buy['pnl']), (21, 6))
        self.assertEqual(sell['pnl'], -11)

    def test_baseline_gap_stop_and_fixed_tp(self):
        self.assertEqual(self.run_path([Quote(1, 0, 0, 100, 102),
                                       Quote(2, 1, 0, 1, 2)])['status'], 'CENSORED')
        stopped = self.run_path([Quote(1, 0, 0, 1000, 1002), Quote(2, 1, 0, 700, 702)])
        self.assertEqual((stopped['reason'], stopped['pnl']), ('SL', -302))
        profit = self.run_path([Quote(1, 0, 0, 1000, 1002), Quote(2, 1, 0, 1400, 1402)])
        self.assertEqual((profit['reason'], profit['pnl']), ('TP', 240))

    def test_barrier_precedes_time_and_discretionary_exit(self):
        quotes = [Quote(i+1, i, i, 1000, 1002) for i in range(100)]
        quotes.append(Quote(101, 100, 100, 700, 702))
        result = self.run_path(quotes, decisions=[Decision(100, 100, 100, 'EXIT')])
        self.assertEqual(result['reason'], 'SL')
        quotes[-1] = Quote(101, 100, 100, 1000, 1002)
        self.assertEqual(self.run_path(quotes)['reason'], 'TIME_EXIT')

    def test_future_quotes_do_not_change_prior_exit(self):
        prefix = [Quote(1, 0, 0, 1000, 1002), Quote(2, 1, 0, 1003, 1005)]
        decision = [Decision(1, 1, 1, 'EXIT')]
        first = self.run_path(prefix + [Quote(3, 2, 0, 900, 902)], decisions=decision)
        second = self.run_path(prefix + [Quote(3, 2, 0, 1300, 1302)], decisions=decision)
        self.assertEqual(first, second)

    def test_missing_coverage_future_feature_and_protected_quote_rejected(self):
        quotes = [Quote(1, 0, 0, 1000, 1002)]
        with self.assertRaisesRegex(ValueError, 'coverage'):
            replay(quotes, 1, allowed_end_exclusive=100)
        with self.assertRaisesRegex(ValueError, 'Noncausal'):
            self.run_path(quotes, decisions=[Decision(1, 2, 1, 'EXIT')])
        with self.assertRaisesRegex(ValueError, 'protected'):
            replay(quotes, 1, allowed_end_exclusive=1, coverage_verified=True)
        with self.assertRaisesRegex(ValueError, 'sequence'):
            self.run_path(quotes + quotes)
        with self.assertRaisesRegex(ValueError, 'Reversal'):
            self.run_path(quotes, decisions=[Decision(1, 1, 1, 'REVERSE')])
