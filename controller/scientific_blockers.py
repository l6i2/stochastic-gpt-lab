"""Evidence-only adjudication. Never converts native timestamps or admits data."""
from datetime import datetime
from .pretrain_contracts import seal


def receipt_sampling(row,collector_clock,boot_id):
    """Order-bound the TimeGMT call, not the UTC instant of a market event.

    Native code reads read_uptime_ms before TimeGMT, then writes/flushes. Python
    samples collector uptime after reading that complete line. Both counters
    refer to the same verified boot. Resolution error remains uncalibrated.
    """
    if str(collector_clock['boot_id'])!=str(boot_id):
        raise ValueError('RECEIPT_BOOT_MISMATCH')
    callback=row['callback_uptime_ms'];read=row['read_uptime_ms'];ingest=collector_clock['uptime_ms']
    if not callback<=read<=ingest:
        raise ValueError('RECEIPT_COUNTER_ORDER_INVALID')
    return dict(sequence=row['sequence'],callback_counter_ms=callback,
        host_label_read_counter_bracket_ms=[read,ingest],
        observation_window_width_ms=ingest-read,host_gmt_label_seconds=row['receipt_host_gmt_seconds'],
        counter_resolution_bound='UNCALIBRATED',host_label_utc_certified=False,
        broker_generation_inferred=False)


def iso_ns(value):
    if not isinstance(value,str) or not (value.endswith('Z') or value.endswith('+00:00')):
        raise ValueError('UTC_LABEL_REQUIRED')
    raw=value.removesuffix('Z').removesuffix('+00:00')
    seconds,_,fraction=raw.partition('.')
    if len(fraction)>9 or (fraction and not fraction.isdigit()):
        raise ValueError('INVALID_TIME_FRACTION')
    return int(datetime.fromisoformat(seconds+'+00:00').timestamp())*10**9+int((fraction+'0'*9)[:9])


def power_pairs(events):
    """Pair by Windows RecordId, not wall time across a clock correction."""
    pending={};pairs=[]
    for e in sorted(events,key=lambda r:r['record_id']):
        if e['provider']!='Microsoft-Windows-Kernel-Power':continue
        family={506:'MODERN_STANDBY',507:'MODERN_STANDBY',42:'SUSPEND',107:'SUSPEND'}.get(e['id'])
        if family is None:continue
        if e['id'] in (506,42):pending[family]=e
        elif family in pending:
            a=pending.pop(family)
            pairs.append(dict(kind=family,entry=a,exit=e,
                start_ns=iso_ns(a['host_utc_label']),end_ns=iso_ns(e['host_utc_label'])))
    return pairs


def adjudicate(incident,events):
    fact=incident['fact']
    if seal(fact)!=incident['incident_id']:
        raise ValueError('INCIDENT_FACT_HASH_CHANGED')
    before=fact['before'];after=fact['after']
    result=dict(incident_id=incident['incident_id'],kind=fact['kind'],source_record_hash=fact['source_record_hash'],
        classification='UNKNOWN_CAUSE',cause='ROOT_CAUSE_NOT_ESTABLISHED',observation_verified=True,
        coverage='UNKNOWN_NO_BACKFILL',missing_broker_event_count=None,admitted=False,
        before=before,after=after,evidence_record_ids=[],scope='OBSERVED_CALLBACKS_ONLY')
    if fact['kind']!='CALLBACK_TIMER_GAP' or before is None:
        # Observing disconnected/connected proves a state, not its root cause.
        return result
    same_session=before['session_id']==after['session_id']
    sequence_contiguous=after['sequence']==before['sequence']+1
    elapsed=after['callback_uptime_ms']-before['callback_uptime_ms']
    if elapsed!=fact['elapsed_ms'] or elapsed<0:
        raise ValueError('GAP_COUNTER_MISMATCH')
    result.update(elapsed_ms=elapsed,sequence_contiguous=sequence_contiguous,same_session=same_session)
    if not same_session or not sequence_contiguous:
        result['cause']='SOURCE_DISCONTINUITY_REQUIRES_SEPARATE_RECONSTRUCTION'
        return result
    lo=before['receipt_host_gmt_seconds']*10**9
    hi=(after['receipt_host_gmt_seconds']+1)*10**9
    # The one-second envelope is the recorded integer-second quantization,
    # never a clock-error tolerance or an acceptance criterion.
    barriers=[e for e in events if e['provider']=='Microsoft-Windows-Kernel-General' and e['id']==1
        and lo<=iso_ns(e['host_utc_label'])<=hi]
    overlaps=[p for p in power_pairs(events) if p['end_ns']>=p['start_ns']
        and p['end_ns']>lo and p['start_ns']<hi]
    boot=str(incident['first_detected_host_clock']['boot_id'])
    bound=[]
    for p in overlaps:
        ids=[p['entry']['fields'].get('BootId'),p['exit']['fields'].get('BootId')]
        if all(v is not None and str(v)==boot for v in ids):bound.append(p)
    contained=[p for p in bound if (lo+10**9)<=p['start_ns'] and p['end_ns']<=hi-10**9]
    result['evidence_record_ids']=sorted({e['record_id'] for e in barriers}|
        {e['record_id'] for p in overlaps for e in (p['entry'],p['exit'])})
    result['wall_clock_barriers']=[dict(record_id=e['record_id'],
        old=e['fields'].get('OldTime'),new=e['fields'].get('NewTime')) for e in barriers]
    if contained and not barriers:
        result.update(classification='VERIFIED_CAUSE',cause='OS_POWER_INTERRUPTION_CONTRIBUTOR',
            scope='POWER_EPISODE_WITHIN_GAP_NOT_EXCLUSIVE_CAUSE_OR_COMPLETE_LOSS_ACCOUNTING')
    elif bound or overlaps:
        result.update(classification='PROBABLE_CAUSE',cause='OS_POWER_CONTEXT_CLOCK_OR_BOUNDARY_LIMITS',
            scope='CORROBORATED_POWER_CONTEXT_NOT_EXACT_CALLBACK_STALL_PROOF')
    # Even a verified contributing cause does not establish gap coverage.
    result['unexplained_residual_possible']=True
    return result


