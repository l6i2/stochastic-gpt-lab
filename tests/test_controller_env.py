import unittest
from pathlib import Path
from controller.mt5_env import account_mode, require_active_environment, resolve_active


class EnvironmentTests(unittest.TestCase):
    def test_unique_active_folder_and_paired_editor(self):
        row = dict(terminal=str(Path('XM/terminal64.exe').resolve()),
                   metaeditor=str(Path('XM/metaeditor64.exe').resolve()),
                   data_folder='data', xm=True)
        process = dict(ExecutablePath=row['terminal'], CommandLine='terminal64.exe')
        self.assertEqual(resolve_active([process], [row]), row)
        self.assertIsNone(resolve_active([], [row]))
        self.assertIsNone(resolve_active([process, process], [row]))
        self.assertIsNone(resolve_active([process], [row, row]))
        process['CommandLine'] += ' /portable'
        self.assertIsNone(resolve_active([process], [row]))

    def test_modes_fail_closed(self):
        self.assertEqual(account_mode(0), 'DEMO')
        self.assertEqual(account_mode(2), 'REAL')
        self.assertEqual(account_mode(None), 'UNKNOWN')
        with self.assertRaises(RuntimeError):
            require_active_environment({'DATA_FOLDER': None})
        with self.assertRaises(RuntimeError):
            require_active_environment({'DATA_FOLDER': 'data', 'XM_ACTIVE': True,
                                        'READ_ONLY_API_STATUS': 'PACKAGE_UNAVAILABLE'})


if __name__ == '__main__':
    unittest.main()
