"""Cold-start the verified XM installation; never terminate terminal processes."""
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psutil

from .artifact_collector import collect, find_artifacts, write_manifest
from .compile_runner import EA, ea_path, sha256
from .mt5_env import active_processes, read_origin
from .safety_gate import ROOT, assert_research_range_allowed
from .tester_config import config, preset, write_preset, tester_end


def now():
    return datetime.now(timezone.utc).isoformat()


def pinned_environment():
    candidates = sorted((ROOT / 'outputs/controller/runs').glob('r*/run_manifest.json'), reverse=True)
    for path in candidates:
        record = json.loads(path.read_text())
        environment = record.get('environment', {})
        if environment.get('READ_ONLY_API_STATUS') == 'VERIFIED' and environment.get('XM_ACTIVE'):
            source = ea_path(environment)
            if record.get('ea_hash') != sha256(source) or record.get('ex5_hash') != sha256(source.with_suffix('.ex5')):
                continue
            data = Path(environment['DATA_FOLDER']).resolve()
            terminal = Path(environment['TERMINAL_PATH']).resolve()
            if Path(read_origin(data / 'origin.txt')).resolve() != terminal.parent:
                raise RuntimeError('ENVIRONMENT: origin changed since verified session')
            if not terminal.is_file() or not Path(environment['METAEDITOR_PATH']).is_file():
                raise RuntimeError('ENVIRONMENT: verified binaries missing')
            record.setdefault('compile_log',str(path.parent/'compile.log'))
            return environment, record
    raise RuntimeError('ENVIRONMENT: no matching verified compilation/environment checkpoint')


def log_paths(environment):
    data = Path(environment['DATA_FOLDER'])
    roots = {'terminal': data / 'logs', 'tester': data / 'Tester/logs', 'mql5': data / 'MQL5/Logs'}
    for index, folder in enumerate(environment['TESTER_AGENT_FOLDERS']):
        roots[f'agent_{index}'] = Path(folder) / 'logs'
    return roots


def baseline(environment):
    return {str(p): {'size': p.stat().st_size, 'mtime_ns': p.stat().st_mtime_ns,
                     'kind': kind} for kind, root in log_paths(environment).items()
            for p in root.glob('*.log')}


def read_deltas(environment, previous):
    result = {}
    for kind, root in log_paths(environment).items():
        chunks = []
        for path in root.glob('*.log'):
            offset = previous.get(str(path), {}).get('size', 0)
            size = path.stat().st_size
            if size < offset:
                raise RuntimeError('TESTER_LAUNCH: log truncated during run')
            with path.open('rb') as stream:
                stream.seek(offset)
                raw = stream.read()
            if raw:
                encoding = 'utf-16' if raw.startswith(b'\xff\xfe') else 'utf-16-le' if b'\x00' in raw[:100] else 'utf-8-sig'
                chunks.append(raw.decode(encoding, errors='replace').lstrip('\ufeff'))
        result[kind] = '\n'.join(chunks)
    return result


def redact(text):
    safe = []
    for line in text.splitlines():
        if re.search(r'password|passwd|token|authorization', line, re.I):
            safe.append('[sensitive line omitted]')
        else:
            line = re.sub(r'#\d+', '#***', line)
            line = re.sub(r"'\d{5,}'", "'***'", line)
            line = re.sub(r'(?i)(login|account)(\s*[:=]?\s*)\d+', r'\1\2***', line)
            safe.append(line)
    return '\n'.join(safe)


