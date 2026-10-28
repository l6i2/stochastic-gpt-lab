"""Archive safety, multiplicity, restart, and corruption checks with fake quotes."""
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest

spec = importlib.util.spec_from_file_location('raw_archive', Path(__file__).resolve().parents[1] / 'python/pc_a_raw_archive.py')
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)


def tick(ms):
    return dict(time=ms // 1000, time_msc=ms, bid=1., ask=2., last=0., volume=0, volume_real=0., flags=6)


class Fake:
    COPY_TICKS_ALL = 0
    TIMEFRAME_M5 = 5
    latest = 1200000
    fail = False

    def symbol_info_tick(self, symbol):
        return types.SimpleNamespace(time_msc=self.latest)

    def copy_ticks_range(self, symbol, start, end, flags):
        if self.fail:
            return None
        a, b = int(start.timestamp() * 1000), int(end.timestamp() * 1000)
        return [tick(ms) for ms in (600000, 600001, 600001, 600002, 900000, 1199999) if a <= ms <= b]

    def copy_rates_range(self, *args):
        return []


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.manifest = archive.new_manifest('prospective', 'test', 600001)
        archive.atomic(self.folder / 'manifest.json', self.manifest)

    def test_no_backfill_multiplicity_and_idempotent_restart(self):
        first = archive.collect(self.folder, Fake(), 'test')
        self.assertEqual(first['segments'][0]['ticks']['rows'], 5)
        self.assertEqual(first['segments'][0]['start_native_msc'], 600001)
        second = archive.collect(self.folder, Fake(), 'test')
        self.assertEqual(first, second)
        self.assertFalse(second['maturity_eligible'])
        self.assertFalse(second['scientific_acceptance'])

    def test_failed_query_never_advances_checkpoint(self):
        api = Fake(); api.fail = True
        with self.assertRaisesRegex(RuntimeError, 'QUERY_FAILED'):
            archive.collect(self.folder, api, 'test')
        self.assertEqual(archive.verify(self.folder)['next_native_msc'], 600001)

    def test_detects_file_and_chain_corruption(self):
        state = archive.collect(self.folder, Fake(), 'test')
        path = self.folder / state['segments'][0]['ticks']['file']
        path.write_bytes(b'corrupt')
        with self.assertRaisesRegex(RuntimeError, 'TAMPERED'):
            archive.verify(self.folder)

    def test_server_change_and_clock_regression_stop(self):
        with self.assertRaisesRegex(RuntimeError, 'SERVER_CHANGED'):
            archive.collect(self.folder, Fake(), 'different')
        api = Fake(); api.latest = 100
        with self.assertRaisesRegex(RuntimeError, 'REGRESSION'):
            archive.collect(self.folder, api, 'test')

    def test_gates_cannot_be_enabled(self):
        self.manifest['train_access_allowed'] = True
        archive.atomic(self.folder / 'manifest.json', self.manifest)
        with self.assertRaisesRegex(RuntimeError, 'GATE_TAMPERED'):
            archive.verify(self.folder)

    def test_orphan_after_crash_is_not_adopted(self):
        (self.folder / 'orphan_ticks.csv.gz').write_bytes(b'uncommitted')
        self.assertEqual(archive.verify(self.folder)['segments'], [])
        self.assertEqual(len(archive.collect(self.folder, Fake(), 'test')['segments']), 1)

    def test_non_native_query_response_is_rejected(self):
        api = Fake()
        api.copy_ticks_range = lambda *args: [tick(99999999)]
        with self.assertRaisesRegex(RuntimeError, 'ROUNDTRIP'):
            archive.collect(self.folder, api, 'test')

    def test_bar_cursor_preserves_complete_bar_across_tick_windows(self):
        api = Fake()
        bar = dict(time=900, open=1., high=2., low=1., close=2., tick_volume=1, spread=1, real_volume=0)
        api.copy_rates_range = lambda *args: [bar]
        api.latest = 1000000
        first = archive.collect(self.folder, api, 'test')
        self.assertEqual(sum(s['bars']['rows'] for s in first['segments']), 0)
        api.latest = 1200000
        second = archive.collect(self.folder, api, 'test')
        self.assertEqual(sum(s['bars']['rows'] for s in second['segments']), 1)
        self.assertEqual(second['next_bar_native_msc'], 1200000)

    def test_query_cap_rejects_potential_truncation(self):
        api = Fake()
        api.copy_ticks_range = lambda *args: [tick(600001)] * archive.MAX_ROWS
        with self.assertRaisesRegex(RuntimeError, 'TOO_LARGE'):
            archive.collect(self.folder, api, 'test')


if __name__ == '__main__':
    unittest.main()
