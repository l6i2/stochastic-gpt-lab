"""Synthetic production-MQL prefix tests in the existing isolated terminal.

No historical period, real dataset, account API, production gate or strategy is
modified. A script invokes the frozen producer OnTick against synthetic adapters;
it does not run ProductionOnInit, train, optimize, score or send orders.
"""
import csv
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
import uuid

from .artifact_collector import atomic_json
from .compile_runner import sha256
from .native_diagnostic import BASE, diagnostic_logs
from .safety_gate import ROOT

OUT = ROOT / 'outputs/pc_a_certification/native_features'
PRODUCER_SHA = 'f2e9bf43cbbdc716148847fe53e1f3dd14b21393775ccc809d05cb5e134cb88d'


def history_preflight(closed_bars):
    """Diagnostic precondition, not a patch of the frozen producer.

    Twenty is the direct-address safety floor in SnapshotTrade. It is not a
    declaration that longer lookbacks/indicators or feed history are ready.
    """
    if type(closed_bars) is not int or closed_bars < 20:
        raise ValueError('UNSAFE_SHORT_HISTORY_FOR_FROZEN_SNAPSHOT_PRODUCER')
    return dict(array_floor_satisfied=True, full_export_window=closed_bars >= 350,
                indicator_semantics_certified=False, training_authorized=False)


