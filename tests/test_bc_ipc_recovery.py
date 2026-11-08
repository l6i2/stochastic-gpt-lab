import types
import unittest
from unittest.mock import Mock,patch
from tools.bc_study_worker import RecoveryReference


class BCIPCRecoveryTests(unittest.TestCase):
    def test_retry_only_attaches_exact_running_process_with_bounded_timeout(self):
        api=Mock();api.last_error.return_value=(-10005,'SYNTHETIC_IPC_TIMEOUT');api.initialize.return_value=True
        process=types.SimpleNamespace(pid=123,info=dict(exe='C:/Program Files/XM Global SC MT5 Terminal/terminal64.exe'))
        with patch('tools.bc_study_worker.NativeReference.connect',side_effect=ValueError('XM_READ_ONLY_ATTACH_FAILED')),patch.dict('sys.modules',MetaTrader5=api),patch('psutil.process_iter',return_value=[process]),patch('psutil.pid_exists',return_value=True),patch('tools.bc_study_worker.station.identity',return_value=dict(tick_size=.01)),patch('tools.bc_study_worker.once') as record:
            ref=RecoveryReference();ref.connect()
            self.assertEqual(ref.bound_pid,123);api.initialize.assert_called_once_with(path=process.info['exe'],timeout=20000)
            self.assertFalse(record.call_args.args[1]['terminal_restarted'])

    def test_identity_failure_never_becomes_a_retry(self):
        api=Mock()
        with patch('tools.bc_study_worker.NativeReference.connect',side_effect=ValueError('PINNED_XM_DEMO_BID_CHART_IDENTITY_MISMATCH')),patch.dict('sys.modules',MetaTrader5=api):
            with self.assertRaisesRegex(ValueError,'IDENTITY_MISMATCH'):RecoveryReference().connect()
            api.initialize.assert_not_called()
