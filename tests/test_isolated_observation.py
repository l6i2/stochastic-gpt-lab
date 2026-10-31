import hashlib
from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from controller.isolated_observation import Observation,eof_anchor,GENESIS
from controller.pretrain_contracts import FEATURES


def clock(uptime=100,boot='synthetic_boot'):
    return dict(host_utc_label='2026-10-31T00:00:00+00:00',monotonic_ns=uptime*1000000,
                uptime_ms=uptime,boot_id=boot,utc_certified=False)


def line(previous,sequence,uptime,**changes):
    row=dict(kind='ONTICK_LATEST_QUOTE',capture_id='synthetic_source',session_id='s',sequence=sequence,
        symbol='US30Cash',server='XMGlobalSC-MT5 5',callback_uptime_ms=uptime,
        callback_program_us=uptime*1000,read_uptime_ms=uptime,receipt_host_gmt_seconds=0,
        connected=True,time=300,time_msc=300001,bid=37000.0,ask=37001.0,flags=6)|changes
    body=json.dumps(row,separators=(',',':'))
    digest=hashlib.sha256((previous+'\n'+body).encode()).hexdigest()
    return (json.dumps(dict(previous=previous,sha256=digest),separators=(',',':'))[:-1]+',"payload":'+body+'}\r\n').encode(),digest


