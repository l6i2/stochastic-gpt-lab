from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from native_time_mapping import (NativeTimestamp, MappingSegment, ClockMapping, native_to_utc,
                                 utc_views, causal_event, load_mapping)
from temporal_causality import utc_milliseconds
from clock_attestation_audit import ordering_flags, audit_capture


class NativeTimeMappingTests(unittest.TestCase):
    def setUp(self):
        self.utc = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)
        self.ms = utc_milliseconds(self.utc)
        self.mapping = ClockMapping('synthetic-test-only', 'TEST_SERVER', ('TEST',),
            (MappingSegment(self.ms - 86400000, self.ms + 86400000, 7200, 7200),), True)

    def raw(self, utc_ms):
        ms = utc_ms + 7200000
        return NativeTimestamp(ms // 1000, ms, 'TEST', 'TEST_SERVER', 'a' * 64)

    def test_native_mapping_preserves_raw_hash_and_views(self):
        raw = self.raw(self.ms)
        event = native_to_utc(raw, self.mapping)
        self.assertEqual(event.utc_msc, self.ms)
        self.assertIs(event.original, raw)
        self.assertEqual(event.views['raw_sha256'], raw.raw_sha256)
        self.assertEqual(event.views['utc_event_sha256'],native_to_utc(raw,self.mapping).views['utc_event_sha256'])
        self.assertNotEqual(event.views['utc_event_sha256'],raw.raw_sha256)
        self.assertTrue(event.views['ecuador_time'].endswith('-05:00'))
        self.assertTrue(event.views['xm_server_time'].startswith('2026-10-23T14:00:00'))
        with self.assertRaises(ValueError): native_to_utc(event, self.mapping)

    def test_mapping_unverified_identity_and_units_fail_closed(self):
        raw = self.raw(self.ms)
        for value, mapping in ((raw, replace(self.mapping, verified=False)),
                (replace(raw, time=raw.time+1), self.mapping),
                (replace(raw, server='OTHER'), self.mapping),
                (replace(raw, raw_sha256=''), self.mapping)):
            with self.assertRaises(ValueError): native_to_utc(value, mapping)

    def test_millisecond_rollover_exact_future_and_stale(self):
        before = native_to_utc(self.raw(self.ms - 1), self.mapping)
        exact = native_to_utc(self.raw(self.ms), self.mapping)
        future = native_to_utc(self.raw(self.ms + 1), self.mapping)
        self.assertEqual(exact.utc_msc-before.utc_msc, 1)
        self.assertTrue(causal_event(exact, feature_max_time=self.utc, decision_time=self.utc)[0])
        self.assertEqual(causal_event(future, feature_max_time=self.utc, decision_time=self.utc)[1], 'FUTURE_QUOTE')
        self.assertEqual(causal_event(exact, feature_max_time=self.utc, decision_time=self.utc+timedelta(milliseconds=5001))[1], 'STALE_QUOTE')
        self.assertEqual(causal_event(before, feature_max_time=self.utc, decision_time=self.utc, previous=exact)[1], 'NORMALIZED_ORDER_VIOLATION')

    def test_server_dst_fallback_ambiguity_and_spring_gap_rejected(self):
        boundary = utc_milliseconds(datetime(2026, 10, 25, 1, tzinfo=timezone.utc))
        segments = (MappingSegment(boundary-86400000,boundary,10800,10800),
                    MappingSegment(boundary,boundary+86400000,7200,7200))
        mapping = replace(self.mapping, segments=segments)
        ambiguous = boundary + 9000000
        raw = NativeTimestamp(ambiguous//1000,ambiguous,'TEST','TEST_SERVER','a'*64)
        with self.assertRaises(ValueError):native_to_utc(raw,mapping)
        spring = replace(mapping,segments=(replace(segments[0],native_utc_offset_seconds=7200),
                                           replace(segments[1],native_utc_offset_seconds=10800)))
        with self.assertRaises(ValueError):native_to_utc(raw,spring)

    def test_ecuador_constant_offset_and_new_york_est_edt(self):
        for month in range(1,13):
            views=utc_views(datetime(2026,month,15,12,tzinfo=timezone.utc))
            self.assertTrue(views['ecuador_time'].endswith('-05:00'))
        self.assertEqual(utc_views(datetime(2026,1,15,tzinfo=timezone.utc))['new_york_abbreviation'],'EST')
        self.assertEqual(utc_views(datetime(2026,7,15,tzinfo=timezone.utc))['new_york_abbreviation'],'EDT')

    def test_new_york_march_november_transitions_and_ecuador_comparison(self):
        for boundary in (datetime(2026,3,8,7,tzinfo=timezone.utc),datetime(2026,11,1,6,tzinfo=timezone.utc)):
            before,after=utc_views(boundary-timedelta(milliseconds=1)),utc_views(boundary)
            self.assertNotEqual(before['new_york_abbreviation'],after['new_york_abbreviation'])
            self.assertTrue(before['ecuador_time'].endswith('-05:00'))
            self.assertTrue(after['ecuador_time'].endswith('-05:00'))
            self.assertNotEqual(before['new_york_time'][-6:],after['new_york_time'][-6:])
        a=utc_views(datetime(2026,11,1,5,30,tzinfo=timezone.utc))
        b=utc_views(datetime(2026,11,1,6,30,tzinfo=timezone.utc))
        self.assertEqual(a['new_york_fold'],0);self.assertEqual(b['new_york_fold'],1)
        self.assertEqual(a['new_york_time'][11:16],b['new_york_time'][11:16])

    def test_mapping_loader_rejects_sealed_but_unverified_config(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'mapping.json';p.write_text(json.dumps({'status':'FAIL'}))
            p.with_name(p.name+'.sha256').write_text(hashlib.sha256(p.read_bytes()).hexdigest())
            with self.assertRaisesRegex(ValueError,'UNVERIFIED'):load_mapping(p)

    def test_mapping_loader_binds_evidence_and_authorized_intervals(self):
        # Synthetic unit-test evidence, never counted as broker attestation.
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);e=folder/'audit.json';p=folder/'mapping.json'
            segments=[vars(self.mapping.segments[0])]
            e.write_text(json.dumps({'clock_attestation':'PASS','native_to_utc_mapping':'PASS',
                                    'complete_frames':50,'authorized_segments':segments}))
            config={'status':'PASS','mapping_id':'synthetic','server':'TEST_SERVER','symbols':['TEST'],
                    'segments':segments,'evidence_file':'audit.json','evidence_sha256':hashlib.sha256(e.read_bytes()).hexdigest()}
            p.write_text(json.dumps(config));p.with_name(p.name+'.sha256').write_text(hashlib.sha256(p.read_bytes()).hexdigest())
            self.assertEqual(native_to_utc(self.raw(self.ms),load_mapping(p)).utc_msc,self.ms)
            e.write_text('{}')
            with self.assertRaisesRegex(ValueError,'HASH_MISMATCH'):load_mapping(p)

    def test_explicit_local_mapping_and_naive_rejection(self):
        shifted=self.utc.astimezone(timezone(timedelta(hours=2)))
        self.assertEqual(utc_views(self.utc),utc_views(shifted))
        with self.assertRaises(ValueError):utc_views(self.utc.replace(tzinfo=None))


class AttestationAuditTests(unittest.TestCase):
    def test_monotonic_regression_units_and_clock_divergence_are_not_hidden(self):
        keys=('mono_start_ms','gmt_before_mono_ms','local_mono_ms','gmt_mono_ms',
              'current_mono_ms','server_mono_ms','tick_mono_ms','mono_end_ms')
        row={k:str(i) for i,k in enumerate(keys)}
        row.update(tick_time='1',tick_time_msc='1001')
        frame={'system_read_start_ms':8,'system_utc_read_ms':9,'system_local_read_ms':10,
               'system_read_end_ms':11,'native':[row]}
        self.assertEqual(ordering_flags(frame),[])
        row['tick_mono_ms']='0'
        self.assertIn('NATIVE_MONOTONIC_ORDER',ordering_flags(frame))
        row['tick_time']='2'
        self.assertIn('SECONDS_MILLISECONDS_MISMATCH',ordering_flags(frame))

    def test_drift_and_current_server_divergence_never_repair_the_clock(self):
        frames=[]
        for frame in range(50):
            native=[]
            for symbol in ('US30Cash','EURUSD','USDCHF'):
                row={k:str(frame*1000) for k in ('mono_start_ms','gmt_before_mono_ms','local_mono_ms',
                   'gmt_mono_ms','current_mono_ms','server_mono_ms','tick_mono_ms','mono_end_ms')}
                row.update(symbol=symbol,tester='0',connected='1',tick_ok='1',tick_time='2000',
                           tick_time_msc='2000000',time_trade_server='1000',time_gmt='0',time_current='2000')
                native.append(row)
            utc=datetime(2026,10,23,tzinfo=timezone.utc)+timedelta(seconds=frame+(20 if frame>=25 else 0))
            frames.append({'frame':frame,'system_utc':utc.isoformat(),'system_read_start_ms':frame*1000,
                'system_utc_read_ms':frame*1000,'system_local_read_ms':frame*1000,'system_read_end_ms':frame*1000,
                'native':native,'pairing_delay_ms':0})
        ref={'comparison':{'status':'REFERENCE_QUORUM','local_clock_within_network_interval':True},'tls_corroborated':True}
        result=audit_capture({'frames':frames,'reference_before':ref,'reference_after':ref})
        self.assertEqual(result['clock_attestation'],'FAIL')
        self.assertFalse(result['wall_monotonic_drift_reconciled'])
        self.assertEqual(result['symbols']['US30Cash']['current_minus_estimated_server_seconds'],[1000])
        self.assertEqual(result['authorized_segments'],[])


if __name__=='__main__':unittest.main()
