"""Apply the explicitly authorized forward-only role cut. No old data writes."""
import json
from pathlib import Path
import sys
import uuid
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from controller.authorized_capture import once,sha,manager_lock,fresh_nts,bracket
from controller.isolated_observation import host_clock,atomic
from controller.pretrain_contracts import seal
from controller.exclusive_roles import role_chain,validate_roles,verify_roles
from tools.prospective_pipeline import NativeReference

BASE=ROOT/'outputs/us30cash_m5_native_observations'
PACKAGE=ROOT/'research/studies/us30cash_m5_native_observations'
DECISION=PACKAGE/'exclusive_cut_v1'


def apply():
    with manager_lock(BASE):
        if (DECISION/'activation_complete.json').exists():
            done=json.loads((DECISION/'activation_complete.json').read_text())
            pointer=json.loads((BASE/'current.json').read_text())
            manifest_path=BASE/pointer['capture_id']/'manifest.json'
            if pointer['capture_id']!=done['capture_id'] or sha(manifest_path)!=done['new_manifest_sha256'] or pointer['manifest_sha256']!=done['new_manifest_sha256']:
                raise ValueError('EXCLUSIVE_ACTIVATION_POINTER_CHANGED')
            verify_roles(ROOT,json.loads(manifest_path.read_text()))
            once(BASE/'exclusive_role_current.json',dict(capture_id=done['capture_id'],dataset_id=done['dataset_id'],assignment=done['role_assignment']))
            return done
        auth_path=DECISION/'authorization.json';auth=json.loads(auth_path.read_text())
        if sha(PACKAGE/'RESERVATION_SCOPE_DECISION_REQUEST.md')!=auth['approved_decision_sha256']:
            raise ValueError('APPROVED_DECISION_CHANGED')
        if not (BASE/'legacy_ingress_closed.json').exists():raise ValueError('LEGACY_WRITERS_NOT_CLOSED')
        closure=json.loads((BASE/'legacy_ingress_closed.json').read_text())
        if closure['authorization_sha256']!=sha(auth_path):raise ValueError('CLOSURE_AUTHORITY_CHANGED')
        import psutil
        for p in psutil.process_iter(['name','cmdline']):
            command=' '.join(p.info['cmdline'] or [])
            if str(ROOT).lower() not in command.lower():continue
            if p.info['name'] not in ('pythonw.exe','python.exe'):continue
            if any(x in command for x in ('cf_study_station.py','new_capture_station.py','native_database_snapshots.py','prospective_pipeline.py')) and '--serve' in command:
                raise ValueError('RESERVATION_WRITER_STILL_ACTIVE')
            if 'research_station.py' in command and 'collect' in command:raise ValueError('RAW_RESERVATION_WRITER_ACTIVE')
        current=json.loads((BASE/'current.json').read_text());oldfolder=BASE/current['capture_id']
        old=json.loads((oldfolder/'manifest.json').read_text())
        if sha(oldfolder/'manifest.json')!=current['manifest_sha256'] or sha(PACKAGE/'contract.json')!=old['contract_sha256']:
            raise ValueError('ORIGINAL_MANIFEST_OR_CONTRACT_CHANGED')
        if old['producer_id']!='cfprod_5c64f0781dc148e5896391b1492ba144':raise ValueError('PRODUCER_CHANGED')
        intent_path=DECISION/'intent.json'
        if not intent_path.exists():
            once(intent_path,dict(capture_id='dbsnap_'+uuid.uuid4().hex,
                dataset_id='us30cash_m5_native_observations_20261105_01_dataset_02',previous_pointer=current,
                authorization_sha256=sha(auth_path),clock=host_clock()))
        intent=json.loads(intent_path.read_text());folder=BASE/intent['capture_id'];folder.mkdir(exist_ok=True)
        evidence=DECISION/'cutoff_clock_evidence.json'
        if not evidence.exists():
            before=fresh_nts();ref=NativeReference()
            try:
                ref.connect();terminal=ref.mt5.terminal_info();account=ref.mt5.account_info()
                if not terminal.connected or terminal.trade_allowed or account.server!='XMGlobalSC-MT5 5':raise ValueError('XM_IDENTITY_OR_TRADING_UNSAFE')
                start=host_clock();q=ref.mt5.symbol_info_tick('US30Cash');cut=host_clock()
                if q is None:raise ValueError('NO_NATIVE_CUT_OBSERVATION')
                quote={k:getattr(q,k) for k in ('time','time_msc','bid','ask','flags')}
            finally:ref.close()
            after=fresh_nts();utc=bracket(before,after,cut)
            cutoff=dict(clock=cut,read_start=start,native_anchor=quote,server='XMGlobalSC-MT5 5',symbol='US30Cash',
                minimum_native_open_msc=(quote['time_msc']//300000+1)*300000,utc=utc,
                domain='RECORDED_HOST_OBSERVATION_ORDER_AND_NATIVE_LABEL_FLOOR_NO_GENERATION_UTC_CERTIFICATION')
            once(evidence,dict(before=before,after=after,cutoff=cutoff))
        cutoff=json.loads(evidence.read_text())['cutoff']
        identities={k:old[k] for k in ('study_id','producer_id')}
        identities.update(capture_id=intent['capture_id'],dataset_id=intent['dataset_id'])
        ledger=role_chain([dict(kind='CLOSE_ALL_PRIOR_FUTURE_INGRESS',scope='PC_A_US30Cash_ALL_PRIOR_RESERVATIONS',
            cutoff_hash=seal(cutoff),previous_assets_and_access_preserved=True),
            dict(kind='ASSIGN_EXCLUSIVE_FORWARD_ROLE',**identities,cutoff_hash=seal(cutoff),admitted=False)])
        assignment=dict(ledger=ledger,cutoff=cutoff,authorization_observed_clock=auth['observed_clock'],
            authorization_path=auth_path.relative_to(ROOT).as_posix(),authorization_sha256=sha(auth_path),
            precut_data_adopted=False,legacy_bounds_recovered=False,training_authorized=False)
        validate_roles(assignment,identities)
        once(DECISION/'role_assignment.json',assignment)
        assignment_ref=dict(path=(DECISION/'role_assignment.json').relative_to(ROOT).as_posix(),sha256=sha(DECISION/'role_assignment.json'))
        once(BASE/'exclusive_role_current.json',dict(capture_id=intent['capture_id'],dataset_id=intent['dataset_id'],assignment=assignment_ref))
        sources=set(old['source_hashes'])|{'controller/exclusive_roles.py'}
        manifest=dict(old,**{k:v for k,v in identities.items() if k not in ('study_id','producer_id')},
            authorization_path=auth_path.relative_to(ROOT).as_posix(),authorization_sha256=sha(auth_path),
            source_hashes={n:sha(ROOT/n) for n in sorted(sources)},intent_clock=cutoff['clock'],activation=cutoff['utc'],
            role_cutoff=cutoff,exclusive_role_assignment=assignment_ref,predecessor_capture_id=old['capture_id'],
            previous_capture_membership_adopted=False,membership_role='EXCLUSIVE_FORWARD_ROLE_QUARANTINED')
        once(folder/'manifest.json',manifest)
        once(folder/'activation_clock_evidence.json',json.loads(evidence.read_text()))
        once(DECISION/'previous_pointer.json',current)
        atomic(BASE/'current.json',dict(capture_id=intent['capture_id'],manifest_sha256=sha(folder/'manifest.json')))
        once(DECISION/'activation_complete.json',dict(**identities,exclusive_cutoff=cutoff,
            role_assignment=assignment_ref,new_manifest_sha256=sha(folder/'manifest.json'),previous_capture_quarantined=True,
            all_previous_reservations_forward_closed=True,legacy_historical_membership_unknown=True,
            dataset_admission=False,training_authorized=False,orders_sent=False))
        atomic(BASE/'enabled.json',dict(enabled=True))
        return json.loads((DECISION/'activation_complete.json').read_text())


if __name__=='__main__':print(json.dumps(apply(),indent=2))
