"""Public time API. Native conversion requires externally attested mapping.

Presentation zones never determine causality. The existing native mapping and
integer UTC guard remain the only conversion/decision implementations.
"""
from datetime import datetime, timedelta, timezone

from native_time_mapping import (
    ClockMapping, NativeTimestamp, NormalizedEvent, ECUADOR, NEW_YORK,
    native_to_utc, causal_event,
)
from temporal_causality import utc_milliseconds


def native_mt5_time_to_utc(value: NativeTimestamp, mapping: ClockMapping) -> NormalizedEvent:
    return native_to_utc(value, mapping)


def normalize_tick_time(value: NativeTimestamp, mapping: ClockMapping) -> NormalizedEvent:
    return native_mt5_time_to_utc(value, mapping)


def utc_to_ecuador(value: datetime) -> datetime:
    utc_milliseconds(value)
    return value.astimezone(ECUADOR)


def utc_to_new_york(value: datetime) -> datetime:
    utc_milliseconds(value)
    return value.astimezone(NEW_YORK)


def xm_server_to_utc(server_label: datetime, mapping: ClockMapping) -> datetime:
    """Explicit wall label only; reject aware (already converted) timestamps.

    Segment offsets originate in external evidence, never an assumed broker TZ.
    """
    if not isinstance(server_label, datetime) or server_label.tzinfo is not None:
        raise ValueError('SERVER_WALL_LABEL_REQUIRED_NO_DOUBLE_CONVERSION')
    if mapping.verified is not True:
        raise ValueError('NATIVE_UTC_MAPPING_UNVERIFIED')
    candidates = []
    for segment in mapping.segments:
        utc = server_label.replace(tzinfo=timezone.utc) - timedelta(seconds=segment.server_utc_offset_seconds)
        if segment.utc_start_msc <= utc_milliseconds(utc) < segment.utc_end_msc:
            candidates.append(utc)
    if len(candidates) != 1:
        raise ValueError('AMBIGUOUS_OR_UNCOVERED_SERVER_TIME')
    return candidates[0]


def validate_causal_timestamp(event: NormalizedEvent, *, feature_max_time: datetime,
                              decision_time: datetime, previous=None) -> tuple[bool, str]:
    if not isinstance(event, NormalizedEvent):
        return False, 'NORMALIZED_UTC_REQUIRED'
    try:
        return causal_event(event, feature_max_time=feature_max_time,
                            decision_time=decision_time, previous=previous)
    except (ValueError, TypeError, AttributeError):
        return False, 'INVALID_TEMPORAL_INPUT'
