import json
from pathlib import Path
import tempfile
import unittest
from controller.dataset_maturity import audit_segment,callback_coverage
from controller.isolated_observation import Observation,eof_anchor,GENESIS
from test_isolated_observation import clock,line


class MaturityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.source=self.root/'source.jsonl'
        raw,self.head=line(GENESIS,0,90,kind='SESSION_START');self.source.write_bytes(raw)
        self.obj=Observation.create(self.root/'isolated',self.source,eof_anchor(self.source),clock(),synthetic=True)
        self.addCleanup(self.obj.close);self.sequence=0

    def append(self,uptime,kind='HEARTBEAT',**changes):
        self.sequence+=1;raw,self.head=line(self.head,self.sequence,uptime,kind=kind,**changes)
        with self.source.open('ab') as s:s.write(raw)
        self.obj.pump(lambda:clock(uptime+1))

    def test_heartbeats_are_not_ticks_bars_signals_or_maturity(self):
        self.append(101);self.append(5101)
        result=audit_segment(self.obj.folder)
        self.assertEqual(result['counts'],{'HEARTBEAT':2})
        self.assertEqual(result['coverage']['short_callback_intervals_ms'],5000)
        self.assertEqual(result['m5_bar_records'],0);self.assertEqual(result['certified_market_coverage_ms'],0)
        self.assertTrue(result['membership']['post_eof_only'])

    def test_gap_split_and_disconnect_are_diagnostic_only(self):
        self.append(101);self.append(5101);self.append(25101,connected=False)
        result=audit_segment(self.obj.folder)['coverage']
        self.assertEqual(result['gap_intervals_ms'],20000)
        self.assertEqual(result['disconnections_observed'],1)
        self.assertTrue(all(w['scientific_status']=='QUARANTINED' for w in result['windows']))

    def test_quotes_count_but_no_fake_bars_or_features(self):
        self.append(101,'ONTICK_LATEST_QUOTE');self.append(5101,'ONTICK_LATEST_QUOTE')
        result=audit_segment(self.obj.folder)
        self.assertEqual(result['counts']['ONTICK_LATEST_QUOTE'],2)
        self.assertEqual(result['equal_native_tick_timestamps'],1)
        self.assertEqual(result['duplicate_record_ids'],0)
        self.assertEqual(result['feature_records'],0)

    def test_original_bytes_tamper_rejected(self):
        self.append(101);raw=self.source.read_bytes();self.source.write_bytes(raw.replace(b'37000.0',b'38000.0'))
        with self.assertRaises(ValueError):audit_segment(self.obj.folder)

    def test_journal_hash_tamper_rejected(self):
        self.append(101);path=self.obj.folder/'journal.jsonl';path.write_bytes(path.read_bytes().replace(b'HEARTBEAT',b'BADBEAT00'))
        with self.assertRaisesRegex(ValueError,'JOURNAL_CHAIN_CHANGED'):audit_segment(self.obj.folder)

    def test_live_append_after_checkpoint_not_adopted_by_audit(self):
        self.append(101)
        before=(self.obj.folder/'checkpoint.json').read_bytes()
        raw,_=line(self.head,2,5101)
        with self.source.open('ab') as s:s.write(raw)
        result=audit_segment(self.obj.folder)
        self.assertEqual(result['verified_rows'],1)
        self.assertEqual((self.obj.folder/'checkpoint.json').read_bytes(),before)

    def test_cross_window_duration_conserved(self):
        rows=[dict(callback_uptime_ms=1,connected=True,kind='HEARTBEAT'),dict(callback_uptime_ms=600001,connected=True,kind='HEARTBEAT')]
        result=callback_coverage(rows,0)
        self.assertEqual(sum(w['gap_interval_ms'] for w in result['windows']),600000)
        self.assertEqual(result['short_callback_intervals_ms'],0)


if __name__=='__main__':unittest.main()
