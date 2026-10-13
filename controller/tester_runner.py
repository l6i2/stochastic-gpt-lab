"""CLI launch with bounded waiting. Never terminates an existing terminal."""
import json
import re
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .artifact_collector import collect, find_artifacts, write_manifest
from .compile_runner import compile_ea, ea_path, sha256
from .mt5_env import require_active_environment, status
from .safety_gate import ROOT, assert_research_range_allowed
from .tester_config import config, preset, write_preset


def read_log(path):
    raw = path.read_bytes()
    return raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig', errors='replace')


def classify_log(text):
    failures = re.findall(r'OnInit[^\n]*(?:error|fail)|fatal|no history|no real ticks|invalid parameter|file[^\n]*error', text, re.I)
    return 'FAIL' if failures else ('PASS' if re.search(r'test passed', text, re.I) else 'INCOMPLETE')


def run(start, end, ea='StochasticIntratradeResearchEA', symbol='US30Cash', timeout=120, config_encoding='utf-16'):
    if timeout <= 0 or config_encoding not in ('utf-16', 'ascii'):
        raise ValueError('Invalid timeout/config encoding')
    assert_research_range_allowed(start, end)
    if symbol != 'US30Cash':
        raise RuntimeError('SECURITY_GATE: only US30Cash supported')
    environment = require_active_environment(status())
    if not environment['SAFE_FOR_RESEARCH']:
        raise RuntimeError('SECURITY_GATE: connected DEMO research environment required')
    run_id = 'r' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '_' + uuid.uuid4().hex[:8]
    folder = ROOT / 'outputs/controller/runs' / run_id
    folder.mkdir(parents=True)
    compiled = compile_ea(environment, folder, ea)
    source = ea_path(environment, ea)
    # The deployed source must match the locally reviewed project source.
    if sha256(source) != sha256(ROOT / 'mt5' / source.name):
        raise RuntimeError('MQL5_COMPILE: deployed source differs from repository; no test launched')
    inputs = preset(run_id)
    local_preset = folder / (run_id + '.set')
    write_preset(local_preset, inputs)
    profile = Path(environment['TESTER_PROFILES']) / local_preset.name
    if profile.exists():
        raise RuntimeError('MT5_CONFIG: preset collision')
    profile.write_bytes(local_preset.read_bytes())
    ini = folder / 'tester.ini'
    (Path(environment['DATA_FOLDER']) / 'reports/controller').mkdir(parents=True, exist_ok=True)
    # Disable chart trading independently of the EA's own mandatory tester gate.
    ini.write_text('[Experts]\nAllowLiveTrading=0\n' + config(
        start, end, profile.name, 'reports\\controller\\' + run_id + '.htm'), encoding=config_encoding)
    started = time.time()
    log_roots = [Path(environment['DATA_FOLDER']) / 'Tester/logs'] + [
        Path(p) / 'logs' for p in environment['TESTER_AGENT_FOLDERS']]
    offsets = {p: p.stat().st_size for root in log_roots for p in root.glob('*.log')}
    manifest = dict(run_id=run_id, git_sha=subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        **compiled, symbol=symbol, period='M5', model='real_ticks', optimization=False,
        inputs=inputs, start_time=datetime.now(timezone.utc).isoformat(),
        tester_status='RUNNING', artifact_hashes={}, **{'from': start, 'to': end})
    manifest['environment'] = environment
    manifest['log_offsets'] = {str(p): offset for p, offset in offsets.items()}
    write_manifest(folder, manifest)
    process = subprocess.Popen([environment['TERMINAL_PATH'], '/config:' + str(ini)],
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    manifest['launcher_pid'] = process.pid
    manifest['terminal_pids'] = [p.pid for p in __import__('psutil').process_iter(['name'])
                                 if (p.info['name'] or '').lower() == 'terminal64.exe']
    write_manifest(folder, manifest)
    complete = None
    text = ''
    identity = False
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        chunks = []
        for root in log_roots:
            for path in root.glob('*.log'):
                with path.open('rb') as stream:
                    stream.seek(offsets.get(path, 0))
                    raw = stream.read()
                if raw:
                    chunks.append(raw.decode('utf-16-le', errors='replace').lstrip('\ufeff'))
        text = '\n'.join(chunks)
        complete = find_artifacts(environment, run_id, started)
        # Require the dedicated expert, requested range, and new completion evidence.
        identity = 'StochasticIntratradeResearch' in text and start.replace('-', '.') in text and end.replace('-', '.') in text
        if identity and classify_log(text) == 'FAIL':
            break
        if complete and identity and classify_log(text) == 'PASS':
            break
        time.sleep(2)
    # Logs may contain an unmasked account ID. Store only whitelisted diagnostic lines.
    safe_lines = [line for line in text.splitlines() if re.search(
        r'test passed|shutdown finished|OnInit|no history|no real ticks|invalid parameter|fatal', line, re.I)]
    safe_lines = [re.sub(r'\b\d{5,}\b', '[number]', line) for line in safe_lines]
    (folder / 'tester.log').write_text('\n'.join(safe_lines), encoding='utf-8')
    passed = bool(complete and identity and classify_log(text) == 'PASS')
    manifest.update(end_time=datetime.now(timezone.utc).isoformat(),
                    tester_status='PASS' if passed else 'FAIL',
                    GUI_INTERACTION_REQUIRED='NO', launcher_exit_code=process.poll())
    if passed:
        manifest['artifact_hashes'] = collect(complete, folder)
    else:
        manifest['blocker'] = ('TESTER_LAUNCH: no verified completion for this run; active terminal may ignore /config. '
                               'No process was killed. Inspect current tester before retrying.')
    for path in (ini, local_preset, folder / 'compile.log', folder / 'tester.log'):
        manifest['artifact_hashes'][path.name] = sha256(path)
    write_manifest(folder, manifest)
    return manifest


def recover(run_id):
    """Collect this nonce's output after the operator restarts XM with the saved INI."""
    if not run_id or not run_id.replace('_', '').isalnum():
        raise ValueError('Valid --run-id required')
    folder = ROOT / 'outputs/controller/runs' / run_id
    record = json.loads((folder / 'run_manifest.json').read_text())
    assert_research_range_allowed(record['from'], record['to'])
    environment = record['environment']
    source = ea_path(require_active_environment(status()))
    if sha256(source) != record['ea_hash'] or sha256(source.with_suffix('.ex5')) != record['ex5_hash']:
        raise RuntimeError('SECURITY_GATE: binary/source changed since launch')
    started = datetime.fromisoformat(record['start_time']).timestamp()
    paths = find_artifacts(environment, run_id, started)
    chunks = []
    for name, offset in record['log_offsets'].items():
        path = Path(name)
        with path.open('rb') as stream:
            stream.seek(offset)
            chunks.append(stream.read().decode('utf-16-le', errors='replace'))
    text = '\n'.join(chunks)
    if not (paths and classify_log(text) == 'PASS'
            and 'StochasticIntratradeResearch' in text
            and record['from'].replace('-', '.') in text and record['to'].replace('-', '.') in text):
        raise RuntimeError('TESTER_LAUNCH: this run has not completed; no artifacts collected')
    record['artifact_hashes'].update(collect(paths, folder))
    record.update(tester_status='PASS', end_time=datetime.now(timezone.utc).isoformat())
    write_manifest(folder, record)
    from .validation import validate_run
    return validate_run(run_id)
