"""Compile pinned research artifacts only; never starts MT5 or runs a probe."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
TERMINAL = Path(r'C:\Program Files\XM Global SC MT5 Terminal\terminal64.exe')
DATA = Path.home() / 'AppData/Roaming/MetaQuotes/Terminal/20C285FE08971A9A2E814AAC44AFC9D2'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    origin = DATA / 'origin.txt'
    raw = origin.read_bytes()
    install = Path(raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig').strip())
    if install.resolve() != TERMINAL.parent.resolve():
        raise ValueError('PINNED_PC_A_INSTALLATION_MISMATCH')
    expert = DATA / 'MQL5/Experts/StochasticBarDecisionResearch'
    probe = DATA / 'MQL5/Scripts/ResearchDiagnostics/PC_A'
    pairs = [(ROOT / 'mt5' / name, expert / name) for name in
             ('StochasticBarDecisionResearchEA.mq5', 'ResearchCore.mqh', 'HeikinAshiCore.mqh')]
    pairs.append((ROOT / 'tests/mql5/FullClockAndTimeSemanticsProbe.mq5',
                  probe / 'FullClockAndTimeSemanticsProbe.mq5'))
    # These destinations were created by this migration. Refuse unrelated changes.
    for source, destination in pairs:
        if not destination.resolve().is_relative_to(DATA.resolve()):
            raise ValueError('DEPLOYMENT_OUTSIDE_PINNED_DATA_FOLDER')
        if destination.exists() and destination.read_bytes().replace(b'\r\n', b'\n') != source.read_bytes().replace(b'\r\n', b'\n'):
            raise ValueError('DEPLOYED_SOURCE_HAS_UNREVIEWED_CHANGES:' + destination.name)
    folder = ROOT / 'outputs/pc_a' / ('compile_' + uuid.uuid4().hex[:12])
    folder.mkdir(parents=True, exist_ok=False)
    for source, destination in pairs:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    result = dict(observed_utc=datetime.now(timezone.utc).isoformat(), orders_sent=0,
                  execution_performed=False, sources={str(p.relative_to(ROOT)): digest(p) for p, _ in pairs}, builds=[])
    for _, source in pairs:
        if source.suffix != '.mq5':
            continue
        log = folder / (source.stem + '.log')
        editor = TERMINAL.with_name('metaeditor64.exe')
        # MetaEditor expects quotes after the switch colon for paths with spaces.
        started = time.time()
        subprocess.run(f'"{editor}" /compile:"{source}" /log:"{log}"',
                       timeout=120, creationflags=subprocess.CREATE_NO_WINDOW, check=False)
        raw = log.read_bytes()
        text = raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig')
        summary = re.findall(r'(\d+) errors?,\s*(\d+) warnings?', text)
        binary = source.with_suffix('.ex5')
        # Native compiler return codes differ by build; require a fresh log and binary.
        passed = bool(summary and summary[-1] == ('0', '0') and binary.is_file()
                      and binary.stat().st_mtime >= started - 2)
        result['builds'].append(dict(source=source.name, status='PASS' if passed else 'FAIL',
                                    source_sha256=digest(source), ex5_sha256=digest(binary) if binary.exists() else None,
                                    compile_log_sha256=digest(log)))
        (folder / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        if not passed:
            raise RuntimeError('COMPILATION_FAILED:' + source.name)
    print(json.dumps(dict(status='PASS', manifest=str(folder / 'manifest.json'), **result), indent=2))


if __name__ == '__main__':
    main()
