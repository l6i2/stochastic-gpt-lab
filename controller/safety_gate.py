"""All date ranges are inclusive dates in the tester's server calendar."""
import json
from datetime import datetime, time, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def bounds(start, end):
    a = datetime.combine(datetime.strptime(start, '%Y-%m-%d').date(), time.min, timezone.utc)
    b = datetime.combine(datetime.strptime(end, '%Y-%m-%d').date(), time.max, timezone.utc)
    if b < a:
        raise ValueError('Invalid date range')
    return int(a.timestamp() * 1000), int(b.timestamp() * 1000)


def boundaries(manifest=None):
    return json.loads(Path(manifest or ROOT / 'outputs/splits/split_manifest.json').read_text())['boundaries']


def is_train_range(start, end, manifest=None):
    a, b = bounds(start, end)
    return a <= b < boundaries(manifest)['validation_start_signal_time_msc']


def is_validation_range(start, end, manifest=None):
    a, b = bounds(start, end)
    limits = boundaries(manifest)
    return limits['validation_start_signal_time_msc'] <= a <= b < limits['final_test_start_signal_time_msc']


def is_final_test_range(start, end, manifest=None):
    return bounds(start, end)[1] >= boundaries(manifest)['final_test_start_signal_time_msc']


def assert_research_range_allowed(start, end, manifest=None):
    if is_final_test_range(start, end, manifest):
        raise RuntimeError('FINAL_TEST_GATE_BLOCKED')


def assert_safe_source(source):
    import re
    text = Path(source).read_text(encoding='utf-8-sig')
    if not re.search(r'input\s+bool\s+LIVE_TRADING\s*=\s*false\s*;', text):
        raise RuntimeError('SECURITY_GATE: LIVE_TRADING=false required')
    if re.search(r'\b(OrderSend|OrderSendAsync|CTrade|PositionOpen)\b', text, re.I):
        raise RuntimeError('SECURITY_GATE: trading API forbidden')