class IsolatedObservationTests(unittest.TestCase):
    @contextmanager
    def workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            try:yield tmp
            finally:self.doCleanups()

    def create(self,root):
        source=root/'source.jsonl'
        before,digest=line(GENESIS,0,90,kind='SESSION_START')
        source.write_bytes(before)
        obj=Observation.create(root/'new_only',source,eof_anchor(source),clock(),synthetic=True)
        self.addCleanup(obj.close)
        return obj,source,before,digest

    def append(self,obj,source,parent,sequence,uptime,**changes):
        raw,digest=line(parent,sequence,uptime,**changes)
        with source.open('ab') as stream:stream.write(raw)
        obj.pump(lambda:clock(uptime+1))
        return digest

    def test_exclusive_route_real_new_id_and_no_prefix_adoption(self):
        with self.workspace() as tmp:
            root=Path(tmp);obj,source,before,digest=self.create(root)
            self.assertEqual(obj.state['source_records'],0)
            self.assertFalse(obj.manifest['dataset_admitted'])
            self.assertEqual(obj.folder.parent,root/'new_only')
            self.assertTrue(obj.manifest['capture_id'].startswith('obs_'))
            self.append(obj,source,digest,1,101)
            event=json.loads((obj.folder/'journal.jsonl').read_text().splitlines()[0])['payload']['event']
            self.assertEqual(event['native_line'].encode(),source.read_bytes()[len(before):])
            self.assertFalse(event['event_creation_equals_receipt'])
            self.assertEqual(source.read_bytes()[:len(before)],before)

    def test_restart_preserves_id_cursor_and_does_not_duplicate(self):
        with self.workspace() as tmp:
            obj,source,_,digest=self.create(Path(tmp))
            self.append(obj,source,digest,1,101);folder=obj.folder;capture_id=obj.manifest['capture_id'];obj.close()
            resumed=Observation.resume(folder,clock(103));self.addCleanup(resumed.close)
            self.assertEqual(resumed.pump(lambda:clock(104)),0)
            self.assertEqual(resumed.state['source_records'],1)
            self.assertEqual(resumed.manifest['capture_id'],capture_id)

    def test_complete_append_before_checkpoint_is_recovered_once(self):
        with self.workspace() as tmp:
            obj,source,_,digest=self.create(Path(tmp))
            old=(obj.folder/'checkpoint.json').read_bytes()
            self.append(obj,source,digest,1,101);folder=obj.folder;obj.close()
            (folder/'checkpoint.json').write_bytes(old)
            resumed=Observation.resume(folder,clock(103));self.addCleanup(resumed.close)
            self.assertEqual(resumed.state['source_records'],1)
            self.assertEqual(resumed.pump(lambda:clock(104)),0)

    def test_partial_source_waits_without_cursor_advance(self):
        with self.workspace() as tmp:
            obj,source,before,digest=self.create(Path(tmp))
            raw,_=line(digest,1,101)
            with source.open('ab') as stream:stream.write(raw[:-2])
            self.assertEqual(obj.pump(lambda:clock(102)),0)
            self.assertEqual(obj.state['source_offset'],len(before))
            with source.open('ab') as stream:stream.write(raw[-2:])
            self.assertEqual(obj.pump(lambda:clock(103)),1)

    def test_old_or_equal_cut_quote_is_not_adopted(self):
        with self.workspace() as tmp:
            obj,source,_,digest=self.create(Path(tmp))
            self.append(obj,source,digest,1,100)
            event=json.loads((obj.folder/'journal.jsonl').read_text().splitlines()[0])['payload']['event']
            self.assertIsNone(event['native_line'])
            self.assertEqual(obj.state['tick_callbacks'],0)

    def test_gap_and_duplicate_are_rejected_not_backfilled(self):
        for sequence in (0,2):
            with self.subTest(sequence=sequence),tempfile.TemporaryDirectory() as tmp:
                obj,source,_,digest=self.create(Path(tmp))
                raw,_=line(digest,sequence,101)
                with source.open('ab') as stream:stream.write(raw)
                with self.assertRaisesRegex(ValueError,'GAP_DUPLICATE'):obj.pump(lambda:clock(102))
                obj.close()

    def test_disconnect_native_regression_and_heartbeat_gap_remain_quarantined(self):
        with self.workspace() as tmp:
            obj,source,_,digest=self.create(Path(tmp))
            digest=self.append(obj,source,digest,1,101)
            digest=self.append(obj,source,digest,2,50101,kind='HEARTBEAT',connected=False)
            self.append(obj,source,digest,3,50102,time=299,time_msc=299999)
            events=[json.loads(s)['payload']['event'] for s in (obj.folder/'journal.jsonl').read_text().splitlines()]
            self.assertEqual(events[1]['callback_gap_ms'],50000)
            self.assertIn('DISCONNECTED',events[1]['quarantine_flags'])
            self.assertIn('NATIVE_TIMESTAMP_REGRESSION_UNMAPPED',events[2]['quarantine_flags'])
            self.assertFalse(obj.manifest['scientific_acceptance'])

    def test_new_boot_session_clock_reset_and_invalid_quote_fail_closed(self):
        for change in ({'session_id':'another'},{'callback_uptime_ms':89},{'ask':36000.0},{'time':299}):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
                obj,source,_,digest=self.create(Path(tmp))
                raw,_=line(digest,1,101,**change)
                with source.open('ab') as stream:stream.write(raw)
                with self.assertRaises(ValueError):obj.pump(lambda:clock(102))
                obj.close()
        with self.workspace() as tmp:
            obj,_,_,_=self.create(Path(tmp));folder=obj.folder;obj.close()
            with self.assertRaisesRegex(ValueError,'BOOT_OR'):Observation.resume(folder,clock(103,'another_boot'))

    def test_local_monotonic_regression_blocks_without_using_wall_clock_as_event(self):
        with self.workspace() as tmp:
            obj,source,_,digest=self.create(Path(tmp))
            raw,_=line(digest,1,101)
            with source.open('ab') as stream:stream.write(raw)
            with self.assertRaisesRegex(ValueError,'LOCAL_MONOTONIC_REGRESSION'):
                obj.pump(lambda:clock(102)|{'monotonic_ns':1})
            obj.pump(lambda:clock(102)|{'host_utc_label':'2099-01-01T00:00:00+00:00'})
            event=json.loads((obj.folder/'journal.jsonl').read_text().splitlines()[0])['payload']['event']
            self.assertEqual(json.loads(event['native_line'])['payload']['time_msc'],300001)
            self.assertEqual(event['native_event_utc_mapping'],'UNVERIFIED')

    def test_tamper_partial_journal_and_truncation_preserved(self):
        with self.workspace() as tmp:
            obj,source,_,digest=self.create(Path(tmp))
            self.append(obj,source,digest,1,101);folder=obj.folder;obj.close()
            path=folder/'journal.jsonl';original=path.read_bytes()
            path.write_bytes(original[:-1])
            with self.assertRaisesRegex(ValueError,'PARTIAL_JOURNAL'):Observation.resume(folder,clock(102))
            self.assertEqual(path.read_bytes(),original[:-1])
            path.write_bytes(original.replace(b'37000',b'38000'))
            with self.assertRaisesRegex(ValueError,'HASH_CHANGED'):Observation.resume(folder,clock(103))

    def test_single_writer_lock(self):
        with self.workspace() as tmp:
            obj,_,_,_=self.create(Path(tmp))
            with self.assertRaisesRegex(RuntimeError,'SINGLE_WRITER'):Observation.resume(obj.folder,clock(102))

    def test_checkpoint_io_failure_stops_writer_and_recovers_complete_row(self):
        with self.workspace() as tmp:
            obj,source,_,digest=self.create(Path(tmp))
            raw,_=line(digest,1,101)
            with source.open('ab') as stream:stream.write(raw)
            with patch('controller.isolated_observation.atomic',side_effect=OSError('SYNTHETIC_STORAGE_FAILURE')):
                with self.assertRaises(OSError):obj.pump(lambda:clock(102))
            with self.assertRaisesRegex(RuntimeError,'PREVIOUS_STORAGE_ERROR'):
                obj._commit({'kind':'synthetic'},dict(obj.state))
            folder=obj.folder;obj.close()
            resumed=Observation.resume(folder,clock(104));self.addCleanup(resumed.close)
            self.assertEqual(resumed.state['source_records'],1)
            self.assertEqual(resumed.pump(lambda:clock(105)),0)

    def test_unknown_historical_kind_and_source_truncation_rejected(self):
        with self.workspace() as tmp:
            obj,source,before,digest=self.create(Path(tmp))
            raw,_=line(digest,1,101,kind='COPY_TICKS_HISTORICAL')
            with source.open('ab') as stream:stream.write(raw)
            with self.assertRaisesRegex(ValueError,'NO_HISTORICAL_REQUERY'):obj.pump(lambda:clock(102))
            source.write_bytes(before[:-1])
            with self.assertRaisesRegex(ValueError,'SOURCE_TRUNCATED'):obj.pump(lambda:clock(103))

    def test_new_boot_gets_linked_segment_and_excludes_new_session_prefix(self):
        with self.workspace() as tmp:
            root=Path(tmp);obj,source,_,digest=self.create(root)
            self.append(obj,source,digest,1,101);previous=obj.folder;previous_id=obj.manifest['capture_id'];obj.close()
            next_source=root/'new_session.jsonl'
            before,digest=line(GENESIS,0,1,kind='SESSION_START',session_id='new_session')
            next_source.write_bytes(before)
            segment=Observation.new_segment(previous,root/'new_only',next_source,clock(2,'next_boot'),synthetic=True)
            self.addCleanup(segment.close)
            self.assertNotEqual(segment.manifest['capture_id'],previous_id)
            self.assertEqual(segment.manifest['parent_segment']['capture_id'],previous_id)
            self.assertEqual(segment.state['source_offset'],len(before))
            self.assertEqual(segment.state['source_records'],0)
            raw,_=line(digest,1,3,session_id='new_session')
            with next_source.open('ab') as stream:stream.write(raw)
            segment.pump(lambda:clock(4,'next_boot'))
            self.assertEqual(segment.state['source_records'],1)
            self.assertFalse(segment.manifest['dataset_admitted'])

    def test_end_to_end_features_persist_without_targets_and_restart(self):
        with self.workspace() as tmp:
            obj,source,_,digest=self.create(Path(tmp))
            for i in range(1,4):digest=self.append(obj,source,digest,i,100+i)
            deps=[dict(feature=f,oldest_source_index=100,last_closed_index=800,
                decision_arrival_index=801,ready_stage=1,decision_stage=2,closed_bars=350,seed_index=100) for f in FEATURES]
            obj.synthetic_features(deps,100,{f:1.0 for f in FEATURES})
            folder=obj.folder;obj.close()
            resumed=Observation.resume(folder,clock(110));self.addCleanup(resumed.close)
            self.assertEqual(resumed.state['synthetic_feature_records'],1)
            self.assertEqual(resumed.state['tick_callbacks'],3)
            self.assertFalse(resumed.manifest['training_authorized'])
            event=json.loads((folder/'journal.jsonl').read_text().splitlines()[-1])['payload']['event']
            self.assertFalse(event['targets_present'])
            self.assertFalse(event['availability']['real_feature_bytes_verified'])


if __name__=='__main__':unittest.main()
