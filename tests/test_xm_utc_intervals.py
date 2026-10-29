import hashlib
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('xm_audit',Path(__file__).resolve().parents[1]/'tools/audit_xm_utc_intervals.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


class XmIntervalTests(unittest.TestCase):
    def measurement(self):
        tick=dict(time=10,time_msc=10000)
        return dict(server=audit.SERVER,symbol='US30Cash',reference=dict(anchor_monotonic_ns=100,
            comparison=dict(status='REFERENCE_QUORUM',utc_lower_ns=1000,utc_upper_ns=1100)),
            samples=[dict(tick=tick,payload_sha256=hashlib.sha256(audit.raw.canonical(tick)).hexdigest(),
                before=dict(monotonic_ns=100),after=dict(monotonic_ns=100))])

    def test_correlation_never_certifies_offset_or_zero_latency(self):
        report=audit.correlation_audit(self.measurement())
        self.assertEqual(report['certified_intervals'],[])
        self.assertEqual(report['offsets_authorized'],[])
        self.assertEqual(report['indistinguishable_monotonic_readings'],1)
        self.assertEqual(report['event_latency'],'UNVERIFIED')

    def test_payload_tamper_identity_and_monotonic_regression_rejected(self):
        for kind in ('hash','server','clock'):
            m=self.measurement()
            if kind=='hash':m['samples'][0]['tick']['time_msc']=10001
            if kind=='server':m['server']='OTHER'
            if kind=='clock':m['samples'][0]['after']['monotonic_ns']=99
            with self.assertRaises(ValueError):audit.correlation_audit(m)

    def test_absent_external_quorum_does_not_infer_utc(self):
        m=self.measurement();m['reference']['comparison']={'status':'UNVERIFIED'}
        report=audit.correlation_audit(m)
        self.assertIsNone(report['native_minus_external_receipt_ns_envelope'])
        self.assertEqual(report['certified_intervals'],[])

    def test_partition_preserves_native_bounds_without_certification(self):
        manifest=dict(server=audit.SERVER,symbol='US30Cash',archive_id='synthetic',kind='historical',
            native_start_msc=100,native_end_exclusive_msc=500,next_native_msc=400,
            segments=[dict(ticks=dict(rows=2),bars=dict(rows=0))],chain_head='synthetic')
        before=audit.raw.canonical(manifest)
        report=audit.quarantine_partition(manifest)
        self.assertEqual(report['native_start_msc'],100)
        self.assertEqual(report['native_end_exclusive_msc'],400)
        self.assertEqual(report['status'],'QUARANTINED')
        self.assertEqual(audit.raw.canonical(manifest),before)
