"""Build a blocked PRE_TRAIN dossier from allowlisted metadata, never protected rows.

No MT5 API, scheduler mutation, training, scoring or scientific activation exists
here. Original contracts, captures and manifests are read-only. Unknown exposure
is a blocker, not an independent dataset. Live manifests are snapshotted once.
"""
import csv
import hashlib
import io
from importlib import metadata as import_metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

from .pretrain_contracts import STUDY_ID, DATASET_ID, FEATURES, chain, verify_chain, seal, temporal_dependencies
from .safety_gate import ROOT

PACKAGE = ROOT/'research/studies/us30cash_m5_native_pretrain_v1'
PARENT_HEAD = 'ee68187ef6c1921d8f7c27c839b38f152b6cca17'
DOMAIN = 'XMGlobalSC-MT5 5|US30Cash|NATIVE_LABELS'


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


def json_metadata(path):
    raw=path.read_bytes()  # caller supplies only allowlisted metadata paths
    return json.loads(raw.decode('utf-8-sig')),hashlib.sha256(raw).hexdigest()


def inventory(root):
    """Names and sizes only, no data file is opened or hashed."""
    groups={}
    for directory, dirs, files in os.walk(root/'outputs',followlinks=False):
        dirs[:]=[d for d in dirs if d.lower() not in
            ('terminal','.venv','venv','site-packages','webview','cache','nts_runtime') and
            not d.startswith('.') and not (Path(directory)/d).is_symlink()]
        for name in files:
            p=Path(directory)/name
            if p.is_symlink() or not name.lower().endswith(('.csv','.csv.gz','.parquet','.bin','.jsonl')):
                continue
            relative=p.relative_to(root).as_posix()
            group='/'.join(relative.split('/')[:3])
            item=groups.setdefault(group,dict(files=0,bytes=0,rows_opened=0,
                classification='QUARANTINED_OR_PREVIOUSLY_EXPOSED_NOT_INDEPENDENCE_EVIDENCE'))
            item['files']+=1
            item['bytes']+=p.stat().st_size
    expected=['outputs/master/master_manifest.json','outputs/splits/split_manifest.json',
              'outputs/future_validation_cohort/cohort_20261019/cohort_manifest.json']
    return dict(scope='THIS_REPOSITORY_OUTPUTS_FILE_METADATA_ONLY_TERMINAL_AND_DEPENDENCIES_EXCLUDED',
        groups=groups,expected_original_manifests={p:('PRESENT_NOT_OPENED' if (root/p).exists() else 'MISSING') for p in expected},
        independent_data_proven=False,protected_dataset_rows_opened=0)


def raw_metadata(path, expected_collector_sha=None):
    """Validate metadata chain, not raw tick/bar payloads or prospective completeness."""
    manifest,source_hash=json_metadata(path)
    if manifest['symbol']!='US30Cash' or manifest['server']!='XMGlobalSC-MT5 5' or manifest['kind'] not in ('historical','prospective') or manifest['archive_id']!=path.parent.name:
        raise ValueError('RAW_SOURCE_IDENTITY_MISMATCH')
    if expected_collector_sha is not None and manifest['collector_sha256']!=expected_collector_sha:
        raise ValueError('RAW_COLLECTOR_SOURCE_CHANGED')
    if any(manifest.get(k) is not False for k in ('scientific_acceptance','train_access_allowed','evaluation_authorized','maturity_eligible','live_trading')):
        raise ValueError('RAW_SCIENTIFIC_GATES_CHANGED')
    previous=None
    cursor=manifest['native_start_msc']
    windows=[]
    for entry in manifest['segments']:
        item=dict(entry)
        recorded=item.pop('entry_sha256')
        if seal(item)!=recorded or item['previous']!=previous or item['start_native_msc']!=cursor or item['end_native_msc']<=cursor:
            raise ValueError('RAW_METADATA_CHAIN_INVALID')
        for kind in ('ticks','bars'):
            asset=item[kind]
            if Path(asset['file']).name!=asset['file'] or type(asset['rows']) is not int or asset['rows']<0 or not re.fullmatch('[0-9a-f]{64}',asset['sha256']):
                raise ValueError('INVALID_RAW_ASSET_METADATA')
        windows.append(dict(start_native_msc=item['start_native_msc'],end_native_exclusive_msc=item['end_native_msc'],
            declared_ticks=item['ticks']['rows'],declared_bars=item['bars']['rows'],entry_sha256=recorded))
        previous,cursor=recorded,item['end_native_msc']
    if previous!=manifest['chain_head'] or cursor!=manifest['next_native_msc']:
        raise ValueError('RAW_METADATA_CURSOR_MISMATCH')
    return dict(archive_id=manifest['archive_id'],kind=manifest['kind'],server=manifest['server'],
        symbol=manifest['symbol'],source_sha256=source_hash,chain_head=previous,
        collector_sha256=manifest['collector_sha256'],start_native_msc=manifest['native_start_msc'],
        end_native_exclusive_msc=manifest['native_end_exclusive_msc'],observed_cursor_native_msc=cursor,
        declared_ticks=sum(w['declared_ticks'] for w in windows),declared_bars=sum(w['declared_bars'] for w in windows),
        metadata_chain='VERIFIED_LOCAL_SNAPSHOT_ONLY',raw_payload_integrity='NOT_RECHECKED_NO_PROTECTED_ROWS_OPENED',
        completeness='UNPROVEN_DO_NOT_INFER_FROM_QUERY_WINDOWS',windows=windows)


