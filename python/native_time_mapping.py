"""One explicit, evidence-gated native->UTC conversion; raw inputs remain immutable."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from importlib import resources
from importlib.metadata import version
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from temporal_causality import utc_milliseconds, validate_decision_times

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
TZDATA_VERSION = version('tzdata')
if TZDATA_VERSION != '2026.5':
    raise RuntimeError('TZDATA_VERSION_NOT_FROZEN')


def _frozen_zone(key: str) -> ZoneInfo:
    # Use the pinned package, not a different system tzdb on another machine.
    with resources.files('tzdata.zoneinfo').joinpath(*key.split('/')).open('rb') as stream:
        return ZoneInfo.from_file(stream, key=key)


ECUADOR = _frozen_zone('America/Guayaquil')
NEW_YORK = _frozen_zone('America/New_York')


@dataclass(frozen=True)
class NativeTimestamp:
    time: int
    time_msc: int
    symbol: str
    server: str
    raw_sha256: str


@dataclass(frozen=True)
class MappingSegment:
    utc_start_msc: int
    utc_end_msc: int
    native_utc_offset_seconds: int
    server_utc_offset_seconds: int


@dataclass(frozen=True)
class ClockMapping:
    mapping_id: str
    server: str
    symbols: tuple[str, ...]
    segments: tuple[MappingSegment, ...]
    verified: bool = False


@dataclass(frozen=True)
class NormalizedEvent:
    original: NativeTimestamp
    utc_msc: int
    mapping_id: str
    views: dict


def utc_views(value: datetime) -> dict:
    """Human zones are views of an explicit instant, never clocks for causality."""
    utc_milliseconds(value)  # Reject naive values, including ambiguous wall times.
    utc = value.astimezone(timezone.utc)
    ny = utc.astimezone(NEW_YORK)
    return {'normalized_utc': utc.isoformat(timespec='milliseconds'),
            'ecuador_time': utc.astimezone(ECUADOR).isoformat(timespec='milliseconds'),
            'new_york_time': ny.isoformat(timespec='milliseconds'),
            'ecuador_timezone': ECUADOR.key, 'new_york_timezone': NEW_YORK.key,
            'new_york_abbreviation': ny.tzname(), 'new_york_fold': ny.fold,
            'tzdata_version': TZDATA_VERSION}


def load_mapping(path: Path) -> ClockMapping:
    path = Path(path)
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != path.with_name(path.name + '.sha256').read_text().strip():
        raise ValueError('MAPPING_SEAL_MISMATCH')
    config = json.loads(payload)
    if config.get('status') != 'PASS':
        raise ValueError('NATIVE_UTC_MAPPING_UNVERIFIED')
    evidence_path = (path.parent / config['evidence_file']).resolve()
    if path.parent.resolve() not in evidence_path.parents:
        raise ValueError('MAPPING_EVIDENCE_PATH_ESCAPE')
    evidence_bytes = evidence_path.read_bytes()
    if hashlib.sha256(evidence_bytes).hexdigest() != config['evidence_sha256']:
        raise ValueError('MAPPING_EVIDENCE_HASH_MISMATCH')
    audit = json.loads(evidence_bytes)
    if (audit.get('clock_attestation') != 'PASS' or audit.get('native_to_utc_mapping') != 'PASS'
            or audit.get('complete_frames', 0) < 50 or audit.get('authorized_segments') != config['segments']):
        raise ValueError('MAPPING_EVIDENCE_NOT_SUFFICIENT')
    segments = tuple(MappingSegment(**s) for s in config['segments'])
    if (not segments or any(any(type(v) is not int for v in vars(s).values())
            or s.utc_start_msc < 0 or s.utc_end_msc <= s.utc_start_msc for s in segments)
            or any(a.utc_end_msc > b.utc_start_msc for a, b in zip(segments, segments[1:]))):
        raise ValueError('INVALID_MAPPING_SEGMENTS')
    return ClockMapping(config['mapping_id'], config['server'], tuple(config['symbols']), segments, True)


def native_to_utc(value: NativeTimestamp, mapping: ClockMapping) -> NormalizedEvent:
    if not isinstance(value, NativeTimestamp):
        raise ValueError('DOUBLE_CONVERSION_OR_UNTYPED_TIMESTAMP')
    if mapping.verified is not True:
        raise ValueError('NATIVE_UTC_MAPPING_UNVERIFIED')
    if (type(value.time) is not int or type(value.time_msc) is not int or value.time < 0
            or value.time_msc < 0 or value.time_msc // 1000 != value.time):
        raise ValueError('SECONDS_MILLISECONDS_MISMATCH')
    if not re.fullmatch('[0-9a-f]{64}', value.raw_sha256):
        raise ValueError('RAW_PROVENANCE_HASH_REQUIRED')
    if value.server != mapping.server or value.symbol not in mapping.symbols:
        raise ValueError('MAPPING_IDENTITY_MISMATCH')
    candidates = []
    for segment in mapping.segments:
        stamp = value.time_msc - segment.native_utc_offset_seconds * 1000
        if segment.utc_start_msc <= stamp < segment.utc_end_msc:
            candidates.append((stamp, segment))
    if len(candidates) != 1:
        raise ValueError('AMBIGUOUS_OR_UNCOVERED_NATIVE_TIME')
    stamp, segment = candidates[0]
    utc = EPOCH + timedelta(milliseconds=stamp)
    views = utc_views(utc)
    views.update(native_mt5_time={'time': value.time, 'time_msc': value.time_msc},
                 xm_server_time=(utc + timedelta(seconds=segment.server_utc_offset_seconds)).replace(tzinfo=None).isoformat(timespec='milliseconds'),
                 xm_server_time_basis='VERIFIED_SERVER_WALL_LABEL', mapping_id=mapping.mapping_id,
                 raw_sha256=value.raw_sha256)
    # Canonical causal identity excludes human timezone views. This is a new
    # derived hash; it never replaces the raw artifact hash.
    causal_payload = {'raw_sha256': value.raw_sha256, 'normalized_utc_msc': stamp,
                      'mapping_id': mapping.mapping_id}
    views['utc_event_sha256'] = hashlib.sha256(json.dumps(causal_payload, sort_keys=True,
        separators=(',', ':')).encode('utf-8')).hexdigest()
    return NormalizedEvent(value, stamp, mapping.mapping_id, views)


def causal_event(event: NormalizedEvent, *, feature_max_time: datetime, decision_time: datetime,
                 previous: NormalizedEvent | None = None) -> tuple[bool, str]:
    feature_msc, decision_msc = utc_milliseconds(feature_max_time), utc_milliseconds(decision_time)
    if previous and (previous.mapping_id != event.mapping_id or previous.utc_msc > event.utc_msc):
        return False, 'NORMALIZED_ORDER_VIOLATION'
    if feature_max_time > decision_time:
        return False, 'FEATURE_LOOKAHEAD'
    return validate_decision_times(feature_max_time_msc=feature_msc,
        decision_time_msc=decision_msc, quote_time_msc=event.utc_msc)
