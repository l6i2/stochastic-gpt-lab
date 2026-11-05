"""Prepare a separate proposed study and exercise metadata-only causal planning."""
import json
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from controller.authorized_capture import sha
from controller.pretrain_contracts import FEATURES, dependency_preflight, seal
from controller.native_study_design import fold_plan
from controller.training_admission_gate import authorize_execution


def prepare():
    old=ROOT/'research/studies/us30cash_m5_native_pretrain_v1'
    target=ROOT/'research/studies/six_alternatives_resolution/proposed_study'
    target.mkdir(parents=True,exist_ok=False)
    def write(name,value):
        (target/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n',encoding='utf8',newline='\n')
    authorization=json.loads((old/'scientific_authorization_package.json').read_text())
    spec=dict(STUDY_ID='US30CASH_M5_NATIVE_OBSERVATIONS_20261105_PROPOSED',
        PRODUCTOR_ID='native_database_observations_v2_proposed',
        DATASET_ID='us30cash_native_observations_20261105_reserved',DATASET_HASH=None,
        mode='PROPOSED_NOT_ACTIVE',activation_utc=None,first_observation=None,
        source='NEW_POST_AUTHORIZATION_NATIVE_DATABASE_OBSERVATIONS_WITH_EXPLICIT_RETRIEVAL_PROVENANCE',
        experimental_capture='outputs/six_alternatives_experiment/current.json',
        adopt_existing_trial=False,original_producer_replaced=False,
        strategy=dict(symbol='US30Cash',timeframe='M5',K=5,D=3,Slowing=3,levels=[20,80],
                      sides=['BUY','SELL'],modes=['FOLLOW','INVERT'],TP=240,SL=180,TIME_EXIT=100,skip=False),
        minimums=dict(own_m5=350,consecutive_signals=800,post_m5=100,evaluable=200,BUY=80,SELL=80,folds_each_side=3),
        evidence_required=['FORWARD_ROLE_ASSIGNMENT_AND_NONOVERLAP','OWN_RECURSIVE_SEEDS','TWO_EXACT_DATABASE_VIEWS',
            'NATIVE_M1_M5_PARITY','FIRST_OBSERVATION_MONOTONIC_PROVENANCE','NATIVE_PREFIX_FEATURE_AVAILABILITY',
            'KNOWN_SESSION_CALENDAR_FOR_ANY_SESSION_BRIDGE','SEALED_MEMBERSHIP_AND_DATASET','SPECIFIC_SCIENTIFIC_GRANT'],
        temporal_claim='NATIVE_REPLAY_CAUSALITY_AND_OBSERVED_AVAILABILITY',
        generation_utc_claim=False,live_execution_availability_claim=False,
        rejection=['UNKNOWN_COVERAGE','REQUERY_CHANGED','SESSION_NOT_ATTESTED','DISCONNECTION','SUSPEND','CLOCK_DISCONTINUITY','UNKNOWN_ROLE_OVERLAP'],
        protected_sets=dict(DISCOVERY_VALIDATION='BLOCKED',HISTORICAL_HOLDOUT='LOCKED',FINAL_TEST='LOCKED'),
        training_authorized=False,scoring_authorized=False,DEMO='DISABLED',LIVE_TRADING=False)
    write('study.json',spec)
    whitelist=json.loads((old/'feature_model_whitelist.json').read_text())
    whitelist['study_id']=spec['STUDY_ID']
    write('feature_whitelist.json',whitelist)
    write('statistical_protocol.json',dict(status='PROPOSED',
        reference_protocol_sha256=sha(old/'PROTOCOL_ES.md'),
        comparisons=['BUY_vs_FOLLOW_ALWAYS','BUY_vs_INVERT_ALWAYS','SELL_vs_FOLLOW_ALWAYS','SELL_vs_INVERT_ALWAYS'],
        null_hypothesis='PAIRED_MEAN_IMPROVEMENT_LE_ZERO',
        validation='FOUR_CHRONOLOGICAL_PURGED_WALK_FORWARD_FOLDS',
        acceptance=authorization['ACCEPTANCE_CRITERIA'],budget=authorization['TRAINING_BUDGET'],
        acquisition_stop='FIRST_800_BASE_SIGNALS_AFTER_350_OWN_BARS_THEN_100_POST_BARS',
        no_retuning=True,terminal_attempt=True))
    observations=[dict(feature=f,oldest_source_index=0,last_closed_index=349,
        decision_arrival_index=350,ready_stage=1,decision_stage=2,closed_bars=350,seed_index=0) for f in FEATURES]
    valid=dependency_preflight(observations,0)
    corrupt=[dict(row) for row in observations];corrupt[0]['last_closed_index']=350
    try:
        dependency_preflight(corrupt,0)
        raise AssertionError('FUTURE_FEATURE_ACCEPTED')
    except ValueError:
        future_rejected=True
    signals=[dict(signal_id='SYNTHETIC_'+str(i),side='BUY' if i%2 else 'SELL',decision=i*20,
        arrival_index=i,follow_exit=i*20+100,invert_exit=i*20+100) for i in range(800)]
    plan=fold_plan(signals)
    try:
        authorize_execution(dict(study_id=spec['STUDY_ID']),ROOT)
        raise AssertionError('UNAUTHORIZED_STUDY_ACCEPTED')
    except PermissionError:
        execution_refused=True
    write('synthetic_validation.json',dict(synthetic=True,rows_from_protected_sets=0,
        dependency_preflight=valid,future_feature_rejected=future_rejected,execution_without_grant_refused=execution_refused,
        folds=[dict(fold=f['fold'],train_count=len(f['train_ids']),evaluation_count=len(f['evaluation_ids']),
                   purged_train=f['purged_or_censored_train'],evaluation_sides=f['evaluation_sides']) for f in plan['folds']],
        actual_fits=0,actual_scoring=0))
    hashes={p.name:sha(p) for p in target.iterdir() if p.is_file()}
    write('hashes.json',dict(files=hashes,root_sha256=seal(hashes)))
    return spec


def verify(folder=None):
    folder=Path(folder) if folder else ROOT/'research/studies/six_alternatives_resolution/proposed_study'
    index=json.loads((folder/'hashes.json').read_text())
    if seal(index['files'])!=index['root_sha256']:
        raise ValueError('PROPOSED_PACKAGE_INDEX_CHANGED')
    actual={p.name for p in folder.iterdir() if p.is_file() and p.name!='hashes.json'}
    if set(index['files'])!=actual:
        raise ValueError('UNSEALED_PROPOSAL_FILE')
    for name,digest in index['files'].items():
        if Path(name).name!=name or sha(folder/name)!=digest:
            raise ValueError('PROPOSED_PACKAGE_FILE_CHANGED')
    study=json.loads((folder/'study.json').read_text())
    if study['minimums']!=dict(own_m5=350,consecutive_signals=800,post_m5=100,evaluable=200,BUY=80,SELL=80,folds_each_side=3):
        raise ValueError('PROPOSED_THRESHOLDS_CHANGED')
    if study['mode']!='PROPOSED_NOT_ACTIVE' or study['DATASET_HASH'] is not None or study['activation_utc'] is not None or study['training_authorized']:
        raise ValueError('PROPOSED_STUDY_SCOPE_CHANGED')
    expected_strategy=dict(symbol='US30Cash',timeframe='M5',K=5,D=3,Slowing=3,levels=[20,80],
        sides=['BUY','SELL'],modes=['FOLLOW','INVERT'],TP=240,SL=180,TIME_EXIT=100,skip=False)
    if study['strategy']!=expected_strategy or study['scoring_authorized'] or study['LIVE_TRADING']:
        raise ValueError('FROZEN_STRATEGY_OR_PERMISSION_CHANGED')
    whitelist=json.loads((folder/'feature_whitelist.json').read_text())
    if whitelist['features']!=list(FEATURES) or whitelist['training_authorized']:
        raise ValueError('WHITELIST_SCOPE_CHANGED')
    return dict(status='VERIFIED_PROPOSAL_ONLY',root_sha256=index['root_sha256'],training_authorized=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    print(json.dumps(verify() if args.verify else prepare(),indent=2))
