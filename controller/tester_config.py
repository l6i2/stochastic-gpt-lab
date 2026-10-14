"""MetaQuotes documented [Tester] configuration, Model=4 (real ticks)."""
from pathlib import Path
from datetime import date, timedelta
from .safety_gate import assert_research_range_allowed
from .profiles import BASE_EA, profile


def preset(run_id, ea=BASE_EA):
    # Numeric enum values are taken from the dedicated EA source.
    values = dict(LIVE_TRADING='false', simulation_mode='0', ConfirmRealTickTesterMode='true',
                  trigger_line='0', profile_weight='0', ProfileBinSize='10.0',
                  ResearchSymbol='US30Cash', SnapshotOutputFile=f'{run_id}_intratrade_snapshots.csv',
                  TargetOutputFile=f'{run_id}_intratrade_snapshot_targets.csv',
                  OutputFile=f'{run_id}_stochastic_events.csv')
    if not run_id.replace('_', '').isalnum():
        raise ValueError('Invalid run ID')
    if profile(ea)['schema'] == '3.0':
        values['ExecutionQuoteOutputFile'] = f'{run_id}_bar_execution_quotes.csv'
    return values


def config(start, end, preset_name, report, manifest=None, ea=BASE_EA):
    assert_research_range_allowed(start, end, manifest)
    if Path(str(report)).is_absolute() or '..' in str(report) or '\n' in str(report):
        raise ValueError('Report must be a safe path relative to the terminal Data Folder')
    values = dict(Expert=profile(ea)['folder'] + '\\' + ea,
                  ExpertParameters=preset_name, Symbol='US30Cash', Period='M5', Model=4,
                  FromDate=start.replace('-', '.'), ToDate=tester_end(end),
                  Optimization=0, ForwardMode=0, Deposit=10000, Currency='USD', Report=str(report),
                  ReplaceReport=0, ShutdownTerminal=0, Visual=0, UseLocal=1, UseRemote=0, UseCloud=0)
    return '[Tester]\n' + ''.join(f'{k}={v}\n' for k, v in values.items())


def tester_end(end):
    # MT5 stops at 00:00 on ToDate. CLI ranges use inclusive calendar dates.
    return (date.fromisoformat(end) + timedelta(days=1)).strftime('%Y.%m.%d')


def write_preset(path, inputs):
    Path(path).write_text(''.join(f'{k}={v}\n' for k, v in inputs.items()), encoding='utf-16')
