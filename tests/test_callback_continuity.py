import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from callback_continuity import analyze,receipt_projection


class ContinuityTests(unittest.TestCase):
    def run_rows(self,rows):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'rows.jsonl';p.write_text(''.join(json.dumps({'payload':r})+'\n' for r in rows))
            return analyze(p)

    def row(self,seq,uptime,kind='HEARTBEAT'):
        return dict(sequence=seq,callback_uptime_ms=uptime,callback_program_us=uptime*1000,
            receipt_host_gmt_seconds=100+uptime//1000,kind=kind,session_id='TEST',connected=True,time=999,time_msc=999999)

    def test_gap_with_tick_is_not_certified_loss_or_disconnect(self):
        rows=[self.row(0,0),self.row(1,40000,'ONTICK_LATEST_QUOTE'),self.row(2,46469)]
        r=self.run_rows(rows);g=r['incidents'][0]
        self.assertEqual(g['elapsed_ms'],46469);self.assertEqual(g['between_tick_callbacks'],1)
        self.assertEqual(g['cause'],'UNDETERMINED');self.assertEqual(g['real_event_loss'],'UNVERIFIED')
        self.assertEqual(r['certified_segments'],[])
        self.assertTrue(all(s['status']=='QUARANTINED' for s in r['segments']))

    def test_nominal_idle_timer_is_not_market_closure(self):
        r=self.run_rows([self.row(0,0),self.row(1,5000),self.row(2,10000)])
        self.assertEqual(r['incidents'],[]);self.assertEqual(r['segments'][0]['status'],'QUARANTINED')

    def test_incident_identity_stable_and_segments_do_not_overlap(self):
        rows=[self.row(0,0),self.row(1,5000),self.row(2,20000),self.row(3,25000)]
        a=self.run_rows(rows);b=self.run_rows(rows+[self.row(4,30000)])
        self.assertEqual(a['incidents'][0]['incident_id'],b['incidents'][0]['incident_id'])
        self.assertTrue(all(x['end_callback_uptime_ms']<=y['start_callback_uptime_ms'] for x,y in zip(b['segments'],b['segments'][1:])))

    def test_receipt_projection_is_explicitly_uncertified(self):
        r=receipt_projection(dict(anchor_kernel_uptime_ms_interval=[100,102],comparison=dict(status='REFERENCE_QUORUM',utc_lower_ns=10000000,utc_upper_ns=20000000)),99)
        self.assertEqual((r['utc_model_lower_ns'],r['utc_model_upper_ns']),(7000000,19000000))
        self.assertFalse(r['certified']);self.assertFalse(r['event_time_inferred'])
        self.assertIsNone(receipt_projection({'comparison':{'status':'UNVERIFIED'}},99))
