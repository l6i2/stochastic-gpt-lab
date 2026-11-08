"""Retrospective diagnostic archive. Never writes to a prospective store."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path

from .pretrain_contracts import canonical, seal

SERVER = 'XMGlobalSC-MT5 5'
SYMBOL = 'US30Cash'
MINUTE = 60000


def retry_ready(item, clock, source_marker):
    if item['status']=='RECOVERED_DIAGNOSTIC':return False
    old=item['clock']
    if old['boot_id']!=clock['boot_id']:return True
    if clock['uptime_ms']-old['uptime_ms']<900000:return False
    return item.get('source_marker')!=source_marker or item.get('attempts_for_source',item['attempts'])<3


def missing_intervals(events, floor):
    pending = []
    gaps = []
    for number,event in events:
        if event['kind'] in ('OBSERVATION_INTERRUPTION','NEW_OBSERVATION_EPOCH'):
            before = (event.get('previous_observation') or {}).get('native_msc')
            if before is not None:
                pending.append(dict(record=number,before=before,reason=event.get('reason'),
                                    classification=event.get('classification','UNKNOWN_INTERRUPTION')))
        if event['kind'] == 'LIVE_LATEST_STATE_POLL':
            after = event['native_quote']['time_msc']
            for item in pending[:]:
                if after <= item['before']:
                    continue
                first = max(floor,item['before']+1)
                end = after
                if first < end:
                    gaps.append(dict(start=first,end=end,incident=item['record'],
                                     reason=item['reason'],classification=item['classification']))
                pending.remove(item)
    merged=[]
    for gap in sorted(gaps,key=lambda g:g['start']):
        incident={k:gap[k] for k in ('incident','reason','classification')}
        if merged and gap['start']<=merged[-1]['end']:
            merged[-1]['end']=max(merged[-1]['end'],gap['end'])
            merged[-1]['incidents'].append(incident)
        else:
            merged.append(dict(start=gap['start'],end=gap['end'],incidents=[incident]))
    return dict(gaps=merged,pending_native_end=len(pending),
                boundary_policy='NATIVE_MILLISECONDS_STRICTLY_BETWEEN_OBSERVATIONS',
                observation_gaps_not_proof_of_market_data_loss=True)


def permitted(start, end, policy):
    if (type(start) is not int or type(end) is not int or start >= end
            or end-start > 300000):
        raise ValueError('INVALID_BOUNDED_NATIVE_INTERVAL')
    if policy['server'] != SERVER or policy['symbol'] != SYMBOL:
        raise ValueError('HISTORICAL_IDENTITY_POLICY_CHANGED')
    if start < policy['minimum_native_msc'] or end > policy['maximum_native_msc']:
        raise PermissionError('PRE_CUT_OR_UNAUTHORIZED_INTERVAL')
    if not any(g['start'] <= start < end <= g['end'] for g in policy['gaps']):
        raise PermissionError('INTERVAL_NOT_IN_OBSERVED_GAP_ALLOWLIST')
    for protected in policy.get('protected_intervals',[]):
        if start//1000*1000 < protected['end'] and ((end+999)//1000+1)*1000 > protected['start']:
            raise PermissionError('PROTECTED_INTERVAL')
    return seal(dict(start=start,end=end,policy_hash=seal(policy),origin='RETROSPECTIVE_XM_DIAGNOSTIC'))


def next_chunks(policy, completed, budget):
    selected = []
    seen = set()
    for gap in sorted(policy['gaps'],key=lambda g:g['start']):
        start = gap['start']
        while start < gap['end'] and len(selected) < budget:
            end = min((start//300000+1)*300000,gap['end'])
            key = seal(dict(start=start,end=end,server=SERVER,symbol=SYMBOL,query_version='INCLUSIVE_ENDPOINT_V2'))
            if key not in seen and key not in completed:
                selected.append(dict(key=key,start=start,end=end))
            seen.add(key)
            start = end
        if len(selected) >= budget:
            break
    return selected


def validate_rows(rows, kind, start, end):
    coordinate = 'time_msc' if kind == 'ticks' else 'time'
    scale = 1 if kind == 'ticks' else 1000
    stamps = [row[coordinate]*scale for row in rows]
    if any(not start <= stamp < end for stamp in stamps):
        raise ValueError('API_RETURNED_OUTSIDE_AUTHORIZED_RANGE')
    if any(b<a for a,b in zip(stamps,stamps[1:])):
        raise ValueError('API_ORDER_REGRESSION')
    fields=('bid','ask') if kind=='ticks' else ('open','high','low','close')
    if any(not math.isfinite(row[key]) for row in rows for key in fields):
        raise ValueError('API_NONFINITE_PRICE')
    if kind != 'ticks':
        frame = 60000 if kind == 'm1' else 300000
        if any(stamp % frame or stamp+frame>end for stamp in stamps):
            raise ValueError('INCOMPLETE_BAR_RETURNED')
        if len(set(stamps))!=len(stamps):
            raise ValueError('DUPLICATE_NATIVE_BAR')
        if any(row['low']>min(row['open'],row['close']) or row['high']<max(row['open'],row['close'])
               or row['tick_volume']<0 for row in rows):
            raise ValueError('API_INCOHERENT_OHLC_OR_VOLUME')


def fetch(api, kind, start, end):
    """Date objects carry native integer labels, without asserting a UTC mapping."""
    if kind!='ticks':
        seconds=60000 if kind=='m1' else 300000
        lower=(start+seconds-1)//seconds*seconds
        upper=end//seconds*seconds-seconds
        if lower>upper:return [],dict(status='NO_COMPLETE_BAR_IN_REQUEST')
    else:
        lower=start//1000*1000;upper=(end+999)//1000*1000
    first = datetime.fromtimestamp(lower/1000,timezone.utc)
    last = datetime.fromtimestamp(upper/1000,timezone.utc)
    if kind == 'ticks':
        array = api.copy_ticks_range(SYMBOL,first,last,api.COPY_TICKS_ALL)
    else:
        frame = api.TIMEFRAME_M1 if kind == 'm1' else api.TIMEFRAME_M5
        array = api.copy_rates_range(SYMBOL,frame,first,last)
    error = api.last_error()[0]
    if array is None or error != 1:
        raise RuntimeError('NATIVE_API_UNAVAILABLE:'+str(error))
    if array.nbytes > 16*1024*1024:
        raise RuntimeError('HISTORICAL_RESOURCE_BOUND')
    rows = [{name:item[name].item() for name in array.dtype.names} for item in array]
    # Some APIs include an exact-end tick. Preserve its count in the receipt,
    # without writing that tick into this half-open interval's payload.
    coordinate = 'time_msc' if kind == 'ticks' else 'time'
    scale = 1 if kind == 'ticks' else 1000
    exact_end = sum(row[coordinate]*scale >= end for row in rows)
    if any(row[coordinate]*scale > upper+(999 if kind=='ticks' else 0) or row[coordinate]*scale<lower for row in rows):
        raise ValueError('API_RETURNED_OUTSIDE_QUERY_ENDPOINT')
    lower_excluded=sum(row[coordinate]*scale<start for row in rows)
    rows = [row for row in rows if start<=row[coordinate]*scale < end]
    validate_rows(rows,kind,start,end)
    return rows,dict(api='copy_ticks_range' if kind=='ticks' else 'copy_rates_range',
                     code=error,excluded_upper_endpoint_rows=exact_end,
                     excluded_lower_endpoint_rows=lower_excluded,
                     query_version='INCLUSIVE_ENDPOINT_V2',
                     datetime_utc_objects_are_native_coordinate_carriers=True)


def retrieve(api, kind, start, end, fallback=None):
    try:
        rows,source = fetch(api,kind,start,end)
    except RuntimeError as exc:
        if fallback is None:
            raise
        rows,source = fallback(kind,start,end)
        validate_rows(rows,kind,start,end)
        source = dict(source,primary_failure=str(exc))
    return rows,source


def quality(ticks, minutes, bars, start, end):
    identities = Counter(canonical(row) for row in ticks)
    invalid = sum(row['bid']<=0 or row['ask']<row['bid'] for row in ticks)
    valid = len(ticks)-invalid
    comparisons = []
    for bar in bars:
        children = [m for m in minutes if bar['time']<=m['time']<bar['time']+300]
        if len(children)!=5:
            comparisons.append(dict(time=bar['time'],status='MISSING_OWN_M1'))
            continue
        computed = dict(open=children[0]['open'],high=max(m['high'] for m in children),
                        low=min(m['low'] for m in children),close=children[-1]['close'],
                        tick_volume=sum(m['tick_volume'] for m in children))
        comparisons.append(dict(time=bar['time'],status='EXACT' if all(bar[k]==v for k,v in computed.items()) else 'DIFFERENT',
                                fields=[k for k,v in computed.items() if bar[k]!=v]))
    tick_bars = []
    for minute in minutes:
        selected = [t for t in ticks if minute['time']*1000<=t['time_msc']<(minute['time']+60)*1000]
        bid = [t['bid'] for t in selected if t['bid']>0]
        fields = []
        if bid:
            values=dict(open=bid[0],high=max(bid),low=min(bid),close=bid[-1])
            fields=[k for k,v in values.items() if minute[k]!=v]
        tick_bars.append(dict(time=minute['time'],tick_rows=len(selected),
            bid_flag_rows=sum(bool(t['flags']&2) for t in selected),native_volume=minute['tick_volume'],
            ohlc='EXACT' if bid and not fields else 'DIFFERENT_OR_MISSING',different_fields=fields))
    return dict(ticks=len(ticks),m1=len(minutes),m5=len(bars),valid_bid_ask_rows=valid,
        invalid_bid_ask_rows=invalid,identical_rows_retained=sum(n-1 for n in identities.values()),
        missing_m1_opens=[stamp//1000 for stamp in range((start+59999)//60000*60000,end//60000*60000,60000)
                          if stamp//1000 not in {m['time'] for m in minutes}],
        m1_m5=comparisons,tick_m1=tick_bars,original_receipt_proven=False,
        broker_tick_completeness_certified=False,ticks_generated_or_simulated=False)


def write_payload(path, rows):
    path = Path(path)
    with path.open('xb') as stream:
        for row in rows:
            stream.write(canonical(row)+b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(folder):
    folder = Path(folder)
    manifest = json.loads((folder/'manifest.json').read_bytes())
    for name,digest in manifest['files'].items():
        if Path(name).name!=name or hashlib.sha256((folder/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('RETROSPECTIVE_PAYLOAD_CHANGED')
    return manifest


def archive_chunk(base, policy, request, reader, previous=None, recovery_clock=None, retry_failed=False):
    """Immutable attempts and an orphan-recoverable receipt after payload fsync."""
    permitted(request['start'],request['end'],policy)
    folder = Path(base)/'requests'/request['key']
    folder.mkdir(parents=True,exist_ok=True)
    attempts = sorted(folder.glob('attempt_*'))
    for attempt in reversed(attempts):
        if (attempt/'manifest.json').exists():
            saved=verify_manifest(attempt)
            if not retry_failed or not saved['failures']:
                return attempt,saved
            break
    attempt = folder/('attempt_'+str(len(attempts)+1).zfill(4))
    attempt.mkdir()
    intent = dict(request,policy=policy,previous=previous,origin='RETROSPECTIVE_XM_DIAGNOSTIC',
                  recovery_clock=recovery_clock,prospective_receipt=False,dataset_admitted=False)
    (attempt/'intent.json').write_bytes(canonical(intent)+b'\n')
    rows = {};sources = {};failures = {}
    for kind in ('m1','m5','ticks'):
        if kind=='m5' and ((request['start']+299999)//300000+1)*300000>request['end']:
            rows[kind]=[];sources[kind]=dict(status='NO_COMPLETE_M5_IN_REQUEST');continue
        try:
            rows[kind],sources[kind] = reader(kind,request['start'],request['end'])
        except (RuntimeError,ValueError) as exc:
            rows[kind]=[];failures[kind]=str(exc)
    files={kind+'.jsonl':write_payload(attempt/(kind+'.jsonl'),items) for kind,items in rows.items()}
    manifest=dict(intent,files=files,sources=sources,failures=failures,
        quality=quality(rows['ticks'],rows['m1'],rows['m5'],request['start'],request['end']),
        status='PARTIAL_API_FAILURE' if failures else 'RECOVERED_DIAGNOSTIC',
        no_transfer_to_prospective=True,source_time_domain='NATIVE_INTEGER_API_COORDINATE_NO_UTC_MAPPING_CLAIM')
    path=attempt/'manifest.json'
    with path.open('xb') as stream:
        stream.write(canonical(manifest)+b'\n');stream.flush();os.fsync(stream.fileno())
    return attempt,manifest
