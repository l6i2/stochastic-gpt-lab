import json
from datetime import datetime, timedelta, timezone
from .artifact_collector import write_manifest
from .safety_gate import ROOT, boundaries, assert_research_range_allowed


def plan():
    coverage = json.loads((ROOT / 'outputs/history_coverage.json').read_text())['real_ticks']
    first = datetime.fromisoformat(coverage['first_server_time']).date()
    last_available = datetime.fromisoformat(coverage['last_server_time']).date()
    # Exclude the entire server date containing FINAL_TEST, including boundary-day lookahead.
    last_allowed = datetime.fromtimestamp(boundaries()['final_test_start_signal_time_msc'] / 1000,
                                         timezone.utc).date() - timedelta(days=1)
    last = min(last_available, last_allowed)
    blocks = []
    for year in range(first.year, last.year + 1):
        start = max(first, datetime(year, 1, 1).date()).isoformat()
        end = min(last, datetime(year, 12, 31).date()).isoformat()
        assert_research_range_allowed(start, end)
        blocks.append(dict(BLOCK_ID=str(year), DATE_FROM=start, DATE_TO=end,
                           STATUS='PENDING', VALIDATOR=None, ARTIFACTS=[], RUN_ID=None))
    return blocks


def history(resume=False, timeout=3600):
    from .tester_runner import run
    from .validation import validate_run
    checkpoint = ROOT / 'outputs/controller/checkpoints/history_state.json'
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    blocks = plan()
    if checkpoint.exists():
        saved = json.loads(checkpoint.read_text())
        if [(b['DATE_FROM'], b['DATE_TO']) for b in saved['blocks']] != [
                (b['DATE_FROM'], b['DATE_TO']) for b in blocks]:
            raise RuntimeError('SECURITY_GATE: checkpoint coverage/split mismatch')
        blocks = saved['blocks']
    # Only a complete smoke acceptance can open the historical execution path.
    smokes = []
    for path in (ROOT / 'outputs/controller/runs').glob('r*/run_manifest.json'):
        record = json.loads(path.read_text())
        if (record.get('from') == '2024-01-01' and record.get('to') == '2024-01-31'
                and record.get('VALIDATION_STATUS') == 'PASS'
                and record.get('CAUSALITY_STATUS') == 'PASS'):
            smokes.append(record)
    def save():
        temporary = checkpoint.with_suffix('.tmp')
        temporary.write_text(json.dumps({'blocks': blocks}, indent=2))
        temporary.replace(checkpoint)
    save()
    if not smokes:
        raise RuntimeError('VALIDATION: AUTOMATED_SMOKE_TEST has not passed; history blocked')
    for block in blocks:
        if block['STATUS'] == 'PASS':
            continue
        block['STATUS'] = 'RUNNING'
        save()
        try:
            record = run(block['DATE_FROM'], block['DATE_TO'], timeout=timeout)
            block['RUN_ID'] = record['run_id']
            block['ARTIFACTS'] = list(record['artifact_hashes'])
            if record['tester_status'] != 'PASS':
                raise RuntimeError('TESTER_LAUNCH: history block failed')
            validation = validate_run(record['run_id'])
            block['VALIDATOR'] = validation
            if validation['VALIDATION_STATUS'] != 'PASS':
                raise RuntimeError('VALIDATION: history block failed')
            block['STATUS'] = 'PASS'
            save()
        except Exception as error:
            block['STATUS'] = 'FAIL'
            block['ERROR'] = str(error)
            save()
            raise
    return {'HISTORY_STATUS': 'PASS', 'blocks': blocks}
