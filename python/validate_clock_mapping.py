"""Validate externally supplied sealed mapping; never infer offsets from tick age."""
import argparse
import json
from pathlib import Path
from native_time_mapping import load_mapping


def validate(path: Path) -> dict:
    mapping = load_mapping(path)
    # This validates a supplied evidence contract, not its external authenticity.
    return {'native_to_utc_mapping': 'EXTERNAL_CONTRACT_VALIDATED',
            'mapping_id': mapping.mapping_id, 'segments': len(mapping.segments),
            'external_authenticity': 'MANUAL_REVIEW_REQUIRED',
            'causal_audit': 'LOCAL_REQUIRED', 'live_trading': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mapping', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = validate(args.mapping)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report = {'native_to_utc_mapping': 'BLOCKED', 'reason': str(exc), 'live_trading': False}
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
    print(json.dumps(report))
    return 2 if report['native_to_utc_mapping'] == 'BLOCKED' else 0


if __name__ == '__main__':
    raise SystemExit(main())
