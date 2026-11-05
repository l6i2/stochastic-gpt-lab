"""Evidence checks for a native-label session gap, never an XM/UTC mapping.

The caller must bind calendar/exception/source-pin hashes to preserved artifacts.
Successful LIVE records mean connection/identity were checked by that pinned
producer; no claim of complete callback receipt or physical generation is made.
"""
import calendar
from datetime import datetime, timedelta
import re
from .pretrain_contracts import seal

DAYS=('MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY','SUNDAY')
IDENTITY=dict(server='XMGlobalSC-MT5 5',symbol='US30Cash')


def parse_probe(records):
    if not records or not records[0].startswith('XM_SESSION_PROBE|START|') or records[-1]!='XM_SESSION_PROBE|END':
        raise ValueError('INCOMPLETE_NATIVE_CALENDAR_PROBE')
    start=dict(part.split('=',1) for part in records[0].split('|')[2:])
    if any(start.get(k)!=v for k,v in IDENTITY.items()):raise ValueError('CALENDAR_IDENTITY_MISMATCH')
    sessions={kind:{day:[] for day in DAYS} for kind in ('QUOTE','TRADE')}
    seen=set()
    for line in records[1:-1]:
        if line.startswith('XM_SESSION_PROBE|CLOCK|'):continue
        match=re.fullmatch(r'XM_SESSION_PROBE\|(QUOTE|TRADE)\|day=([A-Z]+)\|index=(\d+)\|from=(\d\d):(\d\d)\|to=(\d\d):(\d\d)',line)
        if not match:raise ValueError('INVALID_NATIVE_SESSION_RECORD')
        kind,day,index,fh,fm,th,tm=match.groups();index=int(index)
        if day not in DAYS or (kind,day,index) in seen:raise ValueError('DUPLICATE_OR_UNKNOWN_SESSION')
        if index!=len(sessions[kind][day]):raise ValueError('MISSING_SESSION_INDEX')
        seen.add((kind,day,index))
        if int(fh)>23 or int(th)>23 or int(fm)>59 or int(tm)>59:raise ValueError('INVALID_SESSION_HOUR')
        first=int(fh)*60+int(fm);last=int(th)*60+int(tm)
        if last==0:last=1440
        if first>=last:raise ValueError('UNSUPPORTED_OVERNIGHT_OR_ZERO_SESSION')
        if sessions[kind][day] and first<sessions[kind][day][-1][1]:raise ValueError('OVERLAPPING_NATIVE_SESSIONS')
        sessions[kind][day].append([first,last])
    if not any(sessions['QUOTE'].values()):raise ValueError('NO_NATIVE_QUOTE_SESSIONS')
    return dict(**IDENTITY,sessions=sessions,records_sha256=seal(records),
                scope='OBSERVED_WEEKLY_METADATA_NOT_HOLIDAY_OR_HISTORICAL_CERTIFICATION')


def _label(ms):
    # The epoch arithmetic is only a carrier for native wall labels.
    return datetime(1970,1,1)+timedelta(milliseconds=ms)


def quote_open(schedule, stamp):
    label=_label(stamp);minute=label.hour*60+label.minute
    return any(a<=minute<b for a,b in schedule['sessions']['QUOTE'][DAYS[label.weekday()]])


