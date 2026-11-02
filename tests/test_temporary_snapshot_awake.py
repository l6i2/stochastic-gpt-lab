import json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from tools.temporary_snapshot_trial_awake import run


class TemporaryAwake(unittest.TestCase):
    def test_bounded_request_released_without_sleeping_in_test(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'authorization.json').write_text(json.dumps(dict(temporary_awake_authorized=True,maximum_seconds=1200)))
            kernel=Mock();kernel.SetThreadExecutionState.side_effect=[0x80000000,0x80000003]
            with patch('tools.temporary_snapshot_trial_awake.ctypes.windll.kernel32',kernel),patch('tools.temporary_snapshot_trial_awake.time.monotonic',side_effect=[0,0,1201,1201]),patch('tools.temporary_snapshot_trial_awake.time.sleep') as sleep:
                run(p);sleep.assert_not_called()
            self.assertEqual([x.args[0] for x in kernel.SetThreadExecutionState.call_args_list],[0x80000003,0x80000000])
            self.assertEqual(json.loads((p/'status.json').read_text())['state'],'RELEASED')

    def test_no_authorization_does_not_request_power(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'authorization.json').write_text(json.dumps(dict(temporary_awake_authorized=False,maximum_seconds=1200)))
            with patch('tools.temporary_snapshot_trial_awake.ctypes.windll.kernel32') as kernel:
                with self.assertRaises(PermissionError):run(p)
                kernel.SetThreadExecutionState.assert_not_called()

    def test_release_even_if_trial_loop_fails(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'authorization.json').write_text(json.dumps(dict(temporary_awake_authorized=True,maximum_seconds=1200)))
            kernel=Mock();kernel.SetThreadExecutionState.side_effect=[0x80000000,0x80000003]
            with patch('tools.temporary_snapshot_trial_awake.ctypes.windll.kernel32',kernel),patch('tools.temporary_snapshot_trial_awake.time.monotonic',side_effect=[0,0,1,2]),patch('tools.temporary_snapshot_trial_awake.time.sleep',side_effect=RuntimeError('test interruption')):
                with self.assertRaises(RuntimeError):run(p)
            self.assertEqual(kernel.SetThreadExecutionState.call_args_list[-1].args[0],0x80000000)


if __name__=='__main__':unittest.main()
