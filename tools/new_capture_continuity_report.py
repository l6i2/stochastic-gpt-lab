"""Publish new interruption evidence without mutating old evidence or raw capture."""
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'python'))
from controller.authorized_capture import CaptureManager,STATION,sha,once
from controller.pretrain_contracts import seal
from tools.new_capture_station import verify_deployment

REPORT=ROOT/'research/studies/us30cash_m5_native_collection_continuity_20261031_v1'


def write(name,value):
    path=REPORT/name;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')


def previous_source_review():
    old=ROOT/'configs/pc_a_source_hashes_20261031_v27.json'
    manifest=json.loads(old.read_text())
    changed={}
    allowed={'controller/authorized_capture.py'}
    for relative,expected in manifest['files'].items():
        actual=sha(ROOT/relative)
        if actual!=expected:
            if relative not in allowed:raise ValueError('UNEXPECTED_PREVIOUS_ASSET_CHANGE_'+relative)
            committed=subprocess.check_output(['git','show','b95841876d734a137adaf3df1e616f776cec2334:'+relative],cwd=ROOT)
            if hashlib.sha256(committed).hexdigest()!=expected:raise ValueError('PREVIOUS_SOURCE_BINDING_CHANGED')
            changed[relative]=dict(previous_sha256=expected,current_sha256=actual,
                                  reason='PASSIVE_CONTINUITY_MONITOR_HOOK_NO_ADMISSION_OR_POWER_CHANGE')
    return dict(base_manifest_sha256=sha(old),changed_existing_files=changed,
        all_other_previous_files_verified=True,frozen_contracts_or_prior_captures_modified=False)


def query_power_context(gap):
    before=gap['fact']['before']['receipt_host_gmt_seconds']
    after=gap['fact']['after']['receipt_host_gmt_seconds']
    script="[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false);$captureS=[DateTimeOffset]::FromUnixTimeSeconds("+str(int(before)-120)+").LocalDateTime;$captureE=[DateTimeOffset]::FromUnixTimeSeconds("+str(int(after)+120)+").LocalDateTime;try{$v=@(Get-WinEvent -FilterHashtable @{LogName='System';ProviderName='Microsoft-Windows-Kernel-Power';StartTime=$captureS;EndTime=$captureE;Id=506,507} -MaxEvents 20 -ErrorAction Stop | Select-Object Id,RecordId,@{Name='TimeUtc';Expression={$_.TimeCreated.ToUniversalTime().ToString('o')}},Message);@{status='OK';events=$v}|ConvertTo-Json -Depth 5 -Compress}catch{@{status='UNAVAILABLE';events=@();error_type=$_.Exception.GetType().Name}|ConvertTo-Json -Compress}"
    result=subprocess.run(['powershell.exe','-NoProfile','-Command',script],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=25)
    response=json.loads(result.stdout) if result.returncode==0 and result.stdout.strip() else {'status':'UNAVAILABLE','events':[]}
    return dict(incident_id=gap['incident_id'],query_scope='HOST_CLOCK_LABEL_WINDOW_NOT_INDEPENDENT_BROKER_EVENT_UTC',
        host_start_seconds=before-120,host_end_seconds=after+120,maximum_events=20,
        response=response,reason_classification='OS_MODERN_STANDBY_CORROBORATED_IF_506_ENTRY_AND_507_EXIT_PRESENT',
        no_power_policy_changed=True,missing_broker_ticks_recovered=False)


