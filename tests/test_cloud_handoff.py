"""Synthetic-only Cloud contracts; these tests never connect to MT5."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'python'))
from time_semantics import (native_mt5_time_to_utc, normalize_tick_time, utc_to_ecuador,
                            utc_to_new_york, xm_server_to_utc, validate_causal_timestamp)
from native_time_mapping import NativeTimestamp, ClockMapping, MappingSegment
from temporal_causality import utc_milliseconds
from drift_feature_stream import DriftFeatureStream, FEATURES, BINS
from drift_monitor import summarize_feature_csv, compare_health_metadata
from manifest_chain_handoff import incorporate_local
from local_finalize import validate_handoff
from analyze_clock_attestation import analyze
from validate_clock_mapping import validate


class CloudTimeTests(unittest.TestCase):
    def setUp(self):
        self.utc = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)
        self.ms = utc_milliseconds(self.utc)
        self.mapping = ClockMapping('SYNTHETIC', 'TEST', ('TEST',),
            (MappingSegment(self.ms-86400000, self.ms+86400000, 7200, 7200),), True)
        self.raw = NativeTimestamp((self.ms+7200000)//1000, self.ms+7200000, 'TEST', 'TEST', 'a'*64)
        self.event = normalize_tick_time(self.raw, self.mapping)

    def test_exact_future_stale_missing_naive_aware(self):
        check = lambda event, feature, decision: validate_causal_timestamp(event, feature_max_time=feature, decision_time=decision)
        self.assertTrue(check(self.event, self.utc, self.utc)[0])
        self.assertFalse(check(self.event, self.utc+timedelta(milliseconds=1), self.utc)[0])
        self.assertFalse(check(replace(self.event, utc_msc=self.ms+1), self.utc, self.utc)[0])
        self.assertFalse(check(replace(self.event, utc_msc=self.ms-5001), self.utc, self.utc)[0])
        self.assertFalse(check(None, self.utc, self.utc)[0])
        self.assertFalse(check(self.event, None, self.utc)[0])
        self.assertFalse(check(self.event, self.utc, self.utc.replace(tzinfo=None))[0])
        self.assertTrue(check(self.event, utc_to_ecuador(self.utc), utc_to_new_york(self.utc))[0])

    def test_units_double_conversion_unattested_server_and_monotonicity(self):
        for value in (replace(self.raw, time_msc=self.raw.time), self.event):
            with self.assertRaises(ValueError):
                native_mt5_time_to_utc(value, self.mapping)
        with self.assertRaises(ValueError):
            normalize_tick_time(self.raw, replace(self.mapping, verified=False))
        label = self.utc.replace(tzinfo=None)+timedelta(hours=2)
        self.assertEqual(xm_server_to_utc(label, self.mapping), self.utc)
        for value, mapping in ((self.utc,self.mapping),(label,replace(self.mapping,verified=False))):
            with self.assertRaises(ValueError): xm_server_to_utc(value,mapping)
        self.assertFalse(validate_causal_timestamp(self.event, feature_max_time=self.utc,
            decision_time=self.utc, previous=replace(self.event, utc_msc=self.ms+1))[0])

    def test_ecuador_and_new_york_dst(self):
        for month in range(1,13):
            self.assertEqual(utc_to_ecuador(self.utc.replace(month=month)).utcoffset(),timedelta(hours=-5))
        for boundary in (datetime(2026,3,8,7,tzinfo=timezone.utc), datetime(2026,11,1,6,tzinfo=timezone.utc)):
            self.assertNotEqual(utc_to_new_york(boundary-timedelta(milliseconds=1)).utcoffset(),utc_to_new_york(boundary).utcoffset())
        with self.assertRaises(ValueError): utc_to_new_york(self.utc.replace(tzinfo=None))


class CloudDriftTests(CloudTimeTests):
    def bar(self, index):
        return dict(close_time=self.utc+timedelta(minutes=5*index),open=100.,high=110.,low=90.,close=100.+index%5,tick_volume=20)

    def push(self, stream, index):
        bar=self.bar(index)
        event=replace(self.event,utc_msc=utc_milliseconds(bar['close_time']))
        return stream.push(bar,quote=event,decision_time=bar['close_time'],bid=100,ask=101)

    def test_baseline_future_same_producer_and_future_perturbation(self):
        baseline,future=DriftFeatureStream(),DriftFeatureStream()
        values=[]
        for i in range(310):
            left,right=self.push(baseline,i),self.push(future,i)
            self.assertEqual(left,right)
            self.assertEqual(set(left),set(FEATURES))
            values.append(left)
        self.assertIsNotNone(values[-1]['atr14_over_previous_288_bar_median'])
        saved=deepcopy(values)
        self.push(future,311)
        self.assertEqual(values,saved)
        with self.assertRaises(ValueError):self.push(future,311)
        with self.assertRaises(ValueError):future.push({**self.bar(312),'pnl':2},quote=self.event,decision_time=self.utc,bid=1,ask=2)

    def test_exact_whitelist_and_outcome_names(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'features.csv'
            path.write_text('spread\n1\n')
            with self.assertRaises(ValueError):summarize_feature_csv(path,whitelist={'spread','atr'},bins={'spread':[1]})
            for name in ('win_rate','profit_factor','outcomes','labels','pf','future_return'):
                path.write_text(name+'\n1\n')
                with self.assertRaises(ValueError):summarize_feature_csv(path,whitelist={name},bins={name:[1]})
        with self.assertRaises(ValueError):compare_health_metadata({'spread_distribution_metadata':{'x':-1}}, {'spread_distribution_metadata':{'x':1}})


class CloudEvidenceTests(unittest.TestCase):
    def test_manifest_missing_prefix_and_actual_local_supplement(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);history=root/'manifest_history';history.mkdir()
            supplemental=root/'supplemental';supplemental.mkdir()
            old={'previous_manifest_sha256':None,'segments':[],'cohort_id':'fixture'}
            raw=json.dumps(old).encode();parent=hashlib.sha256(raw).hexdigest()
            current=root/'cohort_manifest.json';current.write_text(json.dumps({**old,'previous_manifest_sha256':parent}))
            (root/'cohort_manifest.sha256').write_text(hashlib.sha256(current.read_bytes()).hexdigest())
            self.assertEqual(incorporate_local(root)['pre_anchor'],'UNVERIFIABLE_PRE_ANCHOR')
            (supplemental/(parent+'.json')).write_bytes(raw)
            self.assertEqual(incorporate_local(root,supplemental)['classification'],'VERIFIED')
            (supplemental/(parent+'.json')).write_text('{}')
            with self.assertRaises(ValueError):incorporate_local(root,supplemental)

    def test_clock_parser_refuses_wrong_run_marker_and_unverified_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);markers=root/'markers.txt'
            markers.write_text('CLOCK_ATTESTATION_BEGIN|run=old|\nCLOCK_ATTESTATION_END|run=old|')
            (root/'run.json').write_text(json.dumps({'run_id':'new','markers':str(markers),'native':'unused','script':'unused'}))
            with self.assertRaisesRegex(ValueError,'WRONG_RUN'):analyze(root)
        with self.assertRaises(ValueError):validate(ROOT/'configs/native_time_mapping_v1.prepared.json')

    def test_handoff_cannot_enable_trading_or_unlock_test(self):
        safe={'branch':'research/full-pipeline','final_test':'LOCKED','demo':'DISABLED',
              'live_trading':False,'discovery_validation':'BLOCKED'}
        self.assertEqual(validate_handoff(safe),safe)
        for key,value in (('live_trading',True),('demo','ENABLED'),('final_test','OPEN'),('branch','main')):
            with self.assertRaises(ValueError):validate_handoff({**safe,key:value})

    def test_nonce_cannot_be_retried_in_another_ledger(self):
        import test_future_validation_evaluator as fixtures
        from future_validation_evaluator import evaluate
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            cohort,candidate,table,manifest,auth=fixtures.FutureValidationEvaluatorTests()._fixture(root)
            kwargs=dict(candidate_path=candidate,eval_csv=table,eval_manifest_path=manifest,authorization_path=auth,cohort_root=cohort)
            evaluate(**kwargs,ledger_root=root/'ledger1')
            with self.assertRaisesRegex(ValueError,'already been consumed'):
                evaluate(**kwargs,ledger_root=root/'ledger2')

    def test_evaluator_crash_between_pair_and_nonce_cannot_retry(self):
        import os
        import test_future_validation_evaluator as fixtures
        from future_validation_evaluator import evaluate
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            cohort,candidate,table,manifest,auth=fixtures.FutureValidationEvaluatorTests()._fixture(root)
            kwargs=dict(candidate_path=candidate,eval_csv=table,eval_manifest_path=manifest,authorization_path=auth,cohort_root=cohort)
            real_open=os.open
            def crash(path,*args,**kw):
                if str(path).endswith('.token-consumed'):
                    raise OSError('synthetic disk failure after pair reservation')
                return real_open(path,*args,**kw)
            with patch('future_validation_evaluator.os.open',side_effect=crash), self.assertRaises(OSError):
                evaluate(**kwargs)
            content=json.loads(auth.read_text());content['single_use_nonce']='e'*64;auth.write_text(json.dumps(content))
            with self.assertRaisesRegex(ValueError,'already been consumed'):
                evaluate(**kwargs,ledger_root=root/'another-ledger')

    def test_master_probe_build_orchestration_with_mocked_windows(self):
        import types
        from local_finalize import prepare_probe
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); terminal=root/'terminal64.exe'; terminal.touch()
            terminal.with_name('metaeditor64.exe').touch()
            data=root/'data'; data.mkdir(); folder=root/'evidence'; folder.mkdir()
            fake=types.SimpleNamespace(initialize=lambda *a:True, shutdown=lambda:None,
                terminal_info=lambda:types.SimpleNamespace(connected=True,company='XM',data_path=str(data)),
                account_info=lambda:types.SimpleNamespace(trade_mode=0),ACCOUNT_TRADE_MODE_DEMO=0)
            def compile_fake(args, **kwargs):
                source=Path(args[1].split(':',1)[1]);source.with_suffix('.ex5').write_bytes(b'SYNTHETIC_EX5')
                Path(args[2].split(':',1)[1]).write_text('0 errors, 0 warnings',encoding='utf-16')
            with patch.dict(sys.modules, {'MetaTrader5':fake}), patch('local_finalize.subprocess.run',side_effect=compile_fake):
                manifest=prepare_probe(terminal,folder,'fixture_nonce')
            source=Path(manifest['script']).read_text()
            self.assertIn('RunId="fixture_nonce"',source)
            self.assertNotIn('LOCAL_RUN_ID',source)
            self.assertIn('SymbolInfoSessionQuote',source)
            self.assertNotRegex(source,r'\b(OrderSend|OrderSendAsync|CTrade|PositionOpen)\b')
            self.assertTrue(manifest['sessions'].endswith('fixture_nonce_sessions.txt'))

    def test_complete_clock_parser_resume_and_tamper(self):
        import csv
        import test_simultaneous_clock_capture as fixtures
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);capture=fixtures.SimultaneousCaptureTests().capture()
            rows=[]
            for pair in capture['paired_frames']:
                for row in pair['native']:
                    for key in ('gmt_before_mono_ms','local_mono_ms','gmt_mono_ms','current_mono_ms','server_mono_ms','tick_mono_ms'):
                        row[key]=row['mono_start_ms']
                    row.update(bid='100',ask='101')
                    rows.append(row)
            raw=root/'raw.csv'
            with raw.open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            script=root/'probe.mq5';script.write_bytes(b'SYNTHETIC');script.with_suffix('.ex5').write_bytes(b'SYNTHETIC')
            markers=root/'source_markers.txt';markers.write_text('CLOCK_ATTESTATION_BEGIN|run=fixture|x\nCLOCK_ATTESTATION_END|run=fixture|x\n')
            (root/'capture.json').write_text(json.dumps(capture))
            digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
            (root/'run.json').write_text(json.dumps(dict(run_id='fixture',native=str(raw),markers=str(markers),script=str(script),
                build={'source_sha256':digest(script),'ex5_sha256':digest(script.with_suffix('.ex5'))})))
            first=analyze(root)
            self.assertEqual(first['clock_attestation'],'FAIL')
            self.assertEqual(first['native_to_utc_mapping'],'LOCAL_EXTERNAL_EVIDENCE_REQUIRED')
            self.assertEqual(analyze(root),first)
            (root/'capture.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'RESUME_EVIDENCE'):analyze(root)

    def test_session_snapshot_is_structural_only_never_activated(self):
        from session_evidence_parser import parse_sessions
        records=json.loads((ROOT/'configs/xm_session_probe_evidence_20261023.json').read_text())['records']
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'sessions.txt';source.write_text('\n'.join(records)+'\n')
            result=parse_sessions(source,root)
            self.assertFalse(result['activated'])
            self.assertEqual(result['native_to_utc_mapping'],'UNVERIFIED')
            self.assertEqual(result['holiday_schedule'],'UNKNOWN')
            with self.assertRaises(FileExistsError):parse_sessions(source,root)

    def test_candidate_frozen_boolean_is_mandatory(self):
        import test_future_validation_evaluator as fixtures
        from future_validation_evaluator import evaluate
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            cohort,candidate,table,manifest,auth=fixtures.FutureValidationEvaluatorTests()._fixture(root)
            content=json.loads(candidate.read_text());content.pop('candidate_frozen');candidate.write_text(json.dumps(content))
            digest=hashlib.sha256(candidate.read_bytes()).hexdigest()
            candidate.with_name(candidate.name+'.sha256').write_text(digest)
            fixtures.FutureValidationEvaluatorTests()._bind_causal_fixture(cohort,candidate,table,manifest,auth)
            with self.assertRaisesRegex(ValueError,'frozen candidate'):
                evaluate(candidate_path=candidate,eval_csv=table,eval_manifest_path=manifest,authorization_path=auth,cohort_root=cohort)

    def test_shadow_claim_survives_restart_and_crash_before_logging(self):
        from shadow_mode import ShadowRecorder
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'shadow.jsonl'
            self.assertTrue(ShadowRecorder(path).claim('same'))
            self.assertFalse(ShadowRecorder(path).claim('same'))
            self.assertTrue(ShadowRecorder(path).claim('different'))
            self.assertFalse(path.exists())  # Simulated crash between claim and append.


if __name__=='__main__':unittest.main()
