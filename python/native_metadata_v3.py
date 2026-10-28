"""Versioned native MAIN_K metadata adapter; frozen legacy contracts untouched.

No timestamp normalization, maturity counts, features, labels, or scoring.
The output is invalid until seven complete closed bars are available.
"""
from collections import deque
import math


def main_k(rows):
    window = deque(maxlen=5)
    slowing = deque(maxlen=3)
    for row in rows:
        bar = {k: float(row[k]) for k in ('open', 'high', 'low', 'close')}
        if (not all(math.isfinite(v) and v > 0 for v in bar.values()) or
                not bar['low'] <= min(bar['open'], bar['close']) <= max(bar['open'], bar['close']) <= bar['high']):
            raise ValueError('INVALID_NATIVE_BAR')
        window.append(bar)
        if len(window) < 5:
            yield None
            continue
        low, high = min(x['low'] for x in window), max(x['high'] for x in window)
        slowing.append((bar['close'] - low, high - low))
        if len(slowing) < 3:
            yield None
            continue
        numerator = sum(x[0] for x in slowing)
        denominator = sum(x[1] for x in slowing)
        yield numerator / denominator * 100 if denominator else 100.0
