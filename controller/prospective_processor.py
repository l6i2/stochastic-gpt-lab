"""Incremental native-domain diagnostics. No orders, labels, fit or admission API."""
from collections import deque
from datetime import datetime
import hashlib,json,math,sqlite3
from pathlib import Path
from .pretrain_contracts import canonical,seal
from .isolated_observation import GENESIS
from .native_sequence_coverage import append_quote,compare_bucket


def initial_state():
    return dict(cursors={},segment=None,buckets={},history=[],ha=None,atr=None,previous_k=None,
        own_run_bars=0,own_bars=0,m1_bars=0,rejected_buckets=0,signals_buy=0,signals_sell=0,
        after_warmup_signals=0,first_800_hash=GENESIS,post_signal_bars=0,acquisition_boundary=None,
        incident_count=0,source_records=0,last_callback=None,last_receipt=None,last_tick=None,
        protocol_stream_unbroken=True,evaluable_buy=0,evaluable_sell=0)


class Ledger:
    """One writer; cursor, bounded state and append-only artifacts commit together."""
    def __init__(self,path):
        self.db=sqlite3.connect(path,timeout=5)
        self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('CREATE TABLE IF NOT EXISTS artifacts(n INTEGER PRIMARY KEY, previous TEXT NOT NULL, digest TEXT UNIQUE NOT NULL, body TEXT NOT NULL); CREATE TABLE IF NOT EXISTS checkpoint(id INTEGER PRIMARY KEY CHECK(id=1),body TEXT NOT NULL,digest TEXT NOT NULL); CREATE TRIGGER IF NOT EXISTS no_artifact_update BEFORE UPDATE ON artifacts BEGIN SELECT RAISE(ABORT,"APPEND_ONLY"); END; CREATE TRIGGER IF NOT EXISTS no_artifact_delete BEFORE DELETE ON artifacts BEGIN SELECT RAISE(ABORT,"APPEND_ONLY"); END;')
        try:self._load()
        except BaseException:self.db.close();raise

    def _load(self):
        self.head=GENESIS;self.count=0
        for n,previous,digest,body in self.db.execute('SELECT n,previous,digest,body FROM artifacts ORDER BY n'):
            if n!=self.count or previous!=self.head or seal(dict(previous=previous,payload=json.loads(body)))!=digest:raise ValueError('DERIVED_CHAIN_CHANGED')
            self.head=digest;self.count+=1
        row=self.db.execute('SELECT body,digest FROM checkpoint WHERE id=1').fetchone()
        self.state=json.loads(row[0]) if row else initial_state()
        if row and (seal(self.state)!=row[1] or not self.count):raise ValueError('DERIVED_CHECKPOINT_CHANGED')
        if self.count:
            last=json.loads(self.db.execute('SELECT body FROM artifacts ORDER BY n DESC LIMIT 1').fetchone()[0])
            if not row or last.get('kind')!='CHECKPOINT' or last['state_hash']!=row[1]:raise ValueError('DERIVED_CHECKPOINT_LEDGER_MISMATCH')
        self.pending=[]

    def emit(self,kind,payload):
        self.pending.append(dict(kind=kind,**payload,quarantine=True,admitted=False))

    def commit(self):
        digest=seal(self.state);records=self.pending+[dict(kind='CHECKPOINT',state_hash=digest,source_records=self.state['source_records'],quarantine=True)]
        head=self.head;count=self.count
        with self.db:
            for body in records:
                next_head=seal(dict(previous=head,payload=body))
                self.db.execute('INSERT INTO artifacts VALUES(?,?,?,?)',(count,head,next_head,canonical(body).decode()))
                head=next_head;count+=1
            self.db.execute('INSERT OR REPLACE INTO checkpoint VALUES(1,?,?)',(canonical(self.state).decode(),digest))
        self.head=head;self.count=count;self.pending=[]

    def close(self):self.db.close()


