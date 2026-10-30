import unittest
from controller.native_study_design import fold_plan


class NativeStudyDesignTests(unittest.TestCase):
    def rows(self):
        return [dict(signal_id=str(i),side='BUY' if i%2 else 'SELL',decision=i*10,
                     arrival_index=i,follow_exit=i*10+5,invert_exit=i*10+6) for i in range(16)]

    def test_four_expanding_folds_keep_sides_and_pairs_together(self):
        result=fold_plan(self.rows())
        self.assertEqual([len(f['train_ids']) for f in result['folds']],[8,10,12,14])
        self.assertEqual([len(f['evaluation_ids']) for f in result['folds']],[2]*4)
        self.assertEqual(result['folds'][0]['evaluation_sides'],{'BUY':1,'SELL':1})
        self.assertFalse(result['training_authorized'])
        self.assertFalse(result['scoring_authorized'])

    def test_both_exit_horizons_are_purged_at_equality(self):
        rows=self.rows()
        rows[7]['invert_exit']=80
        rows[9]['follow_exit']=100
        fold=fold_plan(rows)['folds'][0]
        self.assertNotIn('7',fold['train_ids'])
        self.assertNotIn('9',fold['evaluation_ids'])

    def test_censored_labels_are_counted_never_zero_filled(self):
        rows=self.rows()
        rows[3]['follow_exit']=None
        fold=fold_plan(rows)['folds'][0]
        self.assertEqual(fold['purged_or_censored_train'],1)
        self.assertNotIn('3',fold['train_ids'])

    def test_unknown_columns_future_features_and_bad_order_rejected(self):
        for change in ({'pnl':100},{'side':'UNKNOWN'},{'follow_exit':-1}):
            rows=self.rows();rows[0]|=change
            with self.assertRaises(ValueError):fold_plan(rows)
        rows=self.rows();rows[1],rows[2]=rows[2],rows[1]
        with self.assertRaises(ValueError):fold_plan(rows)


if __name__=='__main__':unittest.main()
