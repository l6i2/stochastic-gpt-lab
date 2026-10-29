"""Read-only historical progress; a RUNNING checkpoint alone is not liveness."""
import csv
import json
from datetime import datetime
from pathlib import Path
import sys
import hashlib

import psutil

from .safety_gate import ROOT, assert_research_range_allowed
sys.path.insert(0, str(ROOT / 'python'))
from time_semantics import event_display
from native_time_mapping import NativeTimestamp, load_mapping


def last_event_time(path):
    if not path.exists():
        return None
    try:
        with path.open('rb') as stream:
            header = stream.readline().decode('utf-8-sig').strip()
            stream.seek(0, 2)
            size = stream.tell()
            stream.seek(max(0, size - 65536))
            tail = stream.read().decode('utf-8', errors='replace')
    except PermissionError:
        # MT5 may hold FILE_WRITE outputs exclusively. Never interfere with it.
        return None
    columns = next(csv.reader([header]))
    if 'signal_time_msc' not in columns:
        return None
    # Discard a potentially incomplete final line and any partial first row.
    lines = tail.split('\n')[:-1]
    for line in reversed(lines):
        values = next(csv.reader([line]))
        if len(values) == len(columns):
            value = values[columns.index('signal_time_msc')]
            if value.isdigit():
                return int(value)
    return None


def progress():
    try:
        display_mapping = load_mapping(ROOT / 'configs/native_time_mapping_v1.prepared.json')
    except ValueError:
        display_mapping = None
    state = json.loads((ROOT/'outputs/controller/checkpoints/history_state.json').read_text())
    records = []
    for path in (ROOT/'outputs/controller/runs').glob('r*/run_manifest.json'):
        records.append(json.loads(path.read_text()))
    blocks = []
    for block in state['blocks']:
        assert_research_range_allowed(block['DATE_FROM'], block['DATE_TO'])
        matches = [r for r in records if r.get('from') == block['DATE_FROM'] and r.get('to') == block['DATE_TO']]
        record = max(matches, key=lambda r: r['start_time']) if matches else {}
        active = False
        if record.get('launcher_pid'):
            try:
                process = psutil.Process(record['launcher_pid'])
                started = datetime.fromisoformat(record['start_time']).timestamp()
                active = (process.is_running() and process.name().lower() == 'terminal64.exe'
                          and abs(process.create_time() - started) < 60)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        artifacts = []
        last = None
        for root in record.get('environment', {}).get('TESTER_AGENT_FOLDERS', []):
            folder = Path(root)/'MQL5/Files'
            prefix = record.get('run_id', '')
            if not prefix:
                continue
            for path in folder.glob(prefix + '_*.csv'):
                artifacts.append(dict(name=path.name, bytes=path.stat().st_size))
            last = last_event_time(folder/(prefix + '_stochastic_events.csv')) or last
        # The native signal number is preserved. No UTC inference from its name.
        signal_display = None
        if last is not None:
            source = {'signal_time_msc': last, 'run_id': record.get('run_id')}
            digest = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()
            signal_display = event_display(NativeTimestamp(last // 1000, last, 'US30Cash',
                record.get('environment', {}).get('SERVER', 'UNVERIFIED_SERVER'), digest), display_mapping)
        blocks.append(dict(block=block['BLOCK_ID'], checkpoint_status=block['STATUS'],
                           run_id=record.get('run_id'), tester_status=record.get('tester_status'),
                           process_active=active, last_observed_at=record.get('last_observed_at'),
                           last_exported_signal_time_msc=last, signal_display=signal_display, live_artifacts=artifacts))
    return dict(blocks=blocks, FINAL_TEST='LOCKED', LIVE_TRADING=False)


if __name__ == '__main__':
    print(json.dumps(progress(), indent=2))
