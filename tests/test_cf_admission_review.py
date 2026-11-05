import copy
import unittest
from controller.cf_admission_review import bind_packet,review,no_grant_rejection,from_operational_receipt
from controller.pretrain_contracts import FEATURES


class CfAdmissionRehearsalTests(unittest.TestCase):
    def complete(self):
        identity=dict(study_id='synthetic',dataset_id='synthetic02',producer_id='syntheticC',server='XMGlobalSC-MT5 5',symbol='US30Cash',terminal_trade_allowed=False,receipt_verified=True)
        interval=dict(**{k:identity[k] for k in ('study_id','dataset_id','producer_id')},start_native_msc=600000,end_native_exclusive_msc=900000,origin='POST_CUTOFF_NATIVE_DATABASE_SNAPSHOT',backfill=False,first_observation_post_cut_verified=True)
        return dict(identity=identity,membership=dict(exclusive_verified=True,minimum_native_open_msc=600000,intervals=[interval]),
            coverage=dict(complete=True,five_own_m1=True,ohlc_exact=True,volume_exact=True,two_views_equal=True,bid_ask_preserved=True),
            features=dict(whitelist=list(FEATURES),complete=True,availability=[dict(feature_max_native_msc=899999,decision_native_msc=900000,ready_clock=dict(boot_id='synthetic',monotonic_ns=2),offline_use_clock=dict(boot_id='synthetic',monotonic_ns=3))]),
            seeds=dict(own_post_cut=True,ha_count=350,atr_count=350,native_atr_parity=True),calendar=dict(applicable_verified=True,bridges=[]),
            maturity=dict(warmup=350,signals=800,post_bars=100,evaluable=200,BUY=80,SELL=80,BUY_folds=3,SELL_folds=3,dataset_hash='synthetic',sealed_membership_hash='synthetic'))

    def test_complete_synthetic_packet_never_admits_or_trains(self):
        r=review(bind_packet(self.complete()))
        self.assertEqual(r['REHEARSAL_STATUS'],'CHECKS_SATISFIED_DRY_RUN_ONLY')
        self.assertFalse(r['dataset_admitted']);self.assertFalse(r['TRAINING_EXECUTED'])

    def test_altered_hash_rejected(self):
        p=bind_packet(self.complete());p['artifacts']['maturity']['warmup']=351
        self.assertIn('HASH_CHANGED:maturity',review(p)['rejection_reasons'])

    def test_retroactive_import_wrong_membership_overlap_and_precut_rejected(self):
        for kind in ('backfill','wrong_id','overlap','precut'):
            a=self.complete();row=a['membership']['intervals'][0]
            if kind=='backfill':row['backfill']=True
            elif kind=='wrong_id':row['dataset_id']='old'
            elif kind=='overlap':a['membership']['intervals'].append(copy.deepcopy(row))
            else:row.update(start_native_msc=300000,end_native_exclusive_msc=600000)
            self.assertEqual(review(bind_packet(a))['REHEARSAL_STATUS'],'REJECTED',kind)

    def test_bridge_without_calendar_is_rejected(self):
        a=self.complete();a['calendar']['bridges']=[dict(proof={},before=900000,after=4500000,health={})]
        self.assertIn('UNCERTIFIED_SESSION_BRIDGE',review(bind_packet(a))['rejection_reasons'])

    def test_incomplete_seeds_and_immature_dataset_cannot_pass(self):
        for section,key,value in [('seeds','ha_count',349),('seeds','native_atr_parity',False),('maturity','BUY',79),('maturity','signals',799),('coverage','five_own_m1',False)]:
            a=self.complete();a[section][key]=value
            self.assertEqual(review(bind_packet(a))['REHEARSAL_STATUS'],'NOT_READY')

    def test_native_and_physical_offline_leakage_rejected(self):
        a=self.complete();a['features']['availability'][0]['feature_max_native_msc']=900001
        self.assertIn('NATIVE_FEATURE_LEAKAGE',review(bind_packet(a))['rejection_reasons'])
        a=self.complete();a['features']['availability'][0]['ready_clock']['monotonic_ns']=4
        self.assertIn('FEATURE_NOT_READY_BEFORE_OFFLINE_USE',review(bind_packet(a))['rejection_reasons'])

    def test_absent_grant_rejected_before_any_file_access(self):
        self.assertTrue(no_grant_rejection()['rejected'])

    def test_unknown_real_evidence_is_not_invented(self):
        packet=from_operational_receipt(dict(study_id='s',dataset_id='d',producer_id='p',native_membership=[],technical_consecutive_m5=2))
        self.assertEqual(review(packet)['REHEARSAL_STATUS'],'NOT_READY')
        self.assertIn('OWN_SEEDS_AND_ATR_EVIDENCE',review(packet)['pending_evidence'])

    def test_malformed_packet_fails_closed(self):
        self.assertEqual(review({})['REHEARSAL_STATUS'],'REJECTED')


if __name__=='__main__':unittest.main()