def diagnostic_signal_metadata(root):
    """Only IDs/cutoffs of the already-authorized fixed native diagnostic.

    This file is not a protected split. No feature, label or outcome is selected.
    Verify its already-published identity before reading identity metadata.
    """
    run='diag_fd4e5bf3d468'
    native_runs,_=json_metadata(root/'configs/pc_a_native_tester_evidence_20261030/native_runs.json')
    record=next(r for r in native_runs['runs'] if r['run_id']==run)
    name=run+'_stochastic_events.csv'
    path=root/'outputs/pc_a_certification/native_tester/runs'/run/name
    if digest(path)!=record['artifact_sha256'][name]:raise ValueError('DIAGNOSTIC_IDENTITY_CHANGED')
    with path.open(encoding='utf-8-sig',newline='') as stream:
        signals=[dict(signal_id=row['signal_id'],native_cutoff_msc=int(row['signal_time_msc'])) for row in csv.DictReader(stream)]
    if len(signals)!=28 or len({r['signal_id'] for r in signals})!=28:
        raise ValueError('DIAGNOSTIC_SIGNAL_UNIVERSE_CHANGED')
    return dict(source_run=run,source_sha256=record['artifact_sha256'][name],signals=signals,
                status='DIAGNOSTICALLY_EXPOSED_NOT_NEW_TRAIN_MEMBERSHIP',outcomes_computed=False)


