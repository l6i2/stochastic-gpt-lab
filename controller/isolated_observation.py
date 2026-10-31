"""Append-only observational tail; no historical API, scientific admission or orders.

Reads only records appended after a newly sampled EOF/monotonic boundary in the
existing native observer. Original observer/data are never modified. Does not
claim that a second copy of callbacks is an independent dataset.
"""
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
import uuid

from .pretrain_contracts import canonical, seal, dependency_preflight

GENESIS='0'*64
LINE=re.compile(r'^\{"previous":"([0-9a-f]{64})","sha256":"([0-9a-f]{64})","payload":(.*)\}$')


def native_line(line):
    if not line.endswith(b'\n'):raise ValueError('INCOMPLETE_NATIVE_LINE')
    match=LINE.fullmatch(line.decode('utf-8').rstrip('\r\n'))
    if not match:raise ValueError('INVALID_NATIVE_LINE')
    parent,digest,body=match.groups()
    if hashlib.sha256((parent+'\n'+body).encode()).hexdigest()!=digest:
        raise ValueError('NATIVE_CHAIN_HASH_MISMATCH')
    row=json.loads(body)
    if row['server']!='XMGlobalSC-MT5 5' or row['symbol']!='US30Cash':
        raise ValueError('SOURCE_IDENTITY_MISMATCH')
    if row['kind'] not in ('SESSION_START','SESSION_END','ONTICK_LATEST_QUOTE','QUOTE_READ_FAILED','HEARTBEAT'):
        raise ValueError('UNSUPPORTED_SOURCE_KIND_NO_HISTORICAL_REQUERY')
    return parent,digest,row


def host_clock():
    """Actual host receipt evidence, explicitly not independently attested UTC."""
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
            r'SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters') as key:
        boot=str(winreg.QueryValueEx(key,'BootId')[0])
    clock=ctypes.windll.kernel32.GetTickCount64
    clock.restype=ctypes.c_ulonglong
    return dict(host_utc_label=datetime.now(timezone.utc).isoformat(),
                monotonic_ns=time.perf_counter_ns(),uptime_ms=int(clock()),boot_id=boot,
                utc_certified=False)


def eof_anchor(source):
    """Read only a bounded last-line anchor; never ingest the prior prefix."""
    source=Path(source)
    if source.is_symlink():raise ValueError('SYMLINK_SOURCE_REFUSED')
    with source.open('rb') as stream:
        stream.seek(0,2);size=stream.tell()
        stream.seek(max(0,size-16384));data=stream.read(size-stream.tell())
    lines=data.splitlines(keepends=True)
    if not lines or not lines[-1].endswith(b'\n'):
        raise ValueError('WAIT_FOR_COMPLETE_NATIVE_ANCHOR')
    _,digest,row=native_line(lines[-1])
    return dict(source_offset=size,source_sha256=digest,source_sequence=row['sequence'],
                source_session=row['session_id'],source_capture=row['capture_id'],
                callback_uptime_ms=row['callback_uptime_ms'],prefix_payloads_adopted=0)


def atomic(path,value):
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    with temporary.open('xb') as stream:
        stream.write(canonical(value)+b'\n');stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,path)


