"""Read-only durable-prefix receipts; no collector cursor or market-data writes."""
import hashlib
import json
from pathlib import Path


def prefix(path, length):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        remaining=length
        while remaining:
            data=stream.read(min(1048576,remaining))
            if not data:raise ValueError('SAVED_PREFIX_TRUNCATED')
            digest.update(data);remaining-=len(data)
    return digest.hexdigest()


def receipt(folder, clock):
    folder=Path(folder)
    runtime=json.loads((folder/'runtime_state.json').read_text())
    segments={}
    for name in runtime['segments']:
        if Path(name).name!=name:raise ValueError('INVALID_SEGMENT')
        segment=folder/'segments'/name
        saved=json.loads((segment/'checkpoint.json').read_text())
        journal=segment/'journal.jsonl';length=0;last=None
        with journal.open('rb') as stream:
            for _ in range(saved['rows']):
                line=stream.readline()
                if not line.endswith(b'\n'):raise ValueError('INCOMPLETE_DURABLE_JOURNAL')
                length+=len(line);last=json.loads(line)
        if last and last['sha256']!=saved['chain_head']:raise ValueError('CHECKPOINT_HEAD_CHANGED')
        manifest=segment/'manifest.json'
        source=Path(json.loads(manifest.read_text())['source_path'])
        segments[name]=dict(checkpoint=saved,journal_bytes=length,journal_sha256=prefix(journal,length),
            manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
            source_prefix_sha256=prefix(source,saved['source_offset']))
    status=json.loads((folder/'collector_status.json').read_text())
    return dict(clock=clock,capture_id=status['capture_id'],collection_manifest_sha256=hashlib.sha256((folder/'collection_manifest.json').read_bytes()).hexdigest(),
        active_segment=runtime['active_segment'],segments=segments,
        recent_callback_age_ms=status.get('last_callback_age_ms'),continuity=status.get('continuity',{}),
        dataset_admission=False,live_trading=False)


def verify_previous(folder, saved):
    folder=Path(folder)
    if hashlib.sha256((folder/'collection_manifest.json').read_bytes()).hexdigest()!=saved['collection_manifest_sha256']:
        raise ValueError('CAPTURE_MANIFEST_CHANGED')
    for name,old in saved['segments'].items():
        if Path(name).name!=name:raise ValueError('INVALID_SEGMENT')
        segment=folder/'segments'/name
        manifest=segment/'manifest.json'
        if hashlib.sha256(manifest.read_bytes()).hexdigest()!=old['manifest_sha256']:raise ValueError('SEGMENT_MANIFEST_CHANGED')
        if prefix(segment/'journal.jsonl',old['journal_bytes'])!=old['journal_sha256']:raise ValueError('JOURNAL_PREFIX_CHANGED')
        source=Path(json.loads(manifest.read_text())['source_path'])
        if prefix(source,old['checkpoint']['source_offset'])!=old['source_prefix_sha256']:raise ValueError('NATIVE_PREFIX_CHANGED')
    return True


def transition(previous,current):
    changed=previous['clock']['boot_id']!=current['clock']['boot_id']
    if previous['capture_id']!=current['capture_id']:raise ValueError('CAPTURE_ID_CHANGED')
    fresh=current.get('recent_callback_age_ms')
    resumed=changed and fresh is not None and fresh<=10000 and current['active_segment']!=previous['active_segment']
    return dict(boot_transition_observed=changed,prefix_integrity='VERIFIED',
        restart_recovery='BOOT_CHANGE_AND_FRESH_NEW_SEGMENT_OBSERVED' if resumed else 'WAITING_FOR_FRESH_NEW_BOOT_SEGMENT' if changed else 'WAITING_FOR_NATURAL_WINDOWS_RESTART',
        physical_power_cycle_proven=False,missing_events_recovered=False,backfill=False,scientific_admission=False)
