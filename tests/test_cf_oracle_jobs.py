import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch,Mock
from tools.cf_quality_monitor import oracle_job_status,native_oracle_milestone


class OracleJobTests(unittest.TestCase):
    def test_resource_retry_requires_new_prefix_and_later_success_is_reused(self):
        with TemporaryDirectory() as d:
            root=Path(d);base=root/'outputs';base.mkdir();(root/'tools').mkdir();(root/'controller').mkdir()
            (root/'tools/cf_own_indicator_oracle.py').write_text('# synthetic executable placeholder')
            (root/'controller/cf_feature_review.py').write_text('# synthetic hash input')
            status=dict(technical_warmup=15,capture_id='c',epoch='e',own_seed_bar_hash='seed')
            with patch('psutil.virtual_memory',return_value=Mock(available=1024**3)),patch('psutil.process_iter',return_value=[]),patch('tools.cf_quality_monitor.oracle_process_running',return_value=False),patch('subprocess.Popen',return_value=Mock(pid=999999)) as launch:
                first=native_oracle_milestone(root,base,status);stage=base/'native_oracle_jobs'/first['job_key']
                (stage/'stdout.json').write_text(json.dumps(dict(status='WAITING_FOR_RESOURCES')))
                native_oracle_milestone(root,base,status);self.assertEqual(launch.call_count,1)
                native_oracle_milestone(root,base,dict(status,technical_warmup=16));self.assertEqual(launch.call_count,2)
                completed=dict(status='PASS_OWN_PREFIX_NATIVE_DIAGNOSTIC_ONLY',capture_id='c',epoch='e',own_seed_bar_hash='seed',native_m5=16,ATR_PARITY='PASS_EXACT',MAIN_K_PARITY='PASS_RETAINED_BOUND',original_terminals_preserved=True,orders_sent=0,training_executed=False,dataset_admitted=False)
                (stage/'deferred_prefix_16/stdout.json').write_text(json.dumps(completed))
                self.assertTrue(native_oracle_milestone(root,base,dict(status,technical_warmup=17))['native_parity_verified'])
                native_oracle_milestone(root,base,dict(status,technical_warmup=18));self.assertEqual(launch.call_count,2)

    def test_partial_output_distinguishes_running_from_dead(self):
        with TemporaryDirectory() as d:
            p=Path(d);(p/'stdout.json').write_text('{')
            self.assertEqual(oracle_job_status(p,{},True)['status'],'RUNNING')
            self.assertEqual(oracle_job_status(p,{},False)['status'],'FAILED_NO_VALID_RESULT')

    def test_resource_deferral_is_not_native_parity(self):
        with TemporaryDirectory() as d:
            p=Path(d);(p/'stdout.json').write_text(json.dumps(dict(status='WAITING_FOR_RESOURCES')))
            r=oracle_job_status(p,{},False)
            self.assertTrue(r['retryable_on_new_data']);self.assertFalse(r['native_parity_verified'])

    def test_native_success_requires_same_capture_epoch_and_no_authority_expansion(self):
        expected=dict(capture_id='synthetic',epoch='own',own_seed_bar_hash='seed',milestone=15)
        good=dict(status='PASS_OWN_PREFIX_NATIVE_DIAGNOSTIC_ONLY',capture_id='synthetic',epoch='own',own_seed_bar_hash='seed',native_m5=15,
            ATR_PARITY='PASS_EXACT',MAIN_K_PARITY='PASS_RETAINED_BOUND',original_terminals_preserved=True,
            orders_sent=0,training_executed=False,dataset_admitted=False)
        with TemporaryDirectory() as d:
            p=Path(d)
            for changes,verified in [({},True),({'epoch':'old'},False),({'own_seed_bar_hash':'old_seed'},False),({'training_executed':True},False),({'native_m5':14},False)]:
                (p/'stdout.json').write_text(json.dumps(dict(good,**changes)))
                self.assertEqual(oracle_job_status(p,expected,False)['native_parity_verified'],verified)

    def test_ha_milestone_requires_actual_ha_parity(self):
        with TemporaryDirectory() as d:
            p=Path(d);result=dict(status='PASS_OWN_PREFIX_NATIVE_DIAGNOSTIC_ONLY',capture_id='c',epoch='e',own_seed_bar_hash='seed',native_m5=276,
                ATR_PARITY='PASS_EXACT',MAIN_K_PARITY='PASS_RETAINED_BOUND',HA_PARITY='WAITING',
                original_terminals_preserved=True,orders_sent=0,training_executed=False,dataset_admitted=False)
            (p/'stdout.json').write_text(json.dumps(result))
            self.assertFalse(oracle_job_status(p,dict(capture_id='c',epoch='e',own_seed_bar_hash='seed',milestone=276),False)['native_parity_verified'])
