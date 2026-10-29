"""Public time API. Native conversion requires externally attested mapping.

Presentation zones never determine causality. The existing native mapping and
integer UTC guard remain the only conversion/decision implementations.
"""
from datetime import date, datetime, time, timedelta, timezone

from native_time_mapping import (
    ClockMapping, NativeTimestamp, NormalizedEvent, ECUADOR, NEW_YORK,
    native_to_utc, causal_event,
)
from temporal_causality import utc_milliseconds
from native_time_mapping import EPOCH, TZDATA_VERSION

DISPLAY_TIMEZONE = 'America/Guayaquil'
DISPLAY_COLUMNS = ('Ecuador', 'Nueva York', 'XM', 'UTC')


def instant_display(value: datetime, *, basis: str, mapping=None, server=None, symbol=None) -> dict:
    """An explicitly identified instant. Host receipt is never broker event proof."""
    utc_milliseconds(value)
    if basis not in ('HOST_RECEIPT_UNATTESTED', 'VERIFIED_EVENT_UTC', 'REFERENCE_SESSION'):
        raise ValueError('EXPLICIT_TIME_BASIS_REQUIRED')
    utc = value.astimezone(timezone.utc)
    ny = utc.astimezone(NEW_YORK)
    xm, offset, mapping_id = None, None, None
    if (mapping is not None and mapping.verified is True and server == mapping.server
            and symbol in mapping.symbols):
        segments = [s for s in mapping.segments if s.utc_start_msc <= utc_milliseconds(utc) < s.utc_end_msc]
        if len(segments) == 1:
            offset = segments[0].server_utc_offset_seconds
            xm = (utc + timedelta(seconds=offset)).replace(tzinfo=None).isoformat(timespec='milliseconds')
            mapping_id = mapping.mapping_id
    return dict(primary_timezone=DISPLAY_TIMEZONE, primary_time=utc.astimezone(ECUADOR).isoformat(timespec='milliseconds'),
        Ecuador=utc.astimezone(ECUADOR).isoformat(timespec='milliseconds'),
        **{'Nueva York': ny.isoformat(timespec='milliseconds')}, XM=xm,
        UTC=utc.isoformat(timespec='milliseconds'), time_basis=basis,
        new_york_abbreviation=ny.tzname(), new_york_fold=ny.fold,
        xm_status='VERIFIED_BOUNDED_PERIOD' if xm else 'UNVERIFIED_NO_CONVERSION',
        xm_server_offset_seconds=offset, mapping_id=mapping_id, tzdata_version=TZDATA_VERSION,
        scientific_authorization=False)


def event_display(value: NativeTimestamp, mapping=None) -> dict:
    """Operations, signals and bars share this adapter; native fields never mutate."""
    original = dict(time=value.time, time_msc=value.time_msc, server=value.server,
                    symbol=value.symbol, raw_sha256=value.raw_sha256)
    try:
        if mapping is None:
            raise ValueError('NATIVE_UTC_MAPPING_UNVERIFIED')
        normalized = native_to_utc(value, mapping)
    except ValueError as exc:
        return dict(primary_timezone=DISPLAY_TIMEZONE, primary_time=None, Ecuador=None,
                    **{'Nueva York': None}, XM=f'native time_msc={value.time_msc} (sin mapping)', UTC=None, original_xm=original,
                    status='QUARANTINED', reason=str(exc), scientific_authorization=False)
    view = instant_display(EPOCH + timedelta(milliseconds=normalized.utc_msc),
        basis='VERIFIED_EVENT_UTC', mapping=mapping, server=value.server, symbol=value.symbol)
    view.update(original_xm=original, status='DISPLAY_READY', utc_msc=normalized.utc_msc)
    return view


def chart_points(values, mapping=None):
    """Derived labels only. Preserve input order and integer UTC causal keys."""
    return [event_display(value, mapping) for value in values]


def new_york_wall_to_utc(wall: datetime, *, fold=None) -> datetime:
    if wall.tzinfo is not None or fold not in (None, 0, 1):
        raise ValueError('NAIVE_NEW_YORK_WALL_AND_OPTIONAL_FOLD_REQUIRED')
    candidates = {}
    for f in (0, 1):
        candidate = wall.replace(tzinfo=NEW_YORK, fold=f).astimezone(timezone.utc)
        back = candidate.astimezone(NEW_YORK)
        if back.replace(tzinfo=None) == wall and back.fold == f:
            candidates[f] = candidate
    if not candidates:
        raise ValueError('NONEXISTENT_NEW_YORK_TIME')
    if len(candidates) > 1 and fold is None:
        raise ValueError('AMBIGUOUS_NEW_YORK_TIME_REQUIRES_FOLD')
    if fold is not None and fold not in candidates:
        raise ValueError('INVALID_NEW_YORK_FOLD')
    return candidates[fold] if fold is not None else next(iter(candidates.values()))


def new_york_reference_session(day: date) -> dict:
    """Nominal NYSE core reference, never a US30Cash opening permission/calendar."""
    opening = new_york_wall_to_utc(datetime.combine(day, time(9, 30)))
    closing = new_york_wall_to_utc(datetime.combine(day, time(16)))
    return dict(kind='NYSE_NOMINAL_CORE_REFERENCE_ONLY', date=day.isoformat(),
        start=instant_display(opening, basis='REFERENCE_SESSION'),
        end=instant_display(closing, basis='REFERENCE_SESSION'),
        weekday_candidate=day.weekday() < 5, holiday_and_early_close_status='NOT_EVALUATED',
        xm_us30cash_session_status='UNVERIFIED_USE_EXACT_BROKER_CALENDAR', execution_allowed=False,
        source='https://www.nyse.com/markets/hours-calendars')


def new_york_dst_changes(year: int) -> list[dict]:
    """Find historical transitions in the pinned IANA data, not a US date formula."""
    cursor = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    result = []
    while cursor < end:
        following = min(cursor + timedelta(days=1), end)
        before = cursor.astimezone(NEW_YORK).utcoffset()
        if following.astimezone(NEW_YORK).utcoffset() != before:
            low, high = cursor, following
            while (high - low).total_seconds() > 1:
                middle = low + timedelta(seconds=int((high - low).total_seconds()) // 2)
                if middle.astimezone(NEW_YORK).utcoffset() == before:
                    low = middle
                else:
                    high = middle
            result.append(dict(transition=instant_display(high, basis='REFERENCE_SESSION'),
                offset_before_seconds=int(before.total_seconds()),
                offset_after_seconds=int(high.astimezone(NEW_YORK).utcoffset().total_seconds())))
        cursor = following
    return result


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
