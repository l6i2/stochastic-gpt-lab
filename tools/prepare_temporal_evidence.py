"""Prepare intake templates and data-free research component inventory."""
import argparse
import ast
import json
from pathlib import Path
import sys
import uuid
import urllib.request
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'python'))
import pc_a_raw_archive as raw
from temporal_evidence_intake import template, inspect_bundle, KINDS

COMPONENTS = {
    'causal_time_checks': 'python/temporal_causality.py',
    'causal_native_metadata_adapter': 'python/native_metadata_v3.py',
    'streaming_train_membership_filter': 'python/train_event_source.py',
    'purged_walk_forward': 'python/evaluate_train_exit_walkforward.py',
    'separate_buy_sell_walk_forward': 'python/evaluate_train_intratrade_round2_wf.py',
    'baseline_replay': 'python/replay_quality_train_baseline.py',
    'legacy_model_runner_not_exposed_or_invoked': 'python/train_intratrade_models.py',
}


def public_url(url):
    address = urlparse(url)
    if (address.scheme != 'https' or address.hostname not in ('www.mql5.com', 'www.metatrader5.com', 'www.xm.com')
            or address.username or address.password or address.port not in (None, 443)):
        raise ValueError('PUBLIC_PRIMARY_SOURCE_URL_REQUIRED')
    return url


class PrimaryRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_public(url):
    public_url(url)
    folder = ROOT / 'outputs/pc_a_temporal_intake/public_sources' / uuid.uuid4().hex
    folder.mkdir(parents=True)
    result = dict(url=url, retrieved_utc=raw.utc(), scientific_acceptance=False, event_mapping_authorized=False)
    try:
        request = urllib.request.Request(url, headers={'Cache-Control': 'no-cache'})
        with urllib.request.build_opener(PrimaryRedirect()).open(request, timeout=15) as response:
            body = response.read(2*1024*1024+1)
            if len(body) > 2*1024*1024:
                raise ValueError('PUBLIC_DOCUMENT_SIZE_LIMIT')
            public_url(response.url)
            path = folder / 'source.bin'
            path.write_bytes(body)
            result.update(status='DOWNLOADED_NOT_SEMANTICALLY_VERIFIED', source_sha256=raw.sha(path),
                          bytes=len(body), resolved_url=response.url, http_status=response.status)
    except (OSError, ValueError) as exc:
        result.update(status='UNAVAILABLE_NO_BYPASS', error=type(exc).__name__)
    raw.atomic(folder / 'receipt.json', result)
    print(json.dumps(result, indent=2))


def prepare():
    folder = ROOT / 'outputs/pc_a_temporal_intake'
    folder.mkdir(exist_ok=True)
    inventories = {}
    for name, relative in COMPONENTS.items():
        path = ROOT / relative
        ast.parse(path.read_text(encoding='utf-8-sig'))
        inventories[name] = dict(file=relative, sha256=raw.sha(path), syntax='PASS', executed=False)
    for kind in KINDS:
        value = template(); value['evidence_kind'] = kind
        path = folder / (kind + '.template.json')
        if not path.exists():
            raw.atomic(path, value)
    report = dict(observed_utc=raw.utc(), components=inventories, data_opened=False,
                  training_readiness='BLOCKED_BY_RESEARCH_GOVERNANCE', model_fit_exposed=False,
                  adaptive_search_exposed=False, legacy_train_exhausted=True,
                  requires=['admissible preregistered independent data', 'verified causal mapping and metadata',
                            'sealed chronological membership and purged folds', 'frozen BUY/SELL and FOLLOW/INVERT plan'],
                  low_memory_mode=True, labels_read=False, validation_opened=False, final_test_opened=False,
                  scientific_acceptance=False, demo='DISABLED', live_trading=False)
    raw.atomic(folder / 'research_preparation.json', report)
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'inspect', 'fetch-public'))
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--url')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'fetch-public':
        if args.url is None:
            parser.error('--url required')
        fetch_public(args.url)
    else:
        if args.bundle is None:
            parser.error('--bundle required')
        print(json.dumps(inspect_bundle(args.bundle), indent=2))


if __name__ == '__main__': main()
