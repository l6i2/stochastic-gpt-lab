"""Read-only prospective-prefix audit. No bars, features, labels or scores generated."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from .pretrain_contracts import seal
from .isolated_observation import native_line,GENESIS

# Existing liveness diagnostic, never a market-coverage acceptance tolerance.
HEARTBEAT_GAP_MS=10000


def callback_coverage(observations,start_ms,window_ms=300000):
    buckets={};prior=None;good=0;gap=0;gaps=[];disconnections=0;disconnected_ms=0
    def bucket(i):return buckets.setdefault(i,dict(start_uptime_ms=start_ms+i*window_ms,end_uptime_ms=start_ms+(i+1)*window_ms,callbacks=0,ticks=0,short_callback_interval_ms=0,gap_interval_ms=0,disconnected_endpoint_interval_ms=0,scientific_status='QUARANTINED'))
    for row in observations:
        now=row['callback_uptime_ms']
        if now<start_ms:raise ValueError('PRE_START_OBSERVATION')
        b=bucket((now-start_ms)//window_ms);b['callbacks']+=1;b['ticks']+=row['kind']=='ONTICK_LATEST_QUOTE'
        if prior:
            old=prior['callback_uptime_ms'];delta=now-old
            if delta<0:raise ValueError('CALLBACK_CLOCK_REGRESSION')
            if prior['connected'] and not row['connected']:disconnections+=1
            is_gap=delta>HEARTBEAT_GAP_MS
            if is_gap:gap+=delta;gaps.append(dict(before_uptime_ms=old,after_uptime_ms=now,duration_ms=delta))
            else:good+=delta
            disconnected=not prior['connected'] or not row['connected']
            if disconnected:disconnected_ms+=delta
            position=old
            while position<now:
                i=(position-start_ms)//window_ms;end=min(now,start_ms+(i+1)*window_ms);part=end-position
                bucket(i)['gap_interval_ms' if is_gap else 'short_callback_interval_ms']+=part
                if disconnected:bucket(i)['disconnected_endpoint_interval_ms']+=part
                position=end
        prior=row
    return dict(short_callback_intervals_ms=good,gap_intervals_ms=gap,gaps=gaps,
        disconnections_observed=disconnections,disconnected_endpoint_interval_ms=disconnected_ms,
        interpretation='HOST_UPTIME_CALLBACK_SUPPORT_NOT_MARKET_COVERAGE_OR_UTC_CERTIFICATION',
        windows=[buckets[k] for k in sorted(buckets)])


def audit_segment(folder):
    folder=Path(folder);manifest=json.loads((folder/'manifest.json').read_text());cp=json.loads((folder/'checkpoint.json').read_text())
    if seal(manifest)!=cp['manifest_sha256']:raise ValueError('SEGMENT_MANIFEST_CHANGED')
    anchor=manifest['anchor'];parent=anchor['source_sha256'];sequence=anchor['source_sequence'];offset=anchor['source_offset']
    head=GENESIS;counts=Counter();flags=Counter();callbacks=[];last_state=None;bytes_read=0;file_hash=hashlib.sha256();last_tick=None;equal_tick_times=0
    source_path=Path(manifest['source_path'])
    with (folder/'journal.jsonl').open('rb') as stream,source_path.open('rb') as source:
        source.seek(offset)
        for index in range(cp['rows']):
            line=stream.readline()
            if not line.endswith(b'\n'):raise ValueError('JOURNAL_TRUNCATED_OR_PARTIAL')
            record=json.loads(line);body=record['payload']
            if record['previous']!=head or record['sha256']!=seal(dict(previous=head,payload=body)):raise ValueError('JOURNAL_CHAIN_CHANGED')
            if body['index']!=index or body['capture_id']!=manifest['capture_id']:raise ValueError('JOURNAL_ID_OR_ORDER_CHANGED')
            event=body['event']
            if event['kind'] not in ('SOURCE_OBSERVATION','EXCLUDED_PRE_CUT_METADATA'):raise ValueError('UNEXPECTED_NON_NATIVE_DATA')
            raw=source.readline(32768);native_parent,native_hash,row=native_line(raw)
            if native_parent!=parent or row['sequence']!=sequence+1:raise ValueError('NATIVE_SEQUENCE_OR_CHAIN_CHANGED')
            if row['session_id']!=anchor['source_session'] or row['capture_id']!=anchor['source_capture']:raise ValueError('NATIVE_SOURCE_ID_CHANGED')
            if event['source_sha256']!=native_hash or event['source_sequence']!=row['sequence']:raise ValueError('NATIVE_JOURNAL_REFERENCE_CHANGED')
            offset+=len(raw);parent=native_hash;sequence=row['sequence']
            if event['kind']=='SOURCE_OBSERVATION':
                if event['native_line'].encode()!=raw:raise ValueError('ORIGINAL_NATIVE_BYTES_CHANGED')
                if row['callback_uptime_ms']<=manifest['actual_start_clock']['uptime_ms']:raise ValueError('PRE_CUT_ADOPTED')
                receipt=event['receipt_clock']
                if receipt['boot_id']!=manifest['actual_start_clock']['boot_id'] or not row['callback_uptime_ms']<=row['read_uptime_ms']<=receipt['uptime_ms']:raise ValueError('RECEIPT_ORDER_CHANGED')
                counts[row['kind']]+=1;flags.update(event['quarantine_flags']);callbacks.append(row)
                if row['kind']=='ONTICK_LATEST_QUOTE':
                    if row['time_msc']//1000!=row['time'] or not all(isinstance(row[k],(int,float)) and math.isfinite(row[k]) for k in ('bid','ask')) or not 0<row['bid']<=row['ask']:raise ValueError('INVALID_QUOTE')
                    if last_tick==row['time_msc']:equal_tick_times+=1
                    last_tick=row['time_msc']
            else:counts['EXCLUDED_PRE_CUT_METADATA']+=1
            head=record['sha256'];last_state=body['resulting_state']|dict(chain_head=head,rows=index+1)
            bytes_read+=len(line);file_hash.update(line)
    if head!=cp['chain_head'] or last_state is not None and last_state!=cp:raise ValueError('CHECKPOINT_STATE_CHANGED')
    if offset!=cp['source_offset'] or parent!=cp['source_sha256'] or sequence!=cp['source_sequence']:raise ValueError('CHECKPOINT_NATIVE_CURSOR_CHANGED')
    if counts['ONTICK_LATEST_QUOTE']!=cp['tick_callbacks'] or counts['HEARTBEAT']!=cp['heartbeat_records']:raise ValueError('CHECKPOINT_COUNTS_CHANGED')
    coverage=callback_coverage(callbacks,manifest['actual_start_clock']['uptime_ms'])
    first=callbacks[0] if callbacks else None;last=callbacks[-1] if callbacks else None
    return dict(segment=folder.name,manifest_file_sha256=hashlib.sha256((folder/'manifest.json').read_bytes()).hexdigest(),
        checkpoint=cp,journal_prefix_bytes=bytes_read,journal_prefix_sha256=file_hash.hexdigest(),
        verified_rows=cp['rows'],counts=dict(counts),quarantine_flags=dict(flags),
        source_session=anchor['source_session'],source_capture=anchor['source_capture'],
        membership=dict(first_sequence=anchor['source_sequence']+1,last_sequence=sequence,source_start_offset=anchor['source_offset'],source_end_offset=offset,post_eof_only=True,prior_payloads_adopted=anchor['prefix_payloads_adopted']),
        boot_id=manifest['actual_start_clock']['boot_id'],first_callback_uptime_ms=first['callback_uptime_ms'] if first else None,last_callback_uptime_ms=last['callback_uptime_ms'] if last else None,
        first_host_gmt_seconds=first['receipt_host_gmt_seconds'] if first else None,last_host_gmt_seconds=last['receipt_host_gmt_seconds'] if last else None,
        callback_envelope_ms=last['callback_uptime_ms']-first['callback_uptime_ms'] if first else 0,
        equal_native_tick_timestamps=equal_tick_times,duplicate_record_ids=0,
        hash_chain_and_native_bytes='VERIFIED_AT_DURABLE_CHECKPOINT',coverage=coverage,
        certified_market_coverage_ms=0,m1_bar_records=0,m5_bar_records=0,feature_records=0,signal_records=0,
        note='Current source schema contains quotes/heartbeats only. Zero stored bar/feature/signal records does not certify zero market signals. No derivation or scoring performed.')