def run_cold(start, end, ea=EA, symbol='US30Cash', timeout=1800, variant=1):
    assert_research_range_allowed(start, end)
    if ea != EA or symbol != 'US30Cash' or variant not in (1, 2, 3):
        raise ValueError('Unsupported research launch')
    if active_processes():
        raise RuntimeError('TESTER_LAUNCH: cold start requires no running terminal')
    environment, compiled = pinned_environment()
    source = ea_path(environment)
    run_id = 'r' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '_' + uuid.uuid4().hex[:8]
    folder = ROOT / 'outputs/controller/runs' / run_id
    folder.mkdir(parents=True)
    inputs = preset(run_id)
    local_preset = folder / (run_id + '.set')
    write_preset(local_preset, inputs)
    profiles = [Path(environment['TESTER_PROFILES'])]
    if variant >= 2:
        profiles.append(Path(environment['TERMINAL_PATH']).parent / 'MQL5/Profiles/Tester')
    for directory in profiles:
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / local_preset.name
        if target.exists():
            raise RuntimeError('MT5_CONFIG: unique preset collision')
        target.write_bytes(local_preset.read_bytes())
    ini = folder / 'tester.ini'
    (Path(environment['DATA_FOLDER']) / 'reports/controller').mkdir(parents=True, exist_ok=True)
    content = '[Experts]\nAllowLiveTrading=0\nAllowDllImport=0\n' + config(
        start, end, local_preset.name, 'reports\\controller\\' + run_id + '.htm')
    content = content.replace('ShutdownTerminal=0', 'ShutdownTerminal=1')
    if variant == 3:
        content = content.replace('Expert=StochasticIntratradeResearch\\StochasticIntratradeResearchEA\n',
                                  'Expert=StochasticIntratradeResearch\\StochasticIntratradeResearchEA.ex5\n')
    ini.write_text(content, encoding='ascii' if variant != 2 else 'utf-16')
    command = [environment['TERMINAL_PATH'], '/config:' + str(ini.resolve())]
    previous = baseline(environment)
    (folder / 'launch.json').write_text(json.dumps(dict(command=command,
        windows_command_line=subprocess.list2cmdline(command), logs_before=previous,
        MT5_RUNNING_BEFORE_TEST='NO', variant=variant, prepared_at=now()), indent=2))
    shutil.copy2(compiled['compile_log'], folder / 'compile.log')
    manifest = {k: compiled[k] for k in ('ea_path', 'ea_hash', 'ex5_hash', 'COMPILE_STATUS', 'ERRORS', 'WARNINGS', 'EX5_EXISTS')}
    manifest.update(run_id=run_id, git_sha=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT,text=True).strip(),
        environment=environment, symbol=symbol, period='M5', model='real_ticks', optimization=False,
        inputs=inputs, start_time=now(), tester_status='RUNNING', artifact_hashes={}, tester_to_exclusive=tester_end(end),
        MT5_CLOSED_BEFORE_LAUNCH=True, variant=variant, **{'from': start, 'to': end})
    write_manifest(folder, manifest)
    started = time.time()
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    process = subprocess.Popen(command, startupinfo=startup)
    manifest['launcher_pid'] = process.pid
    write_manifest(folder, manifest)
    deadline = time.monotonic() + timeout
    last_update = 0
    deltas = {}
    while time.monotonic() < deadline:
        deltas = read_deltas(environment, previous)
        if time.monotonic() - last_update > 15:
            for kind, text in deltas.items():
                (folder / (kind + '.log')).write_text(redact(text), encoding='utf-8')
            manifest['last_observed_at'] = now()
            manifest['launcher_exit_code'] = process.poll()
            write_manifest(folder, manifest)
            last_update = time.monotonic()
        if process.poll() is not None:
            time.sleep(2)
            deltas = read_deltas(environment, previous)
            break
        time.sleep(2)
    text = '\n'.join(deltas.values())
    paths = find_artifacts(environment, run_id, started)
    # Evidence must describe the dedicated expert, exact dates, real ticks and M5.
    evidence = dict(test_passed=bool(re.search(r'test passed', text, re.I)),
                    shutdown_finished=bool(re.search(r'shutdown finished', text, re.I)),
                    expert=EA in text, symbol=symbol in text, timeframe='M5' in text,
                    start=start.replace('-', '.') in text, end=tester_end(end) in text,
                    real_ticks=bool(re.search(r'real ticks|real tick', text, re.I)),
                    process_exited=process.poll() is not None, artifacts=bool(paths),
                    data_folder=environment['DATA_FOLDER'].lower() in text.lower(),
                    demo_account=bool(re.search(r'demo account',text,re.I)))
    # Data gaps and generated-tick fallback require investigation, never silent acceptance.
    manifest['diagnostics'] = [redact(line) for line in text.splitlines()
        if re.search(r'error|failed|fatal|no history|no real ticks|invalid|not found|cannot|generated ticks|discarded',line,re.I)]
    passed = all(evidence.values()) and not re.search(r'FATAL RESEARCH RUN|OnInit.*(?:error|fail)|initialization.*failed', text, re.I)
    manifest.update(end_time=now(), tester_status='PASS' if passed else 'FAIL', evidence=evidence,
                    launcher_exit_code=process.poll(), GUI_INTERACTION_REQUIRED='NO')
    for kind, body in deltas.items():
        (folder / (kind + '.log')).write_text(redact(body),encoding='utf-8')
    if passed:
        manifest['artifact_hashes'].update(collect(paths, folder))
    for path in folder.iterdir():
        if path.is_file() and path.name != 'run_manifest.json':
            manifest['artifact_hashes'][path.name] = sha256(path)
    write_manifest(folder, manifest)
    return manifest


