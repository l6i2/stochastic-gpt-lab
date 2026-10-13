#!/usr/bin/env python3
"""Validate the EA dataset and optionally export it losslessly to Parquet."""
import argparse
import json
from pathlib import Path
import sys
from research import read_dataset, validate
from parquet_io import write_parquet


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dataset',type=Path)
    p.add_argument('--audit',type=Path,help='EA audit sidecar; default: DATASET.audit.json')
    p.add_argument('--parquet',type=Path,help='Optional output; requires pyarrow or fastparquet')
    args=p.parse_args()
    audit_path=args.audit or Path(str(args.dataset)+'.audit.json')
    try:
        df=read_dataset(args.dataset)
        if not audit_path.exists(): raise ValueError(f'Missing EA audit: {audit_path}')
        audit=json.loads(audit_path.read_text())
        errors=validate(df,audit)
        if errors:
            print(json.dumps({'valid':False,'errors':errors},indent=2)); return 1
        if args.parquet:
            args.parquet.parent.mkdir(parents=True,exist_ok=True)
            if args.parquet.exists(): raise ValueError('Refusing to overwrite Parquet output')
            write_parquet(df,args.parquet,index=False)
            Path(str(args.parquet)+'.audit.json').write_text(json.dumps(audit,indent=2)+'\n')
        print(json.dumps({'valid':True,'rows':len(df),'columns':len(df.columns),'censored_rows':int((df.follow_exit_reason.eq('END_OF_DATA')|df.invert_exit_reason.eq('END_OF_DATA')).sum())},indent=2))
        return 0
    except (ValueError, OSError, ImportError, KeyError, TypeError, RuntimeError) as exc:
        print(f'Validation failed: {exc}',file=sys.stderr); return 1


if __name__=='__main__': raise SystemExit(main())
