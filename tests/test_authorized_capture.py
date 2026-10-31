import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from controller.authorized_capture import (CaptureManager,REQUEST_SHA,AUTHENTICATION,bracket,
    validate_authorization,verify_decisions,once,io_path)
from controller.isolated_observation import Observation,eof_anchor
from test_isolated_observation import line,clock,GENESIS


class AuthorizedCaptureTests(unittest.TestCase):
    def test_windows_extended_checkpoint_temporary_long_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.jsonl'
            raw,_=line(GENESIS,0,90,kind='SESSION_START');source.write_bytes(raw)
            base=root/('long_boundary_'+'a'*110)
            obj=Observation.create(io_path(base),source,eof_anchor(source),clock(100),synthetic=True)
            folder=obj.folder;obj.close()
            reopened=Observation.resume(folder,clock(101))
            reopened.close()
            self.assertTrue((folder/'checkpoint.json').is_file())

    def fixture(self,root):
        source=root/'native';source.mkdir()
        path=source/'pc_a_prospective_utc_v1_fixture.jsonl'
        raw,digest=line(GENESIS,0,90,kind='SESSION_START');path.write_bytes(raw)
        auth=dict(study_id='US30CASH_M5_NATIVE_20261030_01',approved_request_sha256=REQUEST_SHA,
            collection_authorized=True,previous_reservation_new_ingress_closure_authorized=True,
            training_authorized=False,scoring_authorized=False,dataset_admission_authorized=False,
            demo_enabled=False,live_trading=False,orders_authorized=False)
        auth_path=root/'authorization.json';auth_path.write_text(json.dumps(auth))
        before=dict(authentication=AUTHENTICATION,broker_mapping_authorized=False,clock_adjusted=False,
            origin='time.cloudflare.com',server_transmit_utc_ns=1000000000000,
            server_receive_utc_ns=999999999900,server_advertised_error_ns=100,
            receive_kernel_uptime_ms_interval=[99,100],capture_id='before')
        after=before|dict(server_receive_utc_ns=1000000001000,server_transmit_utc_ns=1000000001100,
                        receive_kernel_uptime_ms_interval=[200,201],capture_id='after')
        samples=iter([before,after])
        manager=CaptureManager(root/'new_study',source,auth_path,lambda:clock(150),lambda:next(samples))
        return manager,path,digest,auth,before,after

    def snapshots(self,manager_root):
        once(manager_root/'prior_evidence_index.json',{'synthetic_previous':'unchanged'})

    def test_authenticated_bracket_uses_remote_causal_order_not_local_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,_,_,_,before,after=self.fixture(Path(tmp))
            value=bracket(before,after,clock(150))
            self.assertEqual(value['utc_interval_ns'],[999999999900,1000000001100])
            self.assertFalse(value['local_clock_offset_or_drift_extrapolated'])
            self.assertFalse(value['broker_event_utc_certified'])
            with self.assertRaises(ValueError):bracket(before|{'authentication':'UNAUTHENTICATED'},after,clock(150))
            with self.assertRaises(ValueError):bracket(before,after,clock(250))

    def test_scope_cannot_grant_training_or_admit_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,_,_,auth,_,_=self.fixture(Path(tmp))
            validate_authorization(auth)
            for k in ('training_authorized','scoring_authorized','dataset_admission_authorized','live_trading','orders_authorized'):
                with self.assertRaises(ValueError):validate_authorization(auth|{k:True})

    def test_activation_immutable_closure_and_new_only_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);m,source,parent,_,_,_=self.fixture(root)
            with patch.object(m,'snapshot_previous',side_effect=self.snapshots):manifest=m.activate()
            capture=manifest['capture_id'];saved=(m.root/'collection_manifest.json').read_bytes()
            self.assertEqual(len(list((m.root/'decisions').glob('*.json'))),3)
            self.assertEqual(verify_decisions(m.root/'decisions'),manifest['decision_chain_head'])
            raw,_=line(parent,1,151)
            with source.open('ab') as stream:stream.write(raw)
            m.clock=lambda:clock(160)
            try:
                status=m.poll();self.assertEqual(status['totals']['tick_callbacks'],1)
            finally:m.close()
            resumed=CaptureManager(m.station,m.native,m.auth_path,lambda:clock(170),lambda:(_ for _ in ()).throw(AssertionError('NO_NEW_NTS_ON_RESUME')))
            self.assertEqual(resumed.activate()['capture_id'],capture)
            try:self.assertEqual(resumed.poll()['totals']['tick_callbacks'],1)
            finally:resumed.close()
            self.assertEqual((m.root/'collection_manifest.json').read_bytes(),saved)
            self.assertFalse(status['dataset_admission'])

    def test_restart_during_activation_reuses_same_capture_and_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);m,_,_,_,before,after=self.fixture(root)
            count=iter([before,OSError('SYNTHETIC_AFTER_MEASUREMENT_FAILURE')])
            def fail_after():
                value=next(count)
                if isinstance(value,Exception):raise value
                return value
            m.nts=fail_after
            with patch.object(m,'snapshot_previous',side_effect=self.snapshots):
                with self.assertRaises(OSError):m.activate()
            intent=json.loads((m.station/'activation_intent.json').read_text())
            boundary=(m.station/intent['capture_id']/'activation_boundary.json').read_bytes()
            m.nts=lambda:after
            result=m.activate()
            self.assertEqual(result['capture_id'],intent['capture_id'])
            self.assertEqual((m.root/'activation_boundary.json').read_bytes(),boundary)

    def test_old_manifest_clock_evidence_and_decision_tamper_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            m,_,_,_,_,_=self.fixture(Path(tmp))
            with patch.object(m,'snapshot_previous',side_effect=self.snapshots):m.activate()
            (m.root/'activation_utc.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'ACTIVATION_EVIDENCE_CHANGED'):m.load()

    def test_boot_recovery_waits_for_new_native_session_then_links_segment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);m,source,_,_,_,_=self.fixture(root)
            with patch.object(m,'snapshot_previous',side_effect=self.snapshots):original=m.activate()
            m.clock=lambda:clock(250,'next_boot')
            self.assertEqual(m.poll()['status'],'WAITING_NEW_NATIVE_SESSION_AFTER_BOOT')
            next_source=m.native/'pc_a_prospective_utc_v1_next.jsonl'
            raw,digest=line(GENESIS,0,1,kind='SESSION_START',session_id='next_session');next_source.write_bytes(raw)
            try:
                self.assertEqual(m.poll()['segments'],2)
                raw,_=line(digest,1,251,session_id='next_session')
                with next_source.open('ab') as stream:stream.write(raw)
                m.clock=lambda:clock(260,'next_boot')
                status=m.poll()
                self.assertEqual(status['capture_id'],original['capture_id'])
                self.assertEqual(status['totals']['tick_callbacks'],1)
                self.assertFalse(status['dataset_admission'])
            finally:m.close()


if __name__=='__main__':unittest.main()