def harness(destination, capture_id):
    """Derive from existing fixture; frozen producer and originals stay intact."""
    from python.build_bar_replay_producer import build_probe
    if not re.fullmatch(r'nfeat_[a-f0-9]{12}', capture_id):
        raise ValueError('INVALID_SYNTHETIC_ID')
    if sha256(ROOT / 'mt5/StochasticBarDecisionResearchEA.mq5') != PRODUCER_SHA:
        raise ValueError('FROZEN_PRODUCER_CHANGED')
    history_preflight(30)
    build_probe(destination)
    text = destination.read_text(encoding='utf-8')

    def change(old, new, count=1):
        nonlocal text
        if text.count(old) != count:
            raise ValueError('FIXTURE_ANCHOR_CHANGED_' + old[:60])
        text = text.replace(old, new)

    change('const string PROBE_ID="__PROBE_ID__";',
           'string PROBE_ID="' + capture_id + '";')
    change('const int PROBE_CUTOFF_BAR=450;',
           'int PROBE_CUTOFF_BAR=450;bool prefix_only=false;long query_checks=0;')
    change('int ProbeBarIndex(){return (int)((ProbeITime("",PERIOD_M5,0)-probe_bars[0].time)/300);}',
           'int ProbeBarIndex(){datetime now=ProbeITime("",PERIOD_M5,0);'
           'for(int j=0;j<ArraySize(probe_bars);j++)if(probe_bars[j].time>=now)return j;'
           'return ArraySize(probe_bars);}')
    change('int index=ProbeBarIndex()-start,n=',
           'if(start<1){probe_failed=true;return -1;}query_checks++;int index=ProbeBarIndex()-start,n=')
    change('int index=ProbeBarIndex()-start;ArrayResize(result,count);',
           'if(start<1){probe_failed=true;return -1;}query_checks++;'
           'int index=ProbeBarIndex()-start;ArrayResize(result,count);')
    change('double ProbeK(int index){return (RawK(index)+RawK(index-1)+RawK(index-2))/3.0;}',
           'double ProbeK(int index){double num=0,den=0;for(int s=0;s<3;s++){'
           'int i=index-s;double lo=DBL_MAX,hi=-DBL_MAX;for(int j=0;j<5;j++){'
           'lo=MathMin(lo,probe_bars[i-j].low);hi=MathMax(hi,probe_bars[i-j].high);}'
           'num+=probe_bars[i].close-lo;den+=hi-lo;}return den==0?100:100*num/den;}')
    change('ArrayResize(result,0);int n=0;',
           'if(to>(ulong)((long)ProbeITime("",PERIOD_M5,0)*1000-1)){probe_failed=true;return -1;}'
           'query_checks++;ArrayResize(result,0);int n=0;')
    change('PROBE_BARS*4', 'PROBE_BARS*5')
    change('b.time=first+j*300;', 'b.time=first+j*300+(j>=410?600:0);')
    change('int offsets[4]={0,60,180,299};', 'int offsets[5]={0,0,60,180,299};')
    change('k<4;k++', 'k<5;k++')
    change('t.bid=k==0?b.open:k==1?b.high:k==2?b.low:b.close;',
           't.bid=k==0?b.open:k==1?b.open+0.25:k==2?b.high:k==3?b.low:b.close;')
    change('probe_ticks[j*4+k]', 'probe_ticks[j*5+k]')
    change('BuildProbe(perturb);ResetProbe(suffix);',
           'BuildProbe(perturb);if(prefix_only){ArrayResize(probe_bars,PROBE_CUTOFF_BAR+1);'
           'ArrayResize(probe_ticks,(PROBE_CUTOFF_BAR+1)*5+1);}ResetProbe(suffix);query_checks=0;')
    # Frozen SnapshotTrade directly addresses 20 bars. A short-history probe
    # exposed an array-bound abort; preserve that negative evidence rather than
    # patching the frozen producer. Thirty bars allow cold HA/long-window tests.
    change('last_bar=probe_bars[350].time;', 'last_bar=probe_bars[30].time;')
    change('probe_cursor=350*4;', 'probe_cursor=30*5;')
    change('b.real_volume=0;', 'b.real_volume=(j%11)*3;')
    change('IntegerToString(ArraySize(events))+"}"',
           'IntegerToString(ArraySize(events))+",\\"query_checks\\":"+IntegerToString(query_checks)+"}"')
    change('RunProbe(false,"base");RunProbe(true,"future_changed");',
           'string root_id=PROBE_ID;int cuts[3]={45,400,450};'
           'for(int c=0;c<3;c++){PROBE_CUTOFF_BAR=cuts[c];PROBE_ID=root_id+"_c"+IntegerToString(cuts[c]);'
           'prefix_only=false;RunProbe(false,"base");RunProbe(true,"future_changed");'
           'prefix_only=true;RunProbe(false,"prefix");prefix_only=false;}PROBE_ID=root_id;')
    if re.search(r'\b(OrderSend|OrderSendAsync|CTrade|PositionOpen)\b', text):
        raise ValueError('TRADING_API_FORBIDDEN')
    destination.write_text(text, encoding='utf-8', newline='\n')
    return sha256(destination)


