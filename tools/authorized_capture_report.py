"""Read-only running-capture audit and sanitized publication evidence."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'python'))
from controller.authorized_capture import CaptureManager,STATION,AUTH,NATIVE,sha,verify_decisions,GENESIS
from controller.pretrain_contracts import seal
from controller.isolated_observation import native_line

REPORT=ROOT/'research/studies/us30cash_m5_native_collection_activation_v1'


def write(name,value):
    (REPORT/name).write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')


def audit_prefix(folder):
    checkpoint=json.loads((folder/'checkpoint.json').read_text())
    manifest=json.loads((folder/'manifest.json').read_text())
    head=GENESIS;rows=0;source_rows=0
    sequence=manifest['anchor']['source_sequence'];source_head=manifest['anchor']['source_sha256']
    with (folder/'journal.jsonl').open('rb') as stream:
        for line in stream:
            if rows>=checkpoint['rows']:break
            record=json.loads(line);body=record['payload']
            if record['previous']!=head or record['sha256']!=seal(dict(previous=head,payload=body)) or body['index']!=rows:
                raise ValueError('LIVE_JOURNAL_PREFIX_CHANGED')
            event=body['event']
            if event.get('source_sequence') is not None:
                if event['source_sequence']!=sequence+1:raise ValueError('LIVE_SOURCE_SEQUENCE_GAP_OR_DUPLICATE')
                sequence=event['source_sequence'];source_rows+=1
                if event['native_line'] is not None:
                    parent,digest,native=native_line(event['native_line'].encode())
                    if parent!=source_head or digest!=event['source_sha256']:raise ValueError('LIVE_NATIVE_BYTES_CHANGED')
                    if native['callback_uptime_ms']<=manifest['actual_start_clock']['uptime_ms']:
                        raise ValueError('PRE_START_NATIVE_PAYLOAD_ADOPTED')
                source_head=event['source_sha256']
            head=record['sha256'];rows+=1
    if rows!=checkpoint['rows'] or head!=checkpoint['chain_head'] or source_rows!=checkpoint['source_records']:
        raise ValueError('LIVE_CHECKPOINT_PREFIX_MISMATCH')
    return dict(rows_verified=rows,source_records_verified=source_rows,source_sequence=sequence,
        chain_head=head,native_source_head=source_head,source_offset=checkpoint['source_offset'],
        tick_callbacks=checkpoint['tick_callbacks'],heartbeat_records=checkpoint['heartbeat_records'],
        hash_and_sequence_prefix='PASS_AT_SNAPSHOT',old_prefix_payloads_adopted=0,
        snapshot_does_not_assert_full_market_coverage=True)


def main():
    from local_finalize import verify_source_manifest
    verify_source_manifest(ROOT/'configs/pc_a_source_hashes_20261031_v26.json')
    manager=CaptureManager();manifest=manager.load();root=manager.root
    for name in ('collection_manifest.json','activation_utc.json','activation_nts_before.json','activation_nts_after.json',
                 'activation_boundary.json','initial_segment.json','prior_evidence_index.json'):
        shutil.copyfile(root/name,REPORT/name)
    shutil.copyfile(root/'segments'/manifest['initial_segment']/'manifest.json',REPORT/'initial_segment_manifest.json')
    decision_folder=REPORT/'decisions';decision_folder.mkdir(exist_ok=True)
    for path in sorted((root/'decisions').glob('*.json')):shutil.copyfile(path,decision_folder/path.name)
    if verify_decisions(decision_folder)!=manifest['decision_chain_head']:raise ValueError('PUBLISHED_DECISIONS_DIFFER')
    runtime=json.loads((root/'runtime_state.json').read_text())
    proofs={segment:audit_prefix(root/'segments'/segment) for segment in runtime['segments']}
    write('integrity_and_no_backfill.json',dict(capture_id=manifest['capture_id'],segments=proofs,
        historical_API_queries=False,source='ORIGINAL_NATIVE_CALLBACK_RECORDS_APPENDED_AFTER_NEW_CUT',
        delayed_ingestion_of_post_activation_callbacks_is_not_historical_backfill=True,
        previous_cohort_segments_adopted=False,quote_timestamp_values_modified=False,
        dataset_admission=False))
    status=json.loads((root/'collector_status.json').read_text())
    supervisor=json.loads((STATION/'supervisor_status.json').read_text())
    watchdog=json.loads((STATION/'watchdog_status.json').read_text())
    startup=subprocess.run(['powershell.exe','-NoProfile','-Command',
        "Get-ItemPropertyValue -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run' -Name 'StochasticGPTLab_PC_A_NewNativeCapture_v1'"],capture_output=True,text=True,check=True)
    if str(ROOT/'tools/new_capture_watchdog.ps1') not in startup.stdout:raise ValueError('USER_STARTUP_COMMAND_MISMATCH')
    write('deployment_and_supervision.json',dict(mode='PER_USER_RUN_AND_MUTEX_WATCHDOG',
        scheduler_attempt='REGISTER_SCHEDULED_TASK_ACCESS_DENIED_0X80070005_NO_TASK_CREATED',
        startup_value='StochasticGPTLab_PC_A_NewNativeCapture_v1',user_startup_verified=True,
        startup_command_sha256=hashlib.sha256(startup.stdout.strip().encode()).hexdigest(),
        watchdog=watchdog,supervisor=supervisor,restart_poll_seconds=5,
        credentials_requested=False,administrator_privileges_used=False,
        prior_tasks_modified=False,requires_awake_PC_logged_in_user_and_XM_observer=True,
        actual_PC_reboot_performed=False,boot_and_new_session_recovery='SYNTHETIC_REGRESSION_PASS',
        deployment_pin_current=json.loads((STATION/'deployment_pin_current.json').read_text())))
    restart=json.loads((STATION/'restart_verification.json').read_text())
    restart['source_report_sha256']=sha(STATION/'restart_verification.json')
    write('process_restart_verification.json',restart)
    failed_root=STATION/'us30cap_7dfc7985cf494cce979dc509b5175445'
    shutil.copyfile(failed_root/'failed_activation.json',REPORT/'failed_attempt_preserved.json')
    observer=NATIVE.parents[2]/'Experts/ResearchDiagnostics/ProspectiveUtcObserver.mq5'
    prior=json.loads((ROOT/'configs/pc_a_callback_write_fix_evidence_20261029/deployment.json').read_text())['observer']
    if sha(observer)!=prior['source_sha256'] or sha(observer.with_suffix('.ex5'))!=prior['binary_sha256']:
        raise ValueError('PRIOR_OBSERVER_CHANGED')
    write('previous_assets_audit.json',dict(source_manifest_v26='PASS_ALL_PREVIOUS_577_SOURCE_AND_EVIDENCE_FILES_UNCHANGED',
        old_installed_observer_source_sha256=sha(observer),old_installed_observer_ex5_sha256=sha(observer.with_suffix('.ex5')),
        original_observers_or_tasks_changed=False,old_datasets_or_checkpoints_written_by_new_collector=False,
        prior_metadata_versions_immutably_snapshotted=sha(root/'prior_evidence_index.json'),
        previous_raw_observers_may_continue_observational_append_without_new_scientific_admission=True,
        other_project_accessed_or_modified=False))
    patterns=['test_authorized_capture.py','test_isolated_observation.py','test_pretrain_contracts.py',
        'test_pretrain_package.py','test_native_independence.py','test_native_study_design.py']
    suite=unittest.TestSuite()
    for pattern in patterns:suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern))
    transcript=io.StringIO();result=unittest.TextTestRunner(stream=transcript,verbosity=2).run(suite)
    write('validation.json',dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        skipped=len(result.skipped),patterns=patterns,transcript=transcript.getvalue(),new_training_or_scoring=False))
    if not result.wasSuccessful():raise SystemExit(1)
    utc=manifest['activation_utc']
    final=dict(PREVIOUS_RESERVATION_STATUS=manifest['previous_reservation_status'],
        NEW_CAPTURE_ID=manifest['capture_id'],NEW_CAPTURE_START_UTC=utc['utc_estimate'],
        NEW_CAPTURE_START_UTC_INTERVAL=[utc['utc_lower'],utc['utc_upper']],
        START_UTC_UNCERTAINTY_HALF_WIDTH_NS=utc['half_width_ns'],START_UTC_SCOPE=utc['uncertainty'],
        START_ECUADOR=datetime.fromisoformat(utc['utc_estimate']).astimezone(ZoneInfo('America/Guayaquil')).isoformat(),
        NO_BACKFILL_PROOF='PASS_NEW_CUT_NATIVE_SEQUENCE_AND_APPEND_PREFIX_AT_SNAPSHOT',
        COLLECTOR_STATUS=status['status'],SOURCE_RECORDS_OBSERVED=status['totals'],
        LIVE_QUOTE_CAPTURE='OBSERVED' if status['totals']['tick_callbacks'] else 'NO_TICK_CALLBACKS_YET_HEARTBEATS_ONLY',
        COHORT_ISOLATION='PASS_NEW_CAPTURE_NAMESPACE_AND_LEDGER_NO_OLD_SEGMENTS_ADOPTED',
        DATASET_ADMISSION='BLOCKED_QUARANTINED',DATASET_HASH=None,CAUSAL_AUDIT='FAIL_GLOBAL_UNCHANGED',
        TRAINING_READINESS='BLOCKED',MANUAL_ACTION_REQUIRED='NONE',
        NEXT_STATE='AUTOMATED_QUARANTINE_CAPTURE_AWAIT_DATA_INTEGRITY_COVERAGE_AND_CAUSAL_CERTIFICATION',
        DISCOVERY_VALIDATION='BLOCKED',HISTORICAL_HOLDOUT='BLOCKED',FINAL_TEST='LOCKED',DEMO='DISABLED',LIVE_TRADING=False,
        training_authorized=False,scoring_authorized=False,orders_sent=0,
        observed_host_clock=status['observed_clock'],capture_manifest_sha256=sha(root/'collection_manifest.json'))
    write('status.json',final)
    files={p.relative_to(REPORT).as_posix():sha(p) for p in sorted(REPORT.rglob('*')) if p.is_file() and p.name!='hashes.json'}
    write('hashes.json',dict(files=files,root_sha256=seal(files)))
    print(json.dumps(dict(capture_id=manifest['capture_id'],collector=status['status'],source_records=status['totals'],
        tests=result.testsRun,errors=len(result.errors),failures=len(result.failures),dataset_admitted=False)))


if __name__=='__main__':main()
