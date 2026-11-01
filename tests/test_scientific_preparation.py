import copy
import unittest
from controller.pretrain_contracts import chain, seal, verify_chain, FEATURES
from controller.scientific_preparation import reconcile, training_plan, progress_projection
from controller.feature_availability_review import GROUPS, review, structure_break_observation
from controller.native_study_runner import execute, acceptance, bootstrap_contrasts, AUTHORIZED_GRANT_HASHES


class ScientificPreparationTests(unittest.TestCase):
    def test_runner_denies_before_any_reader_or_attempt_claim(self):
        def forbidden(*args):
            self.fail('Preparation must never read a dataset or claim a training attempt')
        self.assertEqual(AUTHORIZED_GRANT_HASHES,frozenset())
        for grant in ({},{'authorized':True},{'dataset_hash':'a'*64}):
            with self.assertRaises(PermissionError):execute(grant,forbidden,forbidden)

    def test_resampling_synthetic_only_keeps_origin_and_final_partial_block(self):
        rows=[dict(signal_id=str(i),side='BUY' if i%2 else 'SELL',arrival_index=i,
              observed_bar_index=i*10,candidate=i-4,follow=0,invert=1,fold=i//2+1) for i in range(8)]
        # Most blocks have no signal: bootstrap must not silently drop them.
        m=bootstrap_contrasts(rows,0,903)
        self.assertFalse(m['integrity_and_causal_admission_verified'])
        for r in m['contrasts']:
            self.assertEqual(r['block_count'],3)
            self.assertEqual(r['bootstrap_resamples'],10000)
            self.assertFalse(r['bootstrap_valid'])
        self.assertEqual(acceptance(m),'NOT_READY')
        with self.assertRaises(ValueError):bootstrap_contrasts(rows,1,903)
        with self.assertRaises(ValueError):bootstrap_contrasts(list(reversed(rows)),0,903)

    def test_acceptance_boundaries_using_only_synthetic_summary_metadata(self):
        rows=[dict(side=s,baseline=b,folds=4,bootstrap_valid=True,degenerate=False,
            signal_lower_9875=1,block451_lower_9875=1,positive_fold_fraction=.75,
            max_positive_fold_share=.5,candidate_drawdown=12,baseline_drawdown=10)
            for s in ('BUY','SELL') for b in ('follow','invert')]
        m=dict(n=200,sides=dict(BUY=100,SELL=100),contrasts=rows,integrity_and_causal_admission_verified=True)
        self.assertEqual(acceptance(m),'PASS_INTERNAL_RESEARCH_ONLY')
        self.assertEqual(acceptance(m|{'n':199}),'NOT_READY')
        self.assertEqual(acceptance(m|{'integrity_and_causal_admission_verified':False}),'REJECTED')
        for change,expected in (({'signal_lower_9875':0},'FAIL'),({'block451_lower_9875':0},'FAIL'),
            ({'positive_fold_fraction':.69},'FAIL'),({'max_positive_fold_share':.51},'FAIL'),
            ({'candidate_drawdown':12.01},'FAIL'),({'degenerate':True},'INCONCLUSIVE'),
            ({'bootstrap_valid':False},'INCONCLUSIVE'),({'folds':2},'INCONCLUSIVE')):
            self.assertEqual(acceptance(m|{'contrasts':[rows[0]|change]+rows[1:]}),expected)
        with self.assertRaises(ValueError):acceptance(m|{'contrasts':rows[:3]})

    def base(self):
        rows=chain([dict(dataset='unknown',end=None)])
        return dict(entries=rows,chain_head=rows[-1]['entry_sha256'],missing=['UNKNOWN_BOUNDS'])

    def test_sibling_forks_preserved_not_silently_rebased(self):
        base=self.base()
        overlays=[]
        for kind in ('AUDIT_A','AUDIT_B'):
            r=dict(kind=kind,previous=base['chain_head'],ledger_sequence=1)
            overlays.append(dict(r,entry_sha256=seal(r)))
        original=copy.deepcopy(overlays)
        out=reconcile(base,overlays,[dict(path='receipt',sha256='a'*64)])
        self.assertEqual(overlays,original)
        self.assertEqual(len(out['original_sibling_heads']),2)
        self.assertFalse(out['completeness_verified'])
        self.assertEqual(verify_chain(out['entries']),out['chain_head'])
        for bad in (dict(overlays[0],kind='TAMPERED'),dict(overlays[0],previous='other')):
            with self.assertRaises(ValueError):reconcile(base,[bad],[])
        with self.assertRaises(ValueError):reconcile(base,[overlays[0]]*2,[])

    def test_no_data_plan_has_zero_actual_fits_and_no_authority(self):
        plan=training_plan('a'*64,'b'*64)
        self.assertIsNone(plan['chronological_plan'])
        self.assertEqual(plan['actual_fits'],0)
        self.assertEqual(len(plan['planned_slots']),8)
        self.assertEqual(plan['feature_order'],list(FEATURES))
        self.assertFalse(plan['execution_enabled'])
        self.assertFalse(plan['authorization_requested'])
        with self.assertRaises(ValueError):training_plan('unbound','b'*64)

    def test_plan_purges_exit_on_next_boundary_without_sorting(self):
        rows=[dict(signal_id=str(i),side='BUY' if i%2 else 'SELL',decision=i*10,
                   arrival_index=i+1,follow_exit=i*10+1,invert_exit=i*10+1) for i in range(16)]
        rows[7]['invert_exit']=80
        plan=training_plan('a'*64,'b'*64,signals=rows)
        self.assertNotIn('7',plan['chronological_plan']['folds'][0]['train_ids'])
        with self.assertRaises(ValueError):training_plan('a'*64,'b'*64,signals=list(reversed(rows)))

    def test_every_reviewed_group_rejects_future_or_unavailable_sources(self):
        for name in GROUPS:
            row=dict(feature=name,source_max_native_msc=99,cutoff_native_msc=99,
                decision_native_msc=100,ready_order=1,decision_order=2,
                seed_required=False,seed_own=False,coverage_verified=False,
                utc_mapping_required=False,utc_mapping_verified=False)
            self.assertFalse(review(row)['real_feature_values_verified'])
            for bad in ({'source_max_native_msc':100},{'decision_order':1},
                        {'seed_required':True},{'utc_mapping_required':True}):
                with self.assertRaises(ValueError):review(row|bad)

    def test_structure_inclusive_flags_preserved_and_not_promoted(self):
        r=structure_break_observation(list(range(20,40)),list(range(20)))
        self.assertFalse(r['recent_high_break'])
        self.assertFalse(r['recent_low_break'])
        self.assertNotIn('recent_high_break',FEATURES)

    def test_progress_refuses_threshold_relaxation_or_unreviewed_admission(self):
        base=dict(warmup_required=350,signals_required=800,post_signal_bars_required=100,
                  evaluable_required=200,evaluable_required_each_side=80,admitted_records=0,dataset_hash=None)
        for change in ({'warmup_required':349},{'signals_required':799},
                       {'post_signal_bars_required':99},{'evaluable_required':199},
                       {'evaluable_required_each_side':79},{'admitted_records':1},{'dataset_hash':'x'}):
            with self.assertRaises(ValueError):progress_projection(base|change)
