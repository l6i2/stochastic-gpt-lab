"""Compare native BID sequences, never turn reference re-queries into raw inputs."""
from .pretrain_contracts import seal
from .isolated_observation import GENESIS
from python.native_m5_rebuild import price_units

SCHEMA='native-bid-sequence/1'


def append_quote(previous,row,step):
    ms=int(row['time_msc'])
    if int(row['time'])!=ms//1000:raise ValueError('NATIVE_TIME_UNITS_MISMATCH')
    bid=price_units(row['bid'],step);ask=price_units(row['ask'],step)
    if ask<bid:raise ValueError('CROSSED_NATIVE_QUOTE')
    return seal(dict(previous=previous,quote=dict(time_msc=ms,bid_units=bid,ask_units=ask,flags=int(row['flags']))))


def summarize_reference(rows,start_msc,end_msc,step):
    if start_msc>=end_msc:raise ValueError('INVALID_REFERENCE_INTERVAL')
    count=0;head=GENESIS;last=None;first=None;total=0
    for row in rows:
        ms=int(row['time_msc']);total+=1
        if not start_msc<=ms<end_msc:raise ValueError('REFERENCE_TICK_OUTSIDE_REQUEST')
        if last is not None and ms<last:raise ValueError('REFERENCE_TICKS_OUT_OF_ORDER')
        if int(row['time'])!=ms//1000:raise ValueError('REFERENCE_TIME_UNITS_MISMATCH')
        last=ms
        if not int(row['flags'])&2:continue
        head=append_quote(head,row,step);count+=1
        if first is None:first=ms
    return dict(schema=SCHEMA,start_native_msc=start_msc,end_native_exclusive_msc=end_msc,
        bid_update_count=count,all_reference_ticks=total,bid_sequence_sha256=head,first_bid_native_msc=first,
        last_reference_native_msc=last,origin='COPY_TICKS_RANGE_REFERENCE_REQUERY_ONLY',
        independently_certified_event_generation=False,reference_rows_adopted_as_prospective=0)


def compare_bucket(bucket,reference):
    seconds=bucket['timeframe_seconds'];start=bucket['open_msc'];proof=reference or {};reasons=[]
    if proof.get('schema')!=SCHEMA:reasons.append('BID_SEQUENCE_REFERENCE_MISSING')
    if proof.get('start_native_msc')!=start or proof.get('end_native_exclusive_msc')!=start+seconds*1000:reasons.append('BID_SEQUENCE_REFERENCE_INTERVAL_MISMATCH')
    if proof.get('bid_update_count')!=bucket['tick_volume']:reasons.append('BID_SEQUENCE_COUNT_MISMATCH')
    if not bucket.get('bid_sequence_sha256') or proof.get('bid_sequence_sha256')!=bucket.get('bid_sequence_sha256'):reasons.append('BID_SEQUENCE_HASH_MISMATCH')
    return dict(status='PASS_EXACT_NATIVE_BID_SEQUENCE_REFERENCE' if not reasons else 'UNVERIFIED_OR_MISMATCH',reasons=reasons,independent_utc_certification=False,scientific_admission=False)
