import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import numpy as np

from controller.xm_history_recovery import (archive_chunk,missing_intervals,next_chunks,
    permitted,quality,retrieve,validate_rows,retry_ready)
from tools.xm_historical_recovery import load_checkpoint


def policy():
    return dict(server='XMGlobalSC-MT5 5',symbol='US30Cash',minimum_native_msc=0,
                maximum_native_msc=600000,gaps=[dict(start=0,end=600000)],protected_intervals=[])


def samples(kind):
    if kind=='ticks':
        return [dict(time=i*60,time_msc=i*60000,bid=2.,ask=3.,last=0.,volume=0,flags=2,volume_real=0.) for i in range(5)]
    frame=60 if kind=='m1' else 300
    return [dict(time=i,open=2.,high=2.,low=2.,close=2.,tick_volume=1 if frame==60 else 5,spread=2,real_volume=0)
            for i in range(0,300,frame)]


class Api:
    TIMEFRAME_M1=1;TIMEFRAME_M5=5;COPY_TICKS_ALL=0
    def __init__(self):self.calls=0
    def array(self,kind):
        self.calls+=1;rows=samples(kind)
        dtype=[(k,'f8' if isinstance(v,float) else 'i8') for k,v in rows[0].items()]
        return np.array([tuple(row.values()) for row in rows],dtype=dtype)
    def copy_rates_range(self,symbol,frame,first,last):return self.array('m1' if frame==1 else 'm5')
    def copy_ticks_range(self,*args):return self.array('ticks')
    def last_error(self):return (1,'ok')


