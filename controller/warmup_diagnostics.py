"""Read-only reconstruction of the frozen producer's M5 run; no market queries."""
import json,sqlite3
from pathlib import Path
from .pretrain_contracts import seal

def inspect(path):
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=5)
    try:
        db.execute('BEGIN')
        body,digest=db.execute('SELECT body,digest FROM checkpoint WHERE id=1').fetchone()
        state=json.loads(body)
        if seal(state)!=digest:raise ValueError('CHECKPOINT_HASH_CHANGED')
        last_n,last_digest,last_body=db.execute('SELECT n,digest,body FROM artifacts ORDER BY n DESC LIMIT 1').fetchone()
        if json.loads(last_body).get('state_hash')!=digest:raise ValueError('CHECKPOINT_NOT_BOUND')
        frames={};run=maximum=completed=rejected=0;last_rejection=None;reasons={}
        sql="SELECT n,previous,digest,body FROM artifacts WHERE json_extract(body,'$.kind') IN ('SEGMENT','BAR_COMPARISON','CLOSED_AGGREGATE_BAR','INCOMPLETE_BUCKET') ORDER BY n"
        for n,parent,entry_hash,body in db.execute(sql):
            event=json.loads(body)
            if seal(dict(previous=parent,payload=event))!=entry_hash:raise ValueError('WARMUP_EVIDENCE_HASH_CHANGED')
            kind=event['kind']
            if kind=='SEGMENT':run=0
            elif kind=='BAR_COMPARISON':frames[event['evidence_hash']]=event['bucket']['timeframe_seconds']
            elif kind=='CLOSED_AGGREGATE_BAR' and frames.get(event['bar']['evidence_hash'])==300:
                if seal(event['bar'])!=event['bar_hash']:raise ValueError('BAR_HASH_CHANGED')
                completed+=1;run+=1;maximum=max(maximum,run)
            elif kind=='INCOMPLETE_BUCKET' and event['observed_bucket']['timeframe_seconds']==300:
                rejected+=1;run=0
                last_rejection=dict(ledger_n=n,ledger_digest=entry_hash,native_open_msc=event['observed_bucket']['open_msc'],reasons=event['reasons'])
                for reason in event['reasons']:reasons[reason]=reasons.get(reason,0)+1
        if run!=state['own_run_bars'] or completed!=state['own_bars']:raise ValueError('PERSISTED_WARMUP_COUNTER_MISMATCH')
        return dict(source='FROZEN_ORIGINAL_CALLBACK_PRODUCER_ONLY',current_run=run,maximum_observed_run=maximum,
            completed_m5=completed,rejected_m5=rejected,last_rejection=last_rejection,rejection_reasons=reasons,
            checkpoint_digest=digest,ledger_last_n=last_n,ledger_head=last_digest,scientifically_admitted=0,
            scientific_warmup=0,own_run_counter_verified=True,snapshot_bars_adopted=0,historical_bars_adopted=0)
    finally:db.close()
