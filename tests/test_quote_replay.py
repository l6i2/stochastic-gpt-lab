import unittest

import numpy as np

from python.quote_replay import Quote, Decision, replay, replay_memmap_window
from python.validate_bar_path import QUOTE_DTYPE, baseline


class ReplayTests(unittest.TestCase):
    def test_memmap_window_matches_hold_and_obeys_arrival_latency(self):
        tape = np.array([
            (1000, 100.0, 101.0, 0),
            (1500, 100.5, 101.5, 0),
            (2000, 101.0, 102.0, 1),
            (2500, 342.0, 343.0, 1),
        ], dtype=QUOTE_DTYPE)
        hold = replay_memmap_window(tape, 0, 3, 1, allowed_end_exclusive=5000,
                                    coverage_verified=True)
        expected = baseline(tape, 0, 3, 1)
        self.assertEqual((hold['reason'], hold['exit_sequence'], hold['pnl']),
                         (expected['reason'], expected['exit_index'], expected['pnl']))

        immediate = Decision(1200, 1200, 1200, 'EXIT', available_sequence=1)
        result = replay_memmap_window(tape, 0, 3, 1, decision=immediate,
                                      allowed_end_exclusive=5000, coverage_verified=True)
        self.assertEqual((result['reason'], result['exit_sequence'], result['pnl']),
                         ('POLICY_EXIT', 2, 0.0))

        delayed = Decision(1200, 1200, 1200, 'EXIT', available_sequence=1, latency_msc=1000)
        result = replay_memmap_window(tape, 0, 3, 1, decision=delayed,
                                      allowed_end_exclusive=5000, coverage_verified=True)
        self.assertEqual((result['reason'], result['exit_sequence']), ('TP', 3))

    def test_memmap_window_rejects_future_feature_and_protected_end(self):
        tape = np.array([(1000, 100.0, 101.0, 0), (1500, 100.5, 101.5, 0),
                         (2000, 101.0, 102.0, 1)], dtype=QUOTE_DTYPE)
        bad = Decision(1200, 1201, 1200, 'EXIT', available_sequence=1)
        with self.assertRaisesRegex(ValueError, 'noncausal'):
            replay_memmap_window(tape, 0, 2, 1, decision=bad,
                                 allowed_end_exclusive=3000, coverage_verified=True)
        with self.assertRaisesRegex(ValueError, 'Protected boundary'):
            replay_memmap_window(tape, 0, 2, 1, allowed_end_exclusive=2000,
                                 coverage_verified=True)

    def test_production_decision_waits_for_a_later_quote_and_latency(self):
        quotes=[Quote(1,0,0,1000,1002),Quote(2,1,0,1003,1005),
                Quote(2,2,0,1008,1010),Quote(8,3,0,1010,1012)]
        decision=Decision(1,1,1,'EXIT',available_sequence=1)
        self.assertEqual(self.run_path(quotes,decisions=[decision])['exit_sequence'],2)
        delayed=Decision(1,1,1,'EXIT',available_sequence=1,latency_msc=5)
        self.assertEqual(self.run_path(quotes,decisions=[delayed])['exit_sequence'],3)

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
