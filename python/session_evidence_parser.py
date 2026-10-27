"""Package native session observations locally without certifying server UTC."""
import hashlib
import json
from pathlib import Path
from runtime_session_guard import RuntimeSessionGuard


def parse_sessions(source: Path, folder: Path):
    rows = source.read_text(encoding='utf-8-sig').splitlines()
    if not rows or rows[-1] != 'XM_SESSION_PROBE|END':
        raise ValueError('SESSION_END_MISSING')
    start = dict(part.split('=', 1) for part in rows[0].split('|')[2:])
    report = {'symbol': start['symbol'], 'server': start['server'], 'records': rows,
              'clock_basis': 'UNVERIFIED_NATIVE_LABELS', 'holiday_schedule': 'UNKNOWN',
              'status': 'OBSERVED_ONLY_NOT_ACTIVATED', 'raw_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    path = folder / 'session_observations.json'
    with path.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
    with path.with_name(path.name+'.sha256').open('x') as stream:
        stream.write(hashlib.sha256(path.read_bytes()).hexdigest()+'\n')
    RuntimeSessionGuard(path)  # Structural validation only; runtime gates still required.
    return {'status': 'STRUCTURE_PASS_RUNTIME_GUARD_REQUIRED', 'holiday_schedule': 'UNKNOWN',
            'native_to_utc_mapping': 'UNVERIFIED', 'activated': False}
