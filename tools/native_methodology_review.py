"""One-command diagnostics-only evidence pack; never train, score or open holdouts.

Reuses completed synthetic MQL capture. All real datasets stay unopened; only
previously published seals, source hashes, diagnostic artifacts and tests are read.
"""
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'python'))


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


def main():
    from local_finalize import verify_source_manifest
    from controller.native_feature_diagnostic import OUT, verify_capture
    verify_source_manifest(ROOT/'configs/pc_a_source_hashes_20261030_v23.json')
    adopted=ROOT/'research/native_methodology_v1'
    adoption=json.loads((adopted/'adoption.json').read_text(encoding='utf-8'))
    if sha(ROOT/adoption['approved_proposal_path'])!=adoption['approved_proposal_sha256']:
        raise ValueError('APPROVED_PROPOSAL_CHANGED')
    if adoption['training_authorized'] or adoption['scoring_authorized'] or adoption['global_causal_audit_override']:
        raise ValueError('LIMITED_AUTHORIZATION_EXCEEDED')
    evidence=adopted/'evidence'
    evidence.mkdir(exist_ok=True)

    def write(name, value):
        (evidence/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')

    previous=json.loads((OUT/'latest.json').read_text())
    checkpoint=previous['checkpoint']
    folder=OUT/checkpoint['capture_id']
    availability=verify_capture(folder,checkpoint)
    if availability!=previous['result']:
        raise ValueError('REPLAYED_SYNTHETIC_EVIDENCE_CHANGED')
    write('availability.json',availability)
    compiled_sources=ROOT/'outputs/pc_a_certification/native_tester/terminal/MQL5/Scripts/NativeFeatureDiagnostics'/checkpoint['capture_id']
    write('execution.json',dict(checkpoint,compiled_source_hashes={name:sha(compiled_sources/name)
        for name in ('StochasticBarDecisionResearchEA.mq5','ResearchCore.mqh','HeikinAshiCore.mqh')}))
    shutil.copyfile(folder/'NativeFeaturePrefixProbe.mq5',evidence/'NativeFeaturePrefixProbe.mq5')
    failed=OUT/'nfeat_dbf52a1354b5'
    terminal=ROOT/'outputs/pc_a_certification/native_tester/terminal'
    failed_source=terminal/'MQL5/Scripts/NativeFeatureDiagnostics/nfeat_dbf52a1354b5/NativeFeaturePrefixProbe.mq5'
    # Preserve the negative log line without any terminal/account log context.
    messages=[]
    for path in (terminal/'MQL5/Logs').glob('*.log'):
        text=path.read_bytes().decode('utf-16',errors='replace')
        messages += [line.split('\t')[-1] for line in text.splitlines() if
                     "array out of range in 'StochasticBarDecisionResearchEA.mq5' (152,1031)" in line]
    if not messages or not failed_source.exists():
        raise ValueError('NEGATIVE_HISTORY_EVIDENCE_MISSING')
    write('short_history_failure.json',dict(
        capture_id=failed.name,status='REJECTED_SYNTHETIC_SHORT_HISTORY',closed_history_at_start=15,
        producer_sha256=checkpoint['producer_sha256'],harness_sha256=sha(failed_source),
        ex5_sha256=sha(failed_source.with_suffix('.ex5')),compile_log_sha256=sha(failed/'compile.log'),
        compile_errors=0,compile_warnings=0,completion=False,error=messages[0],
        frozen_producer_changed=False,remediation='DIAGNOSTIC_PREFLIGHT_MINIMUM_20_NOT_FULL_WARMUP',
        earlier_compile_only_attempt=dict(capture_id='nfeat_696afe781bc1',
            compile_log_sha256=sha(OUT/'nfeat_696afe781bc1/compile.log'),
            compiler_process_code=1,compile_errors=0,compile_warnings=0,producer_executed=False)))
    patterns=['test_native_feature_diagnostic.py','test_native_independence.py',
              'test_native_study_design.py','test_native_methodology_proposal.py',
              'test_quote_replay.py','test_controller_causal.py']
    suite=unittest.TestSuite()
    for pattern in patterns:
        suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern))
    transcript=io.StringIO()
    result=unittest.TextTestRunner(stream=transcript,verbosity=2).run(suite)
    write('validation.json',dict(tests_run=result.testsRun,failures=len(result.failures),
        errors=len(result.errors),skipped=len(result.skipped),patterns=patterns,
        transcript=transcript.getvalue()))
    if not result.wasSuccessful():raise SystemExit(1)
    write('status.json',dict(NATIVE_DIAGNOSTIC_METHOD='ADOPTED_DIAGNOSTICS_ONLY',
        SYNTHETIC_AVAILABILITY='PASS_SCOPED_DEFAULT_FROZEN_PRODUCER',
        fields_checked=len(availability['fields']),cutoff_cases=3,synthetic_scenarios=9,
        INDEPENDENT_DATA='MISSING_NOT_ADMITTED',SCIENTIFIC_STUDY='NOT_AUTHORIZED',
        TRAINING_READINESS='BLOCKED',SCORING='NOT_AUTHORIZED',CAUSAL_AUDIT='FAIL_GLOBAL_UNCHANGED',
        DISCOVERY_VALIDATION='BLOCKED',HISTORICAL_HOLDOUT='BLOCKED',FINAL_TEST='LOCKED',
        DEMO='DISABLED',LIVE_TRADING=False,orders_sent=0,
        original_terminal_pids_preserved=checkpoint['original_terminal_pids_preserved'],
        NEXT_STATE='PREPARE_INDEPENDENT_DATA_PACKAGE_BEFORE_NEW_STUDY_AUTHORIZATION'))
    write('hashes.json',{p.name:sha(p) for p in evidence.iterdir() if p.is_file() and p.name!='hashes.json'})
    print(json.dumps(dict(tests=result.testsRun,errors=len(result.errors),failures=len(result.failures),
        fields=len(availability['fields']),synthetic_capture=checkpoint['capture_id'],
        frozen_source_seal='VERIFIED',training_authorized=False)))


if __name__=='__main__':main()
