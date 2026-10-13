"""CLI entry point; additional phases must not bypass environment verification."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
from .mt5_env import status


def main():
    parser = argparse.ArgumentParser(description='Local MT5 research controller')
    parser.add_argument('command', choices=['status', 'compile', 'backtest', 'validate', 'logs', 'history', 'resume'])
    parser.add_argument('--ea', default='StochasticIntratradeResearchEA')
    parser.add_argument('--symbol', default='US30Cash')
    parser.add_argument('--from', dest='start')
    parser.add_argument('--to', dest='end')
    parser.add_argument('--run-id')
    parser.add_argument('--timeout', type=int, default=120)
    parser.add_argument('--mode', choices=['intratrade'], default='intratrade')
    args = parser.parse_args()
    if args.command == 'status':
        result = status()
    elif args.command == 'compile':
        from .compile_runner import compile_ea
        run = Path(__file__).resolve().parents[1] / 'outputs/controller/runs' / (
            'compile_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
        result = compile_ea(status(), run, args.ea)
        (run / 'compile_manifest.json').write_text(json.dumps(result, indent=2))
    elif args.command == 'backtest':
        if not args.start or not args.end:
            parser.error('--from and --to required')
        from .tester_runner import run
        result = run(args.start, args.end, args.ea, args.symbol, args.timeout)
    elif args.command == 'validate':
        from .validation import validate_run
        result = validate_run(args.run_id)
    elif args.command == 'logs':
        if not args.run_id or not args.run_id.replace('_', '').isalnum():
            parser.error('valid --run-id required')
        folder = Path(__file__).resolve().parents[1] / 'outputs/controller/runs' / args.run_id
        result = {p.name: p.read_text(encoding='utf-8', errors='replace') for p in folder.glob('*validator.log')}
        result['manifest'] = json.loads((folder / 'run_manifest.json').read_text())
    else:
        from .history_orchestrator import history
        result = history(resume=args.command == 'resume', timeout=args.timeout)
    print(json.dumps(result, indent=2))
    return 1 if result.get('tester_status') == 'FAIL' or result.get('VALIDATION_STATUS') == 'FAIL' else 0


if __name__ == '__main__':
    raise SystemExit(main())
