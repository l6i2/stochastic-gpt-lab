"""One Windows-only read-only orchestration command; never changes research gates."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, payload):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())


def validate_handoff(data):
    expected = {'branch': 'research/full-pipeline', 'final_test': 'LOCKED',
                'demo': 'DISABLED', 'live_trading': False,
                'discovery_validation': 'BLOCKED'}
    if any(data.get(k) != v for k, v in expected.items()):
        raise ValueError('HANDOFF_SAFETY_CONTRACT_MISMATCH')
    return data


def verify_source_manifest(path, root=ROOT):
    root = Path(root).resolve()
    path = Path(path).resolve()
    if root not in path.parents:
        raise ValueError('SOURCE_MANIFEST_OUTSIDE_REPOSITORY')
    manifest = json.loads(path.read_text(encoding='utf-8-sig'))
    baseline_path = root / 'outputs/status/CLOUD_SOURCE_HASHES.json'
    baseline = json.loads(baseline_path.read_text(encoding='utf-8-sig'))
    files = manifest.get('files', {})
    if not files or not set(baseline['files']).issubset(files):
        raise ValueError('SOURCE_MANIFEST_OMITS_BASELINE_FILES')
    if path != baseline_path.resolve() and manifest.get('parent_manifest_sha256') != sha(baseline_path):
        raise ValueError('SOURCE_MANIFEST_PARENT_MISMATCH')
    for relative, expected in files.items():
        source = (root / relative).resolve()
        if root not in source.parents or sha(source) != expected:
            raise ValueError('CLOUD_SOURCE_HASH_MISMATCH:' + relative)
    return manifest


def discover_terminal(requested=None):
    import psutil
    paths = set()
    for process in psutil.process_iter(['name', 'exe']):
        try:
            if (process.info['name'] or '').lower() == 'terminal64.exe' and process.info['exe']:
                paths.add(Path(process.info['exe']).resolve())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    if requested:
        selected = Path(requested).resolve()
        if selected not in paths:
            raise ValueError('REQUESTED_MT5_NOT_RUNNING')
        return selected
    if len(paths) != 1:
        raise ValueError('OPEN_ONE_XM_TERMINAL_OR_SPECIFY_--terminal')
    return paths.pop()


def prepare_probe(terminal, folder, run_id):
    import MetaTrader5 as mt5
    if not mt5.initialize(str(terminal)):
        raise RuntimeError('MT5_READ_ONLY_INITIALIZE_FAILED')
    try:
        info, account = mt5.terminal_info(), mt5.account_info()
        if not info or not info.connected or not account or account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise ValueError('CONNECTED_DEMO_REQUIRED_NO_ACCOUNT_SWITCH_PERFORMED')
        if not any(word in str(info.company).lower() for word in ('xm', 'trading point')):
            raise ValueError('XM_TERMINAL_IDENTITY_REQUIRED')
        data = Path(info.data_path)
    finally:
        mt5.shutdown()
    editor = terminal.with_name('metaeditor64.exe')
    if not editor.is_file():
        raise FileNotFoundError('MATCHING_METAEDITOR_REQUIRED')
    template = ROOT / 'tests/mql5/FullClockAndTimeSemanticsProbe.mq5'
    destination = data / 'MQL5/Scripts/ResearchDiagnostics' / run_id
    destination.mkdir(parents=True, exist_ok=False)
    script = destination / 'FullClockAndTimeSemanticsProbe.mq5'
    source = template.read_text(encoding='utf-8')
    source = source.replace('input string RunId="LOCAL_RUN_ID";', f'input string RunId="{run_id}";')
    script.write_text(source, encoding='utf-8')
    log = folder / 'compile.log'
    started = time.time()
    # MetaEditor requires quotes after ':' for paths with spaces; return code 1
    # can accompany a successful build. Trust only a fresh binary and clean log.
    subprocess.run(f'"{editor}" /compile:"{script}" /log:"{log}"', timeout=90,
                   check=False, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if not script.with_suffix('.ex5').is_file() or not log.is_file():
        raise RuntimeError('COMPILE_OUTPUT_MISSING')
    raw = log.read_bytes()
    text = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
    if '0 errors, 0 warnings' not in text:
        raise RuntimeError('COMPILE_NOT_ZERO_ERRORS_ZERO_WARNINGS_SEE_LOCAL_LOG')
    if script.with_suffix('.ex5').stat().st_mtime < started - 2:
        raise RuntimeError('COMPILE_BINARY_NOT_FRESH')
    manifest = {'run_id': run_id, 'script': str(script),
                'native': str(data / 'MQL5/Files' / f'{run_id}_native.csv'),
                'markers': str(data / 'MQL5/Files' / f'{run_id}_markers.txt'),
                'sessions': str(data / 'MQL5/Files' / f'{run_id}_sessions.txt'),
                'build': {'source_sha256': sha(script), 'ex5_sha256': sha(script.with_suffix('.ex5'))},
                'template_sha256': sha(template), 'orders_sent': 0}
    write_new(folder / 'run.json', manifest)
    return manifest


def run_capture(folder, manifest, timeout=360):
    native, markers = Path(manifest['native']), Path(manifest['markers'])
    if native.exists() or markers.exists():
        raise FileExistsError('FRESH_NATIVE_FILES_REQUIRED')
    with (folder / 'watcher.log').open('x', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, str(ROOT / 'tools/windows_clock_capture.py'),
                                    '--native', str(native), '--output', str(folder)], stdout=log, stderr=log)
        deadline = time.monotonic() + 90
        try:
            while not (folder / 'ready.json').exists():
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError('WINDOWS_CAPTURE_NOT_ARMED_SEE_WATCHER_LOG')
                time.sleep(.2)
            # Only unavoidable human action. No key input required afterwards.
            print(f"Navigator -> Scripts -> ResearchDiagnostics -> {manifest['run_id']} -> FullClockAndTimeSemanticsProbe", flush=True)
            deadline = None
            while True:
                if deadline is None and native.exists():
                    deadline = time.monotonic() + timeout
                if deadline is not None and time.monotonic() >= deadline:
                    break
                ended = markers.exists() and f"CLOCK_ATTESTATION_END|run={manifest['run_id']}|" in markers.read_text(encoding='utf-8-sig')
                if ended and process.poll() == 0 and (folder / 'capture.json').exists():
                    return
                if process.poll() is not None and process.returncode != 0:
                    raise RuntimeError('CAPTURE_FAILED_SEE_WATCHER_LOG')
                time.sleep(.2)
            raise TimeoutError('END_OR_COMPLETE_CAPTURE_MISSING; no evidence overwritten')
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--terminal', type=Path)
    parser.add_argument('--mapping', type=Path)
    parser.add_argument('--resume-folder', type=Path)
    parser.add_argument('--check-handoff', action='store_true')
    parser.add_argument('--source-manifest', type=Path,
                        default=ROOT / 'outputs/status/CLOUD_SOURCE_HASHES.json')
    args = parser.parse_args()
    handoff = validate_handoff(json.loads((ROOT / 'outputs/status/CLOUD_HANDOFF.json').read_text()))
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip()
    if branch != handoff['branch']:
        raise ValueError('WRONG_BRANCH')
    subprocess.run(['git', 'merge-base', '--is-ancestor', handoff['head'], 'HEAD'], cwd=ROOT, check=True)
    verify_source_manifest(args.source_manifest)
    if args.check_handoff:
        print('HANDOFF_VALID; LOCAL_REQUIRED; no terminal connection')
        return 0
    if sys.platform != 'win32':
        raise OSError('LOCAL_REQUIRED_WINDOWS_MT5')
    run_id = 'cloud_' + uuid.uuid4().hex[:16]
    folder = args.resume_folder.resolve() if args.resume_folder else ROOT / 'outputs/local_clock_attestation' / run_id
    if args.resume_folder:
        manifest = json.loads((folder / 'run.json').read_text())
        run_id = manifest['run_id']
    else:
        folder.mkdir(parents=True, exist_ok=False)
    report = {'run_id': run_id, 'orders_sent': 0, 'final_test': 'LOCKED', 'demo': 'DISABLED',
              'live_trading': False, 'discovery_validation': 'BLOCKED',
              'clock_attestation': 'BLOCKED', 'native_to_utc_mapping': 'LOCAL_EXTERNAL_EVIDENCE_REQUIRED',
              'causal_audit': 'LOCAL_REQUIRED', 'main_k_parity': handoff['main_k_parity']}
    try:
        if not args.resume_folder:
            manifest = prepare_probe(discover_terminal(args.terminal), folder, run_id)
            run_capture(folder, manifest)
        elif not (folder / 'capture.json').exists():
            raise ValueError('INCOMPLETE_CAPTURE_START_NEW_RUN_PRESERVE_PARTIAL')
        from analyze_clock_attestation import analyze
        analysis = analyze(folder)
        if not (folder / 'analysis.json').exists():
            write_new(folder / 'analysis.json', analysis)
        report['clock_attestation'] = analysis['clock_attestation']
        from session_evidence_parser import parse_sessions
        session_folder = folder / ('session_review_' + uuid.uuid4().hex[:8])
        session_folder.mkdir()
        report['session_snapshot'] = parse_sessions(Path(manifest['sessions']), session_folder)
        from causal_metadata_audit import audit_metadata_contract
        report['causal_metadata_check'] = audit_metadata_contract()
        from manifest_chain_handoff import incorporate_local
        cohort = ROOT / 'outputs/future_validation_cohort/cohort_20261019'
        if (cohort / 'cohort_manifest.json').exists():
            report['manifest_chain_report'] = incorporate_local(cohort, ROOT / 'outputs/local_clock_inputs/manifest_history')
        if args.mapping:
            from validate_clock_mapping import validate
            report['mapping_validation'] = validate(args.mapping)
        report['next_action'] = 'Review external native/UTC correspondence and causal evidence; no gates opened'
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, KeyError, ImportError) as exc:
        report['error'] = str(exc)
    finally:
        report['next_state'] = 'HARD_BLOCKER_LOCAL_EVIDENCE_REVIEW'
        report_path = folder / 'final_report.json'
        if report_path.exists():
            report_path = folder / ('final_report_' + uuid.uuid4().hex[:8] + '.json')
        write_new(report_path, report)
        print(json.dumps(report, indent=2))
        print('REPORT: ' + str(report_path))
    return 2  # Capture success is not operational mapping/causal acceptance.


if __name__ == '__main__':
    raise SystemExit(main())
