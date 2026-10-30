import unittest
from controller.native_independence import preflight


class IndependenceTests(unittest.TestCase):
    def fixture(self):
        candidate = dict(study_id='synthetic_fixture', role='TRAIN_NEW_PROPOSED',
            instrument='SYNTHETIC',domain_id='native_fixture_1',source_sha256='a'*64,
            ledger_sha256='b'*64,signal_ids=['new_1'],feature_start=1000,
            decision_start=1100,decision_end=1200,label_end=1500,
            path='outputs/new_native_studies/synthetic_fixture/data.csv')
        roles=['TRAIN_EXHAUSTED','DISCOVERY_VALIDATION','HISTORICAL_HOLDOUT','FINAL_TEST','PROSPECTIVE_QUARANTINE']
        ledger=[dict(instrument='SYNTHETIC',domain_id='native_fixture_1',signal_ids=[r],
                     feature_start=10+i*100,label_end=99+i*100,role=r,source_sha256=str(i)*64) for i,r in enumerate(roles)]
        return candidate, ledger

    def test_structural_pass_is_not_certification_or_permission(self):
        result=preflight(*self.fixture())
        self.assertEqual(result['dataset_rows_opened'],0)
        self.assertFalse(result['training_authorized'])
        self.assertTrue(result['independence_certification'].startswith('UNVERIFIED'))

    def test_protected_roles_and_aliases_fail_before_io(self):
        candidate, ledger=self.fixture()
        for role in ('TRAIN','DISCOVERY_VALIDATION','HISTORICAL_HOLDOUT','FINAL_TEST'):
            with self.assertRaises(ValueError):preflight(candidate|{'role':role},ledger)
        for path in ('historical-holdout/data.csv','Discovery_Validation/data.csv','FINAL-TEST/a',
                     'future_validation_cohort/a','prospective/a','../a',r'C:\private\a'):
            with self.assertRaises(ValueError):preflight(candidate|{'path':path},ledger)

    def test_warmup_and_label_overlap_and_shared_endpoint_rejected(self):
        candidate, ledger=self.fixture()
        for change in ({'feature_start':400},{'feature_start':499},
                       {'decision_start':1100,'decision_end':1200,'label_end':1600}):
            prior=ledger+[ledger[0]|{'feature_start':1550,'label_end':1700}]
            if 'label_end' not in change:prior=ledger
            with self.assertRaisesRegex(ValueError,'OVERLAP'):preflight(candidate|change,prior)

    def test_signal_reuse_and_unknown_clock_domains_rejected(self):
        candidate,ledger=self.fixture()
        with self.assertRaisesRegex(ValueError,'EXPOSED_SIGNAL'):
            preflight(candidate|{'signal_ids':['TRAIN_EXHAUSTED']},ledger)
        with self.assertRaisesRegex(ValueError,'UNCOMPARABLE'):
            preflight(candidate|{'domain_id':'another_server'},ledger)

    def test_no_implicit_membership_or_incomplete_registry(self):
        candidate,ledger=self.fixture()
        for change in ({'signal_ids':[]},{'signal_ids':['a','a']},{'source_sha256':'unknown'},
                       {'feature_start':True},{'label_end':1199}):
            with self.assertRaises(ValueError):preflight(candidate|change,ledger)
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_PROTECTED'):
            preflight(candidate,ledger[:-1])

    def test_same_source_or_unrelated_instrument_is_not_independence(self):
        candidate,ledger=self.fixture()
        with self.assertRaisesRegex(ValueError,'EXPOSED_SOURCE'):
            preflight(candidate|{'source_sha256':ledger[0]['source_sha256']},ledger)
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_PROTECTED'):
            preflight(candidate,ledger[:-1]+[ledger[-1]|{'instrument':'ANOTHER'}])


if __name__=='__main__':unittest.main()