class HistoricalRecoveryTests(unittest.TestCase):
    def test_retries_resume_only_on_budget_or_new_source_evidence(self):
        marker=dict(boot_id='A',native_max=1000)
        item=dict(status='PARTIAL_API_FAILURE',clock=dict(boot_id='A',uptime_ms=100),
                  attempts=3,attempts_for_source=3,source_marker=marker)
        self.assertFalse(retry_ready(item,dict(boot_id='A',uptime_ms=900100),marker))
        self.assertFalse(retry_ready(item,dict(boot_id='A',uptime_ms=101),dict(marker,native_max=2000)))
        self.assertTrue(retry_ready(item,dict(boot_id='A',uptime_ms=900100),dict(marker,native_max=2000)))
        self.assertTrue(retry_ready(item,dict(boot_id='B',uptime_ms=1),dict(marker,boot_id='B')))
        self.assertFalse(retry_ready(dict(item,status='RECOVERED_DIAGNOSTIC'),dict(boot_id='B',uptime_ms=1),marker))

    def request(self):return next_chunks(policy(),set(),1)[0]

    def test_real_shape_interval_and_idempotent_persistence(self):
        api=Api()
        with TemporaryDirectory() as d:
            folder,manifest=archive_chunk(d,policy(),self.request(),lambda kind,a,b:retrieve(api,kind,a,b))
            self.assertEqual(manifest['quality']['m1_m5'][0]['status'],'EXACT')
            self.assertEqual(manifest['quality']['valid_bid_ask_rows'],5)
            before=(folder/'ticks.jsonl').read_bytes()
            second,_=archive_chunk(d,policy(),self.request(),lambda *args:self.fail('duplicate API request'))
            self.assertEqual(folder,second)
            self.assertEqual(before,(second/'ticks.jsonl').read_bytes())
            with patch('tools.xm_historical_recovery.BASE',Path(d)):
                restored=load_checkpoint()
            self.assertEqual(len(restored['completed']),1)
            self.assertFalse(manifest['prospective_receipt'])

    def test_tick_query_retains_final_second_and_excludes_upper_endpoint(self):
        api=Api();rows=samples('ticks')
        rows.extend([dict(rows[-1],time=299,time_msc=299999),dict(rows[-1],time=300,time_msc=300000)])
        array=np.array([tuple(row.values()) for row in rows],dtype=api.array('ticks').dtype)
        with patch.object(api,'copy_ticks_range',return_value=array) as query:
            received,source=retrieve(api,'ticks',0,300000)
        self.assertEqual(query.call_args.args[2].timestamp(),300.)
        self.assertEqual(received[-1]['time_msc'],299999)
        self.assertEqual(source['excluded_upper_endpoint_rows'],1)

    def test_subminute_gap_keeps_millisecond_membership_without_partial_bars(self):
        api=Api();base=samples('ticks')[0]
        ticks=[dict(base,time=t//1000,time_msc=t) for t in (1000,1001,61000,61001,62000)]
        array=np.array([tuple(row.values()) for row in ticks],dtype=api.array('ticks').dtype)
        with patch.object(api,'copy_ticks_range',return_value=array):
            rows,source=retrieve(api,'ticks',1001,61001)
        self.assertEqual([r['time_msc'] for r in rows],[1001,61000])
        self.assertEqual(source['excluded_lower_endpoint_rows'],1)
        with patch.object(api,'copy_rates_range') as query:
            rows,_=retrieve(api,'m1',1001,59999)
            self.assertEqual(rows,[])
            query.assert_not_called()

    def test_failed_api_attempt_has_separate_retry_and_preserves_other_registry(self):
        with TemporaryDirectory() as d:
            root=Path(d);original=root/'registry_a.json';original.write_bytes(b'original')
            def unavailable(*args):raise RuntimeError('synthetic API unavailable')
            first,failed=archive_chunk(root/'B',policy(),self.request(),unavailable)
            saved=(first/'manifest.json').read_bytes()
            second,recovered=archive_chunk(root/'B',policy(),self.request(),lambda kind,a,b:(samples(kind),{}),retry_failed=True)
            self.assertEqual(failed['status'],'PARTIAL_API_FAILURE')
            self.assertEqual(recovered['status'],'RECOVERED_DIAGNOSTIC')
            self.assertNotEqual(first,second)
            self.assertEqual((first/'manifest.json').read_bytes(),saved)
            self.assertEqual(original.read_bytes(),b'original')

    def test_protected_and_pre_cut_requests_never_call_api(self):
        with TemporaryDirectory() as d:
            for restriction in (dict(minimum_native_msc=60000),dict(protected_intervals=[dict(start=120000,end=180000)])):
                denied=dict(policy(),**restriction)
                with self.assertRaises(PermissionError):
                    archive_chunk(d,denied,self.request(),lambda *args:self.fail('protected read'))
            self.assertFalse(list(Path(d).glob('requests/*')))

    def test_api_failure_uses_validated_alternative(self):
        api=Api()
        with patch.object(api,'copy_ticks_range',return_value=None),patch.object(api,'last_error',return_value=(-4,'missing')):
            rows,source=retrieve(api,'ticks',0,300000,lambda *a:(samples('ticks'),dict(api='SYNTHETIC_MQL_FALLBACK')))
        self.assertEqual(len(rows),5)
        self.assertIn('NATIVE_API_UNAVAILABLE',source['primary_failure'])

    def test_incomplete_ticks_and_ohlc_differences_are_not_repaired(self):
        ticks=samples('ticks')[:-1];minutes=samples('m1');bars=samples('m5')
        bars[0]['high']=3.
        report=quality(ticks,minutes,bars,0,300000)
        self.assertEqual(report['m1_m5'][0]['status'],'DIFFERENT')
        self.assertEqual(report['tick_m1'][-1]['ohlc'],'DIFFERENT_OR_MISSING')
        self.assertFalse(report['broker_tick_completeness_certified'])
        duplicate=quality(ticks+ticks[-1:],minutes,bars,0,300000)
        self.assertEqual(duplicate['identical_rows_retained'],1)

    def test_absent_rows_and_changed_hash_remain_detectable(self):
        report=quality([],[],[],0,300000)
        self.assertEqual(len(report['missing_m1_opens']),5)
        with TemporaryDirectory() as d:
            folder,_=archive_chunk(d,policy(),self.request(),lambda kind,a,b:(samples(kind),{}))
            (folder/'ticks.jsonl').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'PAYLOAD_CHANGED'):
                archive_chunk(d,policy(),self.request(),lambda *args:self.fail('must verify first'))

    def test_interrupted_write_preserves_attempt_and_recovers_separately(self):
        with TemporaryDirectory() as d:
            with patch('controller.xm_history_recovery.write_payload',side_effect=OSError('simulated disk failure')):
                with self.assertRaises(OSError):archive_chunk(d,policy(),self.request(),lambda kind,a,b:(samples(kind),{}))
            folder,_=archive_chunk(d,policy(),self.request(),lambda kind,a,b:(samples(kind),{}))
            self.assertEqual(folder.name,'attempt_0002')
            self.assertTrue((folder.parent/'attempt_0001/intent.json').exists())

    def test_overlap_inventory_is_merged_and_does_not_expand_backward(self):
        events=[(1,dict(kind='OBSERVATION_INTERRUPTION',previous_observation=dict(native_msc=1000),reason='SLEEP')),
                (2,dict(kind='OBSERVATION_INTERRUPTION',previous_observation=dict(native_msc=2000))),
                (3,dict(kind='LIVE_LATEST_STATE_POLL',native_quote=dict(time_msc=360000)))]
        gaps=missing_intervals(events,120000)['gaps']
        self.assertEqual(len(gaps),1)
        self.assertEqual(gaps[0]['start'],120000)
        self.assertEqual(len(gaps[0]['incidents']),2)
        validate_rows(samples('m5'),'m5',0,300000)
        with self.assertRaises(ValueError):validate_rows(samples('m5'),'m5',0,120000)

    def test_native_alternative_rejects_protected_scope_before_terminal_access(self):
        from tools.xm_history_native import recover,source
        with TemporaryDirectory() as d:
            denied=dict(policy(),protected_intervals=[dict(start=0,end=300000)])
            with self.assertRaises(PermissionError):recover(Path(d),denied,0,300000,Path(d)/'native')
            self.assertFalse((Path(d)/'native').exists())
        program=source(0,300000,'synthetic')
        self.assertIn('CopyTicksRange',program)
        self.assertIn('CopyRates',program)
        self.assertIn('MQLInfoInteger(MQL_TESTER)',program)
        self.assertNotIn('OrderSend',program)
        self.assertNotIn('CTrade',program)

    def test_explicit_audit_checks_payloads_without_opening_terminal(self):
        from tools.xm_historical_recovery import audit_archive
        from controller.pretrain_contracts import seal
        with TemporaryDirectory() as d:
            root=Path(d)
            folder,_=archive_chunk(root,policy(),self.request(),lambda kind,a,b:(samples(kind),{}))
            (root/'gap_inventory.json').write_text(json.dumps(dict(policy=policy())))
            with patch('tools.xm_historical_recovery.BASE',root):
                state=load_checkpoint()
                (root/'checkpoint.json').write_text(json.dumps(dict(state=state,sha256=seal(state))))
                result=audit_archive()
                self.assertEqual(result['missing_requests'],1)
                self.assertFalse(result['dataset_admitted'])
                (folder/'ticks.jsonl').write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'PAYLOAD_CHANGED'):audit_archive()
