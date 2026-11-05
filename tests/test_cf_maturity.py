import unittest
from controller.cf_maturity import maturity


class MaturityTests(unittest.TestCase):
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
