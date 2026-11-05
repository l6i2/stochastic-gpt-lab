"""Bounded diagnostics on C+F and its existing read-only native observer.

Isolated DB replays and diagnostic IPC reads never enter the capture ledger.
"""
import argparse
from collections import Counter, defaultdict
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import queue
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from controller.authorized_capture import NATIVE, once, sha
from controller.isolated_observation import GENESIS, atomic, native_line
from controller.native_database_snapshots import Store
from controller.pretrain_contracts import canonical, seal


def distribution(values):
    ordered = sorted(values)
    if not ordered:
        return dict(n=0, p50_ms=None, p95_ms=None, p99_ms=None, max_ms=None)
    def quantile(p):
        return round(ordered[math.ceil(len(ordered)*p)-1]/1_000_000, 4)
    return dict(n=len(ordered), p50_ms=quantile(.5), p95_ms=quantile(.95),
                p99_ms=quantile(.99), max_ms=quantile(1))


class Profile:
    def __init__(self):
        self.records = []

    @contextmanager
    def phase(self, name):
        start = time.perf_counter_ns()
        result = 'OK'
        try:
            yield
        except BaseException:
            result = 'ERROR'
            raise
        finally:
            end = time.perf_counter_ns()
            self.records.append(dict(phase=name, start_ns=start, end_ns=end,
                                     duration_ns=end-start, result=result))

    def summary(self):
        grouped = defaultdict(list)
        for row in self.records:
            grouped[row['phase']].append(row['duration_ns'])
        return {name:distribution(values) for name,values in grouped.items()}


class PreparedStore(Store):
    """Trial writer. The exact existing canonical chain and SQLite settings."""
    def commit_profiled(self, events, profile):
        with profile.phase('hash_and_checkpoint'):
            checkpoint = canonical(self.state)
            state_hash = hashlib.sha256(checkpoint).hexdigest()
            head, index = self.head, self.count
            rows = []
            for event in [*events, dict(kind='CHECKPOINT', state_hash=state_hash)]:
                payload = dict(event, quarantine=True, admitted=False)
                digest = seal(dict(previous=head, payload=payload))
                rows.append((index, head, digest, canonical(payload).decode()))
                head, index = digest, index+1
        try:
            with profile.phase('sqlite_write'):
                self.db.execute('BEGIN IMMEDIATE')
                self.db.executemany('INSERT INTO records VALUES(?,?,?,?)', rows)
                self.db.execute('INSERT OR REPLACE INTO state VALUES(1,?,?)', (checkpoint.decode(), state_hash))
            with profile.phase('sqlite_commit'):
                self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        self.head, self.count = head, index


def read_window(folder, limit=800, previous=None):
    path = (folder/'snapshots.sqlite3').resolve().as_uri()+'?mode=ro'
    with closing(sqlite3.connect(path,uri=True)) as db:
        db.execute('BEGIN')
        end = db.execute('SELECT max(n) FROM records').fetchone()[0]
        body,digest = db.execute('SELECT body,digest FROM state WHERE id=1').fetchone()
        state = json.loads(body)
        if seal(state) != digest:
            raise ValueError('SOURCE_STATE_HASH_CHANGED')
        floor = max(0,end-limit+1)
        if previous is not None:
            count = previous['records']
            if db.execute('SELECT digest FROM records WHERE n=?',(count-1,)).fetchone() != (previous['chain_head'],):
                raise ValueError('SOURCE_BEFORE_WINDOW_HEAD_CHANGED')
            floor = max(floor,count)
        if floor>end:raise ValueError('WAITING_FOR_NEW_OBSERVATIONS')
        size = db.execute('SELECT sum(length(body)) FROM records WHERE n>=?',(floor,)).fetchone()[0]
        if size > 16*1024*1024:
            raise ValueError('DIAGNOSTIC_TAIL_MEMORY_BOUND_EXCEEDED')
        tail = db.execute('SELECT n,previous,digest,body FROM records WHERE n>=? ORDER BY n',(floor,)).fetchall()
        expected = tail[0][1]
        batches, batch, polls, boundaries, pairs = [],[],[],[],[]
        start = tail[0][0]
        # Discard the possible partial transaction at the start of the bounded tail.
        first = start == 0 or (previous is not None and start == previous['records'])
        for n,previous,checksum,raw in tail:
            row = json.loads(raw)
            if n != start or previous != expected or seal(dict(previous=previous,payload=row)) != checksum:
                raise ValueError('SOURCE_TAIL_CHAIN_CHANGED')
            start += 1
            expected = checksum
            if row['kind']=='CHECKPOINT':
                if first and batch:batches.append(batch)
                first=True
                batch=[]
            elif first:
                batch.append(row)
                if row['kind']=='LIVE_LATEST_STATE_POLL':polls.append(row)
                if row['kind'] in ('NEW_OBSERVATION_EPOCH','OBSERVATION_INTERRUPTION'):
                    boundaries.append(dict(record=n,kind=row['kind'],reason=row.get('reason')))
                if row['kind']=='DATABASE_SNAPSHOT_PAIR' and row['assessment']['status']=='VERIFIED_DATABASE_VIEW_ONLY':
                    pairs.append(row)
        if row['kind']!='CHECKPOINT' or row['state_hash']!=digest:
            raise ValueError('SOURCE_CHECKPOINT_NOT_BOUND')
    return dict(state=state, batches=batches, polls=polls, boundaries=boundaries,
                pairs=pairs, head=expected, records=end+1)