def known_membership(base,diagnostic_ids,censored_ids):
    """Reconstruct only facts actually present in previously published metadata."""
    from .pretrain_contracts import verify_chain
    verify_chain(base['entries'],base['chain_head'])
    verified=[];unknown=[]
    for r in base['entries']:
        row={k:r.get(k) for k in ('dataset_id','roles','domain_id','start_native_msc',
            'end_native_exclusive_msc','source_sha256','entry_sha256')}
        exact=r.get('start_native_msc') is not None and r.get('end_native_exclusive_msc') is not None
        if exact:
            verified.append(row|dict(scope='DECLARED_NATIVE_INTERVAL_IN_VERIFIED_LEDGER_NOT_COMPLETE_SIGNAL_MEMBERSHIP'))
        else:unknown.append(row|dict(reason='UNKNOWN_BOUNDARY_OR_OPEN_ROLE_NO_SILENT_CLOSURE'))
    ids=[r['signal_id'] for r in diagnostic_ids]
    if len(ids)!=len(set(ids)) or len(censored_ids)!=len(set(censored_ids)):
        raise ValueError('DUPLICATE_PUBLISHED_MEMBERSHIP_ID')
    return dict(verified_interval_metadata=verified,unknown_intervals=unknown,
        known_diagnostic_ids=ids,known_censored_nonmember_ids=list(censored_ids),
        censored_disposition='QUARANTINE_NOT_CONFIRMED_PURGE',
        protected_intersection='UNKNOWN_WITHOUT_ORIGINAL_COMPARABLE_MEMBERSHIP',
        independent_dataset_certified=False)


def enrich_network(decision,incident,events):
    """Network-reason context can support probability, never prove XM routing."""
    f=incident['fact'];before=f['before'];after=f['after']
    result=dict(decision)
    result['network_context']=[]
    if before is None:return result
    lo=before['receipt_host_gmt_seconds']*10**9
    hi=(after['receipt_host_gmt_seconds']+1)*10**9
    for e in events:
        if 'ReasonCode' in e['fields'] and lo<=iso_ns(e['host_utc_label'])<hi:
            result['network_context'].append(dict(provider=e['provider'],record_id=e['record_id'],
                id=e['id'],host_utc_label=e['host_utc_label'],reported_reason=e['fields'],
                scope='HOST_LABEL_CONTEXT_XM_ROUTE_AND_EXACT_CAUSAL_LINK_UNVERIFIED'))
    if (result['classification']=='UNKNOWN_CAUSE' and result['network_context']
        and f['kind']=='DISCONNECTION_OBSERVED_START'):
        result.update(classification='PROBABLE_CAUSE',cause='WLAN_REPORTED_DISCONNECTION_REASON_CONTEXT',
            scope='OS_NETWORK_REASON_OBSERVED_BUT_XM_ROUTE_NOT_PROVEN')
    return result