class Observation:
    """No scientific mode/authorization override exists in this writer."""
    def __init__(self,folder):
        self.folder=Path(folder)
        self.lock=None
        self.poisoned=False

    def _lock(self):
        import msvcrt
        self.lock=(self.folder/'writer.lock').open('a+b')
        if self.lock.seek(0,2)==0:self.lock.write(b'0');self.lock.flush()
        self.lock.seek(0)
        try:msvcrt.locking(self.lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            self.lock.close();self.lock=None
            raise RuntimeError('SINGLE_WRITER_LOCKED')

    def close(self):
        if self.lock is not None:
            import msvcrt
            self.lock.seek(0);msvcrt.locking(self.lock.fileno(),msvcrt.LK_UNLCK,1)
            self.lock.close();self.lock=None

    @classmethod
    def create(cls,base,source,anchor,clock,synthetic=False,parent_segment=None):
        if clock['utc_certified'] is not False:raise ValueError('HOST_CLOCK_CANNOT_SELF_CERTIFY')
        if clock['uptime_ms']<anchor['callback_uptime_ms']:raise ValueError('CLOCK_EPOCH_UNCOMPARABLE')
        capture_id='obs_'+uuid.uuid4().hex
        base=Path(base)
        base.mkdir(parents=True,exist_ok=True)
        if base.is_symlink():raise ValueError('SYMLINK_DESTINATION_REFUSED')
        folder=base/capture_id
        folder.mkdir(exist_ok=False)
        obj=cls(folder);obj._lock()
        manifest=dict(schema_version='isolated-observation/1.0',capture_id=capture_id,
            writer_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            mode='SYNTHETIC_TEST' if synthetic else 'OBSERVATIONAL_QUARANTINE',
            actual_start_clock=clock,anchor=anchor,source_path=str(Path(source).resolve()),
            native_event_timestamps_modified=False,historical_backfill_allowed=False,
            scientific_role_reserved=False,scientific_acceptance=False,dataset_admitted=False,
            training_authorized=False,scoring_authorized=False,orders_sent=0,
            utc_event_certified=False,independent_dataset_verified=False)
        if parent_segment is not None:
            manifest['parent_segment']=parent_segment
            manifest['inter_segment_gap']='UNVERIFIED_NOT_BACKFILLED_NO_CONTINUITY_CERTIFICATION'
        with (folder/'manifest.json').open('xb') as stream:
            stream.write(canonical(manifest)+b'\n');stream.flush();os.fsync(stream.fileno())
        obj.manifest=manifest
        obj.state=dict(rows=0,chain_head=GENESIS,manifest_sha256=seal(manifest),
            source_offset=anchor['source_offset'],source_sha256=anchor['source_sha256'],
            source_sequence=anchor['source_sequence'],last_callback_uptime_ms=anchor['callback_uptime_ms'],
            last_tick_native_msc=None,source_records=0,tick_callbacks=0,heartbeat_records=0,
            synthetic_feature_records=0)
        with (folder/'journal.jsonl').open('xb'):pass
        atomic(folder/'checkpoint.json',obj.state)
        return obj

    @classmethod
    def new_segment(cls,previous_folder,base,source,clock,synthetic=False):
        """Explicit restart transition, fresh EOF; never repairs gaps with history."""
        previous_folder=Path(previous_folder)
        manifest=json.loads((previous_folder/'manifest.json').read_text())
        checkpoint=json.loads((previous_folder/'checkpoint.json').read_text())
        if checkpoint['manifest_sha256']!=seal(manifest):raise ValueError('PARENT_MANIFEST_CHANGED')
        head=GENESIS;rows=0
        with (previous_folder/'journal.jsonl').open('rb') as stream:
            for raw in stream:
                if not raw.endswith(b'\n'):raise ValueError('PARENT_PARTIAL_JOURNAL_NOT_CERTIFIED')
                record=json.loads(raw)
                body=record['payload']
                if record['previous']!=head or record['sha256']!=seal(dict(previous=head,payload=body)) or body['index']!=rows or body['capture_id']!=manifest['capture_id']:
                    raise ValueError('PARENT_JOURNAL_CHANGED')
                head=record['sha256'];rows+=1
        if rows!=checkpoint['rows'] or head!=checkpoint['chain_head']:
            raise ValueError('PARENT_REQUIRES_CHECKPOINT_RECOVERY')
        reference=dict(capture_id=manifest['capture_id'],chain_head=head,rows=rows,
                       manifest_sha256=seal(manifest),source_offset=checkpoint['source_offset'])
        return cls.create(base,source,eof_anchor(source),clock,synthetic,parent_segment=reference)

    @classmethod
    def resume(cls,folder,clock):
        obj=cls(folder);obj._lock()
        try:
            obj.manifest=json.loads((obj.folder/'manifest.json').read_text())
            if clock['boot_id']!=obj.manifest['actual_start_clock']['boot_id'] or clock['uptime_ms']<obj.manifest['actual_start_clock']['uptime_ms']:
                raise ValueError('BOOT_OR_MONOTONIC_DISCONTINUITY_NEW_SEGMENT_REQUIRED')
            saved=json.loads((obj.folder/'checkpoint.json').read_text())
            if saved['manifest_sha256']!=seal(obj.manifest):raise ValueError('MANIFEST_CHANGED')
            state=dict(rows=0,chain_head=GENESIS,manifest_sha256=seal(obj.manifest),
                source_offset=obj.manifest['anchor']['source_offset'],source_sha256=obj.manifest['anchor']['source_sha256'],
                source_sequence=obj.manifest['anchor']['source_sequence'],
                last_callback_uptime_ms=obj.manifest['anchor']['callback_uptime_ms'],last_tick_native_msc=None,
                source_records=0,tick_callbacks=0,heartbeat_records=0,synthetic_feature_records=0)
            matched=saved['rows']==0 and saved['chain_head']==GENESIS
            with (obj.folder/'journal.jsonl').open('rb') as stream:
                for line in stream:
                    if not line.endswith(b'\n'):raise ValueError('PARTIAL_JOURNAL_PRESERVED_STOP')
                    record=json.loads(line)
                    body=record['payload']
                    if record['previous']!=state['chain_head'] or record['sha256']!=seal(dict(previous=state['chain_head'],payload=body)):
                        raise ValueError('JOURNAL_HASH_CHANGED')
                    if body['capture_id']!=obj.manifest['capture_id'] or body['index']!=state['rows']:
                        raise ValueError('JOURNAL_ID_OR_SEQUENCE_CHANGED')
                    state=body['resulting_state']|dict(chain_head=record['sha256'],rows=state['rows']+1)
                    if state['rows']==saved['rows']:
                        if state!=saved:raise ValueError('CHECKPOINT_PREFIX_CHANGED')
                        matched=True
            if not matched:raise ValueError('JOURNAL_TRUNCATED')
            if clock['uptime_ms']<state['last_callback_uptime_ms']:
                raise ValueError('RESUME_MONOTONIC_DISCONTINUITY')
            obj.state=state
            atomic(obj.folder/'checkpoint.json',state)  # recover complete durable orphan rows
            return obj
        except BaseException:
            obj.close();raise

    def _commit(self,event,state):
        if self.lock is None:raise RuntimeError('WRITER_CLOSED')
        if self.poisoned:raise RuntimeError('PREVIOUS_STORAGE_ERROR_REQUIRES_REOPEN_AND_VERIFICATION')
        payload=dict(index=self.state['rows'],capture_id=self.manifest['capture_id'],
                     event=event,resulting_state=state)
        digest=seal(dict(previous=self.state['chain_head'],payload=payload))
        record=dict(previous=self.state['chain_head'],sha256=digest,payload=payload)
        try:
            with (self.folder/'journal.jsonl').open('ab') as stream:
                stream.write(canonical(record)+b'\n');stream.flush();os.fsync(stream.fileno())
            self.state=state|dict(rows=self.state['rows']+1,chain_head=digest)
            atomic(self.folder/'checkpoint.json',self.state)
        except BaseException:
            self.poisoned=True
            raise

    def ingest(self,line,end_offset,receipt):
        parent,digest,row=native_line(line)
        anchor=self.manifest['anchor']
        if receipt['boot_id']!=self.manifest['actual_start_clock']['boot_id']:
            raise ValueError('BOOT_CHANGED_NEW_SEGMENT_REQUIRED')
        if receipt['monotonic_ns']<self.state.get('last_receipt_monotonic_ns',self.manifest['actual_start_clock']['monotonic_ns']):
            raise ValueError('LOCAL_MONOTONIC_REGRESSION')
        if row['session_id']!=anchor['source_session'] or row['capture_id']!=anchor['source_capture']:
            raise ValueError('SOURCE_SESSION_CHANGED_NEW_SEGMENT_REQUIRED')
        if parent!=self.state['source_sha256'] or row['sequence']!=self.state['source_sequence']+1:
            raise ValueError('SOURCE_GAP_DUPLICATE_OR_CHAIN_CHANGED')
        if end_offset!=self.state['source_offset']+len(line):raise ValueError('SOURCE_OFFSET_CHANGED')
        uptime=row['callback_uptime_ms']
        if uptime<self.state['last_callback_uptime_ms'] or row['read_uptime_ms']<uptime or receipt['uptime_ms']<row['read_uptime_ms']:
            raise ValueError('MONOTONIC_RECEIPT_ORDER_INVALID')
        state=dict(self.state,source_offset=end_offset,source_sha256=digest,
            source_sequence=row['sequence'],last_callback_uptime_ms=uptime,
            last_receipt_monotonic_ns=receipt['monotonic_ns'],
            source_records=self.state['source_records']+1)
        pre_cut=uptime<=self.manifest['actual_start_clock']['uptime_ms']
        flags=[]
        if pre_cut:flags.append('PRE_CUT_OR_EQUAL_RESOLUTION_NOT_ADOPTED')
        if row['connected'] is not True:flags.append('DISCONNECTED')
        if row['kind']=='ONTICK_LATEST_QUOTE' and not pre_cut:
            if row['time_msc']//1000!=row['time'] or any(not isinstance(row[k],(int,float)) or not math.isfinite(row[k]) for k in ('bid','ask')) or not 0<row['bid']<=row['ask']:
                raise ValueError('INVALID_NATIVE_QUOTE_OR_UNITS')
            prior=self.state['last_tick_native_msc']
            if prior is not None and row['time_msc']<prior:flags.append('NATIVE_TIMESTAMP_REGRESSION_UNMAPPED')
            state['last_tick_native_msc']=row['time_msc'];state['tick_callbacks']+=1
        if row['kind']=='HEARTBEAT' and not pre_cut:state['heartbeat_records']+=1
        event=dict(kind='SOURCE_OBSERVATION' if not pre_cut else 'EXCLUDED_PRE_CUT_METADATA',
            source_sha256=digest,source_sequence=row['sequence'],receipt_clock=receipt,
            callback_gap_ms=uptime-self.state['last_callback_uptime_ms'],quarantine_flags=flags,
            native_line=None if pre_cut else line.decode('utf-8'),
            native_event_utc_mapping='UNVERIFIED',event_creation_equals_receipt=False,
            feed_completeness='UNPROVEN_ONTICK_CAN_COALESCE',scientific_admission=False)
        self._commit(event,state)
        return event

    def pump(self,receipt_clock=host_clock,max_records=2000):
        source=Path(self.manifest['source_path'])
        if source.stat().st_size<self.state['source_offset']:raise ValueError('SOURCE_TRUNCATED')
        read=0
        with source.open('rb') as stream:
            stream.seek(self.state['source_offset'])
            while read<max_records:
                line=stream.readline(32768)
                if not line:break
                if not line.endswith(b'\n'):
                    if len(line)>=32768:raise ValueError('SOURCE_LINE_EXCEEDS_LIMIT')
                    break  # incomplete source write remains unread, no checkpoint advance
                self.ingest(line,stream.tell(),receipt_clock());read+=1
        return read

    def synthetic_features(self,observations,dataset_start_index,values):
        if self.manifest['mode']!='SYNTHETIC_TEST':raise ValueError('REAL_FEATURE_PRODUCER_NOT_IMPLEMENTED_OR_AUTHORIZED')
        verdict=dependency_preflight(observations,dataset_start_index)
        if set(values)!={r['feature'] for r in observations}:raise ValueError('FEATURE_WHITELIST_CHANGED')
        state=dict(self.state,synthetic_feature_records=self.state['synthetic_feature_records']+1)
        self._commit(dict(kind='SYNTHETIC_FEATURE_FIXTURE',values=values,dependencies=observations,
                          availability=verdict,targets_present=False),state)
