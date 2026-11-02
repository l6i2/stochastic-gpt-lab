"""Exclusive interval classification from verified new derived artifacts only."""
from collections import Counter
from .pretrain_contracts import seal


def classify_tail(records,start_n,parent_head):
    head=parent_head;expected=start_n;comparisons={};counts=Counter();intervals=[];features=[];signals=[]
    for n,previous,digest,body in records:
        if n!=expected or previous!=head or digest!=seal(dict(previous=previous,payload=body)):
            raise ValueError('DERIVED_NEW_TAIL_HASH_OR_ORDER_MISMATCH')
        if body.get('admitted') is True:raise ValueError('UNREVIEWED_SCIENTIFIC_ADMISSION')
        expected+=1;head=digest;kind=body['kind'];counts[kind]+=1
        if kind=='BAR_COMPARISON':comparisons[body['evidence_hash']]=body
        elif kind in ('CLOSED_AGGREGATE_BAR','INCOMPLETE_BUCKET'):
            bucket=body['bar'] if kind=='CLOSED_AGGREGATE_BAR' else body['observed_bucket']
            evidence=body['bar']['evidence_hash'] if kind=='CLOSED_AGGREGATE_BAR' else body['evidence_hash']
            comparison=comparisons.get(evidence)
            if comparison is None:raise ValueError('CLOSED_INTERVAL_WITHOUT_SAME_TRANSACTION_COMPARISON')
            frame=comparison['bucket']['timeframe_seconds']
            if kind=='CLOSED_AGGREGATE_BAR':
                if not comparison['parity_exact'] or comparison['bid_sequence_coverage']['status']!='PASS_EXACT_NATIVE_BID_SEQUENCE_REFERENCE' or comparison['bucket']['issues']:
                    raise ValueError('ACCEPTED_BAR_WITHOUT_EXACT_COVERAGE_REFERENCE')
                if seal(body['bar'])!=body['bar_hash']:raise ValueError('BAR_HASH_CHANGED')
                category='VALID_REFERENCE_PARITY_QUARANTINED';reasons=[]
            else:
                reasons=body['reasons'];category='PARTIAL_REJECTED' if 'FIRST_PARTIAL_BUCKET' in bucket['issues'] else 'REJECTED'
            reference=comparison.get('native_reference') or {}
            intervals.append(dict(ledger_n=n,timeframe_seconds=frame,segment=bucket['segment'],
                native_open_msc=bucket['time']*1000 if kind=='CLOSED_AGGREGATE_BAR' else bucket['open_msc'],
                category=category,reasons=reasons,evidence_hash=evidence,scientifically_certified=False,
                reference_error=reference.get('error'),aggregate_differences=comparison.get('differences',[]),
                raw_bid_count=comparison['bucket'].get('tick_volume'),
                reference_bid_count=(reference.get('bid_sequence_reference') or {}).get('bid_update_count'),
                native_bar_volume=(reference.get('bar') or {}).get('tick_volume')))
        elif kind=='UNFINISHED_BUCKET':
            intervals.append(dict(ledger_n=n,timeframe_seconds=body['timeframe_seconds'],segment=body['segment'],
                native_open_msc=body['open_msc'],category='PARTIAL_ABORTED_AT_SEGMENT_BOUNDARY',
                reasons=body.get('issues',[]),scientifically_certified=False))
        elif kind=='CAUSAL_PREFIX_FEATURES':
            if body['feature_cutoff_native_msc']>=body['decision_input_ref']['native_time_msc'] or body['ready_stage']>=body['decision_stage']:
                raise ValueError('FUTURE_OR_LATE_FEATURE_CONTEXT')
            ctx={k:v for k,v in body.items() if k not in ('kind','feature_hash','quarantine','admitted')}
            if seal(ctx)!=body['feature_hash']:raise ValueError('FEATURE_HASH_CHANGED')
            features.append(dict(ledger_n=n,feature_hash=body['feature_hash'],closed_bar_count=body['closed_bar_count'],
                full_values=body['full_feature_values_present'],scope=body['vintage'],scientific_admission=False))
        elif kind=='MAIN_K_SIGNAL':
            signals.append(dict(ledger_n=n,signal_id=body['signal_id'],side=body['side'],segment=body['segment'],
                feature_hash=body['feature_hash'],evaluable=body['evaluable']))
    summary={str(frame):dict(Counter(r['category'] for r in intervals if r['timeframe_seconds']==frame)) for frame in (60,300)}
    return dict(start_n=start_n,end_exclusive=expected,parent_head=parent_head,new_head=head,
        artifact_counts=dict(counts),intervals=intervals,classification_counts=summary,features=features,signals=signals,
        admitted_intervals=0,certified_event_utc_intervals=0)
