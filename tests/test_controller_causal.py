import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from controller.causal_probe import compare
from controller.cold_start import redact
from controller.history_orchestrator import history


class CausalTests(unittest.TestCase):
    def fixture(self, folder):
        for side in ('base','future_changed'):
            def table(suffix,rows):
                with (folder/f'p_{side}_{suffix}.csv').open('w',newline='') as f:
                    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            (folder/f'p_{side}_summary.json').write_text(json.dumps({'cutoff':100,'failed':False}))
            table('snapshots',[{'snapshot_id':'s','snapshot_time_msc':100,'causal_feature':42}])
            table('targets',[{'snapshot_id':'s','future_pnl':10 if side=='base' else -10}])
            for suffix,key in [('input_ticks','time_msc'),('input_bars','bar_end_msc')]:
                table(suffix,[{key:100,'price':1},{key:200,'price':2 if side=='base' else 9}])

    def test_future_only_proof_and_target_sensitivity(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);self.fixture(folder)
            result=compare(folder,'p')
            self.assertEqual(result['CAUSAL_INVARIANCE'],'PASS')
            self.assertEqual(result['changed_future_targets'],1)
            path=folder/'p_future_changed_snapshots.csv'
            path.write_text(path.read_text().replace('42','43'))
            with self.assertRaisesRegex(RuntimeError,'causal features changed'):
                compare(folder,'p')

    def test_modifying_past_inputs_is_not_an_invariance_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);self.fixture(folder)
            path=folder/'p_future_changed_input_ticks.csv'
            path.write_text(path.read_text().replace('100,1','100,2'))
            with self.assertRaisesRegex(RuntimeError,'past input was modified'):
                compare(folder,'p')

    def test_sensitive_log_lines_and_account_ids_redacted(self):
        text="Network '123456789': demo account\nlogin=123456789\npassword=secret\n#123456789"
        cleaned=redact(text)
        self.assertNotIn('123456789',cleaned)
        self.assertNotIn('secret',cleaned)

    def test_resume_skips_pass_and_failure_stops_next_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);runs=root/'outputs/controller/runs/rsmoke';runs.mkdir(parents=True)
            (runs/'run_manifest.json').write_text(json.dumps({'from':'2024-01-01','to':'2024-01-31',
                'tester_to_exclusive':'2024.02.01','tester_status':'PASS','VALIDATION_STATUS':'PASS','CAUSALITY_STATUS':'PASS'}))
            blocks=[{'BLOCK_ID':str(i),'DATE_FROM':f'202{i}-01-01','DATE_TO':f'202{i}-12-31',
                     'STATUS':'PASS' if i==3 else 'PENDING'} for i in (3,4,5)]
            checkpoint=root/'outputs/controller/checkpoints/history_state.json';checkpoint.parent.mkdir()
            checkpoint.write_text(json.dumps({'blocks':blocks}))
            with patch('controller.history_orchestrator.ROOT',root),patch('controller.history_orchestrator.plan',return_value=blocks),patch('controller.tester_runner.run',return_value={'run_id':'failed','artifact_hashes':{},'tester_status':'FAIL'}) as runner:
                with self.assertRaisesRegex(RuntimeError,'history block failed'):
                    history(resume=True)
                self.assertEqual(runner.call_count,1)
                self.assertEqual(runner.call_args.args[:2],('2024-01-01','2024-12-31'))
            saved=json.loads(checkpoint.read_text())['blocks']
            self.assertEqual([b['STATUS'] for b in saved],['PASS','FAIL','PENDING'])


if __name__=='__main__':
    unittest.main()
