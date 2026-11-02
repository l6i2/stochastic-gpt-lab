"""Inactive proposal validator, not a producer or a dataset-admission authority.

No MT5, filesystem or network access. Input rows are terminal-database snapshots,
never callback payloads. Stable snapshots demonstrate repeatability only.
"""
import hashlib,json,math


def digest(rows):
    return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def review(first,second,*,max_rows=20000):
    """Review a closed half-open range without inventing reception provenance."""
    reasons=[]
    for record in (first,second):
        if record['origin']!='TERMINAL_DATABASE_QUERY':raise ValueError('ORIGIN_MISREPRESENTED')
        if len(record['rows'])>max_rows:raise ValueError('RESOURCE_CAP_EXCEEDED_NOT_TRUNCATED')
        if record['query_end_ns']<record['query_start_ns']:raise ValueError('MONOTONIC_QUERY_REGRESSION')
        if record['start_msc']>=record['end_msc']:raise ValueError('INVALID_HALF_OPEN_RANGE')
        if record['error'] or not record['connected']:reasons.append('QUERY_ERROR_OR_DISCONNECTION')
        if record['rows'] and record['rows'][-1]['time_msc']>=record['end_msc']:raise ValueError('END_BOUNDARY_NOT_FILTERED')
        previous=None
        for row in record['rows']:
            ms=row['time_msc']
            if type(ms) is not int or not record['start_msc']<=ms<record['end_msc']:raise ValueError('OUTSIDE_INTERVAL')
            if previous is not None and ms<previous:raise ValueError('UNSORTED_NO_REORDERING')
            if row['time']!=ms//1000:raise ValueError('TIME_UNITS_MISMATCH')
            if not all(math.isfinite(row[k]) for k in ('bid','ask')) or not 0<row['bid']<=row['ask']:raise ValueError('INVALID_QUOTE')
            previous=ms
        if not record['rows']:reasons.append('EMPTY_NOT_PROOF_OF_MARKET_CLOSURE')
    if first['boot_id']!=second['boot_id']:reasons.append('REBOOT_NEW_SEGMENT_REQUIRED')
    if first['session_id']!=second['session_id']:reasons.append('RESTART_NEW_SEGMENT_REQUIRED')
    if (first['start_msc'],first['end_msc'])!=(second['start_msc'],second['end_msc']):raise ValueError('DIFFERENT_RANGES')
    if second['query_start_ns']<first['query_end_ns']:raise ValueError('OVERLAPPING_QUERY_OBSERVATIONS')
    a=digest(first['rows']);b=digest(second['rows'])
    if a!=b:reasons.append('DATABASE_REVISION_OR_PARTIAL_READ')
    return dict(status='REPEATABLE_DATABASE_SNAPSHOT_ONLY' if not reasons else 'QUARANTINED',
        reasons=sorted(set(reasons)),first_rows=len(first['rows']),second_rows=len(second['rows']),
        first_sha256=a,second_sha256=b,multiplicity_preserved=True,
        callback_receipt_proven=False,event_generation_utc_proven=False,
        eligible_for_frozen_callback_warmup=False,dataset_admitted=False,
        producer_activation_allowed=False,first_observation_interval_ns=[first['query_start_ns'],first['query_end_ns']])
