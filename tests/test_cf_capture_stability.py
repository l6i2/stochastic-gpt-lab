from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from controller.native_database_snapshots import Store
from tools.cf_capture_stability import PreparedStore, Profile, live_timing, sqlite_trial, reopening_observation, passive_snapshot
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

    def test_reopening_records_new_quote_once_across_epoch_and_boot(self):
        poll = dict(native_quote=dict(time_msc=100), read_start=dict(boot_id='A',monotonic_ns=1),
                    read_end=dict(boot_id='A',monotonic_ns=2),connected=True)
        ref = dict(capture_id='synthetic',record=1,checkpoint_epoch='old')
        state, event = reopening_observation(None,poll,ref)
        self.assertIsNone(event)
        unchanged, event = reopening_observation(state,poll,ref)
        self.assertEqual(unchanged,state)
        self.assertIsNone(event)
        newer = dict(poll,native_quote=dict(time_msc=200),read_end=dict(boot_id='B',monotonic_ns=1))
        state, event = reopening_observation(state,newer,dict(ref,record=5,checkpoint_epoch='new'))
        self.assertTrue(event['boot_changed'])
        self.assertTrue(event['checkpoint_epoch_changed'])
        self.assertFalse(event['bridge_allowed'])
        self.assertFalse(event['dataset_admitted'])
        self.assertIsNone(reopening_observation(state,newer,ref)[1])

    def test_future_mutation_does_not_change_atr_prefix_comparison(self):
        bars = [dict(high=3.,low=1.,close=2.) for _ in range(30)]
        rows = [dict(atr='2.0') for _ in bars]
        prefix = native_seed_diagnostic(bars[:16],rows[:16])
        for bar in bars[16:]:
            bar['high'] = 1e9
        full = native_seed_diagnostic(bars,rows)
        self.assertEqual(prefix['seed_hex'],full['seed_hex'])
        self.assertFalse([m for m in full['mismatches'] if m['index'] < 16])

    def test_reopening_journal_survives_watch_checkpoint_loss_without_duplicates(self):
        import json
        with TemporaryDirectory() as directory:
            root=Path(directory)
            base=root/'outputs/us30cash_m5_native_observations'
            folder=base/'synthetic'
            folder.mkdir(parents=True)
            (base/'current.json').write_text(json.dumps(dict(capture_id='synthetic')))
            db=sqlite3.connect(folder/'snapshots.sqlite3')
            db.execute('CREATE TABLE records(n INTEGER PRIMARY KEY,digest TEXT,body TEXT)')
            def append(index,stamp):
                poll=dict(kind='LIVE_LATEST_STATE_POLL',native_quote=dict(time_msc=stamp),
                    read_start=dict(boot_id='A',monotonic_ns=index*10),
                    read_end=dict(boot_id='A',monotonic_ns=index*10+1),
                    connected=True,connection_ns=0,identity_and_quote_ns=0)
                db.execute('INSERT INTO records VALUES(?,?,?)',(index,str(index),json.dumps(poll)))
                db.commit()
                quality=dict(status='PASS_INCREMENTAL_QUARANTINED',capture_id='synthetic',
                             records_verified=index+1,chain_head=str(index),epoch='e')
                (base/'quality_status.json').write_text(json.dumps(quality))
            append(0,100)
            passive_snapshot(root)
            armed=(base/'reopening_watch.json').read_bytes()
            append(1,200)
            passive_snapshot(root)
            first=json.loads((base/'reopening_watch.json').read_bytes())['evidence_sha256']
            (base/'reopening_watch.json').write_bytes(armed)
            append(2,300)
            passive_snapshot(root)
            self.assertEqual(len(list((base/'reopening_observations').glob('*.json'))),1)
            self.assertEqual(json.loads((base/'reopening_watch.json').read_bytes())['evidence_sha256'],first)
            db.close()
