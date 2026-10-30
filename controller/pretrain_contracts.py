"""PRE_TRAIN metadata checks only. No dataset reader, fit, score or activation API."""
import hashlib
import json

STUDY_ID = 'US30CASH_M5_NATIVE_20261030_01'
DATASET_ID = 'us30cash_m5_native_new_01_reserved'
FEATURES = ('stoch_k','delta_k_1','ATR','relative_volume_20','ha_direction','range_to_ATR')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def seal(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def chain(records):
    previous = None
    result = []
    for number, record in enumerate(records):
        item = dict(record, ledger_sequence=number, previous=previous)
        previous = seal(item)
        result.append(dict(item, entry_sha256=previous))
    return result


def verify_chain(records, expected_head=None):
    previous = None
    for number, record in enumerate(records):
        item = dict(record)
        recorded = item.pop('entry_sha256')
        if item['ledger_sequence'] != number or item['previous'] != previous or seal(item) != recorded:
            raise ValueError('EXPOSURE_CHAIN_MISMATCH')
        previous = recorded
    if expected_head is not None and previous != expected_head:
        raise ValueError('EXPOSURE_CHAIN_TRUNCATED_OR_WRONG_ANCHOR')
    return previous


def temporal_dependencies():
    shared = dict(time_domain='XM_NATIVE_ORDER', forming_bar_allowed=False,
        event_cutoff='(closed_bar_open+300)*1000-1',
        availability='NEXT_OBSERVED_M5_CALLBACK_AFTER_SHIFT_1_CONTEXT_COMPUTED',
        equal_timestamps='ARRIVAL_INDEX_AND_COMPUTE_STAGE_REQUIRED',
        prospective_old_history_allowed=False, training_admitted=False)
    definitions = [
        dict(feature='stoch_k',inputs=['closed_M5_OHLC'],bar_offsets=list(range(7)),
             definition='MT5 MAIN_K 5/3/3 SMA LowHigh ratio-of-sums; closed shift 1',
             full_seed_required=False,minimum_input_bars=7,
             semantic_evidence='NATIVE_MAIN_K_PARITY_RETAINED_FIXED_DAY_ONLY'),
        dict(feature='delta_k_1',inputs=['stoch_k','previous_closed_MAIN_K'],bar_offsets=list(range(8)),
             definition='closed MAIN_K[0] minus MAIN_K[1]',full_seed_required=False,minimum_input_bars=8,
             semantic_evidence='FROZEN_PRODUCER_DIFFERENCE_OF_NATIVE_BUFFERS'),
        dict(feature='ATR',inputs=['closed_M5_OHLC','native_indicator_initialization'],bar_offsets=None,
             definition='MT5 iATR(14), closed shift 1; no synthetic range adapter substitution',
             full_seed_required=True,minimum_input_bars=None,
             semantic_evidence='SYNTHETIC_AVAILABILITY_ONLY_NATIVE_INITIALIZATION_NOT_YET_BOUND'),
        dict(feature='relative_volume_20',inputs=['closed_M5_tick_volume'],bar_offsets=list(range(21)),
             definition='volume[0]/mean(volume[1:21]); zero denominator -> missing',
             full_seed_required=False,minimum_input_bars=21,
             semantic_evidence='BID_UPDATE_VOLUME_PARITY_RETAINED_FIXED_DAY_ONLY'),
        dict(feature='ha_direction',inputs=['closed_M5_OHLC','HA_seed_and_entire_recurrence'],bar_offsets=None,
             definition='frozen HeikinAshiCore recurrence from recorded seed; output only when Ready()',
             full_seed_required=True,minimum_input_bars=276,
             semantic_evidence='HA_WARMUP_256_READY_276_IS_NOT_A_FINITE_HISTORY_TRUNCATION'),
        dict(feature='range_to_ATR',inputs=['closed_M5_OHLC','ATR'],bar_offsets=[0],
             definition='(closed high-low)/native ATR[0]; zero or missing denominator -> missing',
             full_seed_required=True,minimum_input_bars=None,
             semantic_evidence='INHERITS_ENTIRE_ATR_INITIALIZATION_DEPENDENCY')]
    return dict(schema_version='native-temporal-dependencies/1.0',
        features=[shared|d for d in definitions],
        direct_snapshot_array_floor=20,producer_requested_context_bars=350,
        context_350_is_not_proof_of_recursive_seed_isolation=True,
        all_warmup_feature_and_label_inputs_must_have_independent_membership=True,
        target_dependency='FOLLOW_AND_INVERT_FULL_ORDERED_PATHS_UNTIL_FROZEN_EXIT_OR_CENSOR',
        target_horizon='100_OBSERVED_M5_BARS_NOT_500_WALL_CLOCK_MINUTES',
        execution_fields_are_predictors=False,UTC_session_fields_permitted=False)


def dependency_preflight(observations, dataset_start_index):
    """Synthetic checks of declared envelopes, not verification of real feature bytes."""
    if {r['feature'] for r in observations} != set(FEATURES) or len(observations) != len(FEATURES):
        raise ValueError('INCOMPLETE_FEATURE_DEPENDENCIES')
    specs = {r['feature']:r for r in temporal_dependencies()['features']}
    for row in observations:
        if set(row) != {'feature','oldest_source_index','last_closed_index','decision_arrival_index',
                        'ready_stage','decision_stage','closed_bars','seed_index'}:
            raise ValueError('UNEXPECTED_DEPENDENCY_FIELDS')
        ints = [row[k] for k in ('oldest_source_index','last_closed_index','decision_arrival_index',
                                'ready_stage','decision_stage','closed_bars')]
        if type(dataset_start_index) is not int or dataset_start_index < 0 or any(type(x) is not int or x < 0 for x in ints):
            raise ValueError('INVALID_DEPENDENCY_POSITION')
        if row['oldest_source_index'] < dataset_start_index:
            raise ValueError('PRE_START_WARMUP_OR_SOURCE')
        if row['last_closed_index'] >= row['decision_arrival_index'] or row['ready_stage'] != 1 or row['decision_stage'] != 2:
            raise ValueError('FORMING_OR_UNAVAILABLE_FEATURE')
        if row['oldest_source_index'] > row['last_closed_index']:
            raise ValueError('INVALID_SOURCE_ENVELOPE')
        spec = specs[row['feature']]
        minimum = spec['minimum_input_bars']
        if row['closed_bars'] < 20 or minimum is not None and row['closed_bars'] < minimum:
            raise ValueError('INSUFFICIENT_HISTORY_OR_WARMUP')
        if spec['full_seed_required'] and (type(row['seed_index']) is not int or
                row['seed_index'] < dataset_start_index or row['seed_index'] != row['oldest_source_index']):
            raise ValueError('UNBOUND_OR_PROTECTED_RECURSIVE_SEED')
    return dict(declared_envelopes='PASS_SYNTHETIC_ONLY',real_feature_bytes_verified=False,training_authorized=False)


def interval_disposition(candidate, ledger):
    """No unknown/open-ended role reservation can become unexposed by omission."""
    if set(candidate) != {'instrument','domain_id','dependency_start','label_end','signal_ids','source_sha256'}:
        raise ValueError('INVALID_CANDIDATE_METADATA')
    start, end = candidate['dependency_start'], candidate['label_end']
    if any(type(x) is not int or x < 0 for x in (start,end)) or end < start or not candidate['signal_ids']:
        raise ValueError('INCOMPLETE_CANDIDATE_INTERVAL')
    if not ledger.get('chain_head'):
        raise ValueError('MISSING_EXPOSURE_CHAIN_ANCHOR')
    verify_chain(ledger['entries'],ledger['chain_head'])
    reasons = set()
    if not ledger['completeness_verified']:
        reasons.add('INCOMPLETE_EXPOSURE_LEDGER')
    for row in ledger['entries']:
        if row['instrument'] != candidate['instrument']:
            continue
        if row.get('source_sha256') and row['source_sha256'] == candidate['source_sha256']:
            reasons.add('PREVIOUSLY_EXPOSED_SOURCE_VERSION')
        if set(row.get('signal_ids',[])) & set(candidate['signal_ids']):
            reasons.add('PREVIOUSLY_EXPOSED_SIGNAL')
        a, b = row.get('start_native_msc'), row.get('end_native_exclusive_msc')
        if row.get('domain_id') != candidate['domain_id'] or a is None:
            reasons.add('UNCOMPARABLE_OR_UNKNOWN_PROTECTED_INTERVAL')
        elif b is None:
            if end >= a:reasons.add('OPEN_ENDED_RESERVED_OR_QUARANTINED_ROLE')
        elif start < b and end >= a:
            reasons.add('WARMUP_FEATURE_OR_LABEL_OVERLAP')
    return dict(status='BLOCKED' if reasons else 'STRUCTURAL_ONLY_NOT_INDEPENDENCE_CERTIFICATION',
        reasons=sorted(reasons),training_authorized=False,scoring_authorized=False)


def preview_prospective_boundary(events, boundary):
    """Prepare isolation logic on supplied synthetic metadata; no activation/writer."""
    if boundary is None:
        return dict(status='INACTIVE_NO_REAL_START',eligible_sequences=[],training_authorized=False)
    if set(boundary) != {'session_id','sequence','first_complete_bar_native_msc'}:
        raise ValueError('INCOMPLETE_FUTURE_BOUNDARY')
    if not isinstance(boundary['session_id'],str) or not boundary['session_id'] or any(
            type(boundary[k]) is not int or boundary[k] < 0 for k in ('sequence','first_complete_bar_native_msc')) or boundary['first_complete_bar_native_msc'] % 300000:
        raise ValueError('INVALID_FUTURE_BOUNDARY')
    selected=[]
    last=boundary['sequence']
    for event in events:
        if event['session_id'] != boundary['session_id']:
            raise ValueError('RESTART_REQUIRES_NEW_VERIFIED_SEGMENT')
        if event['sequence'] <= last:
            raise ValueError('DUPLICATE_OR_OUT_OF_ORDER_RECEIPT')
        last=event['sequence']
        if event['native_bar_open_msc'] < boundary['first_complete_bar_native_msc']:
            continue
        if event['historical_requery'] or not event['connected']:
            raise ValueError('BACKFILL_OR_DISCONNECTED_OBSERVATION')
        selected.append(event['sequence'])
    return dict(status='SYNTHETIC_BOUNDARY_PREVIEW_ONLY',eligible_sequences=selected,
                activation_performed=False,training_authorized=False)