def main():
    verify_deployment();review=previous_source_review()
    manager=CaptureManager();manager.load();capture=manager.root
    summary=json.loads((capture/'continuity_summary.json').read_text())
    status=json.loads((capture/'collector_status.json').read_text())
    incidents=[]
    for path in sorted((capture/'continuity_incidents').glob('*.json')):
        item=json.loads(path.read_text())
        if seal(item['fact'])!=item['incident_id']:raise ValueError('INCIDENT_HASH_CHANGED')
        incidents.append(item)
        destination=REPORT/'incidents'/path.name;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,destination)
    gaps=[r for r in incidents if r['fact']['kind']=='CALLBACK_TIMER_GAP']
    largest=max(gaps,key=lambda r:r['fact']['elapsed_ms'])
    context=query_power_context(largest)
    write('power_context.json',context)
    write('source_review.json',review)
    write('continuity_snapshot.json',summary)
    write('collector_snapshot.json',status)
    restart=json.loads((STATION/'restart_verification.json').read_text())
    write('updated_process_restart.json',restart|{'source_report_sha256':sha(STATION/'restart_verification.json')})
    # The original normalized public restart report retains a verified raw hash.
    # Preserve an exact raw-byte copy in maintenance evidence if that cache was refreshed.
    prior_path=ROOT/'research/studies/us30cash_m5_native_collection_activation_v1/process_restart_verification.json'
    prior=json.loads(prior_path.read_text());expected=prior.pop('source_report_sha256')
    recovered=(json.dumps(prior,indent=2,sort_keys=True)+'\n').replace('\n','\r\n').encode()
    if hashlib.sha256(recovered).hexdigest()!=expected:raise ValueError('PRIOR_RESTART_RAW_HASH_NOT_REPRODUCIBLE')
    recovered_path=STATION/'maintenance_evidence'/(expected+'.json')
    if not recovered_path.exists():
        recovered_path.parent.mkdir(exist_ok=True)
        with recovered_path.open('xb') as stream:stream.write(recovered)
    write('prior_restart_evidence_preservation.json',dict(original_raw_sha256=expected,
        retained_published_report_sha256=sha(prior_path),byte_exact_maintenance_copy_verified=sha(recovered_path)==expected,
        recovery_basis='PUBLISHED_COMPLETE_METADATA_AND_ORIGINAL_SHA256_NOT_INVENTED_DATA'))
    patterns=['test_capture_continuity_monitor.py','test_authorized_capture.py','test_isolated_observation.py']
    suite=unittest.TestSuite()
    for pattern in patterns:suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern))
    transcript=io.StringIO();result=unittest.TextTestRunner(stream=transcript,verbosity=2).run(suite)
    write('validation.json',dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        skipped=len(result.skipped),patterns=patterns,transcript=transcript.getvalue(),
        native_indicator_or_training_tests_rerun=False))
    if not result.wasSuccessful():raise SystemExit(1)
    corroborated=context['response']['status']=='OK' and {506,507}.issubset({r['Id'] for r in context['response']['events']})
    outcome=dict(CAPTURE_ID=status['capture_id'],COLLECTOR_STATUS=status['status'],
        SOURCE_RECORDS=status['totals'],CALLBACK_GAPS=summary['callback_gaps'],
        MAXIMUM_CALLBACK_GAP_MS=summary['maximum_callback_gap_ms'],
        SEQUENCE_INTEGRITY=summary['source_sequence_integrity'],
        INTERRUPTION_DISPOSITION='QUARANTINED_NO_BACKFILL',
        CAUSE='OS_MODERN_STANDBY_CONTEXT_AND_DISCONNECTION_CORROBORATED_NOT_COMPLETE_BROKER_LOSS_PROOF' if corroborated else 'UNDETERMINED_WINDOWS_CONTEXT_NOT_VERIFIED',
        RECONNECTED=summary['last_connected'],CONTINUITY_MONITOR='ACTIVE_INCREMENTAL_IMMUTABLE_INCIDENTS',
        POWER_SETTINGS_CHANGED=False,DATASET_ADMISSION='BLOCKED',CAUSAL_AUDIT='FAIL_GLOBAL_UNCHANGED',
        TRAINING_READINESS='BLOCKED',LIVE_TRADING=False,MANUAL_ACTION_REQUIRED='NONE_FOR_MONITORING',
        NEXT_STATE='CONTINUE_QUARANTINE_CAPTURE_WITH_INTERRUPTION_EVIDENCE',
        INTERRUPTION_HOST_LABEL_INTERVAL_ECUADOR=[datetime.fromtimestamp(largest['fact'][side]['receipt_host_gmt_seconds'],timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('America/Guayaquil')).isoformat() for side in ('before','after')])
    write('status.json',outcome)
    hashes={p.relative_to(REPORT).as_posix():sha(p) for p in sorted(REPORT.rglob('*')) if p.is_file() and p.name!='hashes.json'}
    write('hashes.json',dict(files=hashes,root_sha256=seal(hashes)))
    print(json.dumps(dict(capture_id=status['capture_id'],records=status['totals'],gaps=len(gaps),
        maximum_gap_ms=summary['maximum_callback_gap_ms'],tests=result.testsRun,failures=len(result.failures),errors=len(result.errors))))


if __name__=='__main__':main()
