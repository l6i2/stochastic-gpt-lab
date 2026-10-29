"""Structural evidence intake. No mapping, calendar or cohort activation API.

Even a complete bundle requires independent scientific review; a self-declared
verified/PASS field never becomes authorization. Original sources stay immutable.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

SERVER = 'XMGlobalSC-MT5 5'
SYMBOL = 'US30Cash'
KINDS = ('tick_event', 'bar_time', 'historical_mapping', 'calendar')


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def template():
    return dict(schema_version=1, server=SERVER, symbol=SYMBOL,
                evidence_kind='tick_event', source_url=None, source_file=None, source_sha256=None,
                independent_authority=None, event_binding=None, utc_interval=None,
                applicable_native_interval=None, historical_transitions=None,
                sessions=None, dated_exceptions=None, retrieved_utc=None,
                scientific_acceptance=False)


def utc_interval(value):
    if not isinstance(value, dict) or set(value) != {'start', 'end_exclusive'}:
        raise ValueError('BOUNDED_UTC_INTERVAL_REQUIRED')
    parsed = []
    for key in ('start', 'end_exclusive'):
        item = datetime.fromisoformat(value[key].replace('Z', '+00:00'))
        if item.tzinfo is None or item.utcoffset().total_seconds() != 0:
            raise ValueError('EXPLICIT_UTC_REQUIRED')
        parsed.append(item)
    if parsed[0] >= parsed[1]:
        raise ValueError('INVALID_UTC_INTERVAL')


def inspect_bundle(path):
    path = Path(path).resolve()
    if path.stat().st_size > 2*1024*1024:
        raise ValueError('EVIDENCE_MANIFEST_SIZE_LIMIT')
    payload = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(payload, dict):
        raise ValueError('EVIDENCE_BUNDLE_OBJECT_REQUIRED')
    missing = []
    if payload.get('server') != SERVER or payload.get('symbol') != SYMBOL:
        missing.append('EXACT_SERVER_SYMBOL_REQUIRED')
    kind = payload.get('evidence_kind')
    if kind not in KINDS:
        missing.append('EVIDENCE_KIND_REQUIRED')
    address = urlparse(payload.get('source_url') or '')
    if address.scheme != 'https' or not address.hostname or address.username or address.password:
        missing.append('HTTPS_SOURCE_WITHOUT_CREDENTIALS_REQUIRED')
    authority = payload.get('independent_authority')
    if not isinstance(authority, dict) or not authority.get('issuer') or not authority.get('authentication_method'):
        missing.append('INDEPENDENT_AUTHORITY_IDENTITY_AND_AUTHENTICATION_REQUIRED')
    source = payload.get('source_file')
    if not isinstance(source, str) or not source:
        missing.append('IMMUTABLE_SOURCE_ARTIFACT_REQUIRED')
    else:
        local = (path.parent / source).resolve()
        if path.parent not in local.parents:
            raise ValueError('EVIDENCE_PATH_ESCAPE')
        if not local.is_file() or sha_file(local) != payload.get('source_sha256'):
            missing.append('SOURCE_HASH_MISMATCH_OR_MISSING')
    try:
        utc_interval(payload.get('utc_interval'))
    except (TypeError, ValueError, AttributeError):
        missing.append('EXPLICIT_BOUNDED_UTC_INTERVAL_REQUIRED')
    if kind in ('tick_event', 'bar_time'):
        binding = payload.get('event_binding')
        required = ('native_record_sha256', 'independent_record_sha256', 'matching_rule', 'uniqueness_evidence')
        if not isinstance(binding, dict) or not all(binding.get(key) for key in required):
            missing.append('UNIQUE_NATIVE_TO_INDEPENDENT_RECORD_BINDING_REQUIRED')
        if kind == 'bar_time' and (not isinstance(binding, dict) or not binding.get('bar_open_semantics')):
            missing.append('BAR_OPEN_SEMANTICS_REQUIRED_SEPARATE_FROM_TICKS')
    if kind == 'historical_mapping':
        if not payload.get('applicable_native_interval') or not payload.get('historical_transitions'):
            missing.append('NATIVE_INTERVAL_AND_EVIDENCED_TRANSITIONS_REQUIRED')
    if kind == 'calendar':
        if not payload.get('sessions') or payload.get('dated_exceptions') is None:
            missing.append('DATED_SESSIONS_AND_EXCEPTION_COVERAGE_REQUIRED')
    return dict(status='INCOMPLETE' if missing else 'STRUCTURALLY_COMPLETE_REVIEW_REQUIRED',
                evidence_kind=kind, missing=missing, input_sha256=sha_file(path),
                semantic_authenticity_verified=False, event_mapping_authorized=False,
                calendar_authorized=False, cohort_activation_allowed=False, scientific_acceptance=False)
