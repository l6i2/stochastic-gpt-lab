"""CLI entry point; additional phases must not bypass environment verification."""
from __future__ import annotations

import argparse
import json
from .mt5_env import status


def main():
    parser = argparse.ArgumentParser(description='Local MT5 research controller')
    parser.add_argument('command', choices=['status'])
    parser.parse_args()
    print(json.dumps(status(), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
