import unittest
import json,tempfile,hashlib,platform
from pathlib import Path
from importlib.metadata import version
from unittest.mock import Mock,patch
from controller.training_admission_gate import authorize_execution,snapshot_gate,CHECKS,prepare_authorization_request
from controller.pretrain_contracts import seal
from controller.tick_discrepancy import reconcile
from tools.admitted_training import dispatch


class AdmissionGateTests(unittest.TestCase):
    def bundle(self,root):
        prefix='outputs/admitted_native_studies/test/'
        base=root/prefix;base.mkdir(parents=True)
        package=root/'research/studies/us30cash_m5_native_pretrain_v1';package.mkdir(parents=True)
        for name in ('PROTOCOL_ES.md','feature_model_whitelist.json'):(package/name).write_text('synthetic metadata')
        digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        grant={k:'a'*64 for k in ('dataset_hash','membership_hash','exposure_hash','admission_receipt_hash','environment_hash','plan_hash')}
        rows=[dict(signal_id=str(i),side='BUY' if i%2 else 'SELL',observed_bar_index=i) for i in range(200)]
        grant['dataset_hash']=seal(rows)
        grant.update(study_id='TEST',code_head='c'*40,row_schema='native-study-admitted-rows/1',
            protocol_hash=digest(package/'PROTOCOL_ES.md'),feature_whitelist_hash=digest(package/'feature_model_whitelist.json'),
            dataset_first_observed_bar=0,manifest_path=prefix+'manifest.json',max_fits=8)
        files={};receipts={}
        for key in ('membership_hash','exposure_hash','admission_receipt_hash','environment_hash'):
            p=base/(key+'.json')
            data={'python':platform.python_version(),'numpy':version('numpy'),'scikit-learn':version('scikit-learn')} if key=='environment_hash' else {'synthetic':True}
            p.write_text(json.dumps(data));grant[key]=digest(p);files[prefix+p.name]=digest(p);receipts[key]=prefix+p.name
        (base/'dataset.json').write_text(json.dumps(rows));files[prefix+'dataset.json']=digest(base/'dataset.json')
        m=dict(grant,dataset_last_observed_bar=1000,role='TRAIN_NEW_ADMITTED',quarantine=False,checks={k:True for k in CHECKS},
            maturity=dict(own_warmup=350,consecutive_signals=800,post_signal_bars=100,evaluable_total=200,BUY=80,SELL=80,BUY_folds=3,SELL_folds=3),
            account_mode='DEMO',live_trading=False,protected_sets=dict(DISCOVERY_VALIDATION='BLOCKED',HISTORICAL_HOLDOUT='LOCKED',FINAL_TEST='LOCKED'),
            files=files,receipts=receipts,dataset_path=prefix+'dataset.json')
        (base/'manifest.json').write_text(json.dumps(m));grant['manifest_sha256']=digest(base/'manifest.json')
        return grant,m

    def test_all_receipt_checks_on_synthetic_bundle_without_fit(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);grant,m=self.bundle(root)
            with patch('controller.training_admission_gate.AUTHORIZED_GRANT_HASHES',frozenset([seal(grant)])),patch('controller.training_admission_gate.subprocess.check_output',side_effect=lambda args,**kwargs:'' if args[1]=='status' else grant['code_head']):
                self.assertEqual(authorize_execution(grant,root)['study_id'],'TEST')
                (root/m['dataset_path']).write_text('changed')
                with self.assertRaisesRegex(ValueError,'HASH_CHANGED'):authorize_execution(grant,root)

    def test_signed_manifest_cannot_bypass_maturity_or_quarantine(self):
        for change in ({'quarantine':True},{'account_mode':'REAL'},{'maturity':{}},{'checks':{k:False for k in CHECKS}}):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);grant,m=self.bundle(root);m.update(change)
                p=root/grant['manifest_path'];p.write_text(json.dumps(m));grant['manifest_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
                with patch('controller.training_admission_gate.AUTHORIZED_GRANT_HASHES',frozenset([seal(grant)])):
                    with self.assertRaises(ValueError):authorize_execution(grant,root)

    def test_no_authorization_refuses_before_any_dataset_file_read(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('NO_IO')):
            for grant in ({},{'authorized':True},{'dataset_hash':'a'*64}):
                with self.assertRaises(PermissionError):authorize_execution(grant,'missing')
                with self.assertRaises(PermissionError):dispatch(grant)

    def test_real_unknown_accounts_hard_fail_even_if_counts_exist(self):
        for broker in ({},{'identity_verified':True,'demo':False},{'demo':True}):
            r=snapshot_gate(dict(dataset_hash='a'*64,admitted_records=800),broker)
            self.assertIn('REAL_OR_UNKNOWN_ACCOUNT_HARD_FAIL',r['reasons'])
            self.assertFalse(r['execution_permitted'])

    def test_quarantine_and_installed_code_do_not_allow_training(self):
        r=snapshot_gate(dict(dataset_hash=None,admitted_records=0),dict(identity_verified=True,demo=True))
        self.assertEqual(r['TRAINING_ADMISSION_GATE'],'BLOCKED')
        self.assertFalse(r['authorization_requested'])
        self.assertFalse(r['package_complete'])

    def test_caller_boolean_grant_is_not_scientific_authorization(self):
        r=snapshot_gate(dict(dataset_hash='a'*64,admitted_records=800),dict(identity_verified=True,demo=True),grant={'approved':True},root='missing')
        self.assertFalse(r['execution_permitted'])
        with self.assertRaises(PermissionError):prepare_authorization_request({'approved':True},'missing')

    def test_admitted_package_can_prepare_request_but_cannot_train(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);grant,_=self.bundle(root)
            with patch('controller.training_admission_gate.ADMITTED_PACKAGE_HASHES',frozenset([seal(grant)])),patch('controller.training_admission_gate.subprocess.check_output',side_effect=lambda args,**kwargs:'' if args[1]=='status' else grant['code_head']):
                r=snapshot_gate({},dict(identity_verified=True,demo=True),grant=grant,root=root)
                self.assertTrue(r['authorization_request_ready'])
                self.assertFalse(r['execution_permitted'])
                self.assertFalse(prepare_authorization_request(grant,root)['training_authorized'])

    def tick(self,i,flags=2):
        return dict(time=1,time_msc=1000+i,bid=10,ask=11,flags=flags)

    def test_25_missing_bid_payloads_not_ask_events_or_duplicates(self):
        ref=[self.tick(i) for i in range(284)]
        raw=ref[:259]+[self.tick(300+i,4) for i in range(10)]
        r=reconcile(raw,ref,1000,2000,'1')
        self.assertEqual((r['raw_events'],r['raw_bid'],r['reference_bid']),(269,259,284))
        self.assertEqual(r['missing_reference_payload_occurrences'],25)
        self.assertEqual(r['extra_raw_payload_occurrences'],0)
        self.assertEqual(r['raw_repeated_identical_payloads'],0)
        self.assertFalse(r['reference_adopted_as_raw'])

    def test_same_counts_do_not_hide_payload_difference_or_duplicates(self):
        r=reconcile([self.tick(1)]*2,[self.tick(1),self.tick(2)],1000,2000,'1')
        self.assertEqual(r['net_bid_difference'],0)
        self.assertFalse(r['ordered_bid_payloads_equal'])
        self.assertEqual(r['raw_repeated_identical_payloads'],1)
        with self.assertRaises(ValueError):reconcile([self.tick(1)],[],1200,2000,'1')