def live_timing(window):
    polls = window['polls']
    intervals = []
    long_observations = []
    for previous,current in zip(polls,polls[1:]):
        if previous['read_end']['boot_id']!=current['read_end']['boot_id']:continue
        duration = current['read_end']['monotonic_ns']-previous['read_end']['monotonic_ns']
        if duration<0:raise ValueError('OBSERVED_MONOTONIC_REGRESSION')
        intervals.append(duration)
        if duration>10**10:
            long_observations.append(dict(before=previous['read_end'],after=current['read_end'],
                spacing_ns=duration,identity_and_quote_ns=current['identity_and_quote_ns'],
                previous_poll_timing=current.get('previous_poll_timing')))
    return dict(poll_spacing=distribution(intervals), observed_spacing_over_10s=sum(i>10**10 for i in intervals),
                same_boot_intervals=len(intervals), boundaries=window['boundaries'], long_observations=long_observations,
                connection=distribution([p['connection_ns'] for p in polls]),
                identity_and_quote=distribution([p['identity_and_quote_ns'] for p in polls]),
                commit=distribution([p['previous_poll_timing']['commit_ns'] for p in polls if p.get('previous_poll_timing')]),
                poll=distribution([p['previous_poll_timing']['poll_ns'] for p in polls if p.get('previous_poll_timing')]))


def passive_snapshot(root=ROOT):
    """Reuse the quality reporter's validated head. Never call terminal IPC here."""
    base = root/'outputs/us30cash_m5_native_observations'
    quality = json.loads((base/'quality_status.json').read_text())
    if quality['status'] != 'PASS_INCREMENTAL_QUARANTINED':return
    pointer = json.loads((base/'current.json').read_text())
    capture_id = pointer['capture_id']
    if capture_id != quality['capture_id'] or Path(capture_id).name != capture_id:
        raise ValueError('TELEMETRY_CAPTURE_CHANGED')
    target = base/'stability_telemetry.json'
    if target.exists() and json.loads(target.read_text()).get('chain_head') == quality['chain_head']:
        return
    path = (base/capture_id/'snapshots.sqlite3').resolve().as_uri()+'?mode=ro'
    end = quality['records_verified']
    with closing(sqlite3.connect(path,uri=True)) as db:
        db.execute('BEGIN')
        if db.execute('SELECT digest FROM records WHERE n=?',(end-1,)).fetchone() != (quality['chain_head'],):
            raise ValueError('TELEMETRY_QUALITY_HEAD_CHANGED')
        rows = db.execute("SELECT n,body FROM records WHERE n>=? AND n<? AND json_extract(body,'$.kind') IN ('LIVE_LATEST_STATE_POLL','NEW_OBSERVATION_EPOCH','OBSERVATION_INTERRUPTION') ORDER BY n",(max(0,end-800),end))
        polls, boundaries = [], []
        for index,body in rows:
            row = json.loads(body)
            if row['kind']=='LIVE_LATEST_STATE_POLL':polls.append(row)
            else:boundaries.append(dict(record=index,kind=row['kind'],reason=row.get('reason')))
    atomic(target,dict(chain_head=quality['chain_head'],records=end,epoch=quality['epoch'],
                       observed_host_utc=datetime.now(timezone.utc).isoformat(),
                       timing=live_timing(dict(polls=polls,boundaries=boundaries)),
                       admission=False,training_executed=False))


