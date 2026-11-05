from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from controller.native_database_snapshots import Store
from tools.cf_capture_stability import PreparedStore, Profile, live_timing, sqlite_trial
from tools.cf_own_indicator_oracle import native_seed_diagnostic


class CaptureStabilityTests(unittest.TestCase):
    def test_trial_matches_existing_writer_and_backpressure_is_visible(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)
            baseline=Store(path/'seed.sqlite3');state=baseline.state;baseline.close()
            report=sqlite_trial(path,dict(state=state,batches=[[dict(kind='SYNTHETIC_SAMPLE')]]))
            self.assertTrue(report['byte_equivalent_chain'])
            self.assertTrue(report['queue']['blocked_writer_saturates'])
            self.assertEqual(report['results']['prepared']['synchronous'],2)

    def test_prepared_writer_rolls_back_records_if_checkpoint_insert_fails(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'trial.sqlite3';store=PreparedStore(path);profile=Profile()
            store.commit_profiled([dict(kind='SYNTHETIC_COMMITTED')],profile)
            before=(store.count,store.head)
            store.db.execute("CREATE TEMP TRIGGER fail_checkpoint BEFORE INSERT ON state BEGIN SELECT RAISE(ABORT,'simulated'); END")
            with self.assertRaises(sqlite3.IntegrityError):
                store.commit_profiled([dict(kind='SYNTHETIC_UNCOMMITTED')],profile)
            store.close();reopened=Store(path)
            try:self.assertEqual((reopened.count,reopened.head),before)
            finally:reopened.close()

    def test_latency_keeps_long_intervals_and_does_not_mix_boot_clocks(self):
        polls=[dict(read_end=dict(boot_id=boot,monotonic_ns=ns),connection_ns=1,identity_and_quote_ns=2)
               for boot,ns in [('A',1),('A',11_000_000_001),('B',0)]]
        result=live_timing(dict(polls=polls,boundaries=[]))
        self.assertEqual(result['same_boot_intervals'],1)
        self.assertEqual(result['observed_spacing_over_10s'],1)
        self.assertEqual(result['long_observations'][0]['spacing_ns'],11_000_000_000)

    def test_explanatory_atr_seed_retains_exact_mismatch(self):
        bars=[dict(high=3.,low=1.,close=2.) for _ in range(16)]
        rows=[dict(atr='2.0') for _ in bars]
        self.assertEqual(native_seed_diagnostic(bars,rows)['mismatches'],[])
        rows[14]['atr']=(2.0+2.0**-51).hex()
        rows[14]['atr']=str(float.fromhex(rows[14]['atr']))
        result=native_seed_diagnostic(bars,rows)
        self.assertEqual(result['mismatches'][0]['index'],14)
        self.assertFalse(result['production_feature_modified'])
