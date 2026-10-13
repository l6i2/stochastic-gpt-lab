"""Discover terminals without starting one, logging in, or reading account files."""
from __future__ import annotations

import json
import os
import platform
import subprocess
from pathlib import Path


def active_processes():
    if os.name != 'nt':
        return []
    try:
        import psutil
    except ImportError:
        pass
    else:
        rows = []
        for process in psutil.process_iter(['name', 'exe', 'cmdline']):
            try:
                if (process.info['name'] or '').lower() == 'terminal64.exe':
                    rows.append(dict(ProcessId=process.pid, ExecutablePath=process.info['exe'],
                                     CommandLine=' '.join(process.info['cmdline'] or [])))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return rows
    script = ("@(Get-CimInstance Win32_Process -Filter \"name='terminal64.exe'\" | "
              "Select-Object ProcessId,ExecutablePath,CommandLine) | ConvertTo-Json -Compress")
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                            capture_output=True, text=True, timeout=30, check=True)
    rows = json.loads(result.stdout or '[]')
    return rows if isinstance(rows, list) else [rows]


def read_origin(path):
    raw = path.read_bytes()
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig').strip()


def resolve_active(processes, candidates):
    """Fail closed on multiple processes/folders or portable/custom launch modes."""
    if len(processes) != 1:
        return None
    process = processes[0]
    command = (process.get('CommandLine') or '').lower()
    if '/portable' in command or '/config' in command:
        return None
    executable = process.get('ExecutablePath')
    if not executable:
        return None
    matches = [row for row in candidates
               if Path(row['terminal']).resolve() == Path(executable).resolve()]
    return matches[0] if len(matches) == 1 else None


def account_mode(mode):
    return {0: 'DEMO', 1: 'CONTEST', 2: 'REAL'}.get(mode, 'UNKNOWN')


def status():
    base = Path(os.environ.get('APPDATA', '')) / 'MetaQuotes' / 'Terminal'
    candidates = []
    for origin in sorted(base.glob('*/origin.txt')):
        try:
            install = Path(read_origin(origin))
            terminal = install / 'terminal64.exe'
            editor = install / 'metaeditor64.exe'
            if terminal.is_file():
                candidates.append({'terminal': str(terminal), 'metaeditor': str(editor),
                                   'data_folder': str(origin.parent),
                                   'xm': 'xm' in str(install).lower()})
        except (OSError, UnicodeError):
            continue
    processes = active_processes()
    active = resolve_active(processes, candidates)
    result = {
        'WINDOWS_VERSION': platform.platform(), 'MT5_FOUND': bool(candidates),
        'ACTIVE_TERMINAL_COUNT': len(processes), 'INSTALLATIONS': candidates,
        'TERMINAL_PATH': active['terminal'] if active else None,
        'METAEDITOR_PATH': active['metaeditor'] if active else None,
        'DATA_FOLDER': active['data_folder'] if active else None,
        'XM_ACTIVE': bool(active and active['xm']), 'ACCOUNT_LOGIN_MASKED': None,
        'ACCOUNT_MODE': 'UNKNOWN', 'US30Cash_AVAILABLE': None, 'CONNECTED': None,
        'SAFE_FOR_RESEARCH': False, 'DEMO_EXECUTION_ALLOWED': 'NO',
        'LIVE_TRADING': False, 'DEMO_EXECUTOR': 'NOT_IMPLEMENTED',
        'READ_ONLY_API_STATUS': 'NOT_QUERIED',
    }
    if active:
        data = Path(active['data_folder'])
        result.update(MQL5_FOLDER=str(data / 'MQL5'),
                      EXPERTS_FOLDER=str(data / 'MQL5/Experts'),
                      TESTER_PROFILES=str(data / 'MQL5/Profiles/Tester'),
                      TESTER_AGENT_FOLDERS=[str(p) for p in sorted(
                          (base.parent / 'Tester').glob('*/Agent-*'))],
                      TESTER_LOGS=[str(p) for p in sorted((data / 'Tester/logs').glob('*.log'))])
        # initialize only attaches to an already verified running terminal. No login arguments.
        try:
            import MetaTrader5 as mt5
        except ImportError:
            result['READ_ONLY_API_STATUS'] = 'PACKAGE_UNAVAILABLE'
        else:
            try:
                if mt5.initialize(path=active['terminal'], timeout=5000):
                    info = mt5.terminal_info()
                    account = mt5.account_info()
                    verified = bool(info and Path(info.data_path).resolve() == data.resolve())
                    if verified:
                        result['CONNECTED'] = bool(info.connected)
                        result['US30Cash_AVAILABLE'] = mt5.symbol_info('US30Cash') is not None
                        if account:
                            result['ACCOUNT_MODE'] = account_mode(account.trade_mode)
                            result['ACCOUNT_LOGIN_MASKED'] = '***' + str(account.login)[-2:]
                        result['READ_ONLY_API_STATUS'] = 'VERIFIED'
                    else:
                        result['READ_ONLY_API_STATUS'] = 'DATA_FOLDER_MISMATCH'
                else:
                    result['READ_ONLY_API_STATUS'] = 'ATTACH_FAILED'
            finally:
                mt5.shutdown()
        result['SAFE_FOR_RESEARCH'] = bool(
            result['READ_ONLY_API_STATUS'] == 'VERIFIED' and result['XM_ACTIVE']
            and result['CONNECTED'] and result['US30Cash_AVAILABLE']
            and result['ACCOUNT_MODE'] == 'DEMO')
    return result


def require_active_environment(environment):
    if not environment.get('DATA_FOLDER') or not environment.get('XM_ACTIVE'):
        raise RuntimeError('ENVIRONMENT: active XM terminal and unique Data Folder not verified')
    if environment.get('READ_ONLY_API_STATUS') != 'VERIFIED':
        raise RuntimeError('ENVIRONMENT: active Data Folder requires read-only API verification')
    return environment
