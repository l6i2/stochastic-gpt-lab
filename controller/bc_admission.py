"""B+C pre-admission evidence gates. Never grants admission or training."""
from .pretrain_contracts import seal

GATES=('independence','exclusivity','membership','provenance','tick_coverage',
    'OHLC','BID_ASK','historical_continuity','calendar','ATR_seed','HA_seed',
    'causality','features','exit_horizons','no_leakage','folds','hashes','reproducibility')
MINIMUMS=dict(context=350,signals=800,post_bars=100,evaluable=200,BUY=80,SELL=80,BUY_folds=3,SELL_folds=3)
# No server-specific dated calendar certificate has yet been independently
# verified. A local document/hash or self-declared status is not such a proof.
VERIFIED_CALENDAR_RECEIPTS=frozenset()


def review(counts,evidence):
    if set(counts)!=set(MINIMUMS) or any(type(v) is not int or v<0 for v in counts.values()):
        raise ValueError('BC_INVALID_MATURITY_COUNTS')
    if set(evidence)!=set(GATES):raise ValueError('BC_REQUIRED_EVIDENCE_GATES_MISSING')
    for gate,item in evidence.items():
        if item.get('status') not in ('PASS','FAIL','WAITING_FOR_DATA','WAITING_FOR_EVIDENCE'):
            raise ValueError('BC_INVALID_EVIDENCE_STATUS:'+gate)
        if item['status'] in ('PASS','FAIL') and not item.get('witness_hashes'):
            raise ValueError('BC_BOOLEAN_WITHOUT_EVIDENCE:'+gate)
    deficits={k:max(0,n-counts[k]) for k,n in MINIMUMS.items()}
    failures=[k for k,v in evidence.items() if v['status']=='FAIL']
    pending=[k for k,v in evidence.items() if v['status'] not in ('PASS','FAIL')]
    status='FAIL' if failures else 'WAITING_FOR_DATA' if any(deficits.values()) else 'WAITING_FOR_EVIDENCE' if pending else 'READY_FOR_ADMISSION_REVIEW'
    if counts['signals']>800 or counts['post_bars']>100:
        status='FAIL';failures.append('FROZEN_SAMPLE_BOUNDARY_EXCEEDED')
    result=dict(schema='bc-pre-admission-review/2',status=status,counts=counts,deficits=deficits,
        gates=evidence,failures=failures,pending=pending,technical_package_complete=status=='READY_FOR_ADMISSION_REVIEW',
        training_authorization_status='WAITING_FOR_AUTHORIZATION',
        dataset_admitted=False,training_authorized=False,training_executed=False,
        request_ready=False,reason='SEPARATE_REVIEWED_ADMISSION_AND_HASH_BOUND_TRAINING_GRANT_REQUIRED')
    result['review_hash']=seal(result);return result


def package_template(identity,bindings,review_result):
    """A candidate is never an admitted grant, even if every counter passes."""
    return dict(schema='bc-future-authorization-package/1',study_id=identity['study_id'],
        dataset_id=identity['dataset_id'],dataset_hash=bindings.get('dataset_hash'),
        native_bounds=bindings.get('native_bounds'),membership_hash=bindings.get('membership_hash'),
        exposure_hash=bindings.get('exposure_hash'),protocol_hash=bindings['protocol_hash'],
        feature_whitelist_hash=bindings['feature_whitelist_hash'],code_head=bindings['code_head'],
        environment=bindings['environment'],environment_hash=seal(bindings['environment']),
        code_hash=bindings.get('code_hash'),plan_hash=bindings.get('plan_hash'),
        max_fits=8,authorized_fits=0,positions=[dict(fold=f,side=s) for f in range(1,5) for s in ('BUY','SELL')],
        final_models='FIXED_FOLD4_PER_SIDE_NO_NINTH_FIT',evaluation_active=False,
        entry_strategy='MAIN_K_5_3_3_20_80_NEXT_OBSERVED_M5',
        exit_rules=dict(TP=240,SL=180,TIME_EXIT=100,time_exit_basis='OBSERVED_M5_AND_REAL_EXECUTABLE_QUOTE',
            BUY_entry='ASK',SELL_entry='BID',BUY_exit='BID',SELL_exit='ASK'),
        acceptance_criteria=bindings.get('acceptance_criteria'),hypothesis_budget=4,
        pre_admission_review_hash=review_result['review_hash'],status=review_result['status'],
        training_authorization_status=review_result['training_authorization_status'],
        specific_training_request=None,dataset_admitted=False,training_authorized=False)
