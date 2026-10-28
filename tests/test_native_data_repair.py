import sys
from pathlib import Path
import json
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from native_m5_rebuild import rebuild, compare, price_units
from native_metadata_v3 import main_k
from main_k_native_parity import fixtures
from causal_metadata_audit import main_values


def tick(ms, bid=1.):
    return dict(time=ms // 1000, time_msc=ms, bid=bid, ask=bid + 0.01, flags=6)


class NativeRepairTests(unittest.TestCase):
    def test_empty_buckets_not_fabricated_and_duplicates_count(self):
        rows = [tick(0), tick(0), tick(100, 1.02), tick(600000, 1.03)]
        result = rebuild(rows, start_msc=0, end_msc=900000, tick_size='.01')
        self.assertEqual([r['time'] for r in result['bars']], [0, 600])
        self.assertEqual(result['bars'][0]['tick_volume'], 3)
        self.assertEqual(result['empty_buckets_filled'], 0)

    def test_partial_edges_excluded(self):
        result = rebuild([tick(100), tick(300000), tick(600001)], start_msc=100, end_msc=600002, tick_size='.01')
        self.assertEqual([r['time'] for r in result['bars']], [300])

    def test_price_grid_and_invalid_quotes_rejected(self):
        with self.assertRaises(ValueError): price_units(1.005, '.01')
        with self.assertRaises(ValueError): price_units('NaN', '.01')
        with self.assertRaises(ValueError): rebuild([tick(200), tick(100)], start_msc=0, end_msc=300000, tick_size='.01')

    def test_exact_native_comparison_and_volume_mismatch(self):
        data = rebuild([tick(0)], start_msc=0, end_msc=300000, tick_size='.01')['bars']
        native = [dict(time=0, open=1, high=1, low=1, close=1, tick_volume=1)]
        self.assertTrue(compare(data, native, '.01')['status'].startswith('PASS'))
        native[0]['tick_volume'] = 2
        self.assertEqual(compare(data, native, '.01')['differences'][0]['fields'], ['tick_volume'])
        self.assertFalse(compare([], [], '.01')['status'].startswith('PASS'))

    def test_metadata_five_families_match_independent_native_oracle(self):
        for name, rows in fixtures().items():
            with self.subTest(family=name):
                actual = list(main_k(rows))
                expected = main_values(rows, native_reference=True)
                for a, b in zip(actual, expected):
                    if b is None: self.assertIsNone(a)
                    else: self.assertLessEqual(abs(a - b), 1e-10)

    def test_metadata_stream_is_prefix_causal(self):
        rows = fixtures()['trend']
        self.assertEqual(list(main_k(rows[:80])), list(main_k(rows))[:80])
        self.assertEqual(list(main_k([dict(open=1, high=1, low=1, close=1)] * 7))[-1], 100.)

    def test_ask_only_quotes_do_not_invent_bid_volume_or_bars(self):
        ask = tick(300000); ask['flags'] = 4
        result = rebuild([tick(0), ask], start_msc=0, end_msc=600000, tick_size='.01')
        self.assertEqual(len(result['bars']), 1)
        self.assertEqual(result['ticks_read'], 2)

    def test_future_ticks_do_not_change_completed_prior_bar(self):
        first = rebuild([tick(0), tick(100, 1.02)], start_msc=0, end_msc=300000, tick_size='.01')
        second = rebuild([tick(0), tick(100, 1.02), tick(300000, 99.)], start_msc=0, end_msc=600000, tick_size='.01')
        self.assertEqual(first['bars'][0], second['bars'][0])

    def test_prepared_metadata_keeps_frozen_thresholds_sessions_and_access(self):
        root = Path(__file__).resolve().parents[1]
        old = json.loads((root / 'configs/future_cohort_metadata_spec_v2.prepared.json').read_text())
        new = json.loads((root / 'configs/future_cohort_metadata_spec_v3.prepared.json').read_text())
        for key in ('access', 'causal_regimes', 'sessions', 'quality', 'purpose', 'correction_scope'):
            self.assertEqual(old[key], new[key])
        for key in ('BUY', 'SELL', 'bar_time', 'outputs', 'symbol', 'timeframe'):
            self.assertEqual(old['signal_contract'][key], new['signal_contract'][key])
        self.assertFalse(new['native_adapter']['activation_allowed'])


if __name__ == '__main__': unittest.main()
