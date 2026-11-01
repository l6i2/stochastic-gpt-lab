import unittest
from controller.provenance_independent_plan import recovery_disposition,work_plan


class IndependentProvenancePlanTests(unittest.TestCase):
    def authority(self):
        return dict(collection_authorized=True,dataset_admission_authorized=False,
                    training_authorized=False,scoring_authorized=False,backfill_allowed=False)

    def test_no_original_manifest_fabricated_without_byte_match(self):
        r=recovery_disposition('split','a'*64,[{'sha256':'b'*64}],True)
        self.assertEqual(r['status'],'IRRECOVERABLE_IN_ACCESSIBLE_SEARCHED_SOURCES')
        self.assertFalse(r['global_nonexistence_claim'])
        self.assertFalse(r['automatic_retry'])
        self.assertEqual(recovery_disposition('master',None,[{'sha256':'a'*64}],True)['status'],r['status'])
        self.assertEqual(recovery_disposition('split','a'*64,[{'sha256':'a'*64}],True)['status'],'EXACT_RECOVERY_HASH_MATCH')

    def test_incomplete_search_is_not_irrecoverability(self):
        self.assertEqual(recovery_disposition('split','a'*64,[],False)['status'],'UNRESOLVED_SEARCH_INCOMPLETE')

    def test_legacy_failure_never_disables_collection_or_grants_scientific_access(self):
        p=work_plan([recovery_disposition('split','a'*64,[],True)],live_authority=self.authority())
        self.assertTrue(all(not t['requires_legacy_manifests'] for t in p['tasks']))
        for field in ('frozen_scientific_admission_changed','training','scoring','new_cohort_activated','new_start_selected','historic_data_adopted'):
            self.assertFalse(p[field])
        self.assertEqual(p['admission'],'BLOCKED')

    def test_collection_plan_cannot_smuggle_authorization_or_backfill(self):
        for change in ({'collection_authorized':False},{'training_authorized':True},
                       {'scoring_authorized':True},{'dataset_admission_authorized':True},{'backfill_allowed':True}):
            with self.assertRaises(ValueError):work_plan([],live_authority=self.authority()|change)
