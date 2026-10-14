import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from controller.safety_gate import assert_research_range_allowed, is_train_range, is_validation_range
from controller.tester_config import config, preset
from controller.compile_runner import ea_path, sha256
from controller.tester_runner import classify_log
from controller.artifact_collector import find_artifacts
from controller.history_orchestrator import plan
from controller.profiles import BASE_EA, BAR_EA, profile


class ControllerSafetyTests(unittest.TestCase):
    def test_bar_export_is_explicitly_allowed_and_isolates_evidence(self):
        self.assertNotEqual(profile(BASE_EA)['namespace'], profile(BAR_EA)['namespace'])
        self.assertIn('bar_execution_quotes.csv', profile(BAR_EA)['outputs'])
        self.assertNotIn('ExecutionQuoteOutputFile', preset('test', BASE_EA))
        self.assertEqual(preset('test', BAR_EA)['ExecutionQuoteOutputFile'], 'test_bar_execution_quotes.csv')
        configured = config('2024-01-01', '2024-01-31', 'test.set', 'report', ea=BAR_EA)
        self.assertIn('Expert=StochasticBarDecisionResearch\\StochasticBarDecisionResearchEA', configured)
        with self.assertRaises(RuntimeError):
            profile('unregistered')

    def test_dates_and_crossing(self):
        self.assertTrue(is_train_range('2024-01-01', '2024-01-31'))
        self.assertTrue(is_validation_range('2025-09-01', '2025-09-30'))
        for start, end in [('2026-03-20', '2026-03-20'), ('2024-01-01', '2026-04-01')]:
            with self.assertRaisesRegex(RuntimeError, 'FINAL_TEST_GATE_BLOCKED'):
                assert_research_range_allowed(start, end)
        with self.assertRaises(ValueError):
            assert_research_range_allowed('2024-02-01', '2024-01-01')

    def test_config_preset_reproducible_and_safe(self):
        a = config('2024-01-01', '2024-01-31', 'r1.set', 'report')
        self.assertEqual(a, config('2024-01-01', '2024-01-31', 'r1.set', 'report'))
        self.assertIn('Model=4', a)
        self.assertIn('ToDate=2024.02.01', a)
        self.assertIn('Optimization=0', a)
        self.assertEqual(preset('r1'), preset('r1'))
        self.assertEqual(preset('r1')['LIVE_TRADING'], 'false')
        self.assertFalse(any('password' in k.lower() or 'login' in k.lower() for k in preset('r1')))

    def test_active_folder_and_wrong_ea_rejected(self):
        with self.assertRaises(RuntimeError):
            ea_path({'DATA_FOLDER': None})
        with self.assertRaises(RuntimeError):
            ea_path({'DATA_FOLDER': 'data', 'XM_ACTIVE': True,
                     'READ_ONLY_API_STATUS': 'VERIFIED'}, 'OtherEA')

    def test_log_completion_is_required(self):
        self.assertEqual(classify_log('shutdown finished'), 'INCOMPLETE')
        self.assertEqual(classify_log('test passed'), 'PASS')
        for failure in ['fatal', 'OnInit error', 'no history', 'no real ticks', 'invalid parameter', 'file open error']:
            self.assertEqual(classify_log('test passed\n' + failure), 'FAIL')

    def test_artifacts_require_run_identity_and_freshness(self):
        from controller.artifact_collector import OUTPUTS
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'MQL5/Files'
            root.mkdir(parents=True)
            environment = {'TESTER_AGENT_FOLDERS': [tmp]}
            for name in OUTPUTS:
                (root / ('old_' + name)).write_text('old')
            self.assertIsNone(find_artifacts(environment, 'new', 0))
            self.assertIsNotNone(find_artifacts(environment, 'old', 0))
            self.assertIsNone(find_artifacts(environment, 'old', 0, profile(BAR_EA)['outputs']))
            for name in profile(BAR_EA)['outputs']:
                if not (root/('old_'+name)).exists():
                    (root/('old_'+name)).write_text('separate path evidence')
            self.assertIsNotNone(find_artifacts(environment, 'old', 0, profile(BAR_EA)['outputs']))
            self.assertIsNone(find_artifacts(environment, 'old', 9999999999))
            self.assertEqual(sha256(root / 'old_stochastic_events.csv'), hashlib.sha256(b'old').hexdigest())

    def test_historical_plan_stops_before_final(self):
        blocks = plan()
        self.assertEqual(blocks[0]['DATE_FROM'], '2023-12-20')
        self.assertEqual(blocks[-1]['DATE_TO'], '2026-03-19')
        for block in blocks:
            assert_research_range_allowed(block['DATE_FROM'], block['DATE_TO'])


if __name__ == '__main__':
    unittest.main()
