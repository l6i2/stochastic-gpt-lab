"""Readiness review and bounded observational smoke, never scientific collection.

Default reuses captured evidence. --observational-smoke tails only new native
callbacks for at most 18 seconds; no MT5 attach, account API or history query.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import time
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'python'))
from controller.isolated_observation import Observation,eof_anchor,host_clock
from controller.pretrain_contracts import canonical,seal
from controller.pretrain_package import verify_package,digest

BASE=ROOT/'outputs/pc_a_collection_readiness'
REPORT=ROOT/'research/studies/us30cash_m5_native_collection_readiness_v1'
NATIVE=Path.home()/'AppData/Roaming/MetaQuotes/Terminal/20C285FE08971A9A2E814AAC44AFC9D2/MQL5/Files/ResearchDiagnostics/ProspectiveUTC'


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')


def observational_smoke():
    candidates=list(NATIVE.glob('pc_a_prospective_utc_v1_*.jsonl'))
    if not candidates:raise ValueError('NATIVE_SOURCE_MISSING')
    source=max(candidates,key=lambda p:p.stat().st_mtime_ns)
    code_hashes={n:digest(ROOT/n) for n in ('mt5/ProspectiveUtcObserver.mq5','python/pc_a_raw_archive.py','tools/prospective_utc_station.py',
        'controller/isolated_observation.py','tools/collection_readiness_review.py')}
    anchor=eof_anchor(source)
    start=host_clock()
    obj=Observation.create(BASE/'observations',source,anchor,start)
    folder=obj.folder
    deadline=time.monotonic()+18
    try:
        while time.monotonic()<deadline and obj.state['source_records']<2:
            obj.pump();time.sleep(0.25)
        first_state=dict(obj.state)
    finally:obj.close()
    resumed=Observation.resume(folder,host_clock())
    try:
        same_state=resumed.state==first_state
        resumed.pump()
        final_state=dict(resumed.state)
    finally:resumed.close()
    if any(digest(ROOT/n)!=h for n,h in code_hashes.items()):raise ValueError('EXISTING_OBSERVER_CODE_CHANGED')
    receipt=dict(capture_id=obj.manifest['capture_id'],mode=obj.manifest['mode'],
        status='PASS_NEW_RECORDS_ONLY_OBSERVATIONAL_SMOKE' if final_state['source_records'] else 'NO_NEW_RECORDS_OBSERVED',
        relative_folder=folder.relative_to(ROOT).as_posix(),actual_start_host_clock=start,
        source_anchor={k:v for k,v in anchor.items() if k!='source_path'},
        no_old_prefix_payloads_adopted=True,post_cut_tick_callbacks=final_state['tick_callbacks'],
        post_cut_heartbeats=final_state['heartbeat_records'],source_records=final_state['source_records'],
        checkpoint_restart_exact=same_state,manifest_sha256=digest(folder/'manifest.json'),
        journal_sha256=digest(folder/'journal.jsonl'),checkpoint_sha256=digest(folder/'checkpoint.json'),
        chain_head=final_state['chain_head'],observer_code_hashes_unchanged=code_hashes,
        free_storage_bytes=shutil.disk_usage(BASE).free,scientific_collection_started=False,
        scientific_role_reserved=False,scientific_admission=False,independent_dataset_verified=False,
        quote_callback_live_smoke='OBSERVED' if final_state['tick_callbacks'] else 'NOT_OBSERVED_THIS_BOUNDED_WINDOW',
        event_utc_mapping='UNVERIFIED',active_collection_task_installed=False,
        continuous_collection_started=False,training_authorized=False,scoring_authorized=False)
    write(BASE/'latest_observation.json',receipt)
    return receipt


def review(smoke=False):
    from local_finalize import verify_source_manifest
    verify_source_manifest(ROOT/'configs/pc_a_source_hashes_20261030_v25.json')
    verify_package()
    receipt=observational_smoke() if smoke else json.loads((BASE/'latest_observation.json').read_text())
    folder=ROOT/receipt['relative_folder']
    for name in ('manifest','journal','checkpoint'):
        filename={'manifest':'manifest.json','journal':'journal.jsonl','checkpoint':'checkpoint.json'}[name]
        if digest(folder/filename)!=receipt[name+'_sha256']:raise ValueError('OBSERVATIONAL_EVIDENCE_CHANGED')
    patterns=['test_isolated_observation.py','test_pretrain_contracts.py','test_pretrain_package.py',
              'test_native_independence.py','test_native_study_design.py']
    suite=unittest.TestSuite()
    for pattern in patterns:
        suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern))
    transcript=io.StringIO()
    result=unittest.TextTestRunner(stream=transcript,verbosity=2).run(suite)
    write(REPORT/'validation.json',dict(tests_run=result.testsRun,failures=len(result.failures),
        errors=len(result.errors),skipped=len(result.skipped),patterns=patterns,transcript=transcript.getvalue()))
    if not result.wasSuccessful():raise SystemExit(1)
    write(REPORT/'observational_smoke.json',receipt)
    installed=NATIVE.parents[2]/'Experts/ResearchDiagnostics/ProspectiveUtcObserver.mq5'
    prior=json.loads((ROOT/'configs/pc_a_callback_write_fix_evidence_20261029/deployment.json').read_text())['observer']
    actual_source=digest(installed);actual_binary=digest(installed.with_suffix('.ex5'))
    if actual_source!=prior['source_sha256'] or actual_binary!=prior['binary_sha256']:
        raise ValueError('INSTALLED_OBSERVER_IDENTITY_CHANGED_REVIEW_REQUIRED')
    native_source=(ROOT/'mt5/ProspectiveUtcObserver.mq5').read_text()
    if any(name+'(' in native_source for name in ('CopyTicks','CopyTicksRange','CopyRates','OrderSend','OrderSendAsync')):
        raise ValueError('EXISTING_OBSERVER_NOT_CALLBACK_ONLY')
    write(REPORT/'source_and_storage_audit.json',dict(installed_observer_source_sha256=actual_source,
        installed_observer_ex5_sha256=actual_binary,prior_published_identity_match=True,
        source_startup_guards='PINNED_SYMBOL_SERVER_DEMO_AND_DATA_DIRECTORY_AT_ONINIT',
        receiver_calls='TAIL_NEW_JSONL_ONLY_NO_MT5_API_OR_HISTORICAL_QUERY',
        storage_root='outputs/pc_a_collection_readiness/observations/<NEW_UUID>',
        scientific_dataset_root_reserved='outputs/new_native_studies/us30cash_m5_native_20261030_01/<FUTURE_CAPTURE_ID>',
        shared_with_protected_datasets=False,old_source_files_opened_write=False,
        free_storage_bytes_at_smoke=receipt['free_storage_bytes'],flush='FLUSH_FSYNC_THEN_ATOMIC_CHECKPOINT',
        crash_recovery='COMPLETE_ORPHAN_ROWS_RECOVERED_PARTIAL_ROWS_PRESERVED_AND_BLOCKED',
        independent_failure_domain_backup_verified=False,
        host_receipt_label_ecuador=datetime.fromisoformat(receipt['actual_start_host_clock']['host_utc_label']).astimezone(ZoneInfo('America/Guayaquil')).isoformat(),
        displayed_time_is_host_derived_not_UTC_attestation=True,
        constant_native_fields_not_independent_broker_generation_attestation=True))
    contracts=[('research/native_methodology_v1/adoption.json','cohort_activation_authorized',False),
        ('research/studies/us30cash_m5_native_pretrain_v1/prospective_collection_plan.json','activate_scientific_cohort',False),
        ('research/studies/us30cash_m5_native_pretrain_v1/scientific_authorization_package.json','actual_training_authorized',False)]
    audit=[]
    for path,key,expected in contracts:
        value=json.loads((ROOT/path).read_text())
        if value[key] is not expected:raise ValueError('SCIENTIFIC_AUTHORITY_CHANGED')
        audit.append(dict(path=path,sha256=digest(ROOT/path),field=key,value=value[key]))
    protocol=ROOT/'research/studies/us30cash_m5_native_pretrain_v1/PROTOCOL_ES.md'
    audit.append(dict(path=protocol.relative_to(ROOT).as_posix(),sha256=digest(protocol),
        exact_clause='Requiere inicio real posterior a una asignación de rol exclusiva autorizada',
        scope='SCIENTIFIC_STUDY_ROLE_ALLOCATION_NOT_GENERIC_READ_ONLY_OBSERVATION'))
    write(REPORT/'authority_review.json',dict(evidence=audit,
        observational_capture_permitted_by='CURRENT_USER_ITEM_11_OBSERVATIONAL_QUARANTINE_ONLY',
        scientific_role_allocation_requires_explicit_authorization=True,
        old_cohort_reservation_not_silently_closed=True,
        protected_membership_not_proven_by_permission=True,
        frozen_UTC_cohort_rules_unchanged=True))
    ledger=ROOT/'research/studies/us30cash_m5_native_pretrain_v1/exposure_ledger.json'
    dependencies=ROOT/'research/studies/us30cash_m5_native_pretrain_v1/temporal_dependencies.json'
    required=['NEW_EXCLUSIVE_PROSPECTIVE_ROLE_ALLOCATION_AUTHORIZATION',
        'RESOLVE_OPEN_PROTECTED_PROSPECTIVE_RESERVATION_WITHOUT_RELABELLING_PRIOR_DATA',
        'RECOVER_OR_INDEPENDENTLY_ATTEST_MISSING_PROTECTED_MEMBERSHIP_BOUNDARIES',
        'REAL_POST_START_FEATURE_CAPTURE_AND_NATIVE_INITIALIZATION_PROOF',
        'NATIVE_CALLBACK_COMPLETENESS_AND_HISTORICAL_CLOCK_LIMITS_REMAIN_UNVERIFIED']
    request=dict(kind='COLLECTION_ROLE_AUTHORIZATION_REQUEST_ONLY_NOT_TRAINING',
        study_id='US30CASH_M5_NATIVE_20261030_01',protocol_sha256=digest(protocol),
        exposure_ledger_sha256=digest(ledger),requested=True,authorization_granted=False,
        scope='FORWARD_ONLY_NEW_CAPTURE_AND_EXCLUSIVE_PROVISIONAL_STUDY_RESERVATION',
        does_not_authorize=['DATASET_ADMISSION','TRAINING','SCORING','HOLDOUT_ACCESS','DEMO','ORDERS'],
        actual_start_to_allocate_only_after_authorization=True,existing_observers_to_modify=False,
        protected_prior_segments_remain_sealed=True,unresolved_membership_still_blocks_admission=True,
        scientific_consequence='NO_FURTHER_SCIENTIFIC_ACCRUAL_TO_OLD_COHORT_FROM_NEW_BOUNDARY_ITS_FROZEN_MATURITY_RULES_NOT_RELAXED',
        exact_request='Autorizo únicamente una nueva captura read-only y una reserva prospectiva provisional exclusiva para US30CASH_M5_NATIVE_20261030_01, desde un identificador y frontera real posteriores a esta aprobación. Autorizo cerrar, solo para nuevas incorporaciones desde esa frontera, la reserva de la cohorte us30cash_m5_future_20261019_v1; sus datos previos y contratos quedan sellados y sin modificaciones. Los observadores anteriores continúan sin cambios como archivos observacionales en cuarentena; no se heredan sus segmentos, warmup, señales ni labels. Esta autorización no certifica independencia ni admite el dataset y no permite entrenamiento, scoring, acceso a conjuntos protegidos, DEMO u órdenes. Cualquier incompatibilidad o límite de membership no demostrado mantiene la captura en cuarentena y bloquea su admisión.')
    write(REPORT/'collection_authorization_request.json',request)
    readiness=dict(NEW_STUDY_READINESS='TECHNICAL_PREPARATION_VERIFIED_SCIENTIFIC_START_BLOCKED',
        COLLECTION_AUTHORIZATION_REQUIRED='YES_FOR_EXCLUSIVE_STUDY_ROLE_NO_FOR_PURE_OBSERVATION',
        INDEPENDENT_DATA_MEMBERSHIP='UNVERIFIED_PROTECTED_BOUNDARIES_AND_RESERVATIONS_INCOMPLETE',
        NO_BACKFILL_PROOF='PASS_SYNTHETIC_AND_SCOPED_POST_EOF_OBSERVATIONAL_SMOKE',
        NEW_COLLECTOR_ISOLATION='PASS_UNIQUE_DIAGNOSTIC_OBSERVATION_DIRECTORY_NO_OLD_WRITES',
        CAUSAL_FEATURE_READINESS='PASS_SYNTHETIC_ONLY_REAL_NATIVE_FEATURE_CAPTURE_NOT_READY',
        CLOCK_EVIDENCE='MONOTONIC_BOOT_AND_HOST_RECEIPT_RECORDED_UTC_EVENT_MAPPING_UNVERIFIED',
        DATASET_ADMISSION='BLOCKED',DATASET_HASH=None,TRAINING_READINESS='BLOCKED',
        HARD_BLOCKER=required,MANUAL_ACTION_REQUIRED='ONE_EXPLICIT_SCIENTIFIC_ROLE_ALLOCATION_DECISION',
        NEXT_STATE='WAITING_COLLECTION_ROLE_AUTHORIZATION_NO_SCIENTIFIC_CAPTURE_STARTED',
        CAUSAL_AUDIT='FAIL_GLOBAL_UNCHANGED',DISCOVERY_VALIDATION='BLOCKED',
        HISTORICAL_HOLDOUT='BLOCKED',FINAL_TEST='LOCKED',DEMO='DISABLED',LIVE_TRADING=False,
        read_only_observational_diagnostic_performed=True,new_study_capture_started=False,
        independent_membership_evidence_sha256=digest(ledger),feature_dependencies_sha256=digest(dependencies),
        previous_package_sha256=digest(ROOT/'research/studies/us30cash_m5_native_pretrain_v1/package_hashes.json'),
        previous_package_base_head='8901b03813dfc3db65ba54d25d7387ceae4f22bf')
    write(REPORT/'readiness.json',readiness)
    index={p.name:digest(p) for p in sorted(REPORT.iterdir()) if p.is_file() and p.name!='hashes.json'}
    write(REPORT/'hashes.json',dict(files=index,root_sha256=seal(index)))
    print(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        observational_source_records=receipt['source_records'],live_ticks=receipt['post_cut_tick_callbacks'],
        scientific_capture_started=False,authorization_required='SCIENTIFIC_ROLE_ONLY')))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observational-smoke',action='store_true')
    review(parser.parse_args().observational_smoke)
