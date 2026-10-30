import copy
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from nts_xm_correlation import AUTH, correlate


class CorrelationTests(unittest.TestCase):
    def row(self, u=5000, **changes):
        r=dict(kind='ONTICK_LATEST_QUOTE',session_id='S',sequence=u,callback_uptime_ms=u,
               read_uptime_ms=u,receipt_host_gmt_seconds=100+u//1000,connected=True,time_msc=105000)
        r.update(changes)
        return r

    def record(self,u,boot='B'):
        t=(100+u//1000)*1000000000
        m=dict(authentication=AUTH,protocol='RFC8915_NTS_AEAD15_TLS13',capture_id=str(u),
               receive_kernel_uptime_ms_interval=[u,u],utc_receive_interval_model_ns=[t-10,t+10],
               host_receive_ns=t,offset_server_minus_host_ns=[-10,10],rtt_monotonic_ns=20,
               server_advertised_error_ns=1,server_transmit_utc_ns=t,server_receive_utc_ns=t)
        return dict(payload=dict(boot_identity=boot,run_started_kernel_uptime_ms=u,
            native_receipt_correlations={'S.jsonl':{'native_tick':{'sequence':1}}},
            results=[dict(status='AUTHENTICATED_MEASUREMENT',measurement=m)]))

    def records(self):return [self.record(0),self.record(10000)]

    def test_small_differences_only_partial_never_generation_certified(self):
        r=correlate([self.row()],self.records())[0]
        self.assertEqual(r['status'],'PARTIAL');self.assertFalse(r['event_utc_certified'])
        self.assertIsNone(r['generation_latency_ns']);self.assertIsNone(r['certified_receipt_bounds_ns'])

    def test_loss_of_nts(self):
        self.assertEqual(correlate([self.row()],[])[0]['status'],'QUARANTINED')

    def test_invalid_nts(self):
        records=self.records();records[0]['payload']['results'][0]['measurement']['authentication']='INVALID'
        self.assertEqual(correlate([self.row()],records)[0]['status'],'QUARANTINED')

    def test_nts_outage_not_bridged(self):
        records=self.records();failed=copy.deepcopy(records[0]);failed['payload'].update(run_started_kernel_uptime_ms=4000,results=[{'status':'UNAVAILABLE'}]);records.append(failed)
        self.assertIn('NTS_UNAVAILABLE_WITHIN_BRACKET',correlate([self.row()],records)[0]['reasons'])

    def test_xm_disconnect(self):
        self.assertIn('XM_DISCONNECTED',correlate([self.row(connected=False)],self.records())[0]['reasons'])

    def test_windows_clock_jump(self):
        rows=[self.row(4000),self.row(receipt_host_gmt_seconds=200)]
        self.assertIn('HOST_CLOCK_OR_COUNTER_DISCONTINUITY',correlate(rows,self.records())[-1]['reasons'])

    def test_reboot_and_missing_epoch(self):
        for boot in ('OTHER',None):
            records=self.records();records[1]['payload']['boot_identity']=boot
            self.assertIn('KERNEL_EPOCH_UNVERIFIED_OR_CHANGED',correlate([self.row()],records)[0]['reasons'])

    def test_counter_restart_cannot_join_segments(self):
        rows=[self.row(5000),self.row(1000)]
        self.assertIn('RESTART_OR_UPTIME_REGRESSION',correlate(rows,self.records())[-1]['reasons'])

    def test_dst_does_not_reorder_utc(self):
        a=datetime(2026,11,1,5,59,tzinfo=timezone.utc);b=datetime(2026,11,1,6,1,tzinfo=timezone.utc)
        ny=ZoneInfo('America/New_York');ec=ZoneInfo('America/Guayaquil')
        self.assertNotEqual(a.astimezone(ny).utcoffset(),b.astimezone(ny).utcoffset())
        self.assertGreater(a.astimezone(ny).minute,b.astimezone(ny).minute)
        self.assertLess(a.astimezone(ec),b.astimezone(ec))
        self.assertEqual(correlate([self.row()],self.records())[0]['status'],'PARTIAL')

    def test_out_of_order_native_ticks(self):
        rows=[self.row(4000,time_msc=106000),self.row(time_msc=105000)]
        self.assertIn('NATIVE_TIMESTAMP_OUT_OF_ORDER',correlate(rows,self.records())[-1]['reasons'])

    def test_heartbeat_gap(self):
        rows=[self.row(0,kind='HEARTBEAT'),self.row(10000)]
        self.assertIn('HEARTBEAT_GAP_TWO_TIMER_PERIODS',correlate(rows,self.records())[-1]['reasons'])

    def test_early_tick_inside_later_confirmed_gap(self):
        rows=[self.row(0,kind='HEARTBEAT'),self.row(1000),self.row(46000,kind='HEARTBEAT')]
        self.assertIn('HEARTBEAT_GAP_TWO_TIMER_PERIODS',correlate(rows,self.records())[0]['reasons'])


if __name__=='__main__':unittest.main()
