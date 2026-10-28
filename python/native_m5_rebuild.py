"""Deterministic bid OHLC in the native domain; never fills an empty bucket.

Output is a derived diagnostic, not an accepted research dataset. An acquisition
window alone cannot prove completeness, UTC mapping or a market-closed gap.
"""
from decimal import Decimal
import math


def price_units(value, tick_size):
    value, step = Decimal(str(value)), Decimal(str(tick_size))
    if not value.is_finite() or not step.is_finite() or value <= 0 or step <= 0:
        raise ValueError('INVALID_PRICE_OR_GRID')
    units = value / step
    if units != units.to_integral_value():
        raise ValueError('PRICE_OFF_NATIVE_GRID')
    return int(units)


def rebuild(ticks, *, start_msc, end_msc, tick_size):
    if type(start_msc) is not int or type(end_msc) is not int or start_msc >= end_msc:
        raise ValueError('INVALID_ACQUISITION_WINDOW')
    previous = start_msc
    bucket = None
    output = []
    excluded_boundary_ticks = 0
    count = 0
    for row in ticks:
        ms, seconds = int(row['time_msc']), int(row['time'])
        if seconds != ms // 1000 or not start_msc <= ms < end_msc or ms < previous:
            raise ValueError('INVALID_NATIVE_TIME_OR_ORDER')
        previous = ms
        bid, ask = price_units(row['bid'], tick_size), price_units(row['ask'], tick_size)
        if ask < bid:
            raise ValueError('CROSSED_QUOTE')
        if 'flags' not in row:
            raise ValueError('NATIVE_TICK_FLAGS_REQUIRED')
        opening = ms // 300000 * 300000
        count += 1
        if opening < start_msc or opening + 300000 > end_msc:
            excluded_boundary_ticks += 1
            continue
        # US30Cash BID charts count BID updates, not ASK-only quote events.
        # The raw archive retains every row. This derived series is explicit
        # about the native BID flag (MetaTrader TICK_FLAG_BID == 2).
        if not int(row['flags']) & 2:
            continue
        if bucket is None or bucket['time'] != opening // 1000:
            if bucket:
                output.append(bucket)
            bucket = dict(time=opening // 1000, open=bid, high=bid, low=bid, close=bid,
                          tick_volume=1, first_native_msc=ms, last_native_msc=ms)
        else:
            bucket['high'] = max(bucket['high'], bid)
            bucket['low'] = min(bucket['low'], bid)
            bucket['close'] = bid
            bucket['tick_volume'] += 1
            bucket['last_native_msc'] = ms
    if bucket:
        output.append(bucket)
    return dict(bars=output, tick_size=str(tick_size), price_encoding='INTEGER_NATIVE_TICK_UNITS',
                ticks_read=count, excluded_boundary_ticks=excluded_boundary_ticks,
                empty_buckets_filled=0, native_to_utc_mapping='UNVERIFIED',
                volume_basis='COUNT_TICK_FLAG_BID_UPDATES', scientific_acceptance=False,
                train_access_allowed=False, evaluation_authorized=False)


def compare(derived, native, tick_size):
    originals = {}
    for row in native:
        time = int(row['time'])
        if time in originals or time % 300:
            raise ValueError('DUPLICATE_OR_UNALIGNED_NATIVE_BAR')
        originals[time] = row
    differences = []
    matched = 0
    missing_native = []
    for row in derived:
        other = originals.pop(row['time'], None)
        if other is None:
            missing_native.append(row['time'])
            continue
        matched += 1
        changed = [key for key in ('open', 'high', 'low', 'close') if row[key] != price_units(other[key], tick_size)]
        if row['tick_volume'] != int(other['tick_volume']):
            changed.append('tick_volume')
        if changed:
            differences.append(dict(time=row['time'], fields=changed))
    full_match = matched > 0 and not differences and not missing_native and not originals
    return dict(status='PASS_EXACT_NATIVE_OHLC_AND_TICK_VOLUME' if full_match else 'FAIL_OR_INCOMPLETE',
                compared_bars=matched, differences=differences, missing_native=missing_native,
                missing_derived=sorted(originals), tolerance=0,
                scope='NATIVE_BAR_RECONSTRUCTION_ONLY_NOT_UTC_OR_CAUSAL_ACCEPTANCE')
