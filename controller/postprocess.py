"""Run the existing research builders only on accepted controller blocks."""
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

from .artifact_collector import OUTPUTS, atomic_json
from .compile_runner import sha256
from .safety_gate import ROOT, assert_research_range_allowed


def accepted_blocks():
    state=json.loads((ROOT/'outputs/controller/checkpoints/history_state.json').read_text())
    if not state['blocks'] or any(b['STATUS']!='PASS' for b in state['blocks']):
        raise RuntimeError('VALIDATION: historical blocks have not all passed')
    prepared=[]
    for block in state['blocks']:
        assert_research_range_allowed(block['DATE_FROM'],block['DATE_TO'])
        run=ROOT/'outputs/controller/runs'/block['RUN_ID']
        record=json.loads((run/'run_manifest.json').read_text())
        if record.get('VALIDATION_STATUS')!='PASS' or record.get('CAUSALITY_STATUS')!='PASS':
            raise RuntimeError('VALIDATION: block acceptance is missing')
        target=ROOT/'outputs/controller/validated_blocks'/block['BLOCK_ID']
        target.mkdir(parents=True,exist_ok=True)
        for name in OUTPUTS:
            source=run/(record['run_id']+'_'+name)
            if sha256(source)!=record['artifact_hashes'][source.name]:
                raise RuntimeError('VALIDATION: accepted artifact changed')
            destination=target/name
            if destination.exists():
                if sha256(destination)!=sha256(source):
                    raise RuntimeError('VALIDATION: refusing to overwrite a different prepared block')
            else:
                shutil.copy2(source,destination)
        with (target/'stochastic_events.csv').open(encoding='utf-8-sig',newline='') as stream:
            times=[int(r['signal_time_msc']) for r in csv.DictReader(stream)]
        atomic_json(target/'manifest.json',dict(LIVE_TRADING=False,optimization='OFF',symbol='US30Cash',
            timeframe='M5',model='Every tick based on real ticks',period=[block['DATE_FROM'],block['DATE_TO']],
            max_signal_time_msc=max(times),min_signal_time_msc=min(times),run_id=record['run_id'],
            controller_manifest_sha256=sha256(run/'run_manifest.json'),source_artifact_hashes=record['artifact_hashes']))
        prepared.append(target)
    return prepared


def execute(arguments, log):
    with log.open('w',encoding='utf-8') as stream:
        result=subprocess.run([sys.executable,*map(str,arguments)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=7200)
    if result.returncode:
        raise RuntimeError('VALIDATION: postprocess failed: '+str(log))


def postprocess():
    blocks=accepted_blocks()
    out=ROOT/'outputs/controller/research'
    out.mkdir(parents=True,exist_ok=True)
    master=out/'master'
    # Refuse rerunning an accepted build: it would overwrite valid research data.
    if (out/'postprocess_manifest.json').exists():
        return json.loads((out/'postprocess_manifest.json').read_text())
    if master.exists() and any(master.iterdir()):
        raise RuntimeError('STORAGE: nonempty master destination requires audit before retry')
    execute([ROOT/'python/build_intratrade_master.py',*blocks,'--out',master,
             '--train',ROOT/'outputs/splits/train.parquet','--validation',ROOT/'outputs/splits/validation.parquet'],out/'build.log')
    audit=json.loads((master/'intratrade_master_audit.json').read_text())
    events=out/'all_allowed_events.csv'
    count=0
    with events.open('w',encoding='utf-8',newline='') as destination:
        writer=None
        for block in blocks:
            with (block/'stochastic_events.csv').open(encoding='utf-8-sig',newline='') as stream:
                reader=csv.DictReader(stream)
                if writer is None:
                    writer=csv.DictWriter(destination,fieldnames=reader.fieldnames);writer.writeheader()
                for row in reader:
                    writer.writerow(row);count+=1
    combined=master/'intratrade_master.csv.audit.json'
    atomic_json(combined,dict(schema_version='2.0',target_schema_version='1.0',symbol='US30Cash',
        timeframe='M5',LIVE_TRADING=False,optimization='OFF',aborted=False,snapshot_schedule='1,2,3,5,10,15,20,30,50',
        signals=count,snapshot_rows=audit['master_rows'],target_rows=audit['target_rows'],snapshot_skipped=0))
    execute([ROOT/'python/validate_intratrade_dataset.py',master/'intratrade_master.csv','--audit',combined,
             '--targets',master/'intratrade_targets.csv','--events',events,
             '--train',ROOT/'outputs/splits/train.parquet','--validation',ROOT/'outputs/splits/validation.parquet',
             '--split-manifest',ROOT/'outputs/splits/split_manifest.json'],out/'validate_master.log')
    execute([ROOT/'python/analyze_intratrade.py','--train',out/'splits/train.parquet',
             '--targets',master/'intratrade_targets.csv','--output',out/'analysis/train'],out/'analyze.log')
    result=dict(POSTPROCESS_STATUS='PASS',FINAL_TEST='LOCKED',LIVE_TRADING=False,master=audit,
                analysis=json.loads((out/'analysis/train/manifest.json').read_text()))
    atomic_json(out/'postprocess_manifest.json',result)
    atomic_json(ROOT/'outputs/controller/checkpoints/CONTROLLER_C1_C5_COMPLETE.json',
        dict(CONTROLLER_C1_C5_COMPLETE=True,FINAL_TEST='LOCKED',LIVE_TRADING=False,DEMO_EXECUTOR='NOT_IMPLEMENTED',
             history_state_sha256=sha256(ROOT/'outputs/controller/checkpoints/history_state.json'),
             causal_proof_sha256=sha256(ROOT/'outputs/controller/checkpoints/causal_invariance.json'),
             postprocess_manifest_sha256=sha256(out/'postprocess_manifest.json')))
    return result
