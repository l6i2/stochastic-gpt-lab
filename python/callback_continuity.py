"""Callback-domain intervals and incidents, never inferred market closures or UTC."""
import hashlib
import json
from pathlib import Path

TIMER_PERIOD_MS=5000  # Observer EventSetTimer(5), not a scientific tolerance.


def analyze(path):
    last=None;first=None;heartbeat=None;between=0;gaps=[];largest_row_gap=0
    last_native=None;native_delta=None;deltas=[];rows=0;last_tick_observation=None
    with Path(path).open('rb') as stream:
        for line in stream:
            if not line.endswith(b'\n'):break
            envelope=json.loads(line);row=envelope['payload'];rows+=1
            if first is None:first=row
            if last:
                largest_row_gap=max(largest_row_gap,row['callback_uptime_ms']-last['callback_uptime_ms'])
            if row['kind']=='ONTICK_LATEST_QUOTE':
                # Coordinate difference only. It is neither an offset nor latency.
                native_delta=row['time_msc']-row['receipt_host_gmt_seconds']*1000
                deltas.append(native_delta)
                if len(deltas)>2:deltas=[min(deltas),max(deltas)]
                last_native=row['time_msc']
                last_tick_observation={k:row[k] for k in ('sequence','time','time_msc','callback_uptime_ms','receipt_host_gmt_seconds')}
                if heartbeat:between+=1
            if row['kind']=='HEARTBEAT':
                if heartbeat:
                    elapsed=row['callback_uptime_ms']-heartbeat['callback_uptime_ms']
                    if elapsed>=2*TIMER_PERIOD_MS:
                        key=f"{row['session_id']}:{heartbeat['sequence']}:{row['sequence']}"
                        gaps.append(dict(incident_id=hashlib.sha256(key.encode()).hexdigest(),
                            session_id=row['session_id'],before_sequence=heartbeat['sequence'],after_sequence=row['sequence'],
                            start_uptime_ms=heartbeat['callback_uptime_ms'],end_uptime_ms=row['callback_uptime_ms'],
                            elapsed_ms=elapsed,nominal_timer_period_ms=TIMER_PERIOD_MS,
                            before_host_gmt_seconds=heartbeat['receipt_host_gmt_seconds'],
                            after_host_gmt_seconds=row['receipt_host_gmt_seconds'],
                            between_tick_callbacks=between,connected_at_endpoints=[heartbeat['connected'],row['connected']],
                            program_counter_elapsed_us=row['callback_program_us']-heartbeat['callback_program_us'],
                            cause='UNDETERMINED',real_event_loss='UNVERIFIED',
                            detection_scope='TWO_NOMINAL_TIMER_PERIODS_ELAPSED_NOT_EVENT_LOSS_THRESHOLD'))
                heartbeat=row;between=0
            last=row
    if first is None:return dict(rows=0,incidents=[],segments=[])
    start,end=first['callback_uptime_ms'],last['callback_uptime_ms']
    boundaries=sorted({start,end}|{g[k] for g in gaps for k in ('start_uptime_ms','end_uptime_ms')})
    segments=[]
    for a,b in zip(boundaries,boundaries[1:]):
        if a==b:continue
        overlapping=[g['incident_id'] for g in gaps if g['start_uptime_ms']<b and a<g['end_uptime_ms']]
        segments.append(dict(session_id=first['session_id'],start_callback_uptime_ms=a,end_callback_uptime_ms=b,
            interval='[start,end)',basis='SESSION_SCOPED_UPTIME_NOT_UTC',status='QUARANTINED',
            incident_ids=overlapping,reason='CALLBACK_GAP_AND_TEMPORAL_PROVENANCE' if overlapping else 'TEMPORAL_PROVENANCE_UNVERIFIED'))
    return dict(rows=rows,session_id=first['session_id'],incidents=gaps,segments=segments,
        terminal_endpoint=dict(sequence=last['sequence'],uptime_ms=end,included_in_next_interval=False),
        largest_adjacent_record_gap_ms=largest_row_gap,native_minus_host_label_ms_envelope=[min(deltas),max(deltas)] if deltas else None,
        last_tick_observation=last_tick_observation,
        coordinate_difference_scope='NOT_MAPPING_NOT_EVENT_LATENCY',certified_segments=[],scientific_acceptance=False)


def receipt_projection(reference, uptime_ms):
    bracket=reference.get('anchor_kernel_uptime_ms_interval')
    comparison=reference.get('comparison',{})
    if not bracket or comparison.get('status')!='REFERENCE_QUORUM':return None
    return dict(utc_model_lower_ns=comparison['utc_lower_ns']+(uptime_ms-bracket[1])*1000000,
        utc_model_upper_ns=comparison['utc_upper_ns']+(uptime_ms-bracket[0])*1000000,
        model='SHARED_KERNEL_UPTIME_ZERO_DRIFT_DIAGNOSTIC_ONLY',
        unbounded_components=['UPTIME_QUANTIZATION','OSCILLATOR_DRIFT','SERVER_ABSOLUTE_CLOCK_ERROR','CALLBACK_QUEUE_DELAY'],
        authenticated=False,certified=False,event_time_inferred=False)
