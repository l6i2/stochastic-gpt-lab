"""Measured secants and conditional affine feasibility, never event certification."""
from fractions import Fraction
from nts_xm_correlation import valid_measurement


def ratio(value):
    return dict(numerator=value.numerator,denominator=value.denominator)


def fraction(value):
    return Fraction(value['numerator'],value['denominator'])


def point(measurement,basis):
    m=measurement
    if basis=='QPC':
        clock=m.get('receive_clock_observation',{});freq=clock.get('qpc_frequency_hz',0)
        if freq<=0:return None
        a,b=clock['qpc_ticks_interval']
        if a<0 or b<a:return None
        # Outward integer conversion of raw QPC ticks; no selected tolerance.
        lo=a*1000000000//freq;hi=-(-b*1000000000//freq)
    else:
        a,b=m['receive_kernel_uptime_ms_interval'];lo=a*1000000;hi=b*1000000
    return dict(capture_id=m['capture_id'],x_ns=[lo,hi],utc_ns=m['utc_receive_interval_model_ns'],
        frequency_hz=freq if basis=='QPC' else None,
        offset_ns=m['offset_server_minus_host_ns'],host_ns=m['host_receive_ns'],
        uptime_ms=m['receive_kernel_uptime_ms_interval'])


def secant(a,b):
    dx_lo=b['x_ns'][0]-a['x_ns'][1];dx_hi=b['x_ns'][1]-a['x_ns'][0]
    if dx_lo<=0:return None
    dt_lo=b['utc_ns'][0]-a['utc_ns'][1];dt_hi=b['utc_ns'][1]-a['utc_ns'][0]
    low=Fraction(max(0,dt_lo),dx_hi);high=Fraction(dt_hi,dx_lo)
    # Average change of NTS-minus-Windows offset, not oscillator-only drift.
    delta=[b['offset_ns'][0]-a['offset_ns'][1],b['offset_ns'][1]-a['offset_ns'][0]]
    slopes=[Fraction(d,x)*1000000 for d in delta for x in (dx_lo,dx_hi)]
    return dict(captures=[a['capture_id'],b['capture_id']],elapsed_counter_ns=[dx_lo,dx_hi],
        utc_per_counter_rate=[ratio(low),ratio(high)],
        utc_minus_counter_secant_ppm=[float((low-1)*1000000),float((high-1)*1000000)],
        nts_minus_windows_offset_change_ppm=[float(min(slopes)),float(max(slopes))],
        scope='AVERAGE_SECANT_CONDITIONAL_ON_NTS_ERROR_MODEL_NOT_INSTANTANEOUS_DRIFT')


