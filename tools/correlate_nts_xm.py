"""Read verified local prefixes; publish a derived, non-authorizing correlation."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
sys.path.insert(0,str(ROOT/'tools'))
import pc_a_raw_archive as raw
from authenticated_utc_station import verify_history
from prospective_utc import verify_callback
from nts_xm_correlation import correlate, read_rows
BASE=ROOT/'outputs/pc_a_prospective_utc'


def run():
    folder=BASE/'authenticated_utc'
    state=json.loads((folder/'state.json').read_text())
    count=verify_history(folder,state)
    records=[json.loads(p.read_text()) for p in folder.glob('*.json') if len(p.stem)==32]
    records.sort(key=lambda r:r['payload']['observed_host_utc'])
    sessions={}; totals={'CERTIFIED':0,'PARTIAL':0,'QUARANTINED':0}
    for path in sorted((BASE/'native_mirror').glob('*.jsonl')):
        verified=verify_callback(path)
        # Ensure an NTS link refers to an actual prefix, not merely a filename.
        heads=set()
        consumed=0
        with path.open('rb') as stream:
            for line in stream:
                consumed+=len(line)
                if consumed>verified['bytes_verified']:break
                if line.endswith(b'\n'):heads.add(json.loads(line)['sha256'])
        linked=[]
        for record in records:
            link=record['payload'].get('native_receipt_correlations',{}).get(path.name)
            if link and link.get('native_chain_head') in heads:linked.append(record)
        observations=correlate(read_rows(path,verified['bytes_verified']),linked)
        segments=[]
        for row in observations:
            signature=(row['status'],tuple(row['reasons']))
            if segments and signature==(segments[-1]['status'],tuple(segments[-1]['reasons'])):
                segments[-1]['last_sequence']=row['sequence'];segments[-1]['last_callback_uptime_ms']=row['callback_uptime_ms'];segments[-1]['callbacks']+=1
            else:
                segments.append(dict(status=row['status'],reasons=row['reasons'],first_sequence=row['sequence'],last_sequence=row['sequence'],
                    first_callback_uptime_ms=row['callback_uptime_ms'],last_callback_uptime_ms=row['callback_uptime_ms'],callbacks=1,
                    scope='DISCRETE_OBSERVED_CALLBACKS_NOT_ALL_EVENTS_OR_CONTINUOUS_UTC'))
        for segment in segments:totals[segment['status']]+=1
        for segment in segments:
            members=[r for r in observations if segment['first_sequence']<=r['sequence']<=segment['last_sequence']]
            models=[m for r in members for m in r['conditional_models']]
            segment['callback_read_elapsed_ms_range']=[min(r['callback_read_elapsed_ms'] for r in members),max(r['callback_read_elapsed_ms'] for r in members)]
            segment['conditional_width_ns_range']=[min(m['conditional_width_ns'] for m in models),max(m['conditional_width_ns'] for m in models)] if models else None
            segment['nts_server_minus_host_offset_ns_envelope']=[min(m['observed_offset_server_minus_host_ns'][0] for m in models),max(m['observed_offset_server_minus_host_ns'][1] for m in models)] if models else None
            segment['nts_network_rtt_ns_range']=[min(m['network_rtt_ns'] for m in models),max(m['network_rtt_ns'] for m in models)] if models else None
            segment['native_minus_receipt_coordinate_ns_envelope']=[min(m['native_minus_receipt_coordinate_ns'][0] for m in models),max(m['native_minus_receipt_coordinate_ns'][1] for m in models)] if models else None
            segment['generation_latency_ns']=None
            segment['certified_receipt_bounds_ns']=None
        sessions[path.name]=dict(verified_prefix=verified,segments=segments,callback_correlations=observations)
    report=dict(schema_version=1,observed_host_utc=raw.utc(),nts_chain_head=state['chain_head'],nts_records=count,
        measurements=[dict(record_sha256=r['sha256'],observed_host_utc=r['payload']['observed_host_utc'],
            trigger=r['payload'].get('trigger','LEGACY_NOT_RECORDED'),
            start_uptime_ms=r['payload'].get('run_started_kernel_uptime_ms'),
            prior_due_uptime_ms=r['payload'].get('prior_due_kernel_uptime_ms'),
            results=[dict(status=x['status'],origin=x.get('origin',x.get('measurement',{}).get('origin')),
                receive_uptime=x.get('measurement',{}).get('receive_kernel_uptime_ms_interval'),
                offset_ns=x.get('measurement',{}).get('offset_server_minus_host_ns'),
                rtt_ns=x.get('measurement',{}).get('rtt_monotonic_ns')) for x in r['payload']['results']]) for r in records],
        sessions=sessions,segment_counts=totals,certified_segments=[],
        receipt_bounds='CONDITIONAL_ZERO_DRIFT_MODELS_ONLY_NO_CERTIFIED_BOUNDS',
        broker_calendar='PARTIAL',CAUSAL_AUDIT='FAIL',TRAINING_READINESS='BLOCKED_BY_RESEARCH_GOVERNANCE',
        DISCOVERY_VALIDATION='BLOCKED',FINAL_TEST='LOCKED',DEMO='DISABLED',LIVE_TRADING=False,
        original_data_changed=False,scientific_acceptance=False)
    raw.atomic(BASE/'nts_xm_correlation.json',report)
    return dict(nts_records=count,segment_counts=totals,scientific_acceptance=False)


if __name__=='__main__':
    print(json.dumps(run(),indent=2))
