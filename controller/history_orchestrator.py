import json
from datetime import datetime, timedelta, timezone
from pathlib import Path, PureWindowsPath
from .artifact_collector import atomic_json
from .safety_gate import ROOT, boundaries, assert_research_range_allowed
from .tester_config import tester_end
from .profiles import BASE_EA, profile


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


def is_validated_smoke(record, ea):
    """Require one completed, split-safe smoke for the selected producer."""
    selected = profile(ea)
    try:
        start = datetime.fromisoformat(record['from']).date()
        end = datetime.fromisoformat(record['to']).date()
        span = (end - start).days + 1
    except (KeyError, TypeError, ValueError):
        return False
    inputs = record.get('inputs', {})
    environment = record.get('environment', {})
    evidence = record.get('evidence', {})
    live_values = [value for value in (record.get('LIVE_TRADING'),
                   inputs.get('LIVE_TRADING'), environment.get('LIVE_TRADING')) if value is not None]
    live_values = [value.strip().lower() == 'true' if isinstance(value, str) else bool(value)
                   for value in live_values]
    common = (record.get('tester_status') == 'PASS'
              and record.get('VALIDATION_STATUS') == 'PASS'
              and record.get('CAUSALITY_STATUS') == 'PASS'
              and record.get('tester_to_exclusive') == tester_end(record.get('to', ''))
              and record.get('COMPILE_STATUS') == 'PASS'
              and bool(live_values) and not any(live_values)
              and environment.get('ACCOUNT_MODE') == 'DEMO'
              and environment.get('DEMO_EXECUTION_ALLOWED') == 'NO'
              and record.get('symbol') == 'US30Cash'
              and record.get('period') == 'M5'
              and record.get('model') == 'real_ticks'
              and record.get('optimization') is False
              and record.get('ea_hash')
              and PureWindowsPath(record.get('ea_path', '')).stem == ea
              and 1 <= span <= 31)
    if not common:
        return False
    if selected['schema'] == '3.0':
        return (record.get('BASELINE_REPLAY') == 'PASS'
                and evidence.get('real_ticks') is True
                and evidence.get('artifacts') is True
                and evidence.get('demo_account') is True)
    return start == datetime(2024, 1, 1).date() and end == datetime(2024, 1, 31).date()


def history(resume=False, timeout=3600, ea=BASE_EA):
    from .tester_runner import run
    from .validation import validate_run
    selected = profile(ea)
    output = ROOT / 'outputs' / selected['namespace']
    checkpoint = output / 'checkpoints/history_state.json'
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
    for path in (output / 'runs').glob('r*/run_manifest.json'):
        record = json.loads(path.read_text())
        if is_validated_smoke(record, ea):
            smokes.append(record)
    def save():
        atomic_json(checkpoint,{'blocks':blocks})
    save()
    if not smokes:
        raise RuntimeError('VALIDATION: AUTOMATED_SMOKE_TEST has not passed; history blocked')
    for block in blocks:
        if block['STATUS'] == 'PASS':
            continue
        block['STATUS'] = 'RUNNING'
        save()
        try:
            # Reattach an interrupted monitor instead of starting a duplicate tester.
            interrupted=[]
            completed=[]
            for path in (output/'runs').glob('r*/run_manifest.json'):
                item=json.loads(path.read_text())
                if (item.get('from')==block['DATE_FROM'] and item.get('to')==block['DATE_TO']
                        and item.get('tester_status')=='PASS' and item.get('MT5_CLOSED_BEFORE_LAUNCH')
                        and item.get('artifact_hashes')):
                    completed.append(item)
                if (item.get('from')==block['DATE_FROM'] and item.get('to')==block['DATE_TO']
                        and item.get('tester_status')=='RUNNING' and item.get('MT5_CLOSED_BEFORE_LAUNCH')):
                    interrupted.append(item)
            if completed:
                # Revalidate existing evidence after a validator remediation.
                # Never rerun a successful tester merely because acceptance failed.
                record = max(completed, key=lambda r:r['start_time'])
                block['RUN_ID'] = record['run_id']
                save()
            elif interrupted:
                from .cold_start import monitor_cold
                item=max(interrupted,key=lambda r:r['start_time'])
                block['RUN_ID'] = item['run_id']
                save()
                record=monitor_cold(item['run_id'],timeout=timeout,ea=ea)
            else:
                arguments = dict(timeout=timeout)
                if ea != BASE_EA:
                    arguments['ea'] = ea
                record = run(block['DATE_FROM'], block['DATE_TO'], **arguments)
            block['RUN_ID'] = record['run_id']
            block['ARTIFACTS'] = list(record['artifact_hashes'])
            if record['tester_status'] != 'PASS':
                raise RuntimeError('TESTER_LAUNCH: history block failed')
            validation = validate_run(record['run_id'], ea=ea)
            block['VALIDATOR'] = validation
            if validation['VALIDATION_STATUS'] != 'PASS':
                raise RuntimeError('VALIDATION: history block failed')
            block['STATUS'] = 'PASS'
            block.pop('ERROR', None)
            save()
        except Exception as error:
            block['STATUS'] = 'FAIL'
            block['ERROR'] = str(error)
            save()
            raise
    return {'HISTORY_STATUS': 'PASS', 'blocks': blocks}