def calibrate(records):
    """Input must be chain-verified and in chain order, not host wall-clock order."""
    groups=[];active={};last_record=None;epoch=0;barriers=[]
    for record in records:
        p=record['payload'];boot=p.get('boot_identity');reasons=[]
        if boot is None:reasons.append('BOOT_ID_MISSING')
        if last_record:
            old=last_record
            if old.get('boot_identity')!=boot:reasons.append('BOOT_CHANGED')
            old_event=old.get('clock_change_event_record_id');new_event=p.get('clock_change_event_record_id')
            if old_event is not None and new_event is not None and old_event!=new_event:reasons.append('OS_CLOCK_EVENT_CURSOR_CHANGED')
            start=p.get('run_started_kernel_uptime_ms');prior=old.get('run_started_kernel_uptime_ms')
            if start is not None and prior is not None and start<prior:reasons.append('UPTIME_REGRESSION')
            due=p.get('prior_due_kernel_uptime_ms')
            # One full configured monitor polling period missed. Operational
            # segmentation criterion, not an allowed clock-error tolerance.
            if start is not None and due is not None and start>due+60000:reasons.append('MISSED_NTS_MONITOR_PERIOD')
        valid=[r['measurement'] for r in p['results'] if r.get('status')=='AUTHENTICATED_MEASUREMENT' and valid_measurement(r.get('measurement',{}))]
        if not valid:reasons.append('NO_VALID_AUTHENTICATED_MEASUREMENT')
        if reasons:
            active={};epoch+=1;barriers.append(dict(record_id=p['record_id'],reasons=reasons))
        for result in p['results']:
            if result.get('status')!='AUTHENTICATED_MEASUREMENT' or not valid_measurement(result.get('measurement',{})):
                origin=result.get('origin',result.get('measurement',{}).get('origin'))
                for key in list(active):
                    if key[0]==origin:active.pop(key)
                barriers.append(dict(record_id=p['record_id'],origin=origin,reasons=['AUTHENTICATED_SOURCE_UNAVAILABLE_OR_INVALID']))
        for m in valid:
            for basis in ('KERNEL_UPTIME','QPC'):
                q=point(m,basis)
                if q is None or boot is None:continue
                day=m['server_transmit_utc_ns']//86400000000000
                key=(m['origin'],basis)
                old=active.get(key)
                if old and old['analysis_utc_day']!=day:
                    # Daily report batches, not discontinuity or acceptance
                    # tolerance. Original points and older batches retained.
                    active.pop(key);old=None
                if old and q['frequency_hz']!=old['points'][-1]['frequency_hz']:
                    barriers.append(dict(record_id=p['record_id'],reasons=['QPC_FREQUENCY_CHANGED']));active.pop(key);old=None
                if old and (q['x_ns'][0]<=old['points'][-1]['x_ns'][1] or q['host_ns']<old['points'][-1]['host_ns']):
                    barriers.append(dict(record_id=p['record_id'],reasons=['COUNTER_OR_HOST_REGRESSION']));active.pop(key);old=None
                if old is None:
                    old=dict(group_id=f'{epoch}:{len(groups)}',boot_identity=boot,origin=m['origin'],basis=basis,analysis_utc_day=day,points=[],
                        scientific_acceptance=False,certified=False,unbounded=['SERVER_ABSOLUTE_ERROR_BEYOND_ADVERTISED_MODEL','INSTANTANEOUS_OSCILLATOR_VARIATION'],
                        counter_quantization='UNBOUNDED_LEGACY_GTC_RESOLUTION' if basis=='KERNEL_UPTIME' else 'RAW_QPC_READ_BRACKET_OUTWARD_ROUNDED')
                    groups.append(old);active[key]=old
                old['points'].append(q)
        last_record=p
    for g in groups:
        points=g['points'];pairs=[secant(a,b) for a,b in zip(points,points[1:])];g['adjacent_secants']=[v for v in pairs if v]
        g['baseline_secant']=secant(points[0],points[-1]) if len(points)>1 else None
        low=high=None
        for i,a in enumerate(points):
            for b in points[i+1:]:
                v=secant(a,b)
                if not v:continue
                x,y=map(fraction,v['utc_per_counter_rate'])
                low=x if low is None else max(low,x);high=y if high is None else min(high,y)
        if low is not None:
            feasible=low<=high and high>0
            g['affine_status']='FEASIBLE_CONDITIONAL_MODEL' if feasible else 'REJECTED_CONSTANT_RATE_MODEL'
            g['affine_rate_interval']=[ratio(low),ratio(high)] if feasible else None
        else:g.update(affine_status='INSUFFICIENT_POINTS',affine_rate_interval=None)
    return dict(groups=groups,barriers=barriers,certified_segments=[],
        status='PARTIAL_OBSERVATIONAL_CALIBRATION',extrapolation_allowed=False,
        frequency_decision='KEEP_300_SECONDS_NO_JUSTIFIED_PRECISION_GAIN_FROM_FASTER_SAMPLING',
        generation_time_certified=False,scientific_acceptance=False)


def project_group(group,uptime_ms):
    """Bound only an explicitly constant-rate conditional model, never reality."""
    if group['basis']!='KERNEL_UPTIME' or not group['affine_rate_interval']:return None
    points=group['points'];x=uptime_ms*1000000
    if not points[0]['x_ns'][1]<=x<=points[-1]['x_ns'][0]:return None
    rates=list(map(fraction,group['affine_rate_interval']));bounds=[]
    for p in points:
        products=[r*d for r in rates for d in (x-p['x_ns'][1],x-p['x_ns'][0])]
        bounds.append([p['utc_ns'][0]+min(products).__floor__(),p['utc_ns'][1]+max(products).__ceil__()])
    lo=max(v[0] for v in bounds);hi=min(v[1] for v in bounds)
    if lo>hi:return None
    return dict(group_id=group['group_id'],conditional_receipt_ns=[lo,hi],
        scope='CONSTANT_RATE_CONDITIONAL_MODEL_UNCALIBRATED_GTC_QUANTIZATION',certified=False,event_time_inferred=False)
