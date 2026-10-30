import unittest
from controller.pretrain_contracts import (FEATURES,chain,verify_chain,dependency_preflight,
    interval_disposition,preview_prospective_boundary,temporal_dependencies)


class PretrainContractsTests(unittest.TestCase):
    def feature_rows(self):
        return [dict(feature=f,oldest_source_index=100,last_closed_index=800,
                     decision_arrival_index=801,ready_stage=1,decision_stage=2,
                     closed_bars=350,seed_index=100) for f in FEATURES]

    def ledger(self,**changes):
        row=dict(instrument='US30Cash',domain_id='native_fixture',source_sha256='old',
                 signal_ids=['old_signal'],start_native_msc=100,end_native_exclusive_msc=200)
        entries=chain([row|changes])
        return dict(completeness_verified=True,entries=entries,chain_head=entries[-1]['entry_sha256'])

    def candidate(self,**changes):
        return dict(instrument='US30Cash',domain_id='native_fixture',source_sha256='new',
                    signal_ids=['new_signal'],dependency_start=200,label_end=400)|changes

    def test_hash_chain_detects_change_deletion_and_reordering(self):
        rows=chain([{'id':1},{'id':2}])
        self.assertEqual(verify_chain(rows),rows[-1]['entry_sha256'])
        for changed in ([rows[0]|{'id':3},rows[1]],rows[1:],list(reversed(rows))):
            with self.assertRaises(ValueError):verify_chain(changed)
        with self.assertRaises(ValueError):verify_chain(rows[:-1],rows[-1]['entry_sha256'])

    def test_every_model_feature_has_explicit_closed_or_seed_dependency(self):
        result=dependency_preflight(self.feature_rows(),100)
        self.assertFalse(result['real_feature_bytes_verified'])
        self.assertFalse(result['training_authorized'])
        defs={x['feature']:x for x in temporal_dependencies()['features']}
        self.assertEqual(len(defs['stoch_k']['bar_offsets']),7)
        self.assertEqual(len(defs['delta_k_1']['bar_offsets']),8)
        self.assertEqual(len(defs['relative_volume_20']['bar_offsets']),21)
        self.assertIsNone(defs['ATR']['bar_offsets'])
        self.assertTrue(defs['ha_direction']['full_seed_required'])

    def test_all_feature_warmup_and_availability_failures_rejected(self):
        for feature in FEATURES:
            for change in ({'oldest_source_index':99},{'last_closed_index':801},
                           {'decision_stage':0},{'closed_bars':19}):
                rows=self.feature_rows()
                rows[next(i for i,r in enumerate(rows) if r['feature']==feature)]|=change
                with self.assertRaises(ValueError):dependency_preflight(rows,100)
        for f in ('ATR','ha_direction','range_to_ATR'):
            rows=self.feature_rows();rows[next(i for i,r in enumerate(rows) if r['feature']==f)]['seed_index']=None
            with self.assertRaisesRegex(ValueError,'SEED'):dependency_preflight(rows,100)

    def test_complete_feature_set_and_ha_warmup_cannot_be_bypassed(self):
        with self.assertRaises(ValueError):dependency_preflight(self.feature_rows()[:-1],100)
        rows=self.feature_rows();rows[4]['closed_bars']=275
        with self.assertRaises(ValueError):dependency_preflight(rows,100)

    def test_redownload_signal_reuse_and_dependency_overlap_rejected(self):
        for c in (self.candidate(source_sha256='old'),self.candidate(signal_ids=['old_signal']),
                  self.candidate(dependency_start=199),self.candidate(dependency_start=50,label_end=100)):
            self.assertEqual(interval_disposition(c,self.ledger())['status'],'BLOCKED')
        self.assertFalse(interval_disposition(self.candidate(),self.ledger())['training_authorized'])

    def test_unknown_mapping_and_open_ended_reservations_fail_closed(self):
        for ledger in (self.ledger(domain_id='legacy_unverified'),self.ledger(end_native_exclusive_msc=None),
                       self.ledger(start_native_msc=None),self.ledger()|{'completeness_verified':False}):
            self.assertEqual(interval_disposition(self.candidate(),ledger)['status'],'BLOCKED')

    def test_prepared_boundary_cannot_activate_cohort_or_relabel_backfill(self):
        self.assertEqual(preview_prospective_boundary([],None)['status'],'INACTIVE_NO_REAL_START')
        boundary=dict(session_id='s',sequence=10,first_complete_bar_native_msc=300000)
        event=dict(session_id='s',sequence=11,native_bar_open_msc=300000,historical_requery=False,connected=True)
        result=preview_prospective_boundary([event],boundary)
        self.assertFalse(result['activation_performed'])
        self.assertFalse(result['training_authorized'])
        for change in ({'sequence':10},{'session_id':'restart'},{'historical_requery':True},{'connected':False}):
            with self.assertRaises(ValueError):preview_prospective_boundary([event|change],boundary)
        self.assertEqual(preview_prospective_boundary([event|{'native_bar_open_msc':0}],boundary)['eligible_sequences'],[])


if __name__=='__main__':unittest.main()
