import types
import unittest
from unittest.mock import Mock,patch
from tools.bc_study_worker import RecoveryReference
from tools import bc_pretraining_worker as worker


class BCIPCRecoveryTests(unittest.TestCase):
    def test_memory_retry_waits_for_margin_then_reduces_budget(self):
        low = types.SimpleNamespace(available=worker.ACQUISITION_MEMORY_FLOOR - 1)
        ready = types.SimpleNamespace(available=worker.ACQUISITION_MEMORY_FLOOR)
        disk = types.SimpleNamespace(free=2 * 1024**3)
        with patch.object(worker.ipc, 'run', side_effect=[
            RuntimeError('BC_WAITING_FOR_RESOURCE_MARGIN'), {'processed_this_run': 1}
        ]) as run, patch.object(worker.time, 'sleep') as sleep, patch(
            'psutil.virtual_memory', side_effect=[low, ready]
        ), patch('psutil.disk_usage', return_value=disk):
            self.assertEqual(worker.acquire(2), {'processed_this_run': 1})
            self.assertEqual([call.args for call in run.call_args_list], [(2,), (1,)])
            self.assertEqual(sleep.call_count, 2)

    def test_memory_retry_stops_if_margin_never_returns(self):
        low = types.SimpleNamespace(available=worker.ACQUISITION_MEMORY_FLOOR - 1)
        with patch.object(worker.ipc, 'run', side_effect=RuntimeError(
            'BC_WAITING_FOR_RESOURCE_MARGIN'
        )) as run, patch.object(worker.time, 'sleep') as sleep, patch(
            'psutil.virtual_memory', return_value=low
        ):
            with self.assertRaisesRegex(RuntimeError, 'BC_WAITING_FOR_RESOURCE_MARGIN'):
                worker.acquire(2)
            run.assert_called_once_with(2)
            self.assertEqual(sleep.call_count, 3)

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
