"""Build/review a standalone native MT5 parity harness without changing production."""
from __future__ import annotations
import csv
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
CASES=('trend','range','extremes','equality','warmup')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fixtures():
    result={}
    for name in CASES:
        rows=[]
        for i in range(193):
            low,high,close=100.,110.,105.
            if name=='trend':
                center=100.+(i if i<96 else 192-i)*.5
                low,high,close=center-2,center+2,center+.5
            elif name=='range':
                center=105.+math.sin(i*.31)*4
                low,high,close=center-2-(i%3),center+2+(i%4),center+math.sin(i*.7)
            elif name=='extremes':
                high=110. if i%11<5 else 200.
                close=low+(high-low)*(.01 if i%9<6 else .9)
            elif name=='equality':
                close=[102.,102.,102.,102.1,108.,108.,108.,107.9][(i//8)%8]
            elif name=='warmup':
                low=high=close=100. if i<12 else 100.+i%4
                if i>=12:high=low+5;close=low+2
            rows.append({'bar_index':i,'bar_time':946857600+i*300,'open':close,'high':high,'low':low,'close':close})
        result[name]=rows
    return result


def build_harness(folder:Path,run_id:str,*,terminal_root:Path|None=None)->dict:
    if not re.fullmatch(r'pk_[0-9a-f]{8}',run_id):raise ValueError('Invalid nonce')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    terminal_root=Path(terminal_root or folder)
    scripts=terminal_root/'MQL5/Scripts/ResearchDiagnostics'/run_id;files=terminal_root/'MQL5/Files'
    scripts.mkdir(parents=True,exist_ok=True);files.mkdir(parents=True,exist_ok=True)
    production=ROOT/'mt5/StochasticBarDecisionResearchEA.mq5'
    text=production.read_text(encoding='utf-8-sig')
    expression='stoch=iStochastic(sym,PERIOD_M5,K_PERIOD,D_PERIOD,SLOWING,MODE_SMA,STO_LOWHIGH);'
    if text.count(expression)!=1 or 'const int K_PERIOD=5,D_PERIOD=3,SLOWING=3,' not in text:
        raise ValueError('Frozen production stochastic configuration changed')
    match=re.search(r'bool Buffer\([^\n]+\}',text)
    if not match or 'CopyBuffer(handle,buffer,1,n,a)' not in match[0]:raise ValueError('Production buffer contract changed')
    fragment='const int K_PERIOD=5,D_PERIOD=3,SLOWING=3;\n'+match[0]+'\nint ProductionHandle(string sym){int stoch=INVALID_HANDLE;'+expression+'return stoch;}\n'
    template=(ROOT/'tests/mql5/MainKNativeParity.mq5').read_text(encoding='utf-8-sig')
    source=scripts/'MainKNativeParity.mq5'
    if source.exists():raise FileExistsError('Use a fresh run folder')
    source.write_text(template.replace('__PRODUCTION_FRAGMENT__',fragment).replace('__RUN_ID__',run_id),encoding='utf-8')
    (scripts/'ResearchCore.mqh').write_bytes((ROOT/'mt5/ResearchCore.mqh').read_bytes())
    hashes={}
    for name,rows in fixtures().items():
        path=files/(run_id+'_'+name+'_input.csv')
        with path.open('w',encoding='utf-8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        hashes[name]=sha(path)
    report={'run_id':run_id,'production_source_sha256':sha(production),'production_buffer_fragment_sha256':hashlib.sha256(fragment.encode()).hexdigest(),
            'harness_sha256':sha(source),'research_core_sha256':sha(scripts/'ResearchCore.mqh'),
            'fixture_sha256':hashes,'orders_sent':0,'production_modified':False}
    (folder/'build_manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report

def validate_native_result(folder:Path,run_id:str,*,data_root:Path|None=None,terminal_root:Path|None=None,tolerance:float=1e-10)->dict:
    """Validate native exports against exact inputs and an independent ratio-of-sums oracle."""
    if not re.fullmatch(r'pk_[0-9a-f]{8}',run_id):raise ValueError('Invalid nonce')
    if tolerance!=1e-10:raise ValueError('Native parity tolerance is fixed at 1e-10')
    import sys
    if str(ROOT/'python') not in sys.path:sys.path.insert(0,str(ROOT/'python'))
    from causal_metadata_audit import main_values
    folder=Path(folder);data_root=Path(data_root or folder/'MQL5/Files')
    result_path=data_root/(run_id+'_result.json');output=data_root/(run_id+'_native.csv')
    if not result_path.is_file() or not output.is_file():
        raise ValueError('NATIVE_EXECUTION_NOT_EVIDENCED')
    result=json.loads(result_path.read_text(encoding='utf-8-sig'))
    if result.get('run_id')!=run_id or result.get('native_execution') is not True or result.get('passed') is not True:
        raise ValueError('NATIVE_HARNESS_FAILED')
    build=json.loads((folder/'build_manifest.json').read_text())
    if build['production_source_sha256']!=sha(ROOT/'mt5/StochasticBarDecisionResearchEA.mq5'):
        raise ValueError('PRODUCTION_SOURCE_CHANGED')
    source=Path(terminal_root or folder)/'MQL5/Scripts/ResearchDiagnostics'/run_id/'MainKNativeParity.mq5'
    if sha(source)!=build['harness_sha256']:raise ValueError('HARNESS_SOURCE_CHANGED')
    if sha(source.parent/'ResearchCore.mqh')!=build['research_core_sha256']:raise ValueError('RESEARCH_CORE_CHANGED')
    expected={};oracles={}
    for name in CASES:
        path=data_root/(run_id+'_'+name+'_input.csv')
        if sha(path)!=build['fixture_sha256'][name]:raise ValueError('FIXTURE_INPUT_CHANGED')
        with path.open(encoding='utf-8-sig',newline='') as stream:
            rows=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(stream)]
        expected[name]=rows;oracles[name]=main_values(rows,native_reference=True)
    with output.open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream))
    seen=set();max_error=0.;ready=warm=0;old_metadata_difference=False
    for row in rows:
        name=row['fixture'];i=int(row['bar_index']);key=(name,i)
        if key in seen or name not in expected or not 0<=i<len(expected[name])-1:raise ValueError('INVALID_NATIVE_ROW_MEMBERSHIP')
        seen.add(key)
        if int(row['bar_time'])!=int(expected[name][i]['bar_time']):raise ValueError('NATIVE_BAR_TIME_MISMATCH')
        values=[float(row[k]) for k in ('production_main','native_main','production_d','native_d')]
        if not all(math.isfinite(v) for v in values):raise ValueError('NONFINITE_NATIVE_VALUE')
        if (abs(values[0]-values[1])>tolerance or abs(values[2]-values[3])>tolerance
                or row['production_signal']!=row['native_signal']):raise ValueError('PRODUCTION_NATIVE_MISMATCH')
        oracle=oracles[name][i]
        if oracle is None:warm+=1
        else:
            ready+=1;error=abs(values[1]-oracle);max_error=max(max_error,error)
            if error>tolerance:raise ValueError('INDEPENDENT_NATIVE_REFERENCE_MISMATCH')
            wrong=main_values(expected[name][:i+1],native_reference=False)[-1]
            old_metadata_difference |= abs(values[1]-wrong)>tolerance
    wanted={(name,i) for name in CASES for i in range(len(expected[name])-1)}
    if seen!=wanted:raise ValueError('MISSING_NATIVE_ROWS')
    if not old_metadata_difference:raise ValueError('FIXTURES_FAIL_TO_DISCRIMINATE_OLD_METADATA')
    return {'status':'PASS','run_id':run_id,'rows':len(rows),'ready_rows':ready,'warmup_rows':warm,
            'max_reference_error':max_error,'absolute_tolerance':tolerance,'terminal_build':result['terminal_build'],
            'old_metadata_non_equivalence_confirmed':True,'harness_sha256':build['harness_sha256'],
            'native_output_sha256':sha(output),'production_source_sha256':build['production_source_sha256'],
            'historical_dataset_rebuilt':False,'orders_sent':0}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('build','validate'))
    parser.add_argument('--folder',type=Path,required=True)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--terminal-root',type=Path)
    parser.add_argument('--data-root',type=Path)
    args=parser.parse_args()
    if args.mode=='build':
        result=build_harness(args.folder,args.run_id,terminal_root=args.terminal_root)
    else:
        result=validate_native_result(args.folder,args.run_id,data_root=args.data_root,terminal_root=args.terminal_root)
    print(json.dumps(result,indent=2,sort_keys=True))
