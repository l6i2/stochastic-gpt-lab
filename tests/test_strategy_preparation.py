import copy,unittest
from controller.strategy_diagnostic import summarize,distribution
from controller.pretrain_model_preparation import prepare_unfitted,catalog,LOGISTIC
from controller.feature_availability_review import review,structure_break_observation,GROUPS


class StrategyPreparationTests(unittest.TestCase):
    def rows(self):
        return [dict(follow_side='BUY',follow_exit_reason=reason,follow_PnL=pnl,follow_exit_time=str(i),follow_MFE='10',follow_MAE='5',follow_bars_in_trade='2') for i,(reason,pnl) in enumerate([('TP','240'),('SL','-180'),('END_OF_DATA','')])]

    def meta(self):
        return dict(feature='stoch_k',source_max_native_msc=299999,cutoff_native_msc=299999,decision_native_msc=300001,ready_order=1,decision_order=2,seed_required=False,seed_own=False,coverage_verified=False,utc_mapping_required=False,utc_mapping_verified=False)

    def test_censored_path_never_becomes_zero_pnl(self):
        result=summarize(self.rows(),'FOLLOW')
        self.assertEqual(result['completed'],2);self.assertEqual(result['censored'],1)
        self.assertEqual(result['completed_pnl']['mean'],30)
        self.assertEqual(result['profit_factor'],240/180)
        self.assertEqual(result['closed_pnl_exit_order_drawdown_proxy'],-180)
        self.assertEqual(result['observed_mfe_all']['n'],3)

    def test_missing_completed_outcome_fails(self):
        rows=self.rows();rows[0]['follow_PnL']=''
        with self.assertRaisesRegex(ValueError,'MISSING_COMPLETED'):summarize(rows,'FOLLOW')

    def test_current_logistic_is_exact_unfitted_and_side_separate(self):
        a,am=prepare_unfitted('BUY');b,bm=prepare_unfitted('SELL')
        self.assertIsNot(a,b);self.assertFalse(hasattr(a.named_steps['model'],'coef_'))
        self.assertFalse(hasattr(a.named_steps['scale'],'mean_'))
        self.assertEqual(am['params'],LOGISTIC);self.assertEqual(am['feature_order'],bm['feature_order'])
        self.assertFalse(am['training_authorized']);self.assertFalse(am['scoring_authorized'])
        self.assertNotEqual(am['spec_sha256'],bm['spec_sha256'])

    def test_logistic_change_and_noncurrent_family_blocked(self):
        with self.assertRaisesRegex(ValueError,'FROZEN_LOGISTIC'):prepare_unfitted('BUY',explicit_params=LOGISTIC|{'C':2})
        with self.assertRaisesRegex(ValueError,'OUTSIDE_FROZEN'):prepare_unfitted('BUY','random_forest')
        with self.assertRaisesRegex(ValueError,'SEQUENTIAL_JUSTIFICATION'):prepare_unfitted('SELL','sequential')
        self.assertEqual(catalog()['fits_authorized'],0)

    def test_future_trees_and_boosting_constructor_fixtures_do_not_fit(self):
        forest=dict(n_estimators=2,max_depth=2,min_samples_leaf=2,max_features='sqrt',random_state=1,n_jobs=1)
        model,meta=prepare_unfitted('BUY','random_forest',proposal_only=True,explicit_params=forest)
        self.assertFalse(hasattr(model,'estimators_'));self.assertFalse(meta['current_protocol_family'])
        forest['n_jobs']=-1
        with self.assertRaisesRegex(ValueError,'SINGLE_JOB'):prepare_unfitted('BUY','random_forest',proposal_only=True,explicit_params=forest)
        boosting=dict(max_iter=2,max_leaf_nodes=3,max_depth=2,min_samples_leaf=2,l2_regularization=1,learning_rate=.1,random_state=1,early_stopping=False,validation_fraction=None)
        model,meta=prepare_unfitted('SELL','hist_gradient_boosting',proposal_only=True,explicit_params=boosting)
        self.assertFalse(hasattr(model,'classes_'));self.assertTrue(meta['proposal_only'])
        boosting['early_stopping']=True
        with self.assertRaisesRegex(ValueError,'RANDOM_VALIDATION'):prepare_unfitted('SELL','hist_gradient_boosting',proposal_only=True,explicit_params=boosting)

    def test_future_forming_and_stage_dependencies_rejected(self):
        result=review(self.meta());self.assertFalse(result['admitted']);self.assertEqual(result['coverage'],'PARTIAL_UNVERIFIED')
        for patch in ({'source_max_native_msc':300000},{'ready_order':2},{'cutoff_native_msc':300001}):
            with self.assertRaises(ValueError):review(self.meta()|patch)

    def test_recursive_seed_and_session_mapping_cannot_be_assumed(self):
        with self.assertRaisesRegex(ValueError,'RECURSIVE_SEED'):review(self.meta()|dict(feature='ATR',seed_required=True))
        with self.assertRaisesRegex(ValueError,'SESSION_TIME'):review(self.meta()|dict(feature='NY_hour',utc_mapping_required=True))
        result=review(self.meta()|dict(feature='POC'))
        self.assertFalse(result['whitelisted_for_current_study']);self.assertFalse(result['real_feature_values_verified'])

    def test_structure_inclusive_extreme_flags_are_degenerate_not_repaired(self):
        for current in (50,100,200):
            result=structure_break_observation([current]+[100]*19,[current-1]+[90]*19)
            self.assertFalse(result['recent_high_break']);self.assertFalse(result['recent_low_break'])
            self.assertFalse(result['strategy_changed'])

    def test_every_reviewed_feature_group_rejects_future_dependency(self):
        for feature in GROUPS:
            meta=self.meta()|dict(feature=feature,utc_mapping_required=feature=='hours_sessions',utc_mapping_verified=feature=='hours_sessions')
            result=review(meta);self.assertFalse(result['admitted'])
            with self.assertRaisesRegex(ValueError,'FUTURE_OR_FORMING'):review(meta|dict(source_max_native_msc=300001))


if __name__=='__main__':unittest.main()
