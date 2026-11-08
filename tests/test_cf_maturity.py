import unittest
from controller.cf_maturity import maturity,session_feasibility


class MaturityTests(unittest.TestCase):
    def test_quote_run_bound_does_not_combine_closed_intervals(self):
        result=session_feasibility(dict(sessions=dict(QUOTE=dict(MONDAY=[[60,1440]]))))
        self.assertEqual(result['maximum_one_quote_run_m5'],276)
        self.assertFalse(result['warmup_possible_without_session_bridge'])
        self.assertEqual(result['optimistic_minimum_total_m5'],1249)
        self.assertEqual(result['minimum_quote_runs'],5)
        self.assertEqual(result['minimum_certified_bridges'],4)
        fragmented=session_feasibility(dict(sessions=dict(QUOTE=dict(MONDAY=[[60,720],[780,1440]]))))
        self.assertEqual(fragmented['maximum_one_quote_run_m5'],132)
        self.assertFalse(fragmented['dataset_admitted'])

    def test_partial_boundaries_count_only_complete_aligned_m5(self):
        result=session_feasibility(dict(sessions=dict(QUOTE=dict(MONDAY=[[61,74]]))))
        self.assertEqual(result['maximum_one_quote_run_m5'],1)
        self.assertIsNone(result['calendar_eta'])

    def test_short_realistic_capture_does_not_invent_eta_or_admission(self):
        m=maturity(dict(technical_warmup=5,BUY=0,SELL=0))
        self.assertEqual(m['remaining']['warmup_m5'],345)
        self.assertEqual(m['remaining_warmup_observed_bar_minutes'],1725)
        self.assertIsNone(m['calendar_eta'])
        self.assertEqual(m['scientific_warmup'],0)
        self.assertFalse(m['dataset_admitted'])

    def test_thresholds_remain_independent_and_never_negative(self):
        m=maturity(dict(technical_warmup=351,consecutive_signals=800,post_bars=100,evaluable=200,evaluable_BUY=80,evaluable_SELL=80,BUY_folds=3,SELL_folds=3))
        self.assertTrue(all(v==0 for v in m['remaining'].values()))
        self.assertFalse(m['training_executed'])
