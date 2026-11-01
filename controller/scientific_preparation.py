"""Read-only scientific preparation. No price loader, estimator fit or scoring API.

Reconciliation indexes immutable source facts; it never rewrites their original
chains or infers completeness/independence from the existence of hashes.
"""
from .pretrain_contracts import FEATURES, chain, seal, verify_chain
from .pretrain_model_preparation import LOGISTIC
from .native_study_design import fold_plan


def reconcile(base, overlays, source_receipts):
    verify_chain(base['entries'], base['chain_head'])
    refs = [dict(kind='ORIGINAL_ENTRY', original_entry=r) for r in base['entries']]
    siblings = []
    for overlay in overlays:
        row = dict(overlay)
        recorded = row.pop('entry_sha256')
        if seal(row) != recorded or row['previous'] != base['chain_head'] or row['ledger_sequence'] != len(base['entries']):
            raise ValueError('INVALID_OR_WRONG_PARENT_OVERLAY')
        siblings.append(recorded)
        refs.append(dict(kind='ORIGINAL_SIBLING_OVERLAY', original_entry=overlay))
    if len(set(siblings)) != len(siblings):
        raise ValueError('DUPLICATE_OVERLAY')
    refs += [dict(kind='SOURCE_RECEIPT', receipt=r) for r in source_receipts]
    records = chain(refs)
    return dict(schema='scientific-evidence-reconciliation/1', entries=records,
                chain_head=verify_chain(records), original_base_head=base['chain_head'],
                original_sibling_heads=siblings, originals_rebased=False,
                completeness_verified=False, independence_certified=False,
                missing=list(base['missing']), protected_rows_opened=0)


def training_plan(protocol_hash, whitelist_hash, *, signals=None):
    """Prepare metadata only. Supplied signals are synthetic horizon metadata.

    No authorization flag can turn this planner into an execution interface.
    A future admitted-data runner must bind real membership and authorization
    before any data read. This plan is not that authorization or dataset.
    """
    for value in (protocol_hash, whitelist_hash):
        if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('HASH_BINDINGS_REQUIRED')
    folds = fold_plan(signals) if signals is not None else None
    result = dict(mode='PRE_TRAIN_PLAN_ONLY', protocol_hash=protocol_hash,
        whitelist_hash=whitelist_hash, feature_order=list(FEATURES), family='logistic',
        params=dict(LOGISTIC), planned_slots=[dict(fold=f, side=s) for f in range(1,5) for s in ('BUY','SELL')],
        chronological_plan=folds, scaling='TRAIN_ONLY_DDOF_0_ZERO_SCALE_TO_1',
        missing='NO_IMPUTATION_FINITE_TRAIN_ONLY_MISSING_EVALUATION_FIXED_FOLLOW',
        decision='p>0.5 FOLLOW ELSE INVERT', label='FOLLOW_PNL_MINUS_INVERT_PNL_GT_0',
        max_fits=8, max_launches=1, final_full_dataset_fit=False, optimization_searches=0,
        actual_fits=0, actual_scoring=0, dataset_hash=None, admitted_dataset=False,
        execution_enabled=False, authorization_requested=False,
        execution_requirements=['HASH_BOUND_ADMITTED_DATASET_AND_DEPENDENCIES',
            'COMPLETE_EXPOSURE_AND_MEMBERSHIP', 'EXPLICIT_SCIENTIFIC_AUTHORIZATION',
            'ADMITTED_DATA_ADAPTER_AND_ACCEPTANCE_EVALUATOR_VALIDATION_BEFORE_EXECUTION'])
    return dict(result, plan_sha256=seal(result))


def progress_projection(m):
    """Project the existing automatic worker report; never manufacture bars."""
    keys=('raw_capture_id','status','process_id','observed_clock','raw_records_processed',
          'raw_callback_age_ms','raw_collector_status','source_cursors',
          'm1_aggregate_bars','m5_aggregate_bars','rejected_buckets','m5_parity',
          'warmup_current_own_run','warmup_scientifically_verified','warmup_required',
          'diagnostic_buy_signals','diagnostic_sell_signals','diagnostic_first_signals_progress',
          'signals_required','diagnostic_post_signal_bars','post_signal_bars_required',
          'evaluable_buy','evaluable_sell','evaluable_total','evaluable_required',
          'evaluable_required_each_side','membership','coverage_rule','incident_count',
          'protocol_stream_unbroken','ledger_chain_head','ledger_artifacts',
          'dataset_maturity','dataset_hash','admitted_records','causal_audit','training_readiness')
    if (m['warmup_required'],m['signals_required'],m['post_signal_bars_required'],
        m['evaluable_required'],m['evaluable_required_each_side']) != (350,800,100,200,80):
        raise ValueError('FROZEN_MATURITY_REQUIREMENTS_CHANGED')
    if m['admitted_records'] != 0 or m['dataset_hash'] is not None:
        raise ValueError('UNREVIEWED_ADMISSION_NOT_ALLOWED_BY_PREPARATION')
    return {k:m[k] for k in keys}
