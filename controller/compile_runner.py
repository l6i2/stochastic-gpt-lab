import hashlib
import re
import subprocess
from pathlib import Path
from .mt5_env import require_active_environment
from .safety_gate import assert_safe_source

EA = 'StochasticIntratradeResearchEA'


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def ea_path(environment, ea=EA):
    require_active_environment(environment)
    if ea != EA:
        raise RuntimeError('SECURITY_GATE: only dedicated research EA allowed')
    root = Path(environment['DATA_FOLDER']).resolve() / 'MQL5'
    source = root / 'Experts/StochasticIntratradeResearch' / (ea + '.mq5')
    source = source.resolve(strict=True)
    if not source.is_relative_to(root.resolve()):
        raise RuntimeError('SECURITY_GATE: EA outside active Data Folder')
    assert_safe_source(source)
    seen = set()

    def includes(file):
        file = file.resolve(strict=True)
        if file in seen:
            return
        seen.add(file)
        if not file.is_relative_to(root.resolve()):
            raise RuntimeError('SECURITY_GATE: include outside active MQL5')
        assert_safe = file == source
        text = file.read_text(encoding='utf-8-sig')
        if re.search(r'\b(OrderSend|OrderSendAsync|CTrade|PositionOpen)\b', text, re.I):
            raise RuntimeError('SECURITY_GATE: trading API in source/include')
        for bracket, name in re.findall(r'#include\s*([<"])([^>"\r\n]+)[>"]', text):
            includes((root / 'Include' if bracket == '<' else file.parent) / name)
    includes(source)
    return source


def compile_ea(environment, run_dir, ea=EA):
    source = ea_path(environment, ea)
    editor = Path(environment['METAEDITOR_PATH'])
    if editor.parent.resolve() != Path(environment['TERMINAL_PATH']).parent.resolve():
        raise RuntimeError('ENVIRONMENT: MetaEditor installation mismatch')
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    log = run_dir / 'compile.log'
    if log.exists():
        raise RuntimeError('MQL5_COMPILE: use a fresh run directory')
    started = __import__('time').time()
    subprocess.run([str(editor), '/compile:' + str(source), '/log:' + str(log.resolve())],
                   timeout=180, check=False)
    raw = log.read_bytes()
    text = raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig', errors='replace')
    matches = re.findall(r'(\d+) errors?,\s*(\d+) warnings?', text, re.I)
    if not matches:
        raise RuntimeError('MQL5_COMPILE: no compiler summary')
    errors, warnings = map(int, matches[-1])
    binary = source.with_suffix('.ex5')
    passed = errors == 0 and binary.is_file() and binary.stat().st_mtime >= started - 2
    result = dict(COMPILE_STATUS='PASS' if passed else 'FAIL', ERRORS=errors, WARNINGS=warnings,
                  EX5_EXISTS=binary.is_file(), ea_path=str(source), ea_hash=sha256(source),
                  ex5_hash=sha256(binary) if binary.exists() else None, compile_log=str(log))
    if not passed:
        raise RuntimeError('MQL5_COMPILE: ' + str(result))
    return result
