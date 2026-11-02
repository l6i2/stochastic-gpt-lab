"""Separate authorized database-observation trial. No callback or admission claim."""
import json,sqlite3,hashlib
from .pretrain_contracts import seal,canonical
from .isolated_observation import GENESIS
from .native_sequence_coverage import summarize_reference
from python.native_m5_rebuild import price_units


def new_state():
    return dict(source_records=0,epoch=None,epochs=0,last_poll=None,last_tick=None,
        next_open={},accepted={'60':0,'300':0},rejected={'60':0,'300':0},
        consecutive_m5=0,max_consecutive_m5=0,scientific_warmup=0,last_verified={})


class Store:
    def __init__(self,path):
        self.db=sqlite3.connect(path,timeout=5);self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('CREATE TABLE IF NOT EXISTS records(n INTEGER PRIMARY KEY,previous TEXT NOT NULL,digest TEXT UNIQUE NOT NULL,body TEXT NOT NULL); CREATE TABLE IF NOT EXISTS state(id INTEGER PRIMARY KEY CHECK(id=1),body TEXT NOT NULL,digest TEXT NOT NULL); CREATE TRIGGER IF NOT EXISTS no_update BEFORE UPDATE ON records BEGIN SELECT RAISE(ABORT,"APPEND_ONLY"); END; CREATE TRIGGER IF NOT EXISTS no_delete BEFORE DELETE ON records BEGIN SELECT RAISE(ABORT,"APPEND_ONLY"); END;')
        self.head=GENESIS;self.count=0
        try:
            for n,p,d,b in self.db.execute('SELECT * FROM records ORDER BY n'):
                if n!=self.count or p!=self.head or seal(dict(previous=p,payload=json.loads(b)))!=d:raise ValueError('SNAPSHOT_CHAIN_CHANGED')
                self.count+=1;self.head=d
            row=self.db.execute('SELECT body,digest FROM state WHERE id=1').fetchone();self.state=json.loads(row[0]) if row else new_state()
            if row:
                last=json.loads(self.db.execute('SELECT body FROM records ORDER BY n DESC LIMIT 1').fetchone()[0])
                if seal(self.state)!=row[1] or last.get('kind')!='CHECKPOINT' or last['state_hash']!=row[1]:raise ValueError('SNAPSHOT_STATE_CHANGED')
            elif self.count:raise ValueError('MISSING_SNAPSHOT_STATE')
        except BaseException:self.db.close();raise

    def commit(self,events):
        events=events+[dict(kind='CHECKPOINT',state_hash=seal(self.state),quarantine=True,admitted=False)]
        head=self.head;n=self.count
        with self.db:
            for event in events:
                event=dict(event,quarantine=True,admitted=False);digest=seal(dict(previous=head,payload=event))
                self.db.execute('INSERT INTO records VALUES(?,?,?,?)',(n,head,digest,canonical(event).decode()));head=digest;n+=1
            self.db.execute('INSERT OR REPLACE INTO state VALUES(1,?,?)',(canonical(self.state).decode(),seal(self.state)))
        self.head=head;self.count=n

    def close(self):self.db.close()


def start_epoch(state,tick,clock,reason):
    previous=state['epoch'];state['epochs']+=1
    state.update(epoch=str(state['epochs'])+'_'+str(clock['uptime_ms']),last_poll=clock,last_tick=tick['time_msc'],
        next_open={str(s):(tick['time_msc']//(s*1000)+1)*s*1000 for s in (60,300)},consecutive_m5=0,last_verified={})
    return dict(kind='NEW_OBSERVATION_EPOCH',previous_epoch=previous,epoch=state['epoch'],reason=reason,
        activation_clock=clock,native_cut_tick=tick,first_complete_open=state['next_open'].copy(),
        skipped_prior_content=True,backfill=False,event_utc_certified=False)


def boundary_reason(state,tick,clock,*,terminal_changed=False):
    if not state['epoch']:return 'INITIAL_OR_RECOVERY_FRESH_CUT'
    if terminal_changed:return 'TERMINAL_PID_CHANGED'
    old=state['last_poll']
    if old and clock['boot_id']!=old['boot_id']:return 'WINDOWS_BOOT_CHANGED'
    if old and clock['monotonic_ns']<old['monotonic_ns']:return 'MONOTONIC_REGRESSION'
    if old and clock['uptime_ms']-old['uptime_ms']>10000:return 'POLL_GAP_TWO_EXISTING_5S_TIMERS'
    if old and clock['host_utc_label']<old['host_utc_label']:return 'HOST_WALL_CLOCK_REGRESSION'
    if state['last_tick'] is not None:
        if tick['time_msc']<state['last_tick']:return 'NATIVE_CLOCK_REGRESSION'
        if tick['time_msc']//60000>state['last_tick']//60000+1:return 'NATIVE_MINUTE_GAP_SESSION_CAUSE_UNKNOWN'
    return None


def assess(first,second,bar,start,end,step,query_error=None):
    """Exact view parity, not proof of live receipt or final database immutability."""
    reasons=[]
    for rows in (first,second):summarize_reference(rows,start,end,step)
    a=seal(first);b=seal(second)
    if query_error:reasons.append('QUERY_ERROR_OR_PARTIAL_READ')
    if a!=b:reasons.append('DATABASE_CHANGED_BETWEEN_READS')
    bid=[r for r in first if r['flags']&2]
    if not bid or bar is None:reasons.append('EMPTY_OR_NATIVE_BAR_MISSING_NOT_CALENDAR_PROOF')
    else:
        prices=[price_units(r['bid'],step) for r in bid]
        for k,v in dict(open=prices[0],high=max(prices),low=min(prices),close=prices[-1]).items():
            if price_units(bar[k],step)!=v:reasons.append('NATIVE_'+k.upper()+'_MISMATCH')
        if len(bid)!=bar['tick_volume']:reasons.append('NATIVE_VOLUME_MISMATCH')
        if bar['time']*1000!=start:reasons.append('NATIVE_BAR_TIME_MISMATCH')
    return dict(status='VERIFIED_DATABASE_VIEW_ONLY' if not reasons else 'REJECTED_QUARANTINED',reasons=reasons,
        first_sha256=a,second_sha256=b,rows=len(first),bid_updates=len(bid),
        sequence=summarize_reference(first,start,end,step),callback_receipt_proven=False,
        event_generation_utc_proven=False,scientific_warmup_eligible=False)


def apply_result(state,frame,start,result):
    key=str(frame);accepted=result['status']=='VERIFIED_DATABASE_VIEW_ONLY'
    state['accepted' if accepted else 'rejected'][key]+=1
    if frame==300:
        if accepted:
            previous=state['last_verified'].get(key)
            state['consecutive_m5']=state['consecutive_m5']+1 if previous is not None and start==previous+300000 else 1
            state['max_consecutive_m5']=max(state['max_consecutive_m5'],state['consecutive_m5'])
        else:state['consecutive_m5']=0
    if accepted:state['last_verified'][key]=start
    else:state['last_verified'].pop(key,None)
    state['next_open'][key]=start+frame*1000
