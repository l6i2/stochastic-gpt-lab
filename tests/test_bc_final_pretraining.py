import csv,json,hashlib,tempfile,types
from pathlib import Path
import unittest
from unittest.mock import Mock,patch
from controller.bc_admission import GATES,MINIMUMS,review
from controller.bc_training_rows import initial,consume,validate_rows
from controller.bc_study import STUDY
from controller.pretrain_contracts import FEATURES,seal
from controller.training_admission_gate import authorize_execution
from tools.bc_prefix_oracle import verify_export
from tools.prospective_pipeline import NativeReference
from tests import test_training_admission_gate as fixtures


class FinalPretrainingTests(unittest.TestCase):
    def evidence(self,status='PASS'):return {k:dict(status=status,witness_hashes=['SYNTHETIC_FIXTURE']) for k in GATES}

    def test_counts_do_not_admit_or_authorize(self):
        result=review(MINIMUMS.copy(),self.evidence())
        self.assertEqual(result['status'],'READY_FOR_ADMISSION_REVIEW');self.assertEqual(result['training_authorization_status'],'WAITING_FOR_AUTHORIZATION');self.assertFalse(result['dataset_admitted']);self.assertFalse(result['training_authorized']);self.assertFalse(result['request_ready'])
        counts=MINIMUMS.copy();counts['signals']=801
        self.assertEqual(review(counts,self.evidence())['status'],'FAIL')

    def test_waiting_data_and_fail_priority_are_explicit(self):
        counts=dict.fromkeys(MINIMUMS,0);evidence=self.evidence('WAITING_FOR_EVIDENCE')
        result=review(counts,evidence);self.assertEqual(result['status'],'WAITING_FOR_DATA');self.assertEqual(result['deficits']['context'],350)
        evidence['hashes']=dict(status='FAIL',witness_hashes=['SYNTHETIC_CORRUPT_FILE'])
        self.assertEqual(review(counts,evidence)['status'],'FAIL')
        evidence['hashes']=dict(status='PASS',witness_hashes=[])
        with self.assertRaisesRegex(ValueError,'WITHOUT_EVIDENCE'):review(counts,evidence)

    def test_each_of_18_gates_blocks_readiness_without_promoting_admission(self):
        self.assertEqual(len(GATES),18);self.assertEqual(len(set(GATES)),18)
        for name in GATES:
            with self.subTest(gate=name):
                evidence=self.evidence();evidence[name]=dict(status='WAITING_FOR_EVIDENCE',witness_hashes=[])
                result=review(MINIMUMS.copy(),evidence)
                self.assertEqual(result['status'],'WAITING_FOR_EVIDENCE');self.assertFalse(result['dataset_admitted'])
                evidence[name]=dict(status='FAIL',witness_hashes=['SYNTHETIC_FAILED_WITNESS'])
                self.assertEqual(review(MINIMUMS.copy(),evidence)['status'],'FAIL')

    def signal(self):return dict(signal_id='SYNTHETIC',side='BUY',bar_index=0,features={k:1. for k in FEATURES},feature_max_native_msc=299999)
    def tick(self,stamp,bid=1000.,ask=1002.):return dict(time_msc=stamp,bid=bid,ask=ask)

    def test_entry_features_and_frozen_baseline_replay_parity(self):
        from python.quote_replay import replay,Quote
        state=initial();consume(state,0,[self.tick(1)],self.signal())
        ticks=[self.tick(300001),self.tick(300002,1242.,1244.)]
        consume(state,1,ticks);row=state['rows'][0]
        path=[Quote(t['time_msc'],i,1,t['bid'],t['ask']) for i,t in enumerate(ticks)]
        for name,side in (('follow',1),('invert',-1)):
            expected=replay(path,side,allowed_end_exclusive=600000,coverage_verified=True)
            self.assertEqual(row[name+'_pnl'],expected['pnl']);self.assertEqual(row[name+'_exit'],expected['exit_time_msc'])
        self.assertEqual(validate_rows([row]),seal([row]))

    def test_time_exit_requires_real_next_quote_and_censors_missing_tail(self):
        state=initial();consume(state,0,[self.tick(1)],self.signal())
        for i in range(1,101):consume(state,i,[self.tick(i*300000+1)])
        self.assertEqual(state['rows'],[]);self.assertEqual(len(state['active']),1)
        consume(state,101,[self.tick(30300001)])
        self.assertEqual(state['rows'][0]['follow_pnl'],-2.)
        with self.assertRaisesRegex(ValueError,'OBSERVED_BAR_GAP'):consume(state,103,[self.tick(30900001)])

    def test_future_feature_cannot_enter(self):
        state=initial();signal=self.signal();signal['feature_max_native_msc']=600000
        consume(state,0,[self.tick(1)],signal)
        with self.assertRaisesRegex(ValueError,'NONCAUSAL'):consume(state,1,[self.tick(300001)])

    def test_new_native_export_adapter_against_existing_mql_synthetic_export(self):
        root=Path(__file__).resolve().parents[1]
        file=root/'research/studies/us30cash_m5_native_observations/weekend_20261107/cfweek_382ad54e_oracle.csv'
        with file.open(encoding='utf-8-sig') as stream:rows=list(csv.DictReader(stream))
        bars=[dict(time=int(r['time']),**{k:float(r[k]) for k in ('open','high','low','close')},tick_volume=int(r['volume'])) for r in rows]
        result=verify_export(rows,bars)
        self.assertEqual(result['status'],'PASS_RETROSPECTIVE_CONTEXT_DIAGNOSTIC');self.assertEqual(result['atr_candidate_compared'],287)
        bad=[dict(r) for r in rows];bad[-1]['atr']=str(float(bad[-1]['atr'])+1)
        self.assertEqual(verify_export(bad,bars)['status'],'FAILED_PARITY')

    def bc_bundle(self,root):
        grant,m=fixtures.AdmissionGateTests().bundle(root)
        old='outputs/admitted_native_studies/test/';new='outputs/admitted_native_studies/'+STUDY.lower()+'/'
        source=root/old;target=root/new;source.rename(target)
        grant=json.loads(json.dumps(grant).replace(old,new));m=json.loads(json.dumps(m).replace(old,new))
        package=root/'research/studies/bc_train_future_eval_v1';package.mkdir(parents=True)
        for name in ('contract.json','feature_whitelist.json'):(package/name).write_text('SYNTHETIC_BC_'+name)
        for name,key in (('contract.json','protocol_hash'),('feature_whitelist.json','feature_whitelist_hash')):
            grant[key]=hashlib.sha256((package/name).read_bytes()).hexdigest();m[key]=grant[key]
        grant['study_id']=m['study_id']=STUDY
        (root/grant['manifest_path']).write_text(json.dumps(m));grant['manifest_sha256']=hashlib.sha256((root/grant['manifest_path']).read_bytes()).hexdigest()
        return grant,m,package

    def test_bc_gate_uses_approved_bc_contract_instead_of_legacy(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);grant,m,package=self.bc_bundle(root)
            with patch('controller.training_admission_gate.AUTHORIZED_GRANT_HASHES',frozenset([seal(grant)])),patch('controller.training_admission_gate.subprocess.check_output',side_effect=lambda args,**kwargs:'' if args[1]=='status' else grant['code_head']):
                self.assertEqual(authorize_execution(grant,root)['study_id'],STUDY)
                (package/'contract.json').write_text('CHANGED_SYNTHETIC_PROTOCOL')
                with self.assertRaisesRegex(ValueError,'FROZEN_PROTOCOL'):authorize_execution(grant,root)

    def test_core_connector_retries_same_pid_without_task_change(self):
        from tools import prospective_pipeline as module
        api=Mock();api.initialize.side_effect=[False,True];api.last_error.return_value=(-10005,'SYNTHETIC')
        api.terminal_info.return_value=types.SimpleNamespace(data_path='C:/20C285FE08971A9A2E814AAC44AFC9D2')
        api.account_info.return_value=types.SimpleNamespace(server='XMGlobalSC-MT5 5',trade_mode=0)
        api.symbol_info.return_value=types.SimpleNamespace(chart_mode=0,trade_tick_size=.01)
        process=types.SimpleNamespace(pid=123,info=dict(exe='C:/Program Files/XM Global SC MT5 Terminal/terminal64.exe'))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);bc=root/'outputs/bc_train_future_eval_v1';bc.mkdir(parents=True);(bc/'current.json').write_text('{}')
            with patch.object(module,'ROOT',root),patch.dict('sys.modules',MetaTrader5=api),patch('psutil.process_iter',return_value=[process]),patch.object(module,'once') as record:
                ref=NativeReference();ref.connect()
                self.assertEqual(ref.bound_pid,123);self.assertEqual([c.kwargs['timeout'] for c in api.initialize.call_args_list],[5000,20000])
                self.assertFalse(record.call_args.args[1]['terminal_restarted'])

    def test_change_driven_reviewer_rejects_tampered_cache(self):
        from tools import bc_pretraining_worker as worker
        from controller.bc_study import initial as context_initial
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);base=root/'outputs/bc_train_future_eval_v1';base.mkdir(parents=True)
            package=root/'research/studies/bc_train_future_eval_v1';package.mkdir(parents=True)
            for name in ('contract.json','activation.json','role_decision.json','feature_whitelist.json'):(package/name).write_text('{}')
            (package/'contract.json').write_text('{"approved_proposal":{"statistics":{}}}')
            for name in ('controller/bc_admission.py','controller/bc_training_rows.py','controller/bc_study.py','controller/native_study_runner.py','controller/training_admission_gate.py','tools/bc_pretraining_worker.py','tools/bc_prefix_oracle.py'):
                file=root/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text('SYNTHETIC_ONLY')
            m=dict(study_id=STUDY,dataset_id='SYNTHETIC')
            with patch.object(worker,'ROOT',root),patch.object(worker.station,'BASE',base),patch.object(worker.station,'PACKAGE',package),patch.object(worker.station,'load_manifest',return_value=m),patch.object(worker,'checkpoint',return_value=context_initial()),patch.object(worker.subprocess,'check_output',return_value='synthetic-head'),patch('psutil.process_iter',return_value=[]),patch('psutil.virtual_memory',return_value=types.SimpleNamespace(available=1024**3)):
                first=worker.review_current();second=worker.review_current()
                self.assertEqual(first['status'],'WAITING_FOR_DATA');self.assertFalse(second['reevaluated'])
                packet=base/'pretraining_quarantine/future_authorization_package.json';original=packet.read_bytes();packet.write_text('{"changed":true}')
                with self.assertRaisesRegex(ValueError,'CACHED_CANDIDATE_PACKAGE_CHANGED'):worker.review_current()
                packet.write_bytes(original)
                file=base/'pretraining_quarantine/status.json';value=json.loads(file.read_bytes());value['counts']['context']=350;file.write_text(json.dumps(value))
                with self.assertRaisesRegex(ValueError,'CACHED_REVIEW_CHANGED'):worker.review_current()

    def test_active_recovery_preserves_closed_cf_and_does_not_claim_physical_restart(self):
        import sqlite3
        from controller.bc_recovery import recover
        from controller.prospective_processor import Ledger
        from controller.bc_study import initial as context_initial
        from controller.authorized_capture import sha
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);base=root/'outputs/bc_train_future_eval_v1';base.mkdir(parents=True)
            package=root/'research/studies/bc_train_future_eval_v1';package.mkdir(parents=True)
            old=root/'outputs/us30cash_m5_native_observations';(old/'old_capture').mkdir(parents=True)
            (old/'enabled.json').write_text('{"enabled":false}');(old/'current.json').write_text('{"capture_id":"old_capture"}')
            db=sqlite3.connect(old/'old_capture/snapshots.sqlite3');db.execute('CREATE TABLE records(n INTEGER,digest TEXT)');db.execute('INSERT INTO records VALUES(0,"SYNTHETIC_CLOSED_HEAD")');db.commit();db.close()
            for name in ('authorization.json','contract.json'):(package/name).write_text('{}')
            (package/'cf_preservation_verification.json').write_text(json.dumps(dict(old_records=1,old_chain_head='SYNTHETIC_CLOSED_HEAD')))
            activation=dict(source_hashes={},authorization_sha256=sha(package/'authorization.json'),contract_sha256=sha(package/'contract.json'),old_immutable_hashes={'outputs/us30cash_m5_native_observations/current.json':sha(old/'current.json')},dataset_id='SYNTHETIC')
            (package/'activation.json').write_text(json.dumps(activation));(base/'current.json').write_text(json.dumps(dict(manifest_sha256=sha(package/'activation.json'))))
            ledger=Ledger(base/'ledger.sqlite3');ledger.state['bc']=context_initial();ledger.commit();ledger.close()
            clock=dict(boot_id='SYNTHETIC_1',host_utc_label='2026-11-08T00:00:00+00:00')
            one=recover(root,clock,Mock(return_value=[]));self.assertFalse(one['physical_power_cycle_proven'])
            clock=dict(clock,boot_id='SYNTHETIC_2',host_utc_label='2026-11-09T00:00:00+00:00')
            two=recover(root,clock,Mock(return_value=[]));self.assertTrue(two['boot_transition_observed']);self.assertFalse(two['native_resume_proven'])
            (old/'enabled.json').write_text('{"enabled":true}')
            with self.assertRaisesRegex(ValueError,'INGRESS_REOPENED'):recover(root,clock,Mock(return_value=[]))
