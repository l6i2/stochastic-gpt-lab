import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from controller.pretrain_contracts import FEATURES, seal
from controller.native_study_design import fold_plan
from controller.native_study_runner import execute
from controller.training_admission_gate import authorize_execution
from tests import test_training_admission_gate as gate_fixtures


class FirstTrainingReadinessTests(unittest.TestCase):
    def git_output(self, head, dirty=False):
        return lambda args, **kwargs: (' M controller/native_study_runner.py\n' if dirty else '') if args[1]=='status' else head

    def test_dirty_code_rejects_before_dataset_read(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            grant,manifest=gate_fixtures.AdmissionGateTests().bundle(root)
            original=Path.read_bytes
            def read(path):
                if path==root/manifest['dataset_path']:
                    self.fail('Dataset read after a dirty code revision')
                return original(path)
            with patch('controller.training_admission_gate.AUTHORIZED_GRANT_HASHES',frozenset([seal(grant)])), patch('controller.training_admission_gate.subprocess.check_output',side_effect=self.git_output(grant['code_head'],True)), patch('pathlib.Path.read_bytes',read):
                with self.assertRaisesRegex(ValueError,'WORKTREE_NOT_CLEAN'):
                    authorize_execution(grant,root)

    def test_missing_and_invalid_last_bar_reject_before_training_dispatch(self):
        for last in (None,-1,True):
            with TemporaryDirectory() as d:
                root=Path(d)
                grant,manifest=gate_fixtures.AdmissionGateTests().bundle(root)
                manifest['dataset_last_observed_bar']=last
                path=root/grant['manifest_path'];path.write_text(json.dumps(manifest))
                grant['manifest_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
                with patch('controller.training_admission_gate.AUTHORIZED_GRANT_HASHES',frozenset([seal(grant)])), patch('controller.training_admission_gate.subprocess.check_output',side_effect=self.git_output(grant['code_head'])):
                    with self.assertRaisesRegex(ValueError,'OBSERVED_BOUNDS'):
                        authorize_execution(grant,root)

    def packet(self,n=800):
        rows=[dict(signal_id=str(i),side='BUY' if i%2 else 'SELL',decision=i*10,
                   arrival_index=i,follow_exit=i*10+1,invert_exit=i*10+2,
                   features={feature:1.0 for feature in FEATURES},follow_pnl=float((i//2)%2),
                   invert_pnl=0.,observed_bar_index=i+350) for i in range(n)]
        metadata=[{key:row[key] for key in ('signal_id','side','decision','arrival_index','follow_exit','invert_exit')} for row in rows]
        grant=dict.fromkeys(('study_id','dataset_hash','protocol_hash','feature_whitelist_hash',
                            'membership_hash','exposure_hash','admission_receipt_hash','code_head',
                            'environment_hash','row_schema','plan_hash','dataset_first_observed_bar',
                            'manifest_path','manifest_sha256','max_fits'))
        grant.update(row_schema='native-study-admitted-rows/1',plan_hash=seal(fold_plan(metadata)),
                     dataset_first_observed_bar=0,max_fits=8,dataset_hash=seal(rows))
        return rows,grant

    def test_unbound_positions_reject_before_estimator_preparation(self):
        rows,grant=self.packet()
        rows[-1]['observed_bar_index']=5000;grant['dataset_hash']=seal(rows)
        with patch('controller.native_study_runner.authorize_execution',return_value=dict(dataset_last_observed_bar=2000)), patch('controller.native_study_runner.prepare_unfitted') as factory:
            with self.assertRaisesRegex(ValueError,'OUTSIDE_ADMITTED_OBSERVED_BOUNDS'):
                execute(grant,lambda _:rows,Mock())
            factory.assert_not_called()

    def test_invalid_bounds_reject_before_claim_or_loader(self):
        rows,grant=self.packet();loader=Mock(return_value=rows);claim=Mock()
        with patch('controller.native_study_runner.authorize_execution',return_value={}):
            with self.assertRaisesRegex(ValueError,'OBSERVED_BOUNDS'):
                execute(grant,loader,claim)
        loader.assert_not_called();claim.assert_not_called()

    def test_purged_evaluation_support_rejects_before_any_fit(self):
        rows,grant=self.packet(32)
        with patch('controller.native_study_runner.authorize_execution',return_value=dict(dataset_last_observed_bar=2000)), patch('controller.native_study_runner.prepare_unfitted') as factory:
            with self.assertRaisesRegex(ValueError,'INSUFFICIENT_PURGED_EVALUATION_SUPPORT'):
                execute(grant,lambda _:rows,Mock())
            factory.assert_not_called()

    def test_fixed_fold_four_models_can_be_frozen_without_ninth_fit(self):
        rows,grant=self.packet();models=[];sink=Mock()
        def factory(side):
            model=Mock()
            model.predict_proba.side_effect=lambda x:[[.4,.6] for _ in x]
            models.append(model)
            return model,{}
        with patch('controller.native_study_runner.authorize_execution',return_value=dict(dataset_last_observed_bar=2000)), patch('controller.native_study_runner.prepare_unfitted',side_effect=factory):
            result=execute(grant,lambda _:rows,Mock(),model_sink=sink)
        self.assertEqual(result['fits'],8)
        self.assertEqual(sum(model.fit.call_count for model in models),8)
        selected,binding=sink.call_args.args
        self.assertIs(selected['BUY'],models[-2])
        self.assertIs(selected['SELL'],models[-1])
        self.assertEqual(binding['selected_fold'],4)
        self.assertEqual(binding['additional_fits'],0)
