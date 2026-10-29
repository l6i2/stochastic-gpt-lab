import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from prospective_utc import verify_callback,segment_verdict,GENESIS


class ProspectiveTests(unittest.TestCase):
    def write(self,path,rows):
        previous=GENESIS
        with path.open('wb') as stream:
            for row in rows:
                body=json.dumps(row,separators=(',',':'))
                digest=hashlib.sha256((previous+'\n'+body).encode()).hexdigest()
                stream.write(('{"previous":"'+previous+'","sha256":"'+digest+'","payload":'+body+'}\n').encode())
                previous=digest

    def row(self,sequence,kind='ONTICK_LATEST_QUOTE',stamp=1000):
        return dict(sequence=sequence,kind=kind,server='XMGlobalSC-MT5 5',symbol='US30Cash',
            session_id='test',capture_id='test',callback_uptime_ms=10+sequence,
            read_uptime_ms=10+sequence,connected=True,time=stamp//1000,time_msc=stamp,bid=1,ask=2,flags=2)

    def test_chain_partial_duplicates_and_regression_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'native.jsonl';self.write(path,[self.row(0,'SESSION_START'),self.row(1),self.row(2),self.row(3,stamp=999)])
            before=path.read_bytes();value=verify_callback(path)
            self.assertEqual(value['tick_callbacks'],3);self.assertEqual(value['adjacent_duplicate_quotes'],1)
            self.assertEqual(value['native_timestamp_regressions'],1);self.assertEqual(path.read_bytes(),before)
            with path.open('ab') as f:f.write(b'{')
            self.assertTrue(verify_callback(path,value)['partial_tail'])

    def test_tamper_and_truncation_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'native.jsonl';self.write(path,[self.row(0,'SESSION_START'),self.row(1)])
            checkpoint=verify_callback(path)
            self.write(path,[self.row(0,'SESSION_START')])
            with self.assertRaises(ValueError):verify_callback(path,checkpoint)
            path.write_bytes(path.read_bytes().replace(b'"bid":1',b'"bid":9'))
            with self.assertRaises(ValueError):verify_callback(path)

    def test_sequence_identity_and_monotonic_failures(self):
        for key,value in (('sequence',3),('server','OTHER'),('callback_uptime_ms',0)):
            with tempfile.TemporaryDirectory() as d:
                path=Path(d)/'native.jsonl';bad=self.row(1);bad[key]=value
                self.write(path,[self.row(0,'SESSION_START'),bad])
                with self.assertRaises(ValueError):verify_callback(path)

    def test_implementation_and_self_declared_clock_never_authorize(self):
        for ticks in (0,4):
            verdict=segment_verdict(dict(tick_callbacks=ticks),dict(authenticated_utc_bound=True))
            self.assertEqual(verdict['status'],'QUARANTINED');self.assertEqual(verdict['certified_intervals'],[])

    def test_train_rejects_native_witness_path_before_io(self):
        from train_event_source import assert_train_only_source_path
        with self.assertRaises(ValueError):assert_train_only_source_path('outputs/pc_a_prospective_utc/ticks.csv')

    def test_witness_checkpoint_detects_rewritten_prefix(self):
        spec=importlib.util.spec_from_file_location('station',Path(__file__).resolve().parents[1]/'tools/prospective_utc_station.py')
        station=importlib.util.module_from_spec(spec);spec.loader.exec_module(station)
        with tempfile.TemporaryDirectory() as d:
            station.BASE=Path(d)
            station.append_witness({'test':1});station.append_witness({'test':2})
            path=Path(d)/'external_witness.jsonl';rows=path.read_bytes().splitlines(keepends=True)
            path.write_bytes(rows[0])
            with self.assertRaises(ValueError):station.append_witness({'test':3})
