"""Audit bracketed clock observations without manufacturing a UTC mapping."""
from __future__ import annotations
from datetime import datetime
from temporal_causality import utc_milliseconds


def ordering_flags(frame: dict) -> list[str]:
    errors = []
    host = [frame[k] for k in ('system_read_start_ms', 'system_utc_read_ms',
                              'system_local_read_ms', 'system_read_end_ms')]
    if host != sorted(host):
        errors.append('HOST_MONOTONIC_ORDER')
    for row in frame['native']:
        values = [int(row[k]) for k in ('mono_start_ms', 'gmt_before_mono_ms', 'local_mono_ms',
            'gmt_mono_ms', 'current_mono_ms', 'server_mono_ms', 'tick_mono_ms', 'mono_end_ms')]
        if values != sorted(values):
            errors.append('NATIVE_MONOTONIC_ORDER')
        if values[-1] > host[0]:
            errors.append('SIDECAR_BEFORE_NATIVE_FLUSH')
        if int(row['tick_time_msc']) // 1000 != int(row['tick_time']):
            errors.append('SECONDS_MILLISECONDS_MISMATCH')
    return errors


def audit_capture(capture: dict) -> dict:
    frames = capture['frames']
    complete = (len(frames) == 50 and {f['frame'] for f in frames} == set(range(50))
                and all(len(f['native']) == 3 and {r['symbol'] for r in f['native']}
                    == {'US30Cash', 'EURUSD', 'USDCHF'} for f in frames))
    errors = [error for f in frames for error in ordering_flags(f)]
    if any(a['system_read_end_ms'] > b['system_read_start_ms'] for a, b in zip(frames, frames[1:])):
        errors.append('FRAME_MONOTONIC_REGRESSION')
    if any(r['tester'] != '0' or r['connected'] != '1' or r['tick_ok'] != '1'
           for f in frames for r in f['native']):
        errors.append('NATIVE_ENVIRONMENT_INVALID')
    references = [capture['reference_before'], capture['reference_after']]
    reference_ok = all(r['comparison'].get('status') == 'REFERENCE_QUORUM'
                       and r.get('tls_corroborated') is True for r in references)
    host_ok = reference_ok and all(r['comparison'].get('local_clock_within_network_interval') is True for r in references)
    deltas = []
    for a, b in zip(frames, frames[1:]):
        host_delta = utc_milliseconds(datetime.fromisoformat(b['system_utc'])) - utc_milliseconds(datetime.fromisoformat(a['system_utc']))
        mono_delta = b['system_utc_read_ms'] - a['system_utc_read_ms']
        deltas.append({'from_frame': a['frame'], 'to_frame': b['frame'],
                       'wall_delta_ms': host_delta, 'monotonic_delta_ms': mono_delta,
                       'wall_minus_monotonic_delta_ms': host_delta - mono_delta})
        if host_delta < 0:
            errors.append('HOST_UTC_REGRESSION')
    # Quantized GetTickCount64 cannot certify sub-tick drift. Do not hide any
    # disagreement behind an invented tolerance or upgrade it to a PASS.
    drift_reconciled = all(d['wall_minus_monotonic_delta_ms'] == 0 for d in deltas)
    symbols = {}
    for symbol in ('US30Cash', 'EURUSD', 'USDCHF'):
        rows = [r for f in frames for r in f['native'] if r['symbol'] == symbol]
        symbols[symbol] = {'rows': len(rows), 'distinct_tick_times': len({r['tick_time_msc'] for r in rows}),
            'server_minus_host_gmt_seconds': sorted({int(r['time_trade_server']) - int(r['time_gmt']) for r in rows}),
            'current_minus_estimated_server_seconds': sorted({int(r['time_current']) - int(r['time_trade_server']) for r in rows}),
            'raw_tick_minus_host_gmt_ms': [int(r['tick_time_msc']) - int(r['time_gmt']) * 1000 for r in rows]}
    return {'complete_frames': len(frames) if complete else 0,
            'capture_integrity': 'PASS' if complete and not errors else 'FAIL', 'errors': errors,
            'independent_reference_quorum': 'PASS' if reference_ok else 'FAIL',
            'clock_attestation': 'PASS' if complete and not errors and host_ok and drift_reconciled else 'FAIL',
            'native_to_utc_mapping': 'FAIL', 'authorized_segments': [],
            'mapping_reason': 'Last-tick age and broker offset are confounded; no independent certified native/UTC correspondence. No offset is authorized.',
            'symbols': symbols, 'wall_monotonic_deltas': deltas,
            'pairing_delays_ms': [f['pairing_delay_ms'] for f in frames],
            'clock_drift': 'MEASURED_DELTAS_ONLY; no unproven tolerance or long-term stability claim',
            'wall_monotonic_drift_reconciled': drift_reconciled,
            'startup_dependence': 'UNKNOWN_NO_RESTART', 'session_transition_dependence': 'UNKNOWN_NOT_OBSERVED',
            'dst_transition_dependence': 'UNKNOWN_NOT_OBSERVED', 'market_executable_state': 'UNKNOWN',
            'causal_audit': 'FAIL', 'temporal_causality': 'FAIL_UNATTESTED_OPERATIONAL_RELATIONSHIPS',
            'orders_sent': 0, 'raw_timestamps_changed': False, 'future_tolerance_ms': 0}


if __name__ == '__main__':
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Preserve prior audit evidence')
    result = audit_capture(json.loads(args.capture.read_text(encoding='utf-8')))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('complete_frames', 'capture_integrity', 'clock_attestation', 'native_to_utc_mapping')}))
