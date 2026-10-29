"""Read-only certification snapshot. Receipt correlation never authorizes event UTC."""
import csv
import gzip
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'python'))
import pc_a_raw_archive as raw
from independent_clock_reference import capture_reference
from local_finalize import verify_source_manifest
from native_time_mapping import load_mapping


def project(reference, monotonic_ns):
    comparison = reference['comparison']
    if comparison.get('status') != 'REFERENCE_QUORUM':
        return None
    delta = monotonic_ns - reference['anchor_monotonic_ns']
    return [comparison['utc_lower_ns'] + delta, comparison['utc_upper_ns'] + delta]


def scan(folder, manifest):
    count = identical_adjacent = unit_errors = reversals = 0
    previous = None
    previous_payload = None
    empty_windows = []
    for segment in manifest['segments']:
        local_count = 0
        with gzip.open(folder / segment['ticks']['file'], 'rt', newline='') as stream:
            for row in csv.DictReader(stream):
                stamp = int(row['time_msc'])
                unit_errors += int(stamp // 1000 != int(row['time']))
                reversals += int(previous is not None and stamp < previous)
                payload = tuple(row.get(key) for key in raw.TICK_FIELDS)
                identical_adjacent += int(payload == previous_payload)
                previous, previous_payload = stamp, payload
                count += 1
                local_count += 1
        if not local_count:
            empty_windows.append(segment.get('index', len(empty_windows)))
    return dict(ticks=count, unit_errors=unit_errors, backwards_native_timestamps=reversals,
                adjacent_identical_rows=identical_adjacent, multiplicity_preserved=True,
                empty_query_windows=len(empty_windows), gap_interpretation='UNVERIFIED_WITHOUT_DATED_CALENDAR',
                manifest_sha256=raw.sha(folder / 'manifest.json'))


def main():
    manifest_path = ROOT / 'configs/pc_a_source_hashes_20261029_v10.json'
    verify_source_manifest(manifest_path)
    folder = ROOT / 'outputs/pc_a_certification' / uuid.uuid4().hex
    folder.mkdir(parents=True)
    inventory = {}
    # Mapping is a prerequisite for every feature/quote inequality. Never pass
    # unnormalized native timestamps into the UTC causal contract.
    try:
        load_mapping(ROOT / 'configs/native_time_mapping_v1.prepared.json')
    except ValueError as exc:
        causal = dict(status='FAIL', reason=str(exc), normalized_rows_admitted=0,
                      feature_inequality='NOT_EVALUABLE', quote_inequality='NOT_EVALUABLE')
    else:
        raise RuntimeError('MAPPING_STATE_CHANGED_REVIEW_REQUIRED')
    for name in ('historical_active.json', 'active.json'):
        pointer = json.loads((raw.BASE / name).read_text())
        archive = raw.BASE / pointer['archive_id']
        manifest = raw.verify(archive)
        raw.atomic(folder / (name + '.snapshot.json'), manifest)
        inventory[name] = scan(archive, manifest)
    samples = []
    api, server = raw.connect()
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(capture_reference)
            for _ in range(50):
                before = dict(utc_ns=time.time_ns(), monotonic_ns=time.monotonic_ns())
                tick = api.symbol_info_tick(raw.SYMBOL)
                after = dict(monotonic_ns=time.monotonic_ns(), utc_ns=time.time_ns())
                if tick is None:
                    raise RuntimeError('QUOTE_UNAVAILABLE')
                payload = tick._asdict()
                samples.append(dict(before=before, after=after, tick=payload,
                                    payload_sha256=hashlib.sha256(raw.canonical(payload)).hexdigest()))
                time.sleep(.1)
            reference = pending.result()
    finally:
        api.shutdown()
    for sample in samples:
        sample['reference_utc_interval_at_receipt_ns'] = project(reference, sample['after']['monotonic_ns'])
        sample['api_call_duration_ns'] = sample['after']['monotonic_ns'] - sample['before']['monotonic_ns']
    measurement = dict(server=server, symbol=raw.SYMBOL, samples=samples, reference=reference,
        limitations=['Unauthenticated NTP; TLS Date corroboration is second resolution',
                     'Monotonic projection assumes oscillator stability; no calibrated drift bound',
                     'API call duration is not event network latency',
                     'Repeated latest-quote payload is not a new independently identified event'],
        event_utc_authorized=False, offsets_installed=[], orders_sent=0)
    raw.atomic(folder / 'correlation.json', measurement)
    clock = subprocess.run(['w32tm', '/query', '/status'], capture_output=True, text=True)
    (folder / 'windows_clock.txt').write_text(clock.stdout + clock.stderr, encoding='utf-8')
    summary = dict(head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        inventory=inventory, causal=causal, samples=len(samples), distinct_payloads=len({s['payload_sha256'] for s in samples}),
        reference_status=reference['comparison'], tls_corroborated=reference['tls_corroborated'],
        correlation_sha256=raw.sha(folder / 'correlation.json'),
        clock_status_sha256=raw.sha(folder / 'windows_clock.txt'), source_manifest='VERIFIED',
        UTC_EVENT_PROVENANCE='MISSING_INDEPENDENT_SAME_EVENT_UTC_BINDING',
        NATIVE_TO_UTC_MAPPING='UNVERIFIED', HISTORICAL_TIME_MAPPING='UNVERIFIED',
        BROKER_CALENDAR='PARTIAL', CAUSAL_AUDIT='FAIL_CLOSED_NO_AUTHORIZED_NORMALIZATION',
        scientific_acceptance=False, train_access_allowed=False, orders_sent=0)
    raw.atomic(folder / 'audit.json', summary)
    raw.atomic(folder / 'hashes.json', {p.name: raw.sha(p) for p in folder.iterdir() if p.is_file()})
    raw.atomic(ROOT / 'outputs/pc_a_certification/latest.json', dict(folder=folder.name, audit_sha256=raw.sha(folder / 'audit.json')))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