def tables(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames
        if not columns or len(columns) != len(set(columns)):
            raise ValueError('MISSING_OR_DUPLICATE_COLUMNS')
        rows = list(reader)
        if any(None in row or any(v is None for v in row.values()) for row in rows):
            raise ValueError('MALFORMED_TABLE')
        return columns, rows


def compare_rows(base, changed, key, time_key, cutoff, columns):
    def index(rows):
        rows = [r for r in rows if int(r[time_key]) <= cutoff]
        result = {r[key]: r for r in rows}
        if len(result) != len(rows):
            raise ValueError('DUPLICATE_DECISION_ID')
        return result
    a, b = index(base), index(changed)
    if not a or a.keys() != b.keys():
        raise ValueError('DECISION_UNIVERSE_CHANGED')
    failures = [c for c in columns if any(a[k][c] != b[k][c] for k in a)]
    if failures:
        raise ValueError('FEATURE_FUTURE_DEPENDENCY_' + ','.join(failures))
    return len(a)


def compare_capture(folder, capture_id):
    """Cover every emitted field; never mistake labels or execution for features."""
    from .causal_probe import compare
    import sys
    sys.path.insert(0, str(ROOT / 'python'))
    from research import FEATURE_COLUMNS, METADATA, OUTCOMES, PROFILE_PREFIXES, PROFILE_META
    feature_records = {}
    results = []
    for cut in (45, 400, 450):
        probe = capture_id + '_c' + str(cut)
        result = compare(folder, probe)
        cutoff = result['cutoff']
        for variant in ('base', 'future_changed', 'prefix'):
            summary = json.loads((folder / f'{probe}_{variant}_summary.json').read_text())
            if summary['failed'] or summary['cutoff'] != cutoff or summary['query_checks'] < 1:
                raise ValueError('SYNTHETIC_SOURCE_FAILED')
        event_columns, events = tables(folder / f'{probe}_base_events.csv')
        snapshot_columns, snapshots = tables(folder / f'{probe}_base_snapshots.csv')
        known = set(FEATURE_COLUMNS + METADATA + OUTCOMES +
                    [p + m for p in PROFILE_PREFIXES for m in PROFILE_META])
        if set(event_columns) != known:
            raise ValueError('UNKNOWN_OR_MISSING_EVENT_COLUMNS')
        # Execution fields are intentionally future relative to the nominal
        # signal cutoff. Only the frozen predictor list is compared for entries.
        event_features = list(FEATURE_COLUMNS)
        for variant in ('future_changed', 'prefix'):
            ec, other_events = tables(folder / f'{probe}_{variant}_events.csv')
            sc, other_snapshots = tables(folder / f'{probe}_{variant}_snapshots.csv')
            if ec != event_columns or sc != snapshot_columns:
                raise ValueError('FEATURE_SCHEMA_CHANGED')
            count = compare_rows(events, other_events, 'signal_id', 'signal_time_msc',
                                 cutoff, event_features)
            snap_count = compare_rows(snapshots, other_snapshots, 'snapshot_id',
                                      'snapshot_time_msc', cutoff, snapshot_columns)
            result[variant + '_entry_rows'] = count
            result[variant + '_snapshot_rows'] = snap_count
        for table, columns, rows, time_key in (
                ('entry', event_features, events, 'signal_time_msc'),
                ('snapshot', snapshot_columns, snapshots, 'snapshot_time_msc')):
            for column in columns:
                k = table + '.' + column
                record = feature_records.setdefault(k, dict(column=column, table=table,
                    prefix_equal=True, future_perturbation_equal=True, observed_nonmissing=0))
                record['observed_nonmissing'] += sum(r[column] != '' for r in rows if int(r[time_key]) <= cutoff)
        result['prefix_truncation'] = 'PASS'
        results.append(result)
    temporal = {'UTC_time','NY_time','signal_utc_epoch','NY_hour','NY_minute','weekday','session','server_utc_offset_seconds'}
    snapshot_meta = {'snapshot_id','signal_id','symbol','signal_time_msc','original_signal',
                     'virtual_mode','virtual_side','entry_time_msc','snapshot_bar',
                     'snapshot_time_msc','feature_max_time_msc','mark_time_msc','server_time','ha_status'}
    for record in feature_records.values():
        c = record['column']
        record['semantic_disposition'] = (
            'QUARANTINED_UTC_SEMANTICS' if c in temporal else
            'AUDIT_METADATA_NOT_MODEL_FEATURE' if record['table'] == 'snapshot' and
            (c in snapshot_meta or any(c.endswith('_'+m) for m in PROFILE_META)) else
            'MISSING_ONLY_NOT_PROVEN' if not record['observed_nonmissing'] else
            'PASS_SYNTHETIC_NATIVE_PREFIX_ONLY')
        record['historical_vintage_certified'] = False
        record['training_admitted'] = False
    return dict(status='PASS_SYNTHETIC_NATIVE_AVAILABILITY_WITH_EXPLICIT_EXCLUSIONS',
                cases=results, fields=list(feature_records.values()),
                entry_nonfeatures={c:'OUTCOME_OR_EXECUTION_OR_AUDIT_METADATA_NOT_PREDICTOR'
                                   for c in event_columns if c not in FEATURE_COLUMNS},
                adapter='SYNTHETIC_CAUSAL_ADAPTER_NOT_INDEPENDENT_NATIVE_INDICATOR_NUMERIC_PROOF',
                invariants='FROZEN_PRODUCER_UNMODIFIED', training_authorized=False,
                CAUSAL_AUDIT='FAIL_GLOBAL_UNCHANGED')


def verify_capture(folder, checkpoint):
    capture_id = checkpoint['capture_id']
    if not re.fullmatch(r'nfeat_[a-f0-9]{12}', capture_id) or folder.name != capture_id:
        raise ValueError('INVALID_CAPTURE_ID')
    if checkpoint['status'] != 'COMPLETE_SYNTHETIC' or checkpoint['producer_sha256'] != PRODUCER_SHA:
        raise ValueError('UNVERIFIED_SYNTHETIC_CAPTURE')
    hashes = checkpoint['artifact_hashes']
    if not hashes or not all(f'{capture_id}_c{c}_base_events.csv' in hashes for c in (45,400,450)):
        raise ValueError('MISSING_REQUIRED_ARTIFACTS')
    for name, expected in hashes.items():
        if Path(name).name != name or sha256(folder/name) != expected:
            raise ValueError('SYNTHETIC_ARTIFACT_CHANGED')
    if sha256(folder/'NativeFeaturePrefixProbe.mq5') != checkpoint['harness_sha256']:
        raise ValueError('SYNTHETIC_HARNESS_CHANGED')
    compiled_sources = BASE/'terminal/MQL5/Scripts/NativeFeatureDiagnostics'/capture_id
    for name in ('StochasticBarDecisionResearchEA.mq5','ResearchCore.mqh','HeikinAshiCore.mqh'):
        if sha256(compiled_sources/name) != sha256(ROOT/'mt5'/name):
            raise ValueError('COMPILED_SOURCE_COPY_CHANGED')
    if sha256(compiled_sources/'NativeFeaturePrefixProbe.ex5') != checkpoint['ex5_sha256']:
        raise ValueError('SYNTHETIC_BINARY_CHANGED')
    return compare_capture(folder, capture_id)


def resume():
    latest = json.loads((OUT/'latest.json').read_text())
    checkpoint = latest['checkpoint']
    result = verify_capture(OUT/checkpoint['capture_id'], checkpoint)
    if result != latest['result']:
        raise ValueError('DERIVED_AVAILABILITY_CHANGED')
    return dict(capture_id=checkpoint['capture_id'], status=result['status'],
                reused_existing_capture=True, cases=len(result['cases']), fields=len(result['fields']))


def run(timeout=180):
    import psutil
    target = BASE / 'terminal'
    active = {p.pid for p in psutil.process_iter(['name','exe']) if
              (p.info['name'] or '').lower() == 'terminal64.exe' and
              Path(p.info['exe'] or '').resolve() != (target/'terminal64.exe').resolve()}
    if any((p.info['name'] or '').lower() == 'terminal64.exe' and
           Path(p.info['exe'] or '').resolve() == (target/'terminal64.exe').resolve()
           for p in psutil.process_iter(['name','exe'])):
        raise RuntimeError('ISOLATED_TERMINAL_BUSY')
    seal = json.loads((BASE/'isolation_checkpoint.json').read_text())
    for name, digest in seal['program_hashes'].items():
        if sha256(target/name) != digest:
            raise ValueError('ISOLATED_PROGRAM_HASH_MISMATCH')
    capture_id = 'nfeat_' + uuid.uuid4().hex[:12]
    folder = OUT / capture_id
    folder.mkdir(parents=True)
    scripts = target / 'MQL5/Scripts/NativeFeatureDiagnostics' / capture_id
    scripts.mkdir(parents=True)
    for name in ('StochasticBarDecisionResearchEA.mq5','ResearchCore.mqh','HeikinAshiCore.mqh'):
        shutil.copy2(ROOT/'mt5'/name, scripts/name)
    source = scripts/'NativeFeaturePrefixProbe.mq5'
    harness_sha = harness(source, capture_id)
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    editor = Path(r'C:\Program Files\XM Global SC MT5 Terminal\metaeditor64.exe')
    log = folder/'compile.log'
    started = time.time_ns()
    compiled = subprocess.run(f'"{editor}" /compile:"{source}" /log:"{log}"', startupinfo=startup, timeout=90, check=False)
    if '0 errors, 0 warnings' not in log.read_text(encoding='utf-16') or not source.with_suffix('.ex5').is_file() or source.with_suffix('.ex5').stat().st_mtime_ns < started-2000000000:
        raise RuntimeError('SYNTHETIC_COMPILE_FAILED')
    shutil.copy2(source, folder/source.name)
    ini = folder/'synthetic.ini'
    script = 'NativeFeatureDiagnostics\\' + capture_id + '\\NativeFeaturePrefixProbe'
    ini.write_text('[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\n[StartUp]\nScript='+script+'\nSymbol=US30Cash\nPeriod=M5\nShutdownTerminal=1\n', encoding='utf-16')
    before = {str(p): p.stat().st_size for p in diagnostic_logs(target)}
    process = subprocess.Popen(f'"{target/"terminal64.exe"}" /portable /config:"{ini}"', startupinfo=startup)
    checkpoint = dict(capture_id=capture_id, pid=process.pid, status='RUNNING_SYNTHETIC',
                      compiler_process_exit_code=compiled.returncode, compile_errors=0, compile_warnings=0,
                      harness_sha256=harness_sha, ex5_sha256=sha256(source.with_suffix('.ex5')),
                      producer_sha256=PRODUCER_SHA, orders_sent=0, training_authorized=False)
    atomic_json(folder/'checkpoint.json', checkpoint)
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError('SYNTHETIC_TIMEOUT_PROCESS_LEFT_IDENTIFIED_IN_CHECKPOINT')
    text = ''
    for path in diagnostic_logs(target):
        raw = path.read_bytes()[before.get(str(path),0):]
        text += raw.decode('utf-16-le' if b'\0' in raw[:80] else 'utf-8-sig', errors='replace')
    if 'CAUSAL_PROBE_COMPLETE ' + capture_id not in text:
        checkpoint.update(status='FAILED_SYNTHETIC_NO_COMPLETION', process_exit_code=process.returncode,
                          original_terminal_pids_preserved=all(psutil.pid_exists(p) for p in active))
        atomic_json(folder/'checkpoint.json', checkpoint)
        raise RuntimeError('SYNTHETIC_COMPLETION_MARKER_MISSING')
    for path in (target/'MQL5/Files').glob(capture_id+'_*'):
        shutil.copy2(path, folder/path.name)
    result = compare_capture(folder, capture_id)
    checkpoint.update(status='COMPLETE_SYNTHETIC', original_terminal_pids_preserved=all(psutil.pid_exists(p) for p in active),
                      artifact_hashes={p.name:sha256(p) for p in folder.iterdir() if p.is_file() and p.name!='checkpoint.json'})
    atomic_json(folder/'checkpoint.json', checkpoint)
    atomic_json(folder/'availability.json', result)
    atomic_json(OUT/'latest.json', dict(checkpoint=checkpoint, result=result))
    return dict(capture_id=capture_id, status=result['status'], fields=len(result['fields']),
                cases=len(result['cases']), original_terminal_pids_preserved=checkpoint['original_terminal_pids_preserved'])


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-new', action='store_true', help='Explicitly execute synthetic MQL; default verifies existing capture only')
    args = parser.parse_args()
    print(json.dumps(run() if args.run_new else resume(), indent=2))