def monitor_cold(run_id, timeout=1800):
    """Resume observation of an existing nonce after a monitor interruption."""
    if not run_id.replace('_','').isalnum():
        raise ValueError('Invalid run ID')
    folder = ROOT / 'outputs/controller/runs' / run_id
    manifest = json.loads((folder / 'run_manifest.json').read_text())
    launch = json.loads((folder / 'launch.json').read_text())
    environment = manifest['environment']
    previous = launch['logs_before']
    assert_research_range_allowed(manifest['from'], manifest['to'])
    started = datetime.fromisoformat(manifest['start_time']).timestamp()
    deadline = time.monotonic() + timeout
    def running():
        try:
            p = psutil.Process(manifest['launcher_pid'])
            return p.is_running() and p.name().lower() == 'terminal64.exe' and abs(p.create_time()-started)<60
        except psutil.NoSuchProcess:
            return False
    while running() and time.monotonic() < deadline:
        deltas = read_deltas(environment, previous)
        for kind, body in deltas.items():
            (folder / (kind + '.log')).write_text(redact(body),encoding='utf-8')
        manifest['last_observed_at'] = now()
        write_manifest(folder, manifest)
        time.sleep(10)
    deltas = read_deltas(environment, previous)
    text = '\n'.join(deltas.values())
    paths = find_artifacts(environment, run_id, started)
    evidence = dict(test_passed=bool(re.search(r'test passed', text, re.I)),
        shutdown_finished=bool(re.search(r'shutdown finished', text,re.I)),
        expert=EA in text, symbol=manifest['symbol'] in text, timeframe='M5' in text,
        start=manifest['from'].replace('-','.') in text, end=manifest.get('tester_to_exclusive',manifest['to'].replace('-','.')) in text,
        real_ticks=bool(re.search(r'real ticks|real tick',text,re.I)),process_exited=not running(),artifacts=bool(paths))
    evidence['data_folder']=environment['DATA_FOLDER'].lower() in text.lower()
    evidence['demo_account']=bool(re.search(r'demo account',text,re.I))
    passed = all(evidence.values()) and not re.search(r'FATAL RESEARCH RUN|OnInit.*(?:error|fail)|initialization.*failed',text,re.I)
    manifest.update(end_time=now(),tester_status='PASS' if passed else 'FAIL',evidence=evidence,
                    GUI_INTERACTION_REQUIRED='NO', monitor_resumed=True)
    for kind, body in deltas.items():
        (folder / (kind + '.log')).write_text(redact(body),encoding='utf-8')
    if passed and not any(name.endswith('stochastic_events.csv') for name in manifest['artifact_hashes']):
        manifest['artifact_hashes'].update(collect(paths,folder))
    for path in folder.iterdir():
        if path.is_file() and path.name not in ('run_manifest.json','run_manifest.tmp'):
            manifest['artifact_hashes'][path.name]=sha256(path)
    write_manifest(folder,manifest)
    return manifest
