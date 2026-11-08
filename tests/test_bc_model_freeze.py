import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,Mock
from controller.bc_study import STUDY
from controller.pretrain_contracts import FEATURES,seal
from tools import admitted_training as runner


class BCModelFreezeTests(unittest.TestCase):
    def test_no_grant_rejects_before_any_serialization(self):
        with tempfile.TemporaryDirectory() as directory,patch('joblib.dump') as dump:
            with self.assertRaises(PermissionError):runner.freeze_bc_models({}, {}, {}, Path(directory)/'not-created')
            dump.assert_not_called();self.assertFalse((Path(directory)/'not-created').exists())

    def test_simulated_models_freeze_without_fits_or_eval_activation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);grant=dict(study_id=STUDY,code_head='SYNTHETIC',protocol_hash='SYNTHETIC',environment_hash='SYNTHETIC')
            attempt=root/'outputs/admitted_native_studies'/STUDY.lower()/'authorized_runs'/seal(grant);attempt.mkdir(parents=True)
            binding=dict(selected_fold=4,fits=8,additional_fits=0,grant_sha256=seal(grant),feature_order=list(FEATURES))
            models={side:dict(fixture_only=True,side=side) for side in ('BUY','SELL')};nts=Mock(return_value=dict(synthetic=True))
            with patch.object(runner,'ROOT',root),patch.object(runner,'authorize_execution',return_value={}),patch('controller.authorized_capture.bracket',return_value=dict(synthetic_only=True)):
                receipt=runner.freeze_bc_models(grant,models,binding,attempt,clock=lambda:dict(synthetic=True),nts=nts)
                self.assertEqual(nts.call_count,2);self.assertEqual(len(receipt['models_sha256']),2)
                self.assertFalse(receipt['EVAL_CONTEXT_active']);self.assertFalse(receipt['scoring_authorized'])
                self.assertEqual(receipt['additional_fits'],0)
                before=(attempt/'BUY_fold4.joblib').read_bytes()
                with self.assertRaises(FileExistsError):runner.freeze_bc_models(grant,models,binding,attempt,clock=lambda:{},nts=nts)
                self.assertEqual((attempt/'BUY_fold4.joblib').read_bytes(),before)
