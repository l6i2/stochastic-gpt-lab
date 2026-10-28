"""Produce a point-in-time, non-sensitive PC A recovery evidence bundle."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import re

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'python'))
import pc_a_raw_archive as raw


def main():
    output = ROOT / 'configs/pc_a_recovery_evidence_20261028'
    output.mkdir(exist_ok=True)
    summaries = {}
    for kind, name in (('historical', 'historical_active.json'), ('prospective', 'active.json')):
        pointer = json.loads((raw.BASE / name).read_text())
        state = raw.verify(raw.BASE / pointer['archive_id'])
        raw.atomic(output / (kind + '_manifest.json'), state)
        summaries[kind] = dict(archive_id=state['archive_id'], manifest_sha256=raw.sha(output / (kind + '_manifest.json')),
                               segments=len(state['segments']), ticks=sum(s['ticks']['rows'] for s in state['segments']),
                               m5_bars=sum(s['bars']['rows'] for s in state['segments']), chain_head=state['chain_head'],
                               new_start_utc=state['new_start_utc'], scientific_acceptance=False)
    pointer = json.loads((ROOT / 'outputs/pc_a/active_clock_capture.json').read_text())
    capture = Path(pointer['folder'])
    hashes = json.loads((capture / 'hashes.json').read_text())
    for name, key in (('capture.json', 'capture_sha256'), ('native.csv', 'native_csv_sha256'), ('markers.txt', 'markers_sha256')):
        if raw.sha(capture / name) != hashes[key]:
            raise RuntimeError('CLOCK_EVIDENCE_HASH_MISMATCH')
    analysis = json.loads((capture / 'analysis.json').read_text())
    if analysis['clock_attestation'] != 'PASS':
        raise RuntimeError('CLOCK_ATTESTATION_NOT_PASS')
    parity_folder = ROOT / 'configs/main_k_native_evidence_20261023'
    parity = json.loads((parity_folder / 'validated_audit.json').read_text())
    for name, digest in parity['artifacts_sha256'].items():
        if raw.sha(parity_folder / name) != digest:
            raise RuntimeError('NATIVE_PARITY_EVIDENCE_HASH_MISMATCH')
    compiles = [ROOT / 'outputs/bar_controller/runs/compile_20261028T152121594989/compile_manifest.json',
                ROOT / 'outputs/pc_a/controller_intratrade_compile_verified.json']
    for path in compiles:
        record = json.loads(path.read_text())
        if record['COMPILE_STATUS'] != 'PASS' or record['ERRORS'] != 0 or record['WARNINGS'] != 0:
            raise RuntimeError('COMPILE_NOT_PASS')
        source = Path(record['ea_path'])
        if raw.sha(source) != record['ea_hash'] or raw.sha(source.with_suffix('.ex5')) != record['ex5_hash']:
            raise RuntimeError('COMPILED_BINARY_CHANGED')
    station = json.loads((ROOT / 'outputs/pc_a/raw_station_status.json').read_text())
    tests_path = ROOT / 'outputs/pc_a/tests_recovery.log'
    tests_text = tests_path.read_text(encoding='utf-8-sig')
    total = int(re.search(r'Ran (\d+) tests', tests_text).group(1))
    skipped = int(re.search(r'OK \(skipped=(\d+)\)', tests_text).group(1))
    inventory = [
        dict(artifact='Git source, clock capture, native MAIN_K parity and exact compiled binaries', classification='VERIFIED'),
        dict(artifact='Legacy frozen metadata arithmetic Fast-K approximation', classification='FOUND_BUT_INVALID', reason='Native MAIN_K non-equivalence; original unchanged'),
        dict(artifact='Old raw history, master datasets, sealed split membership and old cohort segments/state', classification='MISSING', scope='Accessible PC A project/chat, relevant backup names, GitHub branch/releases/Actions'),
        dict(artifact='Broker native historical quotes', classification='REGENERABLE', result='2024-01-02 diagnostic acquired; M5 empty and UTC mapping unverified'),
        dict(artifact='Original prospective receipt times if not recoverable from a sealed backup', classification='IRRECOVERABLE', reason='Cannot regenerate past receipt evidence by redownloading broker history; no global absence claim'),
        dict(artifact='New raw historical/prospective archives and verified same-disk copy', classification='LOCAL_ONLY'),
    ]
    report = dict(observed_utc=datetime.now(timezone.utc).isoformat(),
        PC_A_STATUS='PARTIAL', GITHUB_SYNC='PENDING_PUBLICATION', HISTORICAL_DATA='BLOCKED',
        HISTORICAL_DATA_VERSION=summaries['historical']['archive_id'],
        HISTORICAL_VERSION_CLASS='NEW_HISTORICAL_DATA_VERSION_RAW_QUARANTINE',
        METADATA_COMPATIBILITY='FAIL', CLOCK_ATTESTATION='PASS', NATIVE_TO_UTC_MAPPING='FAIL', CAUSAL_AUDIT='FAIL',
        PREVIOUS_COHORT_CONTINUITY='UNVERIFIED', NEW_COHORT='BLOCKED',
        NEW_COHORT_ID=summaries['prospective']['archive_id'], NEW_START_UTC=summaries['prospective']['new_start_utc'],
        NEW_COLLECTOR_VERSION=raw.VERSION, COLLECTOR='RUNNING_RAW_QUARANTINE_ONLY', LOW_MEMORY_MODE=True,
        TRAINING_PIPELINE='BLOCKED', TRAINING_READINESS='BLOCKED_BY_RESEARCH_GOVERNANCE', BEST_CANDIDATE='NONE',
        DISCOVERY_VALIDATION='BLOCKED', FINAL_TEST='LOCKED', DEMO='DISABLED', LIVE_TRADING=False, ORDERS_SENT=0,
        REMOTE_HEAD_BEFORE=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        PUSH_STATUS='PENDING_PUBLICATION', MANUAL_ACTION_REQUIRED='NONE',
        NEXT_STATE='AUTONOMOUS_RAW_QUARANTINE_MAPPING_METADATA_AND_RESEARCH_GOVERNANCE_GATED',
        controller=dict(C1_ENV='PASS', C2_COMPILE='PASS_HASH_REVERIFIED', C3_HEADLESS_TESTER='BLOCKED_NO_SEALED_SPLIT_MANIFEST_AND_TERMINAL_RUNNING',
                        C4_ARTIFACTS='PARTIAL_COMPILE_ONLY_NO_ACCEPTED_TESTER_DATASETS', C5_HISTORY='PARTIAL_TICKS_ACQUIRED_M5_EMPTY'),
        archives=summaries, inventory=inventory, scheduler=station['scheduler'], backup=station['backup'],
        scientific_backfill_absence_utc_proven=False, historical_independence=False,
        tests=dict(total=total, passed=total-skipped, skipped=skipped, failed=0, skip_reason='g++ unavailable',
                   suite_log_sha256=raw.sha(tests_path),
                   compileall='PASS', pip_check='PASS', git_diff_check='PASS',
                   archive_safety_tests=9, stop_resume_same_identity='PASS', scheduled_execution='PASS_LAST_RESULT_0'),
        missing_original_split_manifest=True, old_pc_required_for_new_raw_capture=False)
    raw.atomic(output / 'recovery_status.json', report)
    raw.atomic(output / 'clock_seal_recheck.json', dict(status='PASS', hashes=hashes, interval_only=True, native_to_utc_mapping='UNVERIFIED'))
    raw.atomic(output / 'bundle_hashes.json', {p.name: raw.sha(p) for p in output.glob('*.json') if p.name != 'bundle_hashes.json'})
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
