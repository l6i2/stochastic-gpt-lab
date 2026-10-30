import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from controller.native_feature_diagnostic import harness, compare_rows, tables, verify_capture, history_preflight


class NativeFeatureDiagnosticTests(unittest.TestCase):
    def test_short_history_is_blocked_without_claiming_indicator_readiness(self):
        for count in (0,15,19,True,20.5):
            with self.assertRaisesRegex(ValueError,'UNSAFE_SHORT_HISTORY'):history_preflight(count)
        result=history_preflight(20)
        self.assertTrue(result['array_floor_satisfied'])
        self.assertFalse(result['full_export_window'])
        self.assertFalse(result['indicator_semantics_certified'])

    def test_derivation_keeps_actual_frozen_producer_and_closed_queries(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'Fixture.mq5'
            harness(source,'nfeat_123456789abc')
            text=source.read_text()
            self.assertIn('#include "StochasticBarDecisionResearchEA.mq5"',text)
            self.assertIn('int cuts[3]={45,400,450}',text)
            self.assertIn('if(start<1)',text)
            self.assertIn('prefix_only',text)
            self.assertIn('den==0?100:100*num/den',text)
            self.assertIn('int offsets[5]={0,0,60,180,299}',text)
            self.assertNotIn('OrderSend(',text)
            with self.assertRaises(FileExistsError):harness(source,'nfeat_123456789abc')

    def test_unknown_producer_and_capture_id_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):harness(Path(tmp)/'a.mq5','../wrong')
            with patch('controller.native_feature_diagnostic.sha256',return_value='wrong'):
                with self.assertRaisesRegex(ValueError,'PRODUCER_CHANGED'):
                    harness(Path(tmp)/'a.mq5','nfeat_123456789abc')

    def test_each_checked_field_rejects_future_dependency(self):
        columns=['stoch_k','ha_close','relative_volume_100','vp_session_POC','current_mfe_so_far']
        row=dict(id='s',time='100',**{c:'1' for c in columns})
        for c in columns:
            with self.assertRaisesRegex(ValueError,c):
                compare_rows([row],[row|{c:'2'}],'id','time',100,columns)
        self.assertEqual(compare_rows([row],[row,row|{'id':'future','time':'200'}],
                                     'id','time',100,columns),1)

    def test_missing_duplicate_or_changed_universe_is_failure(self):
        row=dict(id='s',time='100',feature='1')
        for changed in ([],[row,row],[row|{'id':'other'}]):
            with self.assertRaises(ValueError):
                compare_rows([row],changed,'id','time',100,['feature'])

    def test_malformed_or_duplicate_schema_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'a.csv'
            for text in ('a,a\n1,2\n','a,b\n1\n','a\n1,2\n'):
                p.write_text(text)
                with self.assertRaises(ValueError):tables(p)

    def test_unverified_capture_never_opens_tables(self):
        checkpoint=dict(capture_id='nfeat_123456789abc',status='RUNNING_SYNTHETIC',producer_sha256='wrong')
        with patch('controller.native_feature_diagnostic.compare_capture') as compare:
            with self.assertRaises(ValueError):
                verify_capture(Path('nfeat_123456789abc'),checkpoint)
            compare.assert_not_called()


if __name__=='__main__':unittest.main()
