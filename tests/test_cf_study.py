import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path
from controller.cf_study import admission, bridge_allowed, process_events


class CfStudyTests(unittest.TestCase):
    @staticmethod
    def pairs(missing=False):
        clock = dict(boot_id='synthetic',monotonic_ns=1,uptime_ms=1,host_utc_label='synthetic')
        observation = dict(tick_size='0.01',read_end=clock)
        events = [dict(kind='LIVE_LATEST_STATE_POLL',native_quote={'time_msc':600001},read_start=clock,read_end=clock)]
        for n in range(5):
            if missing and n == 2:
                continue
            events.append(dict(kind='DATABASE_SNAPSHOT_PAIR',frame_seconds=60,epoch='synthetic',
                assessment={'status':'VERIFIED_DATABASE_VIEW_ONLY'},
                native_bar=dict(time=300+n*60,open=100,high=102,low=99,close=101,tick_volume=2)))
        events.append(dict(kind='DATABASE_SNAPSHOT_PAIR',frame_seconds=300,epoch='synthetic',
            assessment={'status':'VERIFIED_DATABASE_VIEW_ONLY'},
            native_bar=dict(time=300,open=100,high=102,low=99,close=101,tick_volume=10),
            first_observation=observation,verification_observation=observation))
        return events

    def test_exact_five_minute_parity_and_offline_availability(self):
        state = {}
        events = process_events(state,self.pairs(),clock=lambda:dict(boot_id='synthetic',monotonic_ns=2))
        self.assertEqual(state['cf_features']['own_run_bars'],1)
        self.assertTrue(next(e for e in events if e['kind']=='CF_M1_M5_PARITY')['matched'])
        self.assertFalse(next(e for e in events if e['kind']=='CF_OFFLINE_AVAILABILITY')['physical_original_entry_availability_proven'])

    def test_missing_minute_does_not_count_or_fill(self):
        state = {}
        events = process_events(state,self.pairs(missing=True))
        self.assertEqual(state['cf_features']['own_run_bars'],0)
        self.assertEqual(len(state['cf_m1_cache']),4)
        self.assertFalse(next(e for e in events if e['kind']=='CF_M1_M5_PARITY')['matched'])

    def test_recovery_preserves_committed_features_and_failed_commit_is_atomic(self):
        from tools.cf_study_station import StudyStore
        from controller.native_database_snapshots import Store
        with TemporaryDirectory() as directory:
            path = Path(directory)/'test.sqlite3'
            store = StudyStore(path)
            store.commit(self.pairs())
            digest, count = store.head, store.count
            original = store.state
            with patch.object(Store,'commit',side_effect=RuntimeError('synthetic_disk_error')):
                with self.assertRaises(RuntimeError):
                    store.commit([dict(kind='OBSERVATION_INTERRUPTION')])
            self.assertIs(store.state,original)
            self.assertEqual(store.state['cf_features']['own_run_bars'],1)
            self.assertEqual((store.head,store.count),(digest,count))
            store.close()
            recovered = StudyStore(path)
            self.assertEqual(recovered.state['cf_features']['own_run_bars'],1)
            self.assertEqual((recovered.head,recovered.count),(digest,count))
            recovered.close()

    def test_all_admission_states_and_no_training_permission(self):
        complete = dict(contract_approved=True, independence=True, nonoverlap=True,
            calendar=True, coverage=True, causality=True, seeds=True,
            warmup=350, signals=800, post_bars=100, evaluable=200, BUY=80, SELL=80,
            BUY_folds=3, SELL_folds=3, sealed_membership_hash='synthetic', dataset_hash='synthetic')
        for change, expected in [({},'PASS'),({'warmup':349},'WAITING_FOR_DATA'),
                ({'nonoverlap':False},'WAITING_FOR_EVIDENCE'),({'contract_approved':False},'WAITING_FOR_AUTHORIZATION'),
                ({'integrity_failure':True},'FAIL'),({'trading_allowed':True},'FAIL')]:
            result = admission(dict(complete, **change))
            self.assertEqual(result['NEW_STUDY_DATASET_ADMISSION'], expected)
            self.assertFalse(result['training_authorized'])

    def test_bridge_requires_all_evidence_and_continuous_connection(self):
        proof = dict(identity_verified=True, calendar_current=True, exception_attested=True,
            continuous_connected_observation=True, no_sleep=True, coverage_verified=True,
            server='XMGlobalSC-MT5 5',symbol='US30Cash',from_native_msc=300000,to_native_msc=3900000)
        health = dict(same_boot=True,monotonic=True,connected=True,no_sleep=True,poll_gap_ms=2000)
        self.assertTrue(bridge_allowed(proof,300000,3900000,health))
        for key in ('calendar_current','exception_attested','coverage_verified'):
            self.assertFalse(bridge_allowed(dict(proof, **{key:False}),300000,3900000,health))
        for key in ('same_boot','connected','no_sleep'):
            self.assertFalse(bridge_allowed(proof,300000,3900000,dict(health,**{key:False})))
        self.assertFalse(bridge_allowed(proof,300000,3900000,dict(health,poll_gap_ms=10001)))

    def test_first_observation_is_preserved_and_interruption_resets_context(self):
        state = {}
        event = dict(kind='LIVE_LATEST_STATE_POLL',native_quote={'time_msc':1},read_start={'n':1},read_end={'n':2})
        process_events(state,[event])
        first = state['cf_first_observation'].copy()
        state['cf_features']['own_run_bars'] = 349
        process_events(state,[dict(kind='OBSERVATION_INTERRUPTION'),event])
        self.assertEqual(state['cf_features']['own_run_bars'],0)
        self.assertEqual(state['cf_first_observation'],first)


if __name__ == '__main__':
    unittest.main()
