import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'python'),str(Path(__file__).resolve().parents[1]/'tools')]
from nts_clock_calibration import calibrate,point,project_group,secant
from nts_xm_correlation import AUTH


class CalibrationTests(unittest.TestCase):
    def record(self,i,ppm=10,error=1000,boot='B'):
        u=i*300000;t=1000000000000000+u*1000000+i*3000
        m=dict(capture_id=str(i),origin='NTS',authentication=AUTH,protocol='RFC8915_NTS_AEAD15_TLS13',
            receive_kernel_uptime_ms_interval=[u,u],utc_receive_interval_model_ns=[t-error,t+error],
            host_receive_ns=t,offset_server_minus_host_ns=[-error,error],rtt_monotonic_ns=2*error,
            server_advertised_error_ns=error,server_transmit_utc_ns=t,server_receive_utc_ns=t,
            receive_clock_observation=dict(qpc_ticks_interval=[u*10000,u*10000+1],qpc_frequency_hz=10000000))
        # UTC counter drift is exactly ppm over each elapsed interval.
        m['utc_receive_interval_model_ns']=[1000000000000000+u*1000000+u*ppm-error,1000000000000000+u*1000000+u*ppm+error]
        m['host_receive_ns']=sum(m['utc_receive_interval_model_ns'])//2
        return dict(sha256=str(i),payload=dict(record_id=str(i),boot_identity=boot,
            run_started_kernel_uptime_ms=u,prior_due_kernel_uptime_ms=u,
            results=[dict(status='AUTHENTICATED_MEASUREMENT',measurement=m)]))

    def test_known_secant_and_no_generation_authorization(self):
        r=calibrate([self.record(1),self.record(2),self.record(3)])
        g=next(g for g in r['groups'] if g['basis']=='QPC')
        lo,hi=g['baseline_secant']['utc_minus_counter_secant_ppm']
        self.assertLess(lo,10);self.assertGreater(hi,10)
        self.assertEqual(r['certified_segments'],[]);self.assertFalse(r['generation_time_certified'])

    def test_unknown_boot_cannot_be_calibrated(self):
        self.assertEqual(calibrate([self.record(1,boot=None),self.record(2,boot=None)])['groups'],[])

    def test_boot_change_and_gap_not_bridged(self):
        records=[self.record(1),self.record(2,boot='C'),self.record(10,boot='C')]
        records[-1]['payload']['prior_due_kernel_uptime_ms']=900000
        r=calibrate(records)
        self.assertTrue(all(g['baseline_secant'] is None for g in r['groups']))
        reasons=[v for b in r['barriers'] for v in b['reasons']]
        self.assertIn('BOOT_CHANGED',reasons);self.assertIn('MISSED_NTS_MONITOR_PERIOD',reasons)

    def test_no_valid_nts_splits_source(self):
        records=[self.record(1),self.record(2),self.record(3)]
        records[1]['payload']['results']=[dict(status='UNAVAILABLE',origin='NTS')]
        self.assertTrue(all(g['baseline_secant'] is None for g in calibrate(records)['groups']))

    def test_invalid_authentication_cannot_fit(self):
        records=[self.record(1),self.record(2)];records[1]['payload']['results'][0]['measurement']['authentication']='INVALID'
        self.assertTrue(all(g['baseline_secant'] is None for g in calibrate(records)['groups']))

    def test_regression_and_host_clock_backstep_split(self):
        for field in ('host_receive_ns','receive_kernel_uptime_ms_interval'):
            records=[self.record(1),self.record(2)]
            m=records[1]['payload']['results'][0]['measurement']
            if field=='host_receive_ns':
                m[field]=1;m['utc_receive_interval_model_ns']=[1-1000,1+1000]
            else:m[field]=[0,0]
            r=calibrate(records)
            self.assertIn('COUNTER_OR_HOST_REGRESSION',[v for b in r['barriers'] for v in b['reasons']])

    def test_non_affine_variation_rejects_model_without_tolerance(self):
        records=[self.record(1,ppm=0),self.record(2,ppm=0),self.record(3,ppm=1000)]
        g=calibrate(records)['groups'][0]
        self.assertEqual(g['affine_status'],'REJECTED_CONSTANT_RATE_MODEL');self.assertIsNone(g['affine_rate_interval'])

    def test_reversed_utc_intervals_do_not_disappear_from_constraints(self):
        a=point(self.record(1)['payload']['results'][0]['measurement'],'QPC')
        b=point(self.record(2)['payload']['results'][0]['measurement'],'QPC');b['utc_ns']=[0,1]
        s=secant(a,b)
        self.assertLess(s['utc_per_counter_rate'][1]['numerator'],0)

    def test_bounded_model_and_no_extrapolation_or_mutation(self):
        records=[self.record(1),self.record(2),self.record(3)];original=copy.deepcopy(records)
        g=next(g for g in calibrate(records)['groups'] if g['basis']=='KERNEL_UPTIME')
        r=project_group(g,450000)
        self.assertFalse(r['certified']);self.assertIsNone(project_group(g,1000000));self.assertEqual(records,original)

    def test_missing_qpc_not_fabricated_from_rtt(self):
        m=self.record(1)['payload']['results'][0]['measurement'];m.pop('receive_clock_observation')
        self.assertIsNone(point(m,'QPC'));self.assertIsNotNone(point(m,'KERNEL_UPTIME'))

    def test_qpc_outward_rounding(self):
        m=self.record(1)['payload']['results'][0]['measurement'];m['receive_clock_observation']=dict(qpc_ticks_interval=[1,2],qpc_frequency_hz=3)
        self.assertEqual(point(m,'QPC')['x_ns'],[333333333,666666667])

    def test_os_clock_step_cursor_splits(self):
        records=[self.record(1),self.record(2)]
        records[0]['payload']['clock_change_event_record_id']=100
        records[1]['payload']['clock_change_event_record_id']=101
        r=calibrate(records)
        self.assertTrue(all(g['baseline_secant'] is None for g in r['groups']))
        self.assertIn('OS_CLOCK_EVENT_CURSOR_CHANGED',[v for b in r['barriers'] for v in b['reasons']])

    def test_qpc_frequency_change_splits(self):
        records=[self.record(1),self.record(2)]
        records[1]['payload']['results'][0]['measurement']['receive_clock_observation']['qpc_frequency_hz']=20000000
        self.assertIn('QPC_FREQUENCY_CHANGED',[v for b in calibrate(records)['barriers'] for v in b['reasons']])

    def test_actual_readonly_clock_bracket(self):
        from nts_external import receive_clock_sample
        host,uptime,clock=receive_clock_sample()
        self.assertGreater(host,0);self.assertEqual(clock['scope'],'LOCAL_WALL_READ_NOT_PACKET_ARRIVAL')
        if sys.platform=='win32':
            self.assertLessEqual(uptime[0],uptime[1]);self.assertGreater(clock['qpc_frequency_hz'],0)
            self.assertLessEqual(*clock['qpc_ticks_interval'])

    def test_cache_reuses_same_evidence_and_rejects_tampering(self):
        import correlate_nts_xm as station
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory, patch.object(station,'BASE',Path(directory)):
            key,first=station.cached_calibrate([self.record(1),self.record(2)])
            with patch.object(station,'calibrate',side_effect=AssertionError('Must not repeat')):
                self.assertEqual(station.cached_calibrate([self.record(1),self.record(2)])[1],first)
            p=Path(directory)/'calibration_snapshots'/(key+'.json');value=json.loads(p.read_text());value['payload']['scientific_acceptance']=True;p.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,'CACHE_HASH'):station.cached_calibrate([self.record(1),self.record(2)])


if __name__=='__main__':unittest.main()
