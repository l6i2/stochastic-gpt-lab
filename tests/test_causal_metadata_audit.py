from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
from causal_metadata_audit import main_values,audit_metadata_contract


class CausalMetadataAuditTests(unittest.TestCase):
    def test_hand_computed_counterexample_exposes_non_equivalence_without_market_data(self):
        report=audit_metadata_contract()
        values=report['synthetic_counterexample']
        self.assertAlmostEqual(values['frozen_main_k'],92/3)
        self.assertAlmostEqual(values['native_example_main_k'],1100/210)
        self.assertEqual(values['frozen_flat_main_k'],50)
        self.assertEqual(values['native_example_flat_main_k'],100)
        self.assertEqual(report['status'],'FAIL')
        self.assertTrue(report['frozen_definition_found'])
        self.assertFalse(report['existing_support_counts_usable_for_native_trigger_maturity'])
        self.assertFalse(report['cohort_read'])

    def test_future_only_bar_changes_cannot_change_prior_reference_features(self):
        before=[{'low':40000.,'high':40010.+i%5,'close':40003.+i%3} for i in range(30)]
        after=[dict(b) for b in before]
        for b in after[20:]:
            b['high']+=500
        for native in (False,True):
            self.assertEqual(main_values(before,native_reference=native)[:20],main_values(after,native_reference=native)[:20])
            self.assertNotEqual(main_values(before,native_reference=native)[20:],main_values(after,native_reference=native)[20:])