def sqlite_trial(out, window):
    batches = window['batches'][-40:]
    if not batches:raise ValueError('NO_COMPLETE_BATCH_FOR_SQLITE_TRIAL')
    results = {}
    for label, factory in (('baseline',Store),('prepared',PreparedStore)):
        path=out/(label+'.sqlite3')
        store=factory(path);profile=Profile()
        try:
            store.state=window['state']
            for batch in batches:
                with profile.phase('durable_batch'):
                    if label=='baseline':store.commit(batch)
                    else:store.commit_profiled(batch,profile)
            results[label]=dict(records=store.count, head=store.head, phases=profile.summary(),
                                journal=store.db.execute('PRAGMA journal_mode').fetchone()[0],
                                synchronous=store.db.execute('PRAGMA synchronous').fetchone()[0])
        finally:store.close()
        reopened=Store(path)
        try:
            if reopened.head!=results[label]['head'] or reopened.state!=window['state']:
                raise ValueError('ISOLATED_REOPEN_CHANGED')
        finally:reopened.close()
    if results['baseline']['head']!=results['prepared']['head']:
        raise ValueError('ISOLATED_COMMIT_EQUIVALENCE_FAILED')
    # Exercise the proposed single-writer queue against an unavailable writer.
    handoff=queue.Queue(maxsize=4)
    for index in range(4):handoff.put_nowait(index)
    try:handoff.put_nowait(4)
    except queue.Full:saturated=True
    else:saturated=False
    if not saturated or [handoff.get_nowait() for _ in range(4)]!=list(range(4)):
        raise ValueError('ISOLATION_BACKPRESSURE_POLICY_FAILED')
    return dict(results=results, real_payload_batches=len(batches), byte_equivalent_chain=True,
                queue=dict(capacity=4, blocked_writer_saturates=True, dropped_or_admitted_records=0,
                           disposition='REJECTED_FOR_PRODUCTION_WITHOUT_DURABLE_HANDOFF'))


def ipc_trial(window, out):
    from tools.prospective_pipeline import NativeReference
    ref=NativeReference();profile=Profile()
    pair_by_frame={row['frame_seconds']:row for row in window['pairs']}
    try:
        with profile.phase('connect'):ref.connect()
        api=ref.mt5
        for _ in range(8):
            with profile.phase('iteration'):
                with profile.phase('account_identity'):account=api.account_info()
                with profile.phase('terminal_identity'):terminal=api.terminal_info()
                with profile.phase('symbol_info'):symbol=api.symbol_info('US30Cash')
                if not account or account.server!='XMGlobalSC-MT5 5' or account.trade_mode!=0 or not terminal or not terminal.connected or terminal.trade_allowed or not symbol:
                    raise ValueError('DIAGNOSTIC_XM_IDENTITY_UNSAFE')
                with profile.phase('tick'):tick=api.symbol_info_tick('US30Cash')
                if tick is None:raise ValueError('DIAGNOSTIC_NO_QUOTE')
        for frame,pair in pair_by_frame.items():
            start=datetime.fromtimestamp(pair['start_native_msc']/1000,timezone.utc)
            end=datetime.fromtimestamp((pair['end_native_exclusive_msc']-1000)/1000,timezone.utc)
            with profile.phase('closed_m1' if frame==60 else 'closed_m5'):
                rates=api.copy_rates_range('US30Cash',api.TIMEFRAME_M1 if frame==60 else api.TIMEFRAME_M5,start,end)
            with profile.phase('validate_bar_payload'):
                if rates is None or len(rates)!=1 or any(rates[0][name]!=value for name,value in pair['native_bar'].items()):
                    raise ValueError('DIAGNOSTIC_NATIVE_BAR_CHANGED')
        with profile.phase('atomic_status_publication'):
            atomic(out/'isolated_status.json',dict(status='DIAGNOSTIC_ONLY',orders=0))
    finally:ref.close()
    return dict(phases=profile.summary(), samples=profile.records,
                symbol_checks_retained=True, historical_diagnostic_only=True, orders_sent=0)