def _same_open_run(schedule, one, two):
    first,last=sorted((one//60000*60000,two//60000*60000))
    return last-first<=7*86400000 and all(quote_open(schedule,n) for n in range(first,last+60000,60000))


def _transition_review(request):
    """Fail closed on incomplete evidence; return a receipt without admission."""
    reasons=[]
    def require(condition,reason):
        if not condition:reasons.append(reason)
    before=request.get('from_native_msc');after=request.get('to_native_msc')
    require(isinstance(before,int) and isinstance(after,int) and before<after
            and before%300000==after%300000==0,'INVALID_EXACT_SESSION_GAP')
    if reasons:return dict(status='QUARANTINED',reasons=reasons,bridge_allowed=False)
    require(request.get('last_native_msc',after)<before and request.get('current_native_msc',0)>=after,
            'GAP_NOT_CURRENT_OR_REOPEN_NOT_OBSERVED')
    require(request.get('boundary_reason')=='NATIVE_MINUTE_GAP_SESSION_CAUSE_UNKNOWN','NOT_A_SESSION_GAP_BOUNDARY')
    require(before<=request.get('next_m5_open_msc',-1)<after,'CURSOR_NOT_AT_THIS_CLOSED_INTERVAL')
    calendars=request.get('calendars',[])
    require(len(calendars)==2,'BEFORE_AFTER_NATIVE_CALENDARS_REQUIRED')
    parsed=[]
    for item in calendars:
        try:
            require(seal(item['records'])==item['records_sha256'],'CALENDAR_HASH_MISMATCH')
            parsed.append(parse_probe(item['records']))
        except (KeyError,ValueError):reasons.append('INVALID_NATIVE_CALENDAR')
    if len(parsed)==2:
        require(parsed[0]['sessions']==parsed[1]['sessions'],'CALENDAR_CHANGED_AROUND_TRANSITION')
        # Bound CPU and refuse an incomplete weekly inference of a longer outage.
        require(after-before<=7*86400000,'SESSION_GAP_EXCEEDS_ONE_WEEK')
        if after-before<=7*86400000:
            require(all(not quote_open(parsed[0],n) for n in range(before,after,60000)),
                    'QUOTE_SESSION_OPEN_INSIDE_CLAIMED_CLOSURE')
            require(quote_open(parsed[0],before-60000) and quote_open(parsed[0],after),
                    'CLAIMED_INTERVAL_NOT_FULL_SCHEDULED_CLOSURE')
        require(calendars[0].get('observed_native_msc',after)<before
                and calendars[1].get('observed_native_msc',0)>=after,'CALENDAR_VINTAGE_DOES_NOT_BRACKET_GAP')
        require(_same_open_run(parsed[0],calendars[0].get('observed_native_msc',after),before-60000)
                and _same_open_run(parsed[1],after,calendars[1].get('observed_native_msc',0)),
                'CALENDAR_VINTAGE_NOT_IN_ADJACENT_QUOTE_SESSIONS')
    exception=request.get('exception_receipt') or {}
    require(exception.get('server')==IDENTITY['server'] and exception.get('symbol')==IDENTITY['symbol'],
            'EXCEPTION_IDENTITY_NOT_VERIFIED')
    require(exception.get('from_native_msc')==before and exception.get('to_native_msc')==after
            and exception.get('schedule_effect')=='NORMAL_QUOTE_CLOSURE_CONFIRMED',
            'EXACT_APPLICABLE_EXCEPTION_ATTESTATION_MISSING')
    require(exception.get('source_kind') in ('BROKER_DATED_NOTICE','NATIVE_SERVER_DATED_EXCEPTION')
            and bool(exception.get('source_url_or_artifact')) and bool(exception.get('source_sha256')),
            'BROKER_EXCEPTION_SOURCE_MISSING')
    require(bool(request.get('expected_exception_receipt_sha256'))
            and seal(exception)==request.get('expected_exception_receipt_sha256'),'EXCEPTION_HASH_MISMATCH')
    window=request.get('ledger_window') or {};rows=window.get('records',[])
    require(bool(request.get('expected_source_pin_sha256'))
            and window.get('source_pin_sha256')==request.get('expected_source_pin_sha256'),
            'MONITOR_SOURCE_PIN_NOT_BOUND')
    require(window.get('identity')==IDENTITY,'MONITOR_IDENTITY_MISMATCH')
    head=window.get('previous_hash');index=window.get('first_n');polls=[]
    for row in rows:
        try:
            body=row['payload']
            require(row['n']==index and row['previous']==head
                    and seal(dict(previous=head,payload=body))==row['digest'],'MONITOR_CHAIN_GAP_OR_CHANGED')
            head=row['digest'];index+=1
            require(body['kind'] not in ('NEW_OBSERVATION_EPOCH','OBSERVATION_INTERRUPTION'),
                    'EPOCH_OR_INTERRUPTION_INSIDE_TRANSITION')
            if body['kind']=='LIVE_LATEST_STATE_POLL':polls.append(body)
        except (KeyError,TypeError):reasons.append('MALFORMED_MONITOR_CHAIN')
    require(bool(rows) and head==window.get('expected_head') and index==window.get('last_n',-2)+1,
            'MONITOR_WINDOW_NOT_FULLY_BOUND')
    require(len(polls)>=2,'MONITOR_POLL_COVERAGE_MISSING')
    if len(polls)>=2:
        first,last=polls[0],polls[-1]
        require(first['native_quote']['time_msc']<before and last['native_quote']['time_msc']>=after,
                'MONITOR_DOES_NOT_SPAN_CLOSURE')
        previous=None
        for poll in polls:
            clock=poll['read_end'];tick=poll['native_quote']['time_msc']
            require(not before<=tick<after,'NATIVE_QUOTE_INSIDE_DECLARED_CLOSED_INTERVAL')
            require(poll.get('connected') is True,'DISCONNECTED_OR_UNVERIFIED_POLL')
            require(poll.get('sleep_record_id')==window.get('sleep_record_id')
                    and poll.get('sleep_record_id') is not None,'SLEEP_EVIDENCE_MISSING_OR_CHANGED')
            if previous:
                old=previous['read_end'];delta=clock['uptime_ms']-old['uptime_ms']
                require(clock['boot_id']==old['boot_id'] and 0<=delta<=10000
                        and old['monotonic_ns']<clock['monotonic_ns'],'MONITOR_BOOT_GAP_OR_CLOCK_DISCONTINUITY')
            previous=poll
        elapsed=last['read_end']['monotonic_ns']-first['read_end']['monotonic_ns']
        require(elapsed>=(after-before)*1000000,'INSUFFICIENT_MONOTONIC_CLOSED_INTERVAL_COVERAGE')
    reasons=sorted(set(reasons))
    return dict(status='VERIFIED_NATIVE_SESSION_TRANSITION' if not reasons else 'QUARANTINED',
                reasons=reasons,bridge_allowed=not reasons,proof_sha256=seal(request),
                from_native_msc=before,to_native_msc=after,
                missing_bars_fabricated=False,generation_utc_certified=False,dataset_admitted=False)


def transition_review(request):
    """Malformed evidence is an exclusion, never a runtime permission to bridge."""
    try:return _transition_review(request)
    except (KeyError,TypeError,ValueError,OverflowError):
        return dict(status='QUARANTINED',reasons=['MALFORMED_TRANSITION_EVIDENCE'],bridge_allowed=False,
                    missing_bars_fabricated=False,generation_utc_certified=False,dataset_admitted=False)
