"""Authorized C+F metadata processing and fail-closed dataset admission."""
from .pretrain_contracts import seal
from .prospective_processor import Processor, initial_state
from .isolated_observation import host_clock
from .six_routes import aggregate_m1

REQUIREMENTS = dict(warmup=350, signals=800, post_bars=100, evaluable=200, each_side=80)


def bridge_allowed(proof, before, after, health):
    required = ('identity_verified', 'calendar_current', 'exception_attested',
                'continuous_connected_observation', 'no_sleep', 'coverage_verified')
    return bool(proof and all(proof.get(k) is True for k in required)
                and proof.get('server') == 'XMGlobalSC-MT5 5' and proof.get('symbol') == 'US30Cash'
                and proof.get('from_native_msc') == before and proof.get('to_native_msc') == after
                and before < after and before % 300000 == after % 300000 == 0
                and health.get('same_boot') and health.get('monotonic')
                and health.get('connected') and health.get('no_sleep')
                and health.get('poll_gap_ms', 10001) <= 10000)


def process_events(state, events, clock=host_clock):
    """Only accepted post-cut native bars feed the isolated recursive context."""
    extra = []
    context = state.setdefault('cf_features', initial_state())
    if any(e['kind'] in ('NEW_OBSERVATION_EPOCH', 'OBSERVATION_INTERRUPTION') for e in events):
        state['cf_features'] = context = initial_state()
        state['cf_acquisition_complete'] = False
        state['cf_m1_cache'] = []
        state['cf_offline_use_verified'] = False
        state['cf_full_feature_values'] = False
    if any(e['kind'] == 'OBSERVATION_INTERRUPTION' for e in events):
        return [dict(kind='CF_CONTEXT_INTERRUPTED', reason='NATIVE_OBSERVATION_FAILURE')]
    for event in events:
        if event['kind'] == 'LIVE_LATEST_STATE_POLL' and not state.get('cf_first_observation'):
            state['cf_first_observation'] = dict(native_quote=event['native_quote'],
                                               read_start=event['read_start'], read_end=event['read_end'],
                                               origin='POST_AUTHORIZATION_LIVE_DATABASE_STATE_POLL')
        if event['kind'] == 'DATABASE_SNAPSHOT_PAIR' and event['frame_seconds'] == 60:
            if event['assessment']['status'] == 'VERIFIED_DATABASE_VIEW_ONLY':
                cache = state.setdefault('cf_m1_cache', [])
                cache.append(dict(event['native_bar'], epoch=event['epoch']))
                state['cf_m1_cache'] = cache[-10:]
            continue
        if event['kind'] != 'DATABASE_SNAPSHOT_PAIR' or event['frame_seconds'] != 300:
            continue
        if event['assessment']['status'] != 'VERIFIED_DATABASE_VIEW_ONLY':
            state['cf_features'] = context = initial_state()
            extra.append(dict(kind='CF_CONTEXT_EXCLUDED', reason=event['assessment']['reasons']))
            continue
        bar = dict(event['native_bar'], segment=event['epoch'], evidence_hash=seal(event))
        bar_hash = seal(bar)
        minutes = [row for row in state.get('cf_m1_cache', []) if row['epoch'] == event['epoch']
                   and bar['time'] <= row['time'] < bar['time'] + 300]
        aggregates = aggregate_m1(minutes)
        parity = (len(aggregates) == 1 and aggregates[0]['complete_five_minutes']
                  and all(aggregates[0][k] == bar[k] for k in ('open','high','low','close','tick_volume')))
        extra.append(dict(kind='CF_M1_M5_PARITY', native_open=bar['time'], matched=parity,
                          minute_bar_hashes=[seal(row) for row in minutes], native_m5_hash=bar_hash))
        if not parity:
            state['cf_features'] = context = initial_state()
            state['cf_offline_use_verified'] = False
            state['cf_full_feature_values'] = False
            extra.append(dict(kind='CF_CONTEXT_EXCLUDED', reason='M1_M5_PARITY_OR_COVERAGE_PENDING'))
            continue
        context['own_bars'] += 1
        context['own_run_bars'] += 1
        if context['after_warmup_signals'] >= 800:
            context['post_signal_bars'] = min(100, context['post_signal_bars'] + 1)
            state['cf_acquisition_complete'] = context['post_signal_bars'] == 100
        quote = next(e['native_quote'] for e in events if e['kind'] == 'LIVE_LATEST_STATE_POLL')
        receipt = event['verification_observation']['read_end']
        ref = dict(native_time_msc=quote['time_msc'], segment=event['epoch'],
                   snapshot_hash=seal(event), acquisition_origin='NATIVE_DATABASE_OBSERVATION')
        def emit(kind, body):
            extra.append(dict(kind=kind, **body))
        processor = Processor(context, emit, None, event['first_observation']['tick_size'], REQUIREMENTS, clock)
        processor.features(bar, bar_hash, ref, receipt)
        features = next(e for e in reversed(extra) if e['kind'] == 'CAUSAL_PREFIX_FEATURES')
        ready = features['compute_clock']
        decision = clock()
        if ready['boot_id'] != decision['boot_id'] or ready['monotonic_ns'] > decision['monotonic_ns']:
            raise ValueError('CF_FEATURE_NOT_READY_AT_OFFLINE_USE')
        state['cf_offline_use_verified'] = True
        state['cf_full_feature_values'] = features['full_feature_values_present']
        extra.append(dict(kind='CF_OFFLINE_AVAILABILITY', feature_hash=features['feature_hash'],
                          ready_clock=ready, offline_use_clock=decision,
                          physical_original_entry_availability_proven=False,
                          first_observation=event['first_observation'], native_bar_hash=bar_hash))
    return extra


def admission(facts):
    if facts.get('integrity_failure') or facts.get('contract_changed') or facts.get('trading_allowed'):
        status = 'FAIL'
    elif not facts.get('contract_approved'):
        status = 'WAITING_FOR_AUTHORIZATION'
    elif not all(facts.get(k) is True for k in ('independence', 'nonoverlap', 'calendar', 'coverage', 'causality', 'seeds')):
        status = 'WAITING_FOR_EVIDENCE'
    elif (facts.get('warmup', 0) < 350 or facts.get('signals', 0) != 800
          or facts.get('post_bars', 0) != 100 or facts.get('evaluable', 0) < 200
          or facts.get('BUY', 0) < 80 or facts.get('SELL', 0) < 80
          or facts.get('BUY_folds', 0) < 3 or facts.get('SELL_folds', 0) < 3):
        status = 'WAITING_FOR_DATA'
    elif not facts.get('sealed_membership_hash') or not facts.get('dataset_hash'):
        status = 'WAITING_FOR_EVIDENCE'
    else:
        status = 'PASS'
    pending = [k for k in ('independence','nonoverlap','calendar','coverage','causality','seeds') if facts.get(k) is not True]
    return dict(NEW_STUDY_DATASET_ADMISSION=status, evidence_pending=pending, training_authorized=False,
                TRAINING_ADMISSION_GATE='BLOCKED_NO_SPECIFIC_TRAINING_GRANT', TRAINING_EXECUTED=False)
