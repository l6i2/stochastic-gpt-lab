"""Shared causal producer for operational drift ONLY; no policy/labels/outcomes.

Baseline and future adapters must feed the same normalized closed-bar schema,
start at the same declared warmup boundary, and bind this source's hash.
"""
from collections import deque
from datetime import datetime
import math
import statistics
from time_semantics import validate_causal_timestamp

FEATURES = ('stoch_main_k', 'spread', 'atr14_over_previous_288_bar_median',
            'relative_tick_volume_20', 'ha_body_atr')
BINS = {'stoch_main_k': [20, 40, 60, 80], 'spread': [1, 2, 5, 10],
        'atr14_over_previous_288_bar_median': [.8, 1.25],
        'relative_tick_volume_20': [.5, 1, 2], 'ha_body_atr': [.25, .5, 1]}


class DriftFeatureStream:
    """Explicit normalized input; raw broker times cannot enter the producer."""
    def __init__(self):
        self.bars = deque(maxlen=20)
        self.ranges = deque(maxlen=14)
        self.atr_history = deque(maxlen=288)
        self.numerators = deque(maxlen=3)
        self.denominators = deque(maxlen=3)
        self.previous_close = None
        self.previous_time = None
        self.ha = None

    def push(self, bar, *, quote, decision_time: datetime, bid: float, ask: float):
        if set(bar) != {'close_time', 'open', 'high', 'low', 'close', 'tick_volume'}:
            raise ValueError('EXACT_CLOSED_BAR_SCHEMA_REQUIRED')
        allowed, reason = validate_causal_timestamp(quote, feature_max_time=bar['close_time'], decision_time=decision_time)
        if not allowed:
            raise ValueError(reason)
        if self.previous_time is not None and bar['close_time'] <= self.previous_time:
            raise ValueError('DUPLICATE_OR_NONMONOTONIC_BAR')
        values = [bar[k] for k in ('open', 'high', 'low', 'close', 'tick_volume')] + [bid, ask]
        if any(type(v) not in (float, int) or not math.isfinite(v) for v in values):
            raise ValueError('INVALID_NUMERIC_FEATURE_INPUT')
        o, h, l, c, volume = values[:5]
        if not (0 < l <= min(o, c) <= max(o, c) <= h and volume >= 0 and 0 < bid <= ask):
            raise ValueError('INVALID_BAR_OR_QUOTE')
        prior_volume = statistics.mean(b['tick_volume'] for b in self.bars) if len(self.bars) == 20 else None
        self.bars.append(bar.copy())
        true_range = h-l if self.previous_close is None else max(h-l, abs(h-self.previous_close), abs(l-self.previous_close))
        self.ranges.append(true_range)
        atr = statistics.mean(self.ranges) if len(self.ranges) == 14 else None
        if len(self.bars) >= 5:
            low = min(b['low'] for b in list(self.bars)[-5:])
            high = max(b['high'] for b in list(self.bars)[-5:])
            self.numerators.append(c-low)
            self.denominators.append(high-low)
        main_k = None
        if len(self.numerators) == 3:
            denom = sum(self.denominators)
            main_k = 100*sum(self.numerators)/denom if denom else 100.0
        ha_close = (o+h+l+c)/4
        ha_open = (o+c)/2 if self.ha is None else sum(self.ha)/2
        self.ha = (ha_open, ha_close)
        reference = statistics.median(self.atr_history) if len(self.atr_history) == 288 else None
        result = dict(zip(FEATURES, (main_k, ask-bid, atr/reference if atr is not None and reference else None,
                      volume/prior_volume if prior_volume else None, abs(ha_close-ha_open)/atr if atr else None)))
        if atr is not None:
            self.atr_history.append(atr)
        self.previous_close, self.previous_time = c, bar['close_time']
        return result
