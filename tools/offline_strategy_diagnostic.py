"""Reproduce only the authorized native day; never accepts an arbitrary dataset."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from controller.strategy_diagnostic import run


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args()
    result=run();out=Path(args.out)
    with out.open('x',encoding='utf8',newline='\n') as stream:json.dump(result,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps(dict(scope=result['scope'],signals=result['signal_counts'],replay=result['baseline_replay']['BASELINE_REPLAY'],output=str(out))))