def native_comparison(window):
    sources=sorted(NATIVE.glob('*.jsonl'),key=lambda p:p.stat().st_mtime,reverse=True)
    if not sources:return dict(status='NO_EXISTING_OBSERVER_LOG')
    path=sources[0];limit=path.stat().st_size
    if limit>64*1024*1024:return dict(status='OBSERVER_RESOURCE_BOUND_EXCEEDED',bytes=limit)
    intervals=[p for p in window['pairs'] if p['frame_seconds']==300]
    observed=defaultdict(Counter);timing=[];head=GENESIS;sequence=0;last_kind=None;minimum=None;maximum=None
    with path.open('rb') as stream:
        while stream.tell()<limit:
            raw=stream.readline(limit-stream.tell())
            if not raw.endswith(b'\n'):break
            parent,digest,row=native_line(raw)
            if parent!=head or row['sequence']!=sequence:raise ValueError('OBSERVER_CHAIN_DISCONTINUITY')
            head=digest;sequence+=1;last_kind=row['kind']
            if last_kind!='ONTICK_LATEST_QUOTE':continue
            stamp=row['time_msc']
            minimum=stamp if minimum is None else min(minimum,stamp)
            maximum=stamp if maximum is None else max(maximum,stamp)
            opening=stamp//300000*300000
            observed[opening][(stamp,row['bid'],row['ask'],row['flags'])]+=1
            timing.append((row['read_uptime_ms']-row['callback_uptime_ms'])*1000000)
    comparisons=[]
    for pair in intervals:
        start,end=pair['start_native_msc'],pair['end_native_exclusive_msc']
        if minimum is None or not minimum<=start<end<=maximum:continue
        query=next((row for batch in window['batches'] for row in batch if row['kind']=='DATABASE_QUERY_OBSERVATION'
                    and row['epoch']==pair['epoch'] and row['frame_seconds']==300 and row['observation']['start_native_msc']==start),None)
        if query is None:continue
        reference=Counter((r['time_msc'],r['bid'],r['ask'],r['flags']) for r in query['rows'])
        callbacks=observed[start]
        comparisons.append(dict(start_native_msc=start,reference=sum(reference.values()),callbacks=sum(callbacks.values()),
                                matched=sum((reference&callbacks).values()),missing=sum((reference-callbacks).values()),
                                extra=sum((callbacks-reference).values())))
    return dict(status='OBSERVED_CALLBACK_DIAGNOSTIC',verified_records=sequence,head=head,last_kind=last_kind,
                callback_to_read=distribution(timing),comparison=comparisons,callback_completeness_proven=False,
                event_generation_utc_proven=False,observer_modified=False)


def run(out):
    import psutil
    base=ROOT/'outputs/us30cash_m5_native_observations'
    pointer=json.loads((base/'current.json').read_text());folder=base/pointer['capture_id']
    if folder.parent!=base or sha(folder/'manifest.json')!=pointer['manifest_sha256']:
        raise ValueError('DIAGNOSTIC_CAPTURE_MANIFEST_CHANGED')
    out.mkdir(parents=True)
    started=datetime.now(timezone.utc).isoformat()
    window=read_window(folder)
    outcomes={}
    def attempt(name, operation):
        try:outcomes[name]=operation()
        except Exception as exc:outcomes[name]=dict(status='FAILED_DIAGNOSTIC',reason=type(exc).__name__+':'+str(exc))
    attempt('live_profile',lambda:live_timing(window))
    attempt('sqlite_and_queue',lambda:sqlite_trial(out,window))
    attempt('ipc_and_polling',lambda:ipc_trial(window,out))
    attempt('mql5_observer',lambda:native_comparison(window))
    status=json.loads((base/'status.json').read_text())
    recovery=json.loads((base/'recovery/latest.json').read_text())['receipt']
    outcomes['supervisor']=dict(status=status['status'],last_transition=recovery['latest_transition'],
                                producer_pid=status['process_id'],boot_transition=recovery.get('last_boot_transition'))
    process=psutil.Process(status['process_id']);power=psutil.sensors_battery()
    report=dict(started=started,finished=datetime.now(timezone.utc).isoformat(),capture_id=pointer['capture_id'],
                chain_head=window['head'],records=window['records'],outcomes=outcomes,
                producer_rss_bytes=process.memory_info().rss,available_memory_bytes=psutil.virtual_memory().available,
                producer_cpu_times=list(process.cpu_times())[:2],ac=power.power_plugged if power else None,
                production_changed=False,training_executed=False,orders_sent=0,admission=False)
    once(out/'diagnostic.json',report)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    if not args.out.resolve().is_relative_to(ROOT/'outputs'):raise ValueError('DIAGNOSTIC_OUTPUT_NAMESPACE')
    result=run(args.out)
    print(json.dumps({name:result['outcomes'][name].get('status','MEASURED') for name in result['outcomes']}))
