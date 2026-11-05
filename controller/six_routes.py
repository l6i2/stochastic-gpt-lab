"""Pure M1 aggregation for diagnostics. Missing minutes remain explicit."""
import math


def aggregate_m1(rows):
    buckets = []
    current = None
    previous = None
    for row in rows:
        stamp = int(row['time'])
        if stamp % 60 or previous is not None and stamp <= previous:
            raise ValueError('M1_ORDER_OR_DUPLICATE')
        values = {name: float(row[name]) for name in ('open','high','low','close')}
        if (not all(math.isfinite(v) for v in values.values()) or values['low'] > min(values.values())
                or values['high'] < max(values.values()) or int(row['tick_volume']) < 0):
            raise ValueError('INVALID_M1_VALUES')
        opening = stamp // 300 * 300
        if current is None or current['time'] != opening:
            current = dict(time=opening, **values, tick_volume=0, observed_minutes=[])
            buckets.append(current)
        current['high'] = max(current['high'], values['high'])
        current['low'] = min(current['low'], values['low'])
        current['close'] = values['close']
        current['tick_volume'] += int(row['tick_volume'])
        current['observed_minutes'].append(stamp)
        previous = stamp
    for bucket in buckets:
        bucket['complete_five_minutes'] = bucket['observed_minutes'] == list(range(bucket['time'],bucket['time']+300,60))
    return buckets
