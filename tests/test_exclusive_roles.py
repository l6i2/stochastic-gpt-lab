import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from controller.exclusive_roles import role_chain,validate_roles
from controller.pretrain_contracts import seal
from tools.cf_study_station import StudyStore


class ExclusiveRolesTests(unittest.TestCase):
    def fixture(self):
        manifest=dict(study_id='synthetic',producer_id='producer',capture_id='capture',dataset_id='dataset02')
        cutoff=dict(clock=dict(boot_id='test',monotonic_ns=2),minimum_native_open_msc=600000,native_anchor=dict(time_msc=360001))
        value=dict(cutoff=cutoff,authorization_observed_clock=dict(boot_id='test',monotonic_ns=1),
            precut_data_adopted=False,legacy_bounds_recovered=False,training_authorized=False,
            ledger=role_chain([dict(kind='CLOSE_ALL_PRIOR_FUTURE_INGRESS',scope='PC_A_US30Cash_ALL_PRIOR_RESERVATIONS',cutoff_hash=seal(cutoff)),
                dict(kind='ASSIGN_EXCLUSIVE_FORWARD_ROLE',**manifest,cutoff_hash=seal(cutoff))]))
        return manifest,value

    def test_exclusive_assignment_with_distinct_frame_floors(self):
        manifest,value=self.fixture();roles=validate_roles(value,manifest)
        self.assertTrue(roles['exclusive'])
        self.assertEqual(roles['minimum_native_open_msc'],600000)
        self.assertEqual(roles['minimum_m1_open_msc'],420000)

    def test_tampering_and_duplicate_assignment_rejected(self):
        manifest,value=self.fixture()
        bad=copy.deepcopy(value);bad['ledger'][1]['payload']['dataset_id']='other'
        with self.assertRaises(ValueError):validate_roles(bad,manifest)
        bad=copy.deepcopy(value);bad['ledger'].append(bad['ledger'][-1])
        with self.assertRaises(ValueError):validate_roles(bad,manifest)

    def test_no_retroactive_import_or_training_or_cut_before_authority(self):
        manifest,value=self.fixture()
        for key in ('precut_data_adopted','legacy_bounds_recovered','training_authorized'):
            with self.assertRaises(ValueError):validate_roles(dict(value,**{key:True}),manifest)
        bad=copy.deepcopy(value);bad['authorization_observed_clock']['monotonic_ns']=3
        with self.assertRaises(ValueError):validate_roles(bad,manifest)

    def test_old_bars_refused_without_mutating_checkpoint(self):
        with TemporaryDirectory() as directory:
            store=StudyStore(Path(directory)/'synthetic.sqlite3')
            store.state['cf_exclusive_minimum_native_open_msc']=600000
            store.state['cf_exclusive_minimum_m1_open_msc']=420000
            for frame,start in ((60,360000),(300,300000)):
                with self.assertRaises(ValueError):
                    store.commit([dict(kind='DATABASE_SNAPSHOT_PAIR',frame_seconds=frame,start_native_msc=start)])
            self.assertEqual(store.count,0)
            store.close()


if __name__=='__main__':unittest.main()
