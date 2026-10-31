"""Authorized quarantine capture manager. No historical query, fit, score or orders.

All writes belong to a new study root. Previous reservation closure is a separate
immutable forward-only decision; no previous dataset/manifest/checkpoint is edited.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid

from .isolated_observation import Observation,atomic,eof_anchor,host_clock,GENESIS
from .pretrain_contracts import canonical,seal
from .safety_gate import ROOT

STUDY='US30CASH_M5_NATIVE_20261030_01'
STATION=ROOT/'outputs/new_native_studies/us30cash_m5_native_20261030_01'
NATIVE=Path.home()/'AppData/Roaming/MetaQuotes/Terminal/20C285FE08971A9A2E814AAC44AFC9D2/MQL5/Files/ResearchDiagnostics/ProspectiveUTC'
AUTH=ROOT/'research/studies/us30cash_m5_native_collection_activation_v1/authorization.json'
REQUEST_SHA='614b1c40df5913a6e50531f278d3a9640bde6d98cab87b2e87cee6f28597a5c3'
AUTHENTICATION='TLS_CHAIN_HOSTNAME_ALPN_EXPORTER_AEAD_UID_ORIGIN_VERIFIED'


def io_path(path):
    """Windows extended path for UUID checkpoint temporaries; no path relocation."""
    path=Path(path).resolve()
    if __import__('os').name=='nt' and not str(path).startswith('\\\\?\\'):
        return Path('\\\\?\\'+str(path))
    return path


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


def once(path,value):
    """Immutable file creation; a restart may verify, never replace, identical bytes."""
    data=canonical(value)+b'\n'
    if path.exists():
        if path.read_bytes()!=data:raise ValueError('IMMUTABLE_FILE_ALREADY_DIFFERS_'+path.name)
        return
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data);stream.flush();__import__('os').fsync(stream.fileno())


@contextmanager
def manager_lock(station):
    import msvcrt
    station=Path(station);station.mkdir(parents=True,exist_ok=True)
    with (station/'manager.lock').open('a+b') as stream:
        if stream.seek(0,2)==0:stream.write(b'0');stream.flush()
        stream.seek(0)
        try:msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:raise RuntimeError('CAPTURE_MANAGER_ALREADY_RUNNING')
        try:yield
        finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)


def validate_authorization(auth):
    if auth['study_id']!=STUDY or auth['approved_request_sha256']!=REQUEST_SHA or auth['collection_authorized'] is not True or auth['previous_reservation_new_ingress_closure_authorized'] is not True:
        raise ValueError('LIMITED_COLLECTION_AUTHORIZATION_MISSING')
    for key in ('training_authorized','scoring_authorized','dataset_admission_authorized','demo_enabled','live_trading','orders_authorized'):
        if auth[key] is not False:raise ValueError('AUTHORIZATION_SCOPE_EXCEEDED')


def bracket(before,after,cut):
    for m in (before,after):
        if m['authentication']!=AUTHENTICATION or m['broker_mapping_authorized'] is not False or m['clock_adjusted'] is not False:
            raise ValueError('UNAUTHENTICATED_OR_WRONG_NTS_SCOPE')
    if before['origin']!=after['origin'] or after['server_receive_utc_ns']<before['server_transmit_utc_ns']:
        raise ValueError('NTS_ORIGIN_OR_ORDER_INCONSISTENT')
    if not before['receive_kernel_uptime_ms_interval'][1]<=cut['uptime_ms']<=after['receive_kernel_uptime_ms_interval'][0]:
        raise ValueError('ACTIVATION_NOT_BETWEEN_LOCAL_NTS_RECEIVE_OBSERVATIONS')
    lower=before['server_transmit_utc_ns']-before['server_advertised_error_ns']
    upper=after['server_receive_utc_ns']+after['server_advertised_error_ns']
    if upper<lower:raise ValueError('INVALID_ACTIVATION_UTC_BRACKET')
    estimate=(lower+upper)//2
    label=lambda ns:datetime.fromtimestamp(ns/1000000000,timezone.utc).isoformat()
    return dict(utc_estimate=label(estimate),utc_lower=label(lower),utc_upper=label(upper),
        utc_interval_ns=[lower,upper],estimate_ns=estimate,half_width_ns=(upper-lower+1)//2,
        basis='CAUSAL_ORDER_BETWEEN_AUTHENTICATED_PRE_TRANSMIT_AND_POST_RECEIVE_SERVER_TIMESTAMPS',
        uncertainty='CONDITIONAL_ON_REMOTE_SERVER_ADVERTISED_ERROR_NOT_METROLOGICAL_ABSOLUTE',
        local_clock_offset_or_drift_extrapolated=False,broker_event_utc_certified=False,
        before_capture_id=before['capture_id'],after_capture_id=after['capture_id'])


def append_decisions(folder,payloads):
    parent=GENESIS
    for sequence,payload in enumerate(payloads):
        body=dict(sequence=sequence,previous=parent,payload=payload)
        digest=seal(body)
        once(folder/(f'{sequence:04d}_'+digest+'.json'),dict(body,sha256=digest))
        parent=digest
    return parent


def verify_decisions(folder):
    parent=GENESIS
    for sequence,path in enumerate(sorted(folder.glob('*.json'))):
        row=json.loads(path.read_text());digest=row.pop('sha256')
        if row['sequence']!=sequence or row['previous']!=parent or seal(row)!=digest:
            raise ValueError('IMMUTABLE_DECISION_LEDGER_CHANGED')
        parent=digest
    return parent


def fresh_nts():
    process=subprocess.run([str(ROOT/'.venv/Scripts/python.exe'),str(ROOT/'tools/new_capture_clock.py'),'time.cloudflare.com'],
        capture_output=True,text=True,timeout=25,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if process.returncode:raise RuntimeError('FRESH_AUTHENTICATED_NTS_UNAVAILABLE')
    return json.loads(process.stdout)


class CaptureManager:
    def __init__(self,station=STATION,native=NATIVE,auth_path=AUTH,clock=host_clock,nts=fresh_nts):
        self.station=Path(station);self.native=Path(native);self.auth_path=Path(auth_path)
        self.clock=clock;self.nts=nts;self.writer=None;self.root=None

    def latest_source(self):
        files=list(self.native.glob('pc_a_prospective_utc_v1_*.jsonl'))
        if not files:raise ValueError('WAITING_FOR_PINNED_XM_OBSERVER')
        return max(files,key=lambda p:p.stat().st_mtime_ns)

    def snapshot_previous(self,root):
        paths=['docs/FUTURE_VALIDATION_PROTOCOL.md','docs/PROSPECTIVE_EVALUATION_PROTOCOL.md',
            'research/studies/us30cash_m5_native_pretrain_v1/package_hashes.json',
            'outputs/pc_a_prospective_utc/checkpoints.json']
        index={}
        for relative in paths:
            path=ROOT/relative
            if not path.exists():index[relative]={'status':'MISSING_NOT_INVENTED'};continue
            data=path.read_bytes();digest=hashlib.sha256(data).hexdigest()
            copy=root/'prior_evidence'/(digest+'.snapshot')
            if not copy.exists():
                copy.parent.mkdir(parents=True,exist_ok=True)
                with copy.open('xb') as stream:stream.write(data);stream.flush();__import__('os').fsync(stream.fileno())
            elif copy.read_bytes()!=data:raise ValueError('SNAPSHOT_CHANGED')
            index[relative]=dict(sha256=digest,bytes=len(data),original_modified=False)
        once(root/'prior_evidence_index.json',index)

    def activate(self):
        auth=json.loads(self.auth_path.read_text(encoding='utf-8'))
        validate_authorization(auth)
        self.station.mkdir(parents=True,exist_ok=True)
        pointer=self.station/'current_capture.json'
        if pointer.exists():return self.load()
        current_intent=self.station/'activation_intent_current.json'
        if current_intent.exists():
            ref=json.loads(current_intent.read_text())
            intent_path=self.station/'activation_intents'/ref['file']
            if Path(ref['file']).name!=ref['file'] or sha(intent_path)!=ref['sha256']:
                raise ValueError('ACTIVATION_INTENT_POINTER_CHANGED')
        else:intent_path=self.station/'activation_intent.json'
        if intent_path.exists():intent=json.loads(intent_path.read_text())
        else:
            intent=dict(capture_id='us30cap_'+uuid.uuid4().hex,authorization_sha256=sha(self.auth_path),study_id=STUDY)
            once(intent_path,intent)
        if intent['authorization_sha256']!=sha(self.auth_path):raise ValueError('ACTIVATION_AUTHORIZATION_CHANGED')
        root=self.station/intent['capture_id'];root.mkdir(exist_ok=True)
        if not (root/'prior_evidence_index.json').exists():self.snapshot_previous(root)
        before_path=root/'activation_nts_before.json'
        if not before_path.exists():once(before_path,self.nts())
        before=json.loads(before_path.read_text())
        boundary_path=root/'activation_boundary.json'
        if not boundary_path.exists():
            source=self.latest_source();anchor=eof_anchor(source);cut=self.clock()
            once(boundary_path,dict(source_path=str(source.resolve()),anchor=anchor,clock=cut))
        boundary=json.loads(boundary_path.read_text())
        segment_pointer=root/'initial_segment.json'
        if segment_pointer.exists():segment=json.loads(segment_pointer.read_text())['segment']
        else:
            candidates=list((root/'segments').glob('obs_*/manifest.json'))
            if candidates:
                if len(candidates)!=1:raise ValueError('AMBIGUOUS_INITIAL_SEGMENTS')
                segment=candidates[0].parent.name
            else:
                obj=Observation.create(io_path(root/'segments'),Path(boundary['source_path']),boundary['anchor'],boundary['clock'])
                segment=obj.folder.name;obj.close()
            once(segment_pointer,dict(segment=segment))
        after_path=root/'activation_nts_after.json'
        if not after_path.exists():once(after_path,self.nts())
        after=json.loads(after_path.read_text())
        utc=bracket(before,after,boundary['clock'])
        once(root/'activation_utc.json',utc)
        decisions=[dict(kind='USER_LIMITED_AUTHORIZATION',authorization_sha256=sha(self.auth_path),
                       approved_request_sha256=REQUEST_SHA,training_authorized=False,scoring_authorized=False),
            dict(kind='PREVIOUS_RESERVATION_NEW_INGRESS_CLOSED',reservation_id='us30cash_m5_future_20261019_v1',
                 effective_boundary_sha256=sha(boundary_path),activation_utc_sha256=sha(root/'activation_utc.json'),
                 previous_assets_modified=False,old_observers_remain_observational=True),
            dict(kind='NEW_CAPTURE_RESERVED_QUARANTINED',capture_id=intent['capture_id'],study_id=STUDY,
                 effective_boundary_sha256=sha(boundary_path),dataset_admitted=False,old_segments_adopted=False)]
        decision_head=append_decisions(root/'decisions',decisions)
        manifest=dict(schema_version='authorized-quarantine-capture/1.0',capture_id=intent['capture_id'],study_id=STUDY,
            mode='QUARANTINED',authorization_sha256=sha(self.auth_path),decision_chain_head=decision_head,
            activation_utc=utc,boundary_sha256=sha(boundary_path),initial_segment=segment,
            activation_nts_before_sha256=sha(before_path),activation_nts_after_sha256=sha(after_path),
            activation_utc_sha256=sha(root/'activation_utc.json'),prior_evidence_index_sha256=sha(root/'prior_evidence_index.json'),
            initial_segment_manifest_sha256=sha(root/'segments'/segment/'manifest.json'),
            no_backfill=True,previous_reservation_status='CLOSED_TO_NEW_SCIENTIFIC_INGRESS_FROM_BOUNDARY',
            dataset_admission=False,independence_certified=False,causal_audit='FAIL_GLOBAL_UNCHANGED',
            training_authorized=False,scoring_authorized=False,DEMO='DISABLED',LIVE_TRADING=False,orders_sent=0)
        once(root/'collection_manifest.json',manifest)
        state=root/'runtime_state.json'
        if not state.exists():atomic(state,dict(active_segment=segment,segments=[segment],restarts=0))
        atomic(pointer,dict(capture_id=intent['capture_id'],manifest_sha256=sha(root/'collection_manifest.json')))
        self.root=root
        return manifest

    def load(self):
        pointer=json.loads((self.station/'current_capture.json').read_text())
        if not __import__('re').fullmatch('us30cap_[0-9a-f]{32}',pointer['capture_id']):raise ValueError('INVALID_CAPTURE_POINTER')
        self.root=self.station/pointer['capture_id']
        manifest=json.loads((self.root/'collection_manifest.json').read_text())
        if sha(self.root/'collection_manifest.json')!=pointer['manifest_sha256'] or sha(self.auth_path)!=manifest['authorization_sha256']:
            raise ValueError('COLLECTION_MANIFEST_OR_AUTHORIZATION_CHANGED')
        validate_authorization(json.loads(self.auth_path.read_text()))
        if verify_decisions(self.root/'decisions')!=manifest['decision_chain_head']:
            raise ValueError('DECISION_CHAIN_HEAD_CHANGED')
        for filename,key in (('activation_boundary.json','boundary_sha256'),
                ('activation_nts_before.json','activation_nts_before_sha256'),
                ('activation_nts_after.json','activation_nts_after_sha256'),
                ('activation_utc.json','activation_utc_sha256'),('prior_evidence_index.json','prior_evidence_index_sha256')):
            if sha(self.root/filename)!=manifest[key]:raise ValueError('IMMUTABLE_ACTIVATION_EVIDENCE_CHANGED')
        return manifest

    def poll(self):
        manifest=self.load()
        state_path=self.root/'runtime_state.json';state=json.loads(state_path.read_text())
        folder=self.root/'segments'/state['active_segment']
        now=self.clock()
        old=json.loads((folder/'manifest.json').read_text())
        latest=self.latest_source()
        same_boot=old['actual_start_clock']['boot_id']==now['boot_id']
        same_source=Path(old['source_path']).resolve()==latest.resolve()
        if not same_boot or not same_source:
            if self.writer is not None:self.writer.close();self.writer=None
            if not same_boot and same_source:
                return self.status('WAITING_NEW_NATIVE_SESSION_AFTER_BOOT')
            self.writer=Observation.new_segment(io_path(folder),io_path(self.root/'segments'),latest,self.clock())
            state['active_segment']=self.writer.folder.name;state['segments'].append(self.writer.folder.name);state['restarts']+=1
            atomic(state_path,state)
        elif self.writer is None:self.writer=Observation.resume(io_path(folder),now)
        ingested=self.writer.pump(self.clock,max_records=2000)
        return self.status('ACTIVE_QUARANTINED',ingested)

    def status(self,status,ingested=0):
        manifest=json.loads((self.root/'collection_manifest.json').read_text())
        state=json.loads((self.root/'runtime_state.json').read_text())
        totals=dict(source_records=0,tick_callbacks=0,heartbeat_records=0)
        for segment in state['segments']:
            checkpoint=json.loads((self.root/'segments'/segment/'checkpoint.json').read_text())
            for key in totals:totals[key]+=checkpoint[key]
        current_checkpoint=json.loads((self.root/'segments'/state['active_segment']/'checkpoint.json').read_text())
        segment_manifest=json.loads((self.root/'segments'/state['active_segment']/'manifest.json').read_text())
        now=self.clock()
        age=now['uptime_ms']-current_checkpoint['last_callback_uptime_ms'] if now['boot_id']==segment_manifest['actual_start_clock']['boot_id'] else None
        if status=='ACTIVE_QUARANTINED' and (age is None or age>10000):status='HEARTBEAT_OVERDUE_QUARANTINED'
        result=dict(capture_id=manifest['capture_id'],status=status,new_records_last_poll=ingested,
            observed_clock=now,activation_utc=manifest['activation_utc'],totals=totals,
            last_callback_age_ms=age,liveness_rule='TWO_NOMINAL_5S_TIMER_PERIODS_NOT_EVENT_LOSS_PROOF',
            segments=len(state['segments']),active_segment=state['active_segment'],
            dataset_admission=False,training_authorized=False,scoring_authorized=False,
            native_event_utc_mapping='UNVERIFIED',feed_completeness='UNPROVEN_ONTICK_CAN_COALESCE',
            previous_reservation_status=manifest['previous_reservation_status'],CAUSAL_AUDIT='FAIL_GLOBAL_UNCHANGED',
            LIVE_TRADING=False,orders_sent=0)
        atomic(self.root/'collector_status.json',result)
        return result

    def close(self):
        if self.writer is not None:self.writer.close();self.writer=None
