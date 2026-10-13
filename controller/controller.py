"""CLI entry point; additional phases must not bypass environment verification."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
from .mt5_env import status


def main():
    parser = argparse.ArgumentParser(description='Local MT5 research controller')
    parser.add_argument('command', choices=['status', 'compile'])
    parser.add_argument('--ea', default='StochasticIntratradeResearchEA')
    args = parser.parse_args()
    if args.command == 'status':
        result = status()
    else:
        from .compile_runner import compile_ea
        run = Path(__file__).resolve().parents[1] / 'outputs/controller/runs' / (
            'compile_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
        result = compile_ea(status(), run, args.ea)
        (run / 'compile_manifest.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
