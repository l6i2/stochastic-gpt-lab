"""Execute the production MQL5 snapshot producer with synthetic future perturbations."""
import csv
import json
import shutil
import subprocess
import time
from pathlib import Path
from .cold_start import active_processes, baseline, pinned_environment, read_deltas, redact, now
from .compile_runner import sha256
from .safety_gate import ROOT
from .profiles import BASE_EA, BAR_EA, profile


def compare(folder, probe_id):
    summaries = [json.loads((folder / f'{probe_id}_{side}_summary.json').read_text())
                 for side in ('base', 'future_changed')]
    if any(row['failed'] for row in summaries) or summaries[0]['cutoff'] != summaries[1]['cutoff']:
        raise RuntimeError('CAUSAL_INVARIANCE: producer failed or cutoff mismatch')
    cutoff = summaries[0]['cutoff']
    mutations = {}
    for suffix,time_key in [('input_ticks','time_msc'),('input_bars','bar_end_msc')]:
        raw=[]
        for side in ('base','future_changed'):
            with (folder/f'{probe_id}_{side}_{suffix}.csv').open(encoding='utf-8-sig',newline='') as stream:
                raw.append(list(csv.DictReader(stream)))
        if len(raw[0]) != len(raw[1]):
            raise RuntimeError('CAUSAL_INVARIANCE: input lengths differ')
        changed=0
        for before,after in zip(*raw):
            if before[time_key] != after[time_key]:
                raise RuntimeError('CAUSAL_INVARIANCE: input timestamps changed')
            if before!=after:
                if int(before[time_key])<=cutoff:
                    raise RuntimeError('CAUSAL_INVARIANCE: past input was modified')
                changed+=1
        if changed==0:
            raise RuntimeError('CAUSAL_INVARIANCE: no future input mutations')
        mutations[suffix]=changed
    tables = []
    columns = None
    for side in ('base', 'future_changed'):
        with (folder / f'{probe_id}_{side}_snapshots.csv').open(encoding='utf-8-sig',newline='') as stream:
            reader = csv.DictReader(stream)
            if columns is not None and reader.fieldnames != columns:
                raise RuntimeError('CAUSAL_INVARIANCE: feature schema changed')
            columns = reader.fieldnames
            rows = [row for row in reader if int(row['snapshot_time_msc']) <= cutoff]
            table = {row['snapshot_id']:row for row in rows}
            if len(table) != len(rows):
                raise RuntimeError('CAUSAL_INVARIANCE: duplicate snapshot IDs')
            tables.append(table)
    if not tables[0] or tables[0] != tables[1]:
        raise RuntimeError('CAUSAL_INVARIANCE: causal features changed or no snapshots')
    targets = []
    for side in ('base','future_changed'):
        with (folder / f'{probe_id}_{side}_targets.csv').open(encoding='utf-8-sig',newline='') as stream:
            targets.append({r['snapshot_id']:r for r in csv.DictReader(stream) if r['snapshot_id'] in tables[0]})
    changed_targets = sum(targets[0].get(key) != targets[1].get(key) for key in tables[0])
    if changed_targets == 0:
        raise RuntimeError('CAUSAL_INVARIANCE: future-target sensitivity control failed')
    return dict(CAUSAL_INVARIANCE='PASS', compared_snapshots=len(tables[0]),
                compared_features=len(columns), cutoff=cutoff, changed_future_targets=changed_targets, future_input_mutations=mutations,
                scope='Exact production OnTick, SnapshotTrade, Profile, HA and virtual trade state; synthetic causal market-data/indicator adapter')


