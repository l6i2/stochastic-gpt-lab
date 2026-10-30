"""Conditional receipt correlation. No path here authorizes event UTC or datasets."""
import json
from pathlib import Path

AUTH = 'TLS_CHAIN_HOSTNAME_ALPN_EXPORTER_AEAD_UID_ORIGIN_VERIFIED'


def valid_measurement(m):
    try:
        a, b = m['receive_kernel_uptime_ms_interval']
        lo, hi = m['utc_receive_interval_model_ns']
        x, y = m['offset_server_minus_host_ns']
        return (m['authentication'] == AUTH and m['protocol'] == 'RFC8915_NTS_AEAD15_TLS13'
                and 0 <= a <= b and lo <= hi and x <= y
                and m['host_receive_ns'] + x == lo and m['host_receive_ns'] + y == hi
                and m['rtt_monotonic_ns'] >= 0 and m['server_advertised_error_ns'] >= 0
                and m['server_transmit_utc_ns'] >= m['server_receive_utc_ns'])
    except (KeyError, TypeError, ValueError):
        return False


def project(m, uptime):
    """Zero-drift diagnostic, never a certified or extrapolated validity interval."""
    a, b = m['receive_kernel_uptime_ms_interval']
    lo, hi = m['utc_receive_interval_model_ns']
    return [lo + (uptime-b)*1000000, hi + (uptime-a)*1000000]


def correlate(rows, records):
    rows = list(rows)
    if not rows:
        return []
    session = rows[0]['session_id']
    heartbeat_gaps = []
    prior_heartbeat = None
    for row in rows:
        if row['kind'] == 'HEARTBEAT':
            if prior_heartbeat is not None and row['callback_uptime_ms']-prior_heartbeat >= 10000:
                heartbeat_gaps.append((prior_heartbeat, row['callback_uptime_ms']))
            prior_heartbeat = row['callback_uptime_ms']
    anchors = []
    for record in records:
        # Only records already verified against the append-only station chain.
        payload = record['payload']
        linked = any(link.get('native_tick', {}).get('sequence') is not None
                     and name in payload.get('native_receipt_correlations', {})
                     for name, link in payload.get('native_receipt_correlations', {}).items()
                     if name.endswith(session+'.jsonl'))
        if not linked:
            continue
        for r in payload['results']:
            if r.get('status') == 'AUTHENTICATED_MEASUREMENT' and valid_measurement(r.get('measurement', {})):
                m = r['measurement']
                anchors.append((m['receive_kernel_uptime_ms_interval'][0], m, payload.get('boot_identity')))
    anchors.sort(key=lambda v: v[0])
    result = []
    previous = None
    heartbeat = None
    last_native = None
    for row in rows:
        u = row['callback_uptime_ms']
        reasons = []
        if not row['connected']:
            reasons.append('XM_DISCONNECTED')
        if previous and (u < previous['callback_uptime_ms'] or row['session_id'] != previous['session_id']):
            reasons.append('RESTART_OR_UPTIME_REGRESSION')
        if previous:
            # TimeGMT is whole seconds. A difference outside this quantization
            # envelope is a discontinuity observation, not an oscillator bound.
            residual = (row['receipt_host_gmt_seconds']-previous['receipt_host_gmt_seconds'])*1000-(u-previous['callback_uptime_ms'])
            if abs(residual) >= 1000:
                reasons.append('HOST_CLOCK_OR_COUNTER_DISCONTINUITY')
        if (heartbeat and u-heartbeat['callback_uptime_ms'] >= 10000) or any(a < u <= b for a,b in heartbeat_gaps):
            reasons.append('HEARTBEAT_GAP_TWO_TIMER_PERIODS')
        if row['kind'] == 'HEARTBEAT':
            heartbeat = row
        if row['kind'] != 'ONTICK_LATEST_QUOTE':
            previous = row
            continue
        if last_native is not None and row['time_msc'] < last_native:
            reasons.append('NATIVE_TIMESTAMP_OUT_OF_ORDER')
        last_native = row['time_msc']
        left = [a for a in anchors if a[0] <= u]
        right = [a for a in anchors if a[1]['receive_kernel_uptime_ms_interval'][1] >= u]
        pair = [left[-1], right[0]] if left and right else []
        models = []
        if not pair:
            reasons.append('NO_AUTHENTICATED_BRACKETING_MEASUREMENTS')
        else:
            if pair[0][1]['capture_id'] == pair[1][1]['capture_id']:
                reasons.append('NOT_TWO_DISTINCT_NTS_MEASUREMENTS')
            boots = {a[2] for a in pair}
            if None in boots or len(boots) != 1:
                reasons.append('KERNEL_EPOCH_UNVERIFIED_OR_CHANGED')
            for record in records:
                p = record['payload']
                start = p.get('run_started_kernel_uptime_ms')
                if start is not None and pair[0][0] <= start <= pair[1][0] and not any(
                        r.get('status') == 'AUTHENTICATED_MEASUREMENT' and valid_measurement(r.get('measurement', {}))
                        for r in p['results']):
                    reasons.append('NTS_UNAVAILABLE_WITHIN_BRACKET')
                    break
            for _, m, _ in pair:
                bounds = project(m, u)
                models.append(dict(capture_id=m['capture_id'], conditional_receipt_ns=bounds,
                    native_minus_receipt_coordinate_ns=[row['time_msc']*1000000-bounds[1], row['time_msc']*1000000-bounds[0]],
                    observed_offset_server_minus_host_ns=m['offset_server_minus_host_ns'],
                    network_rtt_ns=m['rtt_monotonic_ns'], conditional_width_ns=bounds[1]-bounds[0]))
        result.append(dict(session_id=session, sequence=row['sequence'], callback_uptime_ms=u,
            status='QUARANTINED' if reasons else 'PARTIAL', reasons=reasons,
            conditional_models=models, certified_receipt_bounds_ns=None,
            generation_latency_ns=None, callback_read_elapsed_ms=row['read_uptime_ms']-u,
            event_utc_certified=False, scientific_acceptance=False,
            missing=['OSCILLATOR_AND_COUNTER_ERROR_BOUND', 'INDEPENDENT_GENERATION_EVENT_BINDING',
                     'BROKER_GENERATION_TO_CALLBACK_DELAY_BOUND'],
            scope='OBSERVATIONAL_BRACKETING_NOT_CONTINUOUS_NTS_VALIDITY'))
        previous = row
    return result


def read_rows(path, max_bytes=None):
    consumed = 0
    with Path(path).open('rb') as stream:
        for line in stream:
            consumed += len(line)
            if max_bytes is not None and consumed > max_bytes:
                break
            if not line.endswith(b'\n'):
                break
            yield json.loads(line)['payload']
