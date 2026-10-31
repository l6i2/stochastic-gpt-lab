from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
import unittest

from controller.capture_continuity_monitor import audit
from controller.isolated_observation import Observation,eof_anchor,GENESIS
from test_isolated_observation import line,clock


class ContinuityMonitorTests(unittest.TestCase):
    @contextmanager
    def workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            try:yield Path(tmp)
            finally:self.doCleanups()

    def fixture(self,root):
        source=root/'source.jsonl';raw,parent=line(GENESIS,0,90,kind='SESSION_START');source.write_bytes(raw)
        capture=root/'capture';capture.mkdir()
        writer=Observation.create(capture/'segments',source,eof_anchor(source),clock(100),synthetic=True)
        self.addCleanup(writer.close)
        (capture/'collection_manifest.json').write_text(json.dumps({'capture_id':'synthetic_capture'}))
        (capture/'runtime_state.json').write_text(json.dumps(dict(active_segment=writer.folder.name,segments=[writer.folder.name])))
        return capture,writer,source,parent

    def append(self,writer,source,parent,sequence,uptime,connected=True):
        raw,digest=line(parent,sequence,uptime,kind='HEARTBEAT',connected=connected)
        with source.open('ab') as stream:stream.write(raw)
        writer.pump(lambda:clock(uptime+1))
        return digest

    def test_gap_disconnect_reconnect_and_incremental_idempotence(self):
        with self.workspace() as root:
            capture,writer,source,parent=self.fixture(root)
            for seq,up,connected in ((1,110,True),(2,50110,False),(3,55110,False),(4,60110,True)):
                parent=self.append(writer,source,parent,seq,up,connected)
            result=audit(capture,lambda:clock(60120))
            self.assertEqual(result['maximum_callback_gap_ms'],50000)
            self.assertEqual(result['callback_gaps'],1)
            self.assertEqual(result['disconnection_starts'],1)
            self.assertEqual(result['reconnection_observations'],1)
            self.assertTrue(result['last_connected'])
            prior={p.name:p.read_bytes() for p in (capture/'continuity_incidents').glob('*.json')}
            again=audit(capture,lambda:clock(60130))
            self.assertEqual(result,again)
            self.assertEqual(prior,{p.name:p.read_bytes() for p in (capture/'continuity_incidents').glob('*.json')})
            self.assertFalse(result['dataset_admission'])

    def test_incident_mutation_and_raw_prefix_change_are_rejected(self):
        with self.workspace() as root:
            capture,writer,source,parent=self.fixture(root)
            self.append(writer,source,parent,1,50110,False)
            audit(capture,lambda:clock(50120))
            incident=next((capture/'continuity_incidents').glob('*.json'))
            data=json.loads(incident.read_text());data['fact']['elapsed_ms']=0;incident.write_text(json.dumps(data))
            with self.assertRaises(ValueError):audit(capture,lambda:clock(50130))

    def test_loss_of_monitor_checkpoint_replays_without_duplicate_incidents(self):
        with self.workspace() as root:
            capture,writer,source,parent=self.fixture(root)
            self.append(writer,source,parent,1,50110,False)
            first=audit(capture,lambda:clock(50120))
            # Only derived monitor state is removed in this isolated temporary fixture.
            (capture/'continuity_monitor_cursor.json').unlink()
            second=audit(capture,lambda:clock(50130))
            self.assertEqual(first['incident_ids'],second['incident_ids'])
            self.assertEqual(first['verified_rows'],second['verified_rows'])

    def test_normal_callbacks_do_not_prove_coverage_or_event_utc(self):
        with self.workspace() as root:
            capture,writer,source,parent=self.fixture(root)
            self.append(writer,source,parent,1,110)
            result=audit(capture,lambda:clock(120))
            self.assertEqual(result['callback_gaps'],0)
            self.assertIn('UNPROVEN',result['capture_completeness'])
            self.assertFalse(result['training_authorized'])

    def test_journal_truncation_is_detected_without_a_new_callback(self):
        with self.workspace() as root:
            capture,writer,source,parent=self.fixture(root)
            self.append(writer,source,parent,1,110)
            audit(capture,lambda:clock(120))
            (writer.folder/'journal.jsonl').write_bytes(b'')
            with self.assertRaisesRegex(ValueError,'JOURNAL_TRUNCATED'):audit(capture,lambda:clock(130))


if __name__=='__main__':unittest.main()