class Processor:
    def __init__(self,state,emit,oracle,tick_size,requirements,clock=None):
        self.s=state;self.emit=emit;self.oracle=oracle;self.step=str(tick_size);self.req=requirements
        from .isolated_observation import host_clock
        self.clock=clock or host_clock
        from python.native_m5_rebuild import price_units
        self.units=lambda price:price_units(price,self.step)

    def incident(self,reason,ref):
        self.s['incident_count']+=1;self.s['protocol_stream_unbroken']=False
        for bucket in self.s['buckets'].values():bucket['issues']=sorted(set(bucket['issues']+[reason]))
        self.emit('INCIDENT',dict(reason=reason,source=ref))

    def reset_context(self):
        self.s.update(history=[],ha=None,atr=None,previous_k=None,own_run_bars=0)

    def segment(self,segment,manifest_hash):
        if self.s['segment']!=segment:
            if self.s['segment'] is not None:
                self.incident('SEGMENT_OR_BOOT_BOUNDARY',dict(segment=segment))
                for b in self.s['buckets'].values():self.emit('UNFINISHED_BUCKET',b)
            self.s.update(segment=segment,buckets={},last_callback=None,last_receipt=None,last_tick=None)
            self.reset_context();self.emit('SEGMENT',dict(segment=segment,raw_manifest_hash=manifest_hash))

    def event(self,row,ref,receipt):
        self.s['source_records']+=1;now=row['callback_uptime_ms'];prior=self.s['last_callback']
        if prior is not None:
            delta=now-prior
            if delta<0:raise ValueError('SOURCE_MONOTONIC_REGRESSION')
            if delta>10000:self.incident('CALLBACK_GAP_TWO_EXISTING_TIMERS',dict(**ref,elapsed_ms=delta))
        old=self.s['last_receipt']
        if old:
            if receipt['boot_id']!=old['boot_id'] or receipt['monotonic_ns']<old['monotonic_ns']:raise ValueError('RECEIPT_CLOCK_DISCONTINUITY')
            if datetime.fromisoformat(receipt['host_utc_label'])<datetime.fromisoformat(old['host_utc_label']):self.incident('WINDOWS_WALL_CLOCK_BACKWARD',ref)
        self.s['last_callback']=now;self.s['last_receipt']=receipt
        if not row['connected']:self.incident('DISCONNECTED',ref)
        if row['kind']=='QUOTE_READ_FAILED':self.incident('QUOTE_READ_FAILED',ref)
        if row['kind']!='ONTICK_LATEST_QUOTE':return
        if row['time_msc']//1000!=row['time'] or not all(math.isfinite(row[k]) for k in ('bid','ask')) or not 0<row['bid']<=row['ask']:raise ValueError('INVALID_NATIVE_QUOTE')
        last=self.s['last_tick'];stamp=row['time_msc']
        key=[stamp,row['bid'],row['ask'],row['flags']]
        if last:
            if stamp<last[0]:self.incident('NATIVE_TIME_REGRESSION_NO_SORT',ref);return
            if key==last:self.incident('INDISTINGUISHABLE_QUOTE_CALLBACKS',ref)
        self.s['last_tick']=key
        if not row['flags']&2:return  # frozen BID-volume basis, raw remains intact
        price=self.units(row['bid']);self.units(row['ask'])
        for seconds in (60,300):
            name=str(seconds);opening=stamp//(seconds*1000)*seconds*1000
            bucket=self.s['buckets'].get(name)
            if bucket and opening!=bucket['open_msc']:
                if opening<bucket['open_msc']:self.incident('BAR_ORDER_REGRESSION',ref);continue
                consecutive=opening==bucket['open_msc']+seconds*1000
                if not consecutive:bucket['issues']=sorted(set(bucket['issues']+['UNKNOWN_NATIVE_SESSION_GAP']))
                self.close_bucket(bucket,row,ref,receipt)
                bucket=None
                first=False
            else:first=bucket is None
            if bucket is None:
                bucket=dict(timeframe_seconds=seconds,open_msc=opening,open=price,high=price,low=price,close=price,tick_volume=0,bid_sequence_sha256=GENESIS,first_ref=ref,last_ref=ref,segment=self.s['segment'],tick_size=self.step,issues=['FIRST_PARTIAL_BUCKET'] if first else [])
                self.s['buckets'][name]=bucket
            bucket['high']=max(bucket['high'],price);bucket['low']=min(bucket['low'],price);bucket['close']=price;bucket['tick_volume']+=1;bucket['last_ref']=ref
            if 'bid_sequence_sha256' in bucket:bucket['bid_sequence_sha256']=append_quote(bucket['bid_sequence_sha256'],row,self.step)
            if not row['connected']:bucket['issues']=sorted(set(bucket['issues']+['DISCONNECTED']))

    def close_bucket(self,bucket,tick,ref,receipt):
        seconds=bucket['timeframe_seconds'];native=None if 'FIRST_PARTIAL_BUCKET' in bucket['issues'] else self.oracle(bucket['open_msc']//1000,seconds)
        parity=False;differences=[]
        if native and native.get('bar'):
            bar=native['bar']
            differences=[k for k in ('open','high','low','close') if self.units(bar[k])!=bucket[k]]
            if int(bar['time'])*1000!=bucket['open_msc']:differences.append('time')
            if int(bar['tick_volume'])!=bucket['tick_volume']:differences.append('tick_volume')
            parity=not differences
        sequence_proof=compare_bucket(bucket,native.get('bid_sequence_reference') if native else None)
        sequence_ok=sequence_proof['status']=='PASS_EXACT_NATIVE_BID_SEQUENCE_REFERENCE'
        evidence=dict(bucket=bucket,native_reference=native,parity_exact=parity,differences=differences,bid_sequence_coverage=sequence_proof,closure_ref=ref,native_closure_msc=tick['time_msc'],source_receipt=receipt,compute_clock=self.clock(),coverage_scope='EXACT_NATIVE_BID_SEQUENCE_AND_AGGREGATE_REFERENCE_NOT_INDEPENDENT_GENERATION_UTC')
        evidence_hash=seal(evidence);self.emit('BAR_COMPARISON',dict(evidence_hash=evidence_hash,**evidence))
        if not parity or not sequence_ok or bucket['issues']:
            self.s['rejected_buckets']+=1
            if seconds==300 and bucket['issues']!=['FIRST_PARTIAL_BUCKET']:self.s['protocol_stream_unbroken']=False
            self.emit('INCOMPLETE_BUCKET',dict(observed_bucket=bucket,evidence_hash=evidence_hash,reasons=bucket['issues']+([] if parity else ['NATIVE_PARITY_MISSING_OR_FAILED'])+sequence_proof['reasons']))
            if seconds==300:self.reset_context()
            return
        if (bucket['open_msc']//1000+seconds)*1000-1>=tick['time_msc']:raise ValueError('BAR_NOT_CLOSED_AT_DECISION_INPUT')
        step=float(self.step)
        bar=dict(time=bucket['open_msc']//1000,**{k:bucket[k]*step for k in ('open','high','low','close')},tick_volume=bucket['tick_volume'],segment=bucket['segment'],evidence_hash=evidence_hash)
        bar_hash=seal(bar);self.emit('CLOSED_AGGREGATE_BAR',dict(bar=bar,bar_hash=bar_hash,closure_ref=ref,quality='EXACT_NATIVE_AGGREGATE_AND_BID_SEQUENCE_REFERENCE',scientific_coverage_certified=False))
        if seconds==60:self.s['m1_bars']+=1;return
        self.s['own_bars']+=1;self.s['own_run_bars']+=1
        if self.s['protocol_stream_unbroken'] and self.s['after_warmup_signals']>=self.req['signals'] and self.s['post_signal_bars']<self.req['post_bars']:
            self.s['post_signal_bars']+=1
            if self.s['post_signal_bars']==self.req['post_bars'] and self.s['acquisition_boundary'] is None:
                self.s['acquisition_boundary']=dict(bar_hash=bar_hash,source_ref=ref,admission=False)
                self.emit('DIAGNOSTIC_STOP_BOUNDARY',self.s['acquisition_boundary'])
        self.features(bar,bar_hash,ref,receipt)

    def features(self,bar,bar_hash,ref,receipt):
        if (bar['time']+300)*1000-1>=ref['native_time_msc']:raise ValueError('FEATURE_FUTURE_AT_DECISION')
        from python.native_metadata_v3 import main_k
        history=self.s['history'];previous=history[-1] if history else None
        history.append(dict(bar,bar_hash=bar_hash));self.s['history']=history[-351:]
        n=self.s['own_run_bars'];ha=self.s['ha']
        hc=(bar['open']+bar['high']+bar['low']+bar['close'])/4
        ho=(bar['open']+bar['close'])/2 if ha is None else (ha['open']+ha['close'])/2
        self.s['ha']=dict(open=ho,close=hc,seed_bar_hash=ha['seed_bar_hash'] if ha else bar_hash,count=n)
        atr=self.s['atr'] or dict(tr=[],value=None,seed_bar_hash=bar_hash,count=0)
        if previous:
            tr=max(bar['high'],previous['close'])-min(bar['low'],previous['close'])
            old=atr['tr'][0] if len(atr['tr'])==14 else None;atr['tr']=(atr['tr']+[tr])[-14:]
            if atr['value'] is None and len(atr['tr'])==14:atr['value']=sum(atr['tr'])/14
            elif atr['value'] is not None:atr['value']=atr['value']+(tr-old)/14
        atr['count']+=1;self.s['atr']=atr
        k=list(main_k(history[-7:]))[-1];previous_k=self.s['previous_k'];self.s['previous_k']=k
        volumes=[b['tick_volume'] for b in history[-21:-1]] if len(history)>=21 else []
        volume_mean=sum(volumes)/20 if volumes else None
        values=dict(stoch_k=k,delta_k_1=k-previous_k if k is not None and previous_k is not None else None,ATR=atr['value'],relative_volume_20=bar['tick_volume']/volume_mean if volume_mean else None,ha_direction=(1 if hc>ho else -1 if hc<ho else 0) if n>=276 else None,range_to_ATR=(bar['high']-bar['low'])/atr['value'] if atr['value'] else None)
        context=dict(values=values,bar_hash=bar_hash,feature_cutoff_native_msc=(bar['time']+300)*1000-1,
            decision_input_ref=ref,ready_stage=1,decision_stage=2,source_receipt=receipt,compute_clock=self.clock(),
            dependency_oldest_bar_hash=self.s['ha']['seed_bar_hash'],closed_bar_count=n,
            dependency_chain_hash=seal(dict(previous=self.s.get('dependency_hash',GENESIS),bar_hash=bar_hash)),
            ATR_scope='OWN_HISTORY_METAQUOTES_EXAMPLE_RECURRENCE_NATIVE_IATR_PARITY_PENDING',HA_scope='FROZEN_HA_OPEN_CLOSE_RECURRENCE_READY_276_OWN_SEED',vintage='DERIVED_FROM_RECORDED_PREFIX_NOT_NATIVE_CALLBACK_FEATURE_EXPORT',
            full_feature_values_present=all(v is not None and math.isfinite(v) for v in values.values()),scientific_causality_certified=False)
        self.s['dependency_hash']=context['dependency_chain_hash'];feature_hash=seal(context)
        self.emit('CAUSAL_PREFIX_FEATURES',dict(feature_hash=feature_hash,**context))
        side='BUY' if previous_k is not None and k is not None and previous_k<=20 and k>20 else 'SELL' if previous_k is not None and k is not None and previous_k>=80 and k<80 else None
        if side:
            self.s['signals_buy' if side=='BUY' else 'signals_sell']+=1
            signal=dict(side=side,previous_k=previous_k,main_k=k,bar_hash=bar_hash,feature_hash=feature_hash,
                signal_cutoff_native_msc=context['feature_cutoff_native_msc'],entry_observation_ref=ref,segment=bar['segment'],closed_bar_count=n,warmup_diagnostic_ready=n>=self.req['warmup'],evaluable=False,reason='COVERAGE_MEMBERSHIP_NATIVE_INDICATOR_VINTAGE_AND_AUTHORIZATION_PENDING')
            signal_id=seal(signal);self.emit('MAIN_K_SIGNAL',dict(signal_id=signal_id,**signal))
            if self.s['protocol_stream_unbroken'] and n>=self.req['warmup'] and self.s['after_warmup_signals']<self.req['signals']:
                self.s['after_warmup_signals']+=1;self.s['first_800_hash']=seal(dict(previous=self.s['first_800_hash'],signal_id=signal_id))

    def maturity(self):
        return dict(raw_records_processed=self.s['source_records'],m1_aggregate_bars=self.s['m1_bars'],m5_aggregate_bars=self.s['own_bars'],warmup_current_own_run=self.s['own_run_bars'],warmup_required=self.req['warmup'],warmup_scientifically_verified=0,
            diagnostic_buy_signals=self.s['signals_buy'],diagnostic_sell_signals=self.s['signals_sell'],diagnostic_first_signals_progress=self.s['after_warmup_signals'],signals_required=self.req['signals'],diagnostic_post_signal_bars=self.s['post_signal_bars'],post_signal_bars_required=self.req['post_bars'],
            evaluable_total=0,evaluable_buy=0,evaluable_sell=0,evaluable_required=self.req['evaluable'],evaluable_required_each_side=self.req['each_side'],rejected_buckets=self.s['rejected_buckets'],incident_count=self.s['incident_count'],protocol_stream_unbroken=self.s['protocol_stream_unbroken'],
            membership='RAW_AND_DERIVED_LINEAGE_TRACKED_LEGACY_NONOVERLAP_PENDING',exposure='APPEND_ONLY_ARTIFACT_LEDGER_NO_LABELS',causal_audit='FAIL_GLOBAL_UNCHANGED',dataset_maturity='NOT_READY_QUARANTINED',training_readiness='BLOCKED',admitted_records=0,dataset_hash=None,live_trading=False)
