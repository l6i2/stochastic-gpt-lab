"""CLI launch with bounded waiting. Never terminates an existing terminal."""
import re


def read_log(path):
    raw = path.read_bytes()
    return raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig', errors='replace')


def classify_log(text):
    failures = re.findall(r'OnInit[^\n]*(?:error|fail)|fatal|no history|no real ticks|invalid parameter|file[^\n]*error', text, re.I)
    return 'FAIL' if failures else ('PASS' if re.search(r'test passed', text, re.I) else 'INCOMPLETE')


def run(start, end, ea='StochasticIntratradeResearchEA', symbol='US30Cash', timeout=3600):
    from .cold_start import run_cold
    return run_cold(start, end, ea, symbol, timeout)


def recover(run_id):
    from .cold_start import monitor_cold
    from .validation import validate_run
    record = monitor_cold(run_id)
    if record['tester_status'] != 'PASS':
        raise RuntimeError('TESTER_LAUNCH: this run has not passed')
    return validate_run(run_id)
