import sqlite3
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from controller.cf_recovery import classify, classify_boot, snapshot
from controller.authorized_capture import manager_lock
from controller.native_database_snapshots import Store
from tools.cf_study_station import DurabilityFailure, StudyStore, durable_publish


class CfRecoveryTests(unittest.TestCase):
    def test_abrupt_exit_during_sqlite_write_preserves_committed_prefix(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'capture.sqlite3'
            store = Store(path)
            store.commit([dict(kind='CF_M1_M5_PARITY', matched=True)])
            before, _ = snapshot(path)
            store.close()
            script = """
import os, sqlite3, sys
db = sqlite3.connect(sys.argv[1]); db.execute('BEGIN IMMEDIATE')
db.execute('INSERT INTO records VALUES(?, ?, ?, ?)', (2, 'partial', 'partial', '{}'))
db.execute('UPDATE state SET body = ?', ('{}',))
os._exit(23)
"""
            crashed = subprocess.run([sys.executable,'-c',script,str(path)],timeout=15)
            self.assertEqual(crashed.returncode,23)
            self.assertEqual(snapshot(path,before)[0],before)
            reopened = Store(path)
            reopened.commit([dict(kind='NEW_OBSERVATION_EPOCH',epoch='new',reason='PROCESS_RESTART_FRESH_CUT_NO_BACKFILL')])
            reopened.close()
            after, events = snapshot(path,before)
            self.assertGreater(after['records'],before['records'])
            self.assertEqual(after['TOTAL_VERIFIED_M5'],1)
            self.assertEqual(after['CURRENT_CONSECUTIVE_M5'],0)
            self.assertEqual(after['SCIENTIFICALLY_ELIGIBLE_M5'],0)
            self.assertEqual(events[0]['classification'],'UNKNOWN_INTERRUPTION')

    def test_missing_checkpoint_and_wrong_prefix_fail_closed(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'capture.sqlite3'
            store = Store(path);store.commit([]);store.close()
            before, _ = snapshot(path)
            with self.assertRaisesRegex(ValueError,'PREFIX_CHANGED'):
                snapshot(path,dict(before,chain_head='changed'))
            db=sqlite3.connect(path)
            try:
                with db:db.execute('DELETE FROM state')
            finally:db.close()
            with self.assertRaisesRegex(ValueError,'CHECKPOINT_MISSING'):
                snapshot(path)

    @unittest.skipUnless(sys.platform == 'win32', 'Windows exclusive manager lock')
    def test_duplicate_process_cannot_take_recovery_lock(self):
        with TemporaryDirectory() as directory, manager_lock(Path(directory)):
            code = "from pathlib import Path; from controller.authorized_capture import manager_lock; import sys\nwith manager_lock(Path(sys.argv[1])): pass"
            other = subprocess.run([sys.executable,'-c',code,directory],capture_output=True,text=True,timeout=15)
            self.assertNotEqual(other.returncode,0)
            self.assertIn('CAPTURE_MANAGER_ALREADY_RUNNING',other.stderr)

    def test_durability_failures_escape_native_batch_retry(self):
        with TemporaryDirectory() as directory:
            store = StudyStore(Path(directory)/'capture.sqlite3');store.commit([]);store.fail_stop=True
            with patch.object(Store,'commit',side_effect=OSError('disk')):
                with self.assertRaises(DurabilityFailure):store.commit([])
            self.assertEqual(store.count,1)
            store.close()
            with patch('tools.cf_study_station.atomic',side_effect=OSError('status file locked')):
                with self.assertRaises(DurabilityFailure):durable_publish(Path(directory)/'status.json',{})
            self.assertFalse(issubclass(DurabilityFailure,Exception))

    def test_classification_requires_specific_evidence(self):
        self.assertEqual(classify(dict(reason='WINDOWS_VERIFIED_SLEEP_EVENT')),'SLEEP')
        self.assertEqual(classify(dict(reason='XM_DISCONNECTED')),'XM_DISCONNECT')
        self.assertEqual(classify(dict(reason='NATIVE_MINUTE_GAP_SESSION_CAUSE_UNKNOWN')),'UNKNOWN_INTERRUPTION')
        self.assertEqual(classify(dict(kind='CF_VERIFIED_SESSION_TRANSITION',review={'bridge_allowed':True})),'MARKET_CLOSED')
        stop = dict(provider='Microsoft-Windows-Kernel-General',id=13)
        boot = dict(provider='Microsoft-Windows-Kernel-General',id=12)
        intent = dict(provider='User32',id=1074,intent='restart')
        self.assertEqual(classify_boot([intent]),'UNKNOWN_INTERRUPTION')
        self.assertEqual(classify_boot([intent,stop,boot]),'WINDOWS_RESTART')
        self.assertEqual(classify_boot([dict(intent,intent='power off'),stop,boot]),'NORMAL_SHUTDOWN')
        self.assertEqual(classify_boot([intent,stop,boot,boot]),'UNKNOWN_INTERRUPTION')
        self.assertEqual(classify_boot([intent,stop,boot,dict(provider='Microsoft-Windows-Kernel-Power',id=41)]),'UNKNOWN_INTERRUPTION')
