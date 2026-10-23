"""Fail-closed audit of Windows/native observation overlap, not clock repair."""
from __future__ import annotations


def audit_overlap(capture: dict, *, end_marker_present: bool) -> dict:
    pairs = capture['paired_frames']
    errors = []
    if len(pairs) != 50 or {p['frame'] for p in pairs} != set(range(50)):
        errors.append('INCOMPLETE_OR_DUPLICATE_FRAMES')
    for previous, current in zip(pairs, pairs[1:]):
        if (current['frame'] <= previous['frame']
                or current['native_start_ms'] < previous['native_end_ms']
                or current['windows_after']['qpc_end_ns'] < previous['windows_after']['qpc_end_ns']):
            errors.append('FRAME_MONOTONIC_ORDER')
    for pair in pairs:
        rows = pair['native']
        if (len(rows) != 3 or {r['symbol'] for r in rows} != {'US30Cash', 'EURUSD', 'USDCHF'}
                or any(int(r['frame']) != pair['frame'] for r in rows)):
            errors.append('NATIVE_FRAME_MEMBERSHIP')
        before, after = pair['windows_before'], pair['windows_after']
        if (before['start_tick_ms'] > before['end_tick_ms']
                or before['end_tick_ms'] > pair['native_start_ms']
                or pair['native_start_ms'] > pair['native_end_ms']
                or pair['native_end_ms'] > after['start_tick_ms']
                or after['start_tick_ms'] > after['end_tick_ms']
                or before['qpc_start_ns'] > before['qpc_end_ns']
                or before['qpc_end_ns'] > after['qpc_start_ns']
                or after['qpc_start_ns'] > after['qpc_end_ns']):
            errors.append('WINDOWS_NATIVE_BRACKET_INVALID')
        for row in rows:
            if row['tester'] != '0' or row['connected'] != '1' or row['tick_ok'] != '1':
                errors.append('INVALID_NATIVE_ENVIRONMENT')
            if int(row['tick_time_msc']) // 1000 != int(row['tick_time']):
                errors.append('SECONDS_MILLISECONDS_MISMATCH')
    if not end_marker_present:
        errors.append('NATIVE_END_MARKER_MISSING')
    reference_ok = any(r['reference']['comparison'].get('status') == 'REFERENCE_QUORUM'
                       and r['reference'].get('tls_corroborated') is True for r in capture['references'])
    precise_checks = []
    # Use outer QPC brackets of each reference acquisition; never silently equate
    # GetTickCount, perf_counter and another clock's numeric origins.
    for pair in pairs:
        windows = pair['windows_after']
        intervals = []
        for sample in capture['references']:
            ref = sample['reference']
            comparison = ref['comparison']
            if comparison.get('status') != 'REFERENCE_QUORUM' or not ref.get('tls_corroborated'):
                continue
            low = comparison['utc_lower_ns'] + windows['qpc_start_ns'] - sample['qpc_end_ns']
            high = comparison['utc_upper_ns'] + windows['qpc_end_ns'] - sample['qpc_start_ns']
            intervals.append((low, high))
        precise_checks.append(bool(intervals) and all(low <= windows['precise_utc_ns'] <= high for low, high in intervals))
    source_status_ok = all(capture[phase][name].get('returncode') == 0
                          for phase in ('w32_before', 'w32_after') for name in ('source', 'status', 'offset'))
    windows_ok = (reference_ok and source_status_ok and bool(precise_checks) and all(precise_checks))
    offsets = sorted({int(r['time_trade_server']) - int(r['time_gmt']) for p in pairs for r in p['native']})
    return {'clock_probe': 'PASS' if end_marker_present and len(pairs) == 50 else 'FAIL',
            'simultaneous_overlap': 'PASS' if not errors else 'FAIL', 'errors': errors,
            'paired_frames': len(pairs), 'native_rows': sum(len(p['native']) for p in pairs),
            'windows_clock_sync': 'PASS' if windows_ok else 'FAIL',
            'independent_reference_available': reference_ok,
            'precise_windows_inside_reference_intervals': all(precise_checks) if precise_checks else False,
            'w32_source_status_offset_available': source_status_ok,
            'observed_estimated_server_minus_host_gmt_seconds': offsets,
            'broker_server_offset': 'OBSERVED_ONLY_NOT_CERTIFIED', 'broker_dst': 'PARTIAL',
            'authoritative_clock': 'NONE_OPERATIONALLY_ATTESTED', 'native_to_utc_mapping': 'FAIL',
            'temporal_causality': 'FAIL', 'causal_audit': 'FAIL', 'authorized_mapping_segments': [],
            'future_quote_policy': 'REJECT', 'future_tolerance_ms': 0, 'clock_changed': False, 'orders_sent': 0}