def run_probe(timeout=600,ea=BASE_EA):
    if active_processes():
        raise RuntimeError('ENVIRONMENT: causal script requires a closed terminal')
    selected=profile(ea)
    environment, compiled = pinned_environment(ea)
    probe_id = 'causal_' + __import__('uuid').uuid4().hex[:12]
    folder = ROOT / 'outputs' / selected['namespace'] / 'causality' / probe_id
    folder.mkdir(parents=True)
    script_relative='ControllerResearch'
    if ea==BAR_EA:
        script_relative='ControllerResearchBar/'+probe_id
    scripts = Path(environment['DATA_FOLDER']) / 'MQL5/Scripts' / script_relative
    scripts.mkdir(parents=True,exist_ok=True)
    source = scripts / 'SnapshotCausalProbe.mq5'
    if ea==BAR_EA:
        from python.build_bar_replay_producer import build_probe
        for name in (ea+'.mq5','ResearchCore.mqh','HeikinAshiCore.mqh'):
            shutil.copy2(ROOT/'mt5'/name,scripts/name)
        build_probe(source)
        source.write_text(source.read_text().replace('__PROBE_ID__',probe_id),encoding='utf-8')
    else:
        source.write_text((ROOT/'tests/mql5/SnapshotCausalProbe.mq5').read_text().replace('__PROBE_ID__',probe_id),encoding='utf-8')
    log = folder / 'compile.log'
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    subprocess.run([environment['METAEDITOR_PATH'],'/compile:'+str(source),'/log:'+str(log)],timeout=600,check=False,startupinfo=startup)
    if '0 errors, 0 warnings' not in log.read_text(encoding='utf-16'):
        raise RuntimeError('CAUSAL_INVARIANCE: harness compile failed: '+str(log))
    shutil.copy2(source,folder/source.name)
    if ea==BAR_EA:
        for name in (ea+'.mq5','ResearchCore.mqh','HeikinAshiCore.mqh'):
            shutil.copy2(scripts/name,folder/name)
    ini = folder/'causal.ini'
    ini.write_text('[Experts]\nAllowLiveTrading=0\nAllowDllImport=0\n[StartUp]\nScript='+script_relative.replace('/','\\')+'\\SnapshotCausalProbe\nShutdownTerminal=1\n',encoding='ascii')
    previous = baseline(environment)
    command=[environment['TERMINAL_PATH'],'/config:'+str(ini)]
    (folder/'launch.json').write_text(json.dumps(dict(command=command,logs_before=previous,started_at=now()),indent=2))
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    process=subprocess.Popen(command,startupinfo=startup)
    deadline=time.monotonic()+timeout
    while process.poll() is None and time.monotonic()<deadline:
        for kind,body in read_deltas(environment,previous).items():
            (folder/(kind+'.log')).write_text(redact(body),encoding='utf-8')
        time.sleep(5)
    if process.poll() is None:
        raise RuntimeError('CAUSAL_INVARIANCE: script timeout; process left running')
    deltas=read_deltas(environment,previous)
    text='\n'.join(deltas.values())
    for kind,body in deltas.items():
        (folder/(kind+'.log')).write_text(redact(body),encoding='utf-8')
    if 'CAUSAL_PROBE_COMPLETE '+probe_id not in text:
        raise RuntimeError('CAUSAL_INVARIANCE: script completion not confirmed: '+str(folder))
    files=Path(environment['DATA_FOLDER'])/'MQL5/Files'
    for path in files.glob(probe_id+'_*'):
        shutil.copy2(path,folder/path.name)
    result=compare(folder,probe_id)
    if ea==BAR_EA:
        import numpy as np
        from python.validate_bar_path import validate as validate_path, QUOTE_DTYPE
        streams=[]
        parity={}
        for side in ('base','future_changed'):
            path=folder/f'{probe_id}_{side}_quote_path.bin'
            streams.append(np.fromfile(path,dtype=QUOTE_DTYPE))
            parity[side]=validate_path(path,folder/f'{probe_id}_{side}_trade_index.csv',
                folder/f'{probe_id}_{side}_events.csv',folder/f'{probe_id}_{side}_execution_quotes.csv',
                int(streams[-1]['time_msc'].max())+1)
        before,after=[a[a['time_msc']<=result['cutoff']] for a in streams]
        if not len(before) or before.tobytes()!=after.tobytes():
            raise RuntimeError('CAUSAL_INVARIANCE: past quote tape changed')
        result['BASELINE_REPLAY']=parity
        result['quote_prefix_records']=len(before)
    result.update(ea_hash=compiled['ea_hash'],ex5_hash=compiled['ex5_hash'],
        producer_hashes={p.name:sha256(p) for p in (ROOT/'mt5').glob('*.mq*')},
        harness_sha256=sha256(source),run_id=probe_id,process_exit_code=process.returncode,
        artifact_hashes={p.name:sha256(p) for p in folder.iterdir() if p.is_file()})
    (folder/'causal_manifest.json').write_text(json.dumps(result,indent=2))
    checkpoint=ROOT/'outputs'/selected['namespace']/'checkpoints/causal_invariance.json'
    checkpoint.parent.mkdir(parents=True,exist_ok=True)
    checkpoint.write_text(json.dumps(result,indent=2))
    return result