def build(root=ROOT, package=PACKAGE):
    root,package=Path(root),Path(package)
    package.mkdir(parents=True,exist_ok=True)

    def write(name,value):
        path=package/name
        path.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
        return digest(path)

    inv=inventory(root)
    write('dataset_inventory.json',inv)
    raw=[raw_metadata(p,digest(root/'python/pc_a_raw_archive.py')) for p in sorted((root/'outputs/pc_a_raw_archive').glob('*/manifest.json'))]
    write('archive_windows.json',raw)
    signals=diagnostic_signal_metadata(root)
    write('known_exposed_signal_membership.json',signals)
    master_hash='e2c05a24551078efb584cc4732b796846f3b98793d21978522b36be141de59c1'
    freeze=root/'docs/DATASET_FREEZE.md'
    records=[dict(dataset_id='stochastic_master_v1',instrument='US30Cash',domain_id='LEGACY_SERVER_NATIVE_UNRECONCILED',
        source_sha256=master_hash,source_hash_basis='PUBLISHED_FREEZE_NOT_LOCALLY_REHASHED',
        evidence_path='docs/DATASET_FREEZE.md',evidence_sha256=digest(freeze),
        roles=['TRAIN_EXHAUSTED','DISCOVERY_VALIDATION_PROTECTED','FINAL_TEST_PROTECTED'],
        exposure='MASTER_CONTAINS_PROTECTED_TAIL_TRAIN_PREVIOUSLY_RESEARCHED',
        declared_native_date_range=['2023-12-20','2026-10-13_PARTIAL'],
        declared_signals=20422,declared_purged_train=12243,declared_purged_discovery=4077,
        start_native_msc=None,end_native_exclusive_msc=None,signal_ids=[],membership='MISSING_ORIGINAL_IDS',
        versions=['master_v1','schema3_quality_v1_related_not_equivalent_sources']),
        dict(dataset_id='legacy_quality_v1',instrument='US30Cash',domain_id='LEGACY_SERVER_NATIVE_UNRECONCILED',
        source_sha256=None,evidence_path='docs/INTRATRADE_RESEARCH_PROTOCOL.md',
        evidence_sha256=digest(root/'docs/INTRATRADE_RESEARCH_PROTOCOL.md'),
        roles=['TRAIN_EXHAUSTED','DISCOVERY_VALIDATION_PROTECTED'],exposure='17_HYPOTHESES_0_SURVIVORS_RECORDED_HISTORY_NOT_NEW_BUDGET',
        start_native_msc=None,end_native_exclusive_msc=None,signal_ids=[],membership='MISSING_ORIGINAL_IDS',
        inherited_train_membership_hash='4823eb1aa4ca08899ffcbcff957b4dfb726b30c9dd074a2c968efb1f133bb1c1',
        inherited_hash_basis='PUBLISHED_HYPOTHESIS_REGISTRY_NOT_RECOVERED_MEMBERSHIP',
        membership_reference_path='research/hypotheses/HYP-20261017-DYN-001.json',
        membership_reference_sha256=digest(root/'research/hypotheses/HYP-20261017-DYN-001.json')),
        dict(dataset_id='historical_holdout_unresolved',instrument='US30Cash',domain_id='UNKNOWN',source_sha256=None,
        roles=['HISTORICAL_HOLDOUT_PROTECTED'],exposure='PROTECTED_UNKNOWN_EXTENT_NOT_ASSERTED_VIEWED',
        evidence_path='CURRENT_USER_RESTRICTION',start_native_msc=None,end_native_exclusive_msc=None,
        signal_ids=[],membership='MISSING_UNKNOWN_PROTECTED_INTERVAL'),
        dict(dataset_id='us30cash_m5_future_20261019_v1',instrument='US30Cash',domain_id='DECLARED_UTC_NOT_RECONCILED_TO_XM_NATIVE',
        source_sha256=None,roles=['PROTECTED_PROSPECTIVE_COHORT'],exposure='RESERVED_NOT_AVAILABLE_FOR_TRAIN',
        evidence_path='docs/FUTURE_VALIDATION_PROTOCOL.md',evidence_sha256=digest(root/'docs/FUTURE_VALIDATION_PROTOCOL.md'),
        declared_start_utc='2026-10-19T00:00:00Z',start_native_msc=None,end_native_exclusive_msc=None,
        open_ended_reservation=True,signal_ids=[],membership='ORIGINAL_SEGMENTS_AND_START_MAPPING_MISSING')]
    for archive in raw:
        records.append(dict(dataset_id=archive['archive_id'],instrument=archive['symbol'],domain_id=DOMAIN,
            source_sha256=archive['source_sha256'],source_hash_basis='CURRENT_MANIFEST_SNAPSHOT_NOT_TICK_PAYLOAD_HASH',
            roles=['HISTORICAL_DIAGNOSTIC_EXPOSED'] if archive['kind']=='historical' else ['PROSPECTIVE_QUARANTINE_RESERVED'],
            exposure='NOT_INDEPENDENT_NEW_TRAIN',start_native_msc=archive['start_native_msc'],
            end_native_exclusive_msc=archive['end_native_exclusive_msc'],
            observed_cursor_native_msc=archive['observed_cursor_native_msc'],
            signal_ids=[s['signal_id'] for s in signals['signals']] if archive['kind']=='historical' else [],
            signal_membership_basis='SAME_DAY_DIAGNOSTIC_NOT_RAW_SIGNAL_CAPTURE' if archive['kind']=='historical' else 'NO_SIGNALS_GENERATED',
            window_index_sha256=seal(archive['windows']),metadata_chain=archive['metadata_chain'],
            independent_data=False,scientific_acceptance=False))
    native_runs,run_hash=json_metadata(root/'configs/pc_a_native_tester_evidence_20261030/native_runs.json')
    for record in native_runs['runs']:
        records.append(dict(dataset_id=record['run_id'],instrument='US30Cash',domain_id=DOMAIN,
            source_sha256=record['artifact_sha256'][record['run_id']+'_bar_quote_path.bin'],
            roles=['NATIVE_DIAGNOSTIC_EXPOSED'],exposure='SAME_HISTORICAL_DAY_NOT_INDEPENDENT_REDOWNLOAD',
            start_native_msc=1704153600000,end_native_exclusive_msc=1704240000000,
            signal_ids=[s['signal_id'] for s in signals['signals']],
            evidence_path='configs/pc_a_native_tester_evidence_20261030/native_runs.json',evidence_sha256=run_hash,
            versions=record['artifact_sha256'],scientific_acceptance=False))
    seen_runs={r['run_id'] for r in native_runs['runs']}
    for path in sorted((root/'outputs/pc_a_certification/native_tester/runs').glob('diag_*/run_manifest.json')):
        d,h=json_metadata(path)
        if d['run_id'] in seen_runs:continue
        if d['start']!='2024-01-02' or d['end']!='2024-01-02':
            raise ValueError('UNKNOWN_DIAGNOSTIC_INTERVAL_REQUIRES_REVIEW')
        records.append(dict(dataset_id=d['run_id'],instrument='US30Cash',domain_id=DOMAIN,
            source_sha256=d['artifacts'].get(d['run_id']+'_bar_quote_path.bin'),
            evidence_path=path.relative_to(root).as_posix(),evidence_sha256=h,
            roles=['NATIVE_DIAGNOSTIC_EXPOSED'],exposure='SAME_APPROVED_DAY_DIAGNOSTIC_NOT_NEW_TRAIN',
            start_native_msc=1704153600000,end_native_exclusive_msc=1704240000000,
            signal_ids=[s['signal_id'] for s in signals['signals']],versions=d['artifacts'],scientific_acceptance=False))
    write('research_registry_inventory.json',dict(
        files=[dict(path=p.relative_to(root).as_posix(),source_sha256=digest(p),
                    classification='REGISTERED_RESEARCH_EVIDENCE_NOT_UNUSED_DATA_OR_NEW_BUDGET')
               for pattern in ('hypotheses','hypotheses_v2','hypotheses_round2')
               for p in sorted((root/'research'/pattern).glob('*.json'))],
        outcome_fields_parsed=False,prior_result_summary='17_DYNAMIC_HYPOTHESES_0_SURVIVORS_AS_PREVIOUSLY_DOCUMENTED',
        fresh_budget_inferred=False))
    previous_ledger=subprocess.run(['git','show','HEAD:'+ (package/'exposure_ledger.json').relative_to(root).as_posix()],
        cwd=root,capture_output=True,check=False)
    previous_hash=hashlib.sha256(previous_ledger.stdout).hexdigest() if previous_ledger.returncode==0 else None
    ledger=dict(schema_version='exposure-ledger/1.0',study_id=STUDY_ID,entries=chain(records),
        previous_published_ledger_sha256=previous_hash,
        previous_version_retained_by='GIT_HISTORY_NEVER_REPLACE_PUBLISHED_SNAPSHOT_WITHOUT_NORMAL_COMMIT',
        completeness_verified=False,missing=['ORIGINAL_MASTER_SPLIT_AND_SIGNAL_MEMBERSHIPS',
            'HISTORICAL_HOLDOUT_EXACT_RESERVATION','PROSPECTIVE_ROLE_END_OR_NONOVERLAP_ATTESTATION',
            'RECONCILED_COMPARABLE_TIME_DOMAINS','COMPLETE_PRIOR_EXPOSURE_LEDGER_OUTSIDE_LOCAL_METADATA'],
        protected_dataset_rows_opened=0,outcomes_scored=False,independent_data_proven=False)
    ledger['chain_head']=verify_chain(ledger['entries'])
    ledger_hash=write('exposure_ledger.json',ledger)
    membership=dict(dataset_id=DATASET_ID,status='UNALLOCATED_NO_REAL_DATA',
        source_dataset_sha256=None,signal_ids=[],intervals=[],warmup_intervals=[],label_intervals=[],
        source_segments=[],zero_rows_is_not_a_certified_dataset=True,
        legacy_membership='PARTIAL_KNOWN_DIAGNOSTIC_IDS_ONLY',
        protected_ids_unknown=True,independent_membership_verified=False)
    membership_hash=write('dataset_membership.json',membership)
    dependencies_hash=write('temporal_dependencies.json',temporal_dependencies())
    versions={}
    for distribution in ('numpy','pandas','scikit-learn','MetaTrader5'):
        try:versions[distribution]=import_metadata.version(distribution)
        except import_metadata.PackageNotFoundError:versions[distribution]='MISSING_NOT_INSTALLED_AUTOMATICALLY'
    write('environment_versions.json',dict(python=sys.version.split()[0],packages=versions,
        packages_imported_for_training=False,dependency_install_performed=False,low_memory_mode=True))
    availability,availability_hash=json_metadata(root/'research/native_methodology_v1/evidence/availability.json')
    audit=[]
    for feature in FEATURES:
        record=next(r for r in availability['fields'] if r['table']=='entry' and r['column']==feature)
        if record['semantic_disposition']!='PASS_SYNTHETIC_NATIVE_PREFIX_ONLY':raise ValueError('FEATURE_DIAGNOSTIC_NOT_PASSED')
        audit.append(dict(feature=feature,synthetic_native_prefix='PASS_RETAINED_NOT_RERUN',
            historical_data_vintage='UNVERIFIED',new_dataset_feature_bytes='MISSING',
            new_dataset_warmup_source_and_seed='UNBOUND',training_admitted=False))
    write('feature_causality.json',dict(features=audit,evidence_sha256=availability_hash,
        status='PARTIAL_SYNTHETIC_PROOF_REAL_STUDY_INPUTS_MISSING',
        producer_sha256=digest(root/'mt5/StochasticBarDecisionResearchEA.mq5'),
        new_native_probe_run=False,global_causal_audit='FAIL_UNCHANGED'))
    whitelist=dict(schema_version='native-study-whitelist/1.0',study_id=STUDY_ID,
        features=list(FEATURES),models=[dict(family='LOGISTIC_REGRESSION_L2',separate_original_sides=['BUY','SELL'],
        C=1,solver='lbfgs',max_iter=1000,class_weight=None,seed=20261030)],
        forbidden=['UTC','NY_SESSION','IDS','TIMESTAMPS','ENTRY_QUOTES','SPREAD_AT_ENTRY','TARGETS','FUTURE_OUTCOMES'],
        definitions_sha256=dependencies_hash,training_authorized=False,
        missing_policy='NO_IMPUTATION_NO_FIT_WITH_MISSING_PREDICTORS_FIXED_FOLLOW_FALLBACK_REPORT_ALL')
    whitelist_hash=write('feature_model_whitelist.json',whitelist)
    plan=dict(status='PREPARED_NOT_ACTIVE',study_id=STUDY_ID,dataset_id=DATASET_ID,
        actual_start=None,activation_session=None,activation_sequence=None,
        first_complete_native_bar=None,activate_scientific_cohort=False,
        existing_read_only_sources=['StochasticGPTLab_PC_A_ProspectiveUTC_v1','StochasticGPTLab_PC_A_RawQuarantine_v1'],
        collector_source_sha256=digest(root/'python/pc_a_raw_archive.py'),
        observer_role='RAW_CALLBACKS_QUARANTINED_NOT_EXHAUSTIVE_FEED_PROOF',
        current_archives_adopted=False,old_cohorts_mixed=False,historical_backfill_allowed=False,
        boundary='NEW_REAL_SESSION_SEQUENCE_AND_FIRST_COMPLETE_BAR_AFTER_SEPARATELY_AUTHORIZED_ROLE_ALLOCATION',
        warmup='NEW_POST_START_ONLY_MINIMUM_350_CLOSED_BARS_PLUS_BOUND_NATIVE_INDICATOR_AND_HA_SEEDS',
        acquisition_stop='FIRST_800_UNFILTERED_BASE_SIGNALS_AFTER_WARMUP_THEN_100_OBSERVED_BARS_FOR_BOTH_LABEL_HORIZONS',
        stop_uses_outcomes=False,restart='CLOSE_SEGMENT_AND_REATTEST_CONTINUITY_NO_BACKFILL',
        gaps='PRESERVE_AND_QUARANTINE_UNEXPLAINED_LOSS_NO_FILL',
        requirements=['EXCLUSIVE_NONOVERLAPPING_ROLE_RESERVATION',
            'POST_START_NATIVE_BARS_AND_FEATURES_CAPTURED_OR_ADMITTED_CAUSAL_REPLAY_WITH_VINTAGE_LIMITATION',
            'ISOLATED_TESTER_HISTORY_WITH_NO_PROTECTED_SEED_INPUTS',
            'OBSERVED_CALLBACKS_NOT_ASSUMED_ALL_BROKER_TICKS',
            'REAL_SOURCE_IDENTITY_HASHES_MONOTONIC_SEQUENCE_RESTART_AND_RECEIPT_CHAIN'],
        new_task_installed=False,existing_tasks_modified=False,training_authorized=False)
    write('prospective_collection_plan.json',plan)
    write('coverage_audit.json',dict(status='BLOCKED_NO_INDEPENDENT_DATASET',
        independent_ticks=None,independent_bars=None,expected_session_calendar='NOT_CERTIFIED',
        raw_manifest_counts=[{k:a[k] for k in ('archive_id','declared_ticks','declared_bars','observed_cursor_native_msc')} for a in raw],
        original_native_day='RETAINED_PASS_79211_TICKS_1376_M1_276_M5_NOT_INDEPENDENT',
        query_window_chain='METADATA_CONTIGUITY_NOT_MARKET_COVERAGE',
        protected_rows_opened=0,independence='NOT_PROVEN'))
    budget=dict(hypothesis_families=1,hyperparameter_configurations=1,
        separate_side_estimators=2,walk_forward_folds=4,max_planned_fold_fits=8,
        max_scientific_launches=1,final_full_data_fit=0,optimization_searches=0,
        actual_fits_authorized=0,actual_scoring_authorized=0,
        new_TRAIN_budget_activated=False,exhausted_TRAIN_reopened=False)
    protocol_path=package/'PROTOCOL_ES.md'
    if not protocol_path.exists():raise ValueError('STUDY_PROTOCOL_MUST_BE_WRITTEN_BEFORE_BUILD')
    protocol_hash=digest(protocol_path)
    Path(str(protocol_path)+'.sha256').write_text(protocol_hash+'  PROTOCOL_ES.md\n',encoding='ascii',newline='\n')
    code_files=['controller/pretrain_contracts.py','controller/pretrain_package.py',
        'controller/native_study_design.py','controller/native_independence.py','controller/native_feature_diagnostic.py',
        'tools/pretrain_study_review.py','tests/test_pretrain_contracts.py','tests/test_pretrain_package.py',
        'mt5/StochasticBarDecisionResearchEA.mq5','mt5/ResearchCore.mqh','mt5/HeikinAshiCore.mqh']
    code_hashes={name:digest(root/name) for name in code_files}
    write('code_source_hashes.json',dict(reviewed_base_head=PARENT_HEAD,files=code_hashes,
        implementation_commit='ENCLOSING_GIT_COMMIT_AND_PUBLICATION_RECEIPT',
        code_set_sha256=seal(code_hashes)))
    criteria=dict(required_evidence=['INDEPENDENT_COMPLETE_MEMBERSHIP_AND_EXPOSURE_LEDGER',
        'NO_PROTECTED_OR_PREVIOUSLY_EXPOSED_DEPENDENCIES',
        'HASH_VERIFIED_DATASET_AND_NATIVE_SOURCE_IDENTITY',
        'CLOSED_FEATURE_AVAILABILITY_AND_BOUND_POST_START_RECURSIVE_SEEDS',
        'VERIFIED_COVERAGE_NO_FABRICATED_BARS_OR_PROSPECTIVE_BACKFILL',
        'PREREGISTERED_STATISTICAL_GATES_AND_SINGLE_FAMILY_BUDGET',
        'EXPLICIT_HASH_BOUND_NEW_STUDY_AUTHORIZATION_BEFORE_ANY_FIT'],
        minimum_evaluation_signals=200,minimum_each_side=80,minimum_evaluable_folds_per_side=3,
        minimum_positive_fold_fraction_each_comparison=0.7,maximum_positive_effect_share_one_fold=0.5,
        maximum_drawdown_ratio_to_each_baseline=1.2,primary_comparisons=4,
        one_sided_bootstrap_lower_confidence=0.9875,required_lower_bound='STRICTLY_GREATER_THAN_ZERO',
        bootstrap_resamples=10000,signal_and_451_observed_bar_block_checks_required=True,
        future_tolerance_milliseconds=0,invalid_required_quotes_allowed=0,
        protected_dependency_overlap_allowed=0,unknown_seed_or_coverage_action='NOT_READY_OR_QUARANTINED',
        statistical_failure='TERMINAL_NO_RETUNING_OR_PERIOD_EXTENSION')
    request=dict(STUDY_ID=STUDY_ID,DATASET_ID=DATASET_ID,DATASET_HASH=None,
        EXPOSURE_LEDGER_HASH=ledger_hash,DATASET_MEMBERSHIP_HASH=membership_hash,
        FEATURE_WHITELIST_HASH=whitelist_hash,PROTOCOL_HASH=protocol_hash,
        CODE_HEAD=None,REVIEWED_BASE_HEAD=PARENT_HEAD,CODE_SOURCE_SET_HASH=seal(code_hashes),
        CODE_HEAD_BINDING='RESOLVED_IN_POST_COMMIT_PUBLICATION_RECEIPT_NOT_BASE_HEAD',
        TRAINING_BUDGET=budget,ACCEPTANCE_CRITERIA=criteria,
        mode='PRE_TRAIN',authorization_requested=False,authorization_ready=False,
        actual_training_authorized=False,actual_scoring_authorized=False,
        reason='NO_VERIFIABLE_INDEPENDENT_DATASET_AND_INCOMPLETE_EXPOSURE_HISTORY')
    write('scientific_authorization_package.json',request)
    gates=dict(NEW_STUDY_PACKAGE='PREPARED_INCOMPLETE_EVIDENCE_PRE_TRAIN',
        INDEPENDENT_DATA_AVAILABLE=False,EXPOSURE_LEDGER='PARTIAL_CHAIN_VERIFIED_METADATA_ONLY',
        DATASET_MEMBERSHIP='UNALLOCATED_KNOWN_EXPOSED_IDS_SEPARATELY_RECORDED',
        FEATURE_CAUSALITY='PARTIAL_SYNTHETIC_PROOF_NEW_DATA_NOT_VERIFIED',
        TEMPORAL_DEPENDENCIES='PREPARED_ALL_6_FEATURES_RECURSIVE_SEEDS_REQUIRED',
        COVERAGE_AUDIT='BLOCKED_NO_NEW_DATASET',STATISTICAL_PROTOCOL='DESIGN_PREREGISTERED_NO_DATA_ROLE_ACTIVATION',
        FEATURE_WHITELIST='FROZEN_HASH_BOUND_NOT_TRAINING_ADMISSION',TRAINING_BUDGET=budget,
        PRE_TRAIN_GATES='BLOCKED',SCIENTIFIC_AUTHORIZATION_REQUIRED='LATER_ONLY_AFTER_COMPLETE_DATA_PACKAGE',
        HARD_BLOCKER=ledger['missing']+['NO_INDEPENDENT_DATASET','UNBOUND_POST_START_RECURSIVE_FEATURE_SEEDS'],
        MANUAL_ACTION_REQUIRED='NONE_AT_THIS_PREPARATION_STAGE',CAUSAL_AUDIT='FAIL_GLOBAL_UNCHANGED',
        DISCOVERY_VALIDATION='BLOCKED',HISTORICAL_HOLDOUT='BLOCKED',FINAL_TEST='LOCKED',
        DEMO='DISABLED',LIVE_TRADING=False,training_authorized=False,scoring_authorized=False,
        NEXT_STATE='PRE_TRAIN_WAIT_FOR_VERIFIABLE_INDEPENDENT_DATA_AND_EXCLUSIVE_ROLE_BOUNDARY')
    write('pre_train_gates.json',gates)
    return gates


def verify_package(package=PACKAGE):
    """Verify published PRE_TRAIN metadata, never grant scientific authorization."""
    package=Path(package)
    index,_=json_metadata(package/'package_hashes.json')
    if seal(index['files'])!=index['root_sha256']:
        raise ValueError('PACKAGE_INDEX_CHANGED')
    for name,expected in index['files'].items():
        if Path(name).name!=name or (package/name).is_symlink() or digest(package/name)!=expected:
            raise ValueError('PACKAGE_FILE_CHANGED')
    ledger,_=json_metadata(package/'exposure_ledger.json')
    verify_chain(ledger['entries'],ledger['chain_head'])
    request,_=json_metadata(package/'scientific_authorization_package.json')
    if any(request.get(k) is not False for k in ('authorization_requested','authorization_ready','actual_training_authorized','actual_scoring_authorized')):
        raise ValueError('PRE_TRAIN_AUTHORITY_EXCEEDED')
    return dict(integrity='PASS_METADATA_PACKAGE_ONLY',mode='PRE_TRAIN',
        independent_dataset_verified=False,scientific_authorization_requested=False,
        training_authorized=False,scoring_authorized=False)


if __name__=='__main__':
    print(json.dumps(build(),ensure_ascii=False,indent=2))
