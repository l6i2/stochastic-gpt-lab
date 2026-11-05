import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from controller.authorized_capture import once,sha
from controller.isolated_observation import host_clock
from tools.cf_study_station import StudyStore
from tools.cf_quality_monitor import run_once


class QualityMonitorTests(unittest.TestCase):
    def fixture(self,root):
        base=root/'outputs/us30cash_m5_native_observations';folder=base/'synthetic';folder.mkdir(parents=True)
        once(folder/'manifest.json',dict(source_hashes={}))
        once(base/'current.json',dict(capture_id='synthetic',manifest_sha256=sha(folder/'manifest.json')))
        once(base/'status.json',dict(capture_id='synthetic',clock=host_clock(),status='ACTIVE_QUARANTINED',technical_warmup=0,consecutive_signals=0))
        store=StudyStore(folder/'snapshots.sqlite3');store.commit([]);store.close()
        return base,folder

    @patch('tools.cf_quality_monitor.verify_roles',return_value=None)
    def test_repeat_skips_verified_prefix_and_wrong_cursor_fails(self,_):
        with TemporaryDirectory() as d:
            root=Path(d);base,folder=self.fixture(root)
            first=run_once(root);second=run_once(root)
            self.assertEqual(second['new_records_verified'],0)
            self.assertEqual(first['chain_head'],second['chain_head'])
            cursor=json.loads((base/'quality_checkpoint.json').read_text());cursor['head']='wrong'
            (base/'quality_checkpoint.json').write_text(json.dumps(cursor))
            with self.assertRaisesRegex(ValueError,'PREFIX_CHANGED'):run_once(root)

    @patch('tools.cf_quality_monitor.verify_roles',return_value=None)
    def test_explicit_interruption_excludes_orphan_queries_without_blocking_future(self,_):
        with TemporaryDirectory() as d:
            root=Path(d);base,folder=self.fixture(root)
            store=StudyStore(folder/'snapshots.sqlite3')
            store.commit([dict(kind='DATABASE_QUERY_OBSERVATION',epoch='s',frame_seconds=60,
                observation=dict(start_native_msc=0,end_native_exclusive_msc=60000)),
                dict(kind='OBSERVATION_INTERRUPTION')]);store.close()
            result=run_once(root)
            self.assertEqual(result['orphan_queries_excluded_on_explicit_interruption'],1)
            self.assertFalse(result['scientific_admission'])
