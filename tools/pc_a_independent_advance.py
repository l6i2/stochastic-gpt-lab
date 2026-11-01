"""Read-only advancement receipt. Legacy recovery never controls live capture.

Consumes the bounded recovery receipt and existing automatic reports. Original
datasets, producer, acquisition boundary and scientific gates are untouched.
"""
import argparse,json,hashlib,sqlite3,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'python'),str(ROOT/'tools')]
from controller.provenance_independent_plan import recovery_disposition,work_plan
from controller.scientific_blockers import adjudicate,enrich_network,iso_ns
from controller.pretrain_contracts import seal
from controller.authorized_capture import CaptureManager,sha
from tools.verify_prospective_operation import sample,compare_samples,verify_ledgers
from authenticated_utc_station import verify_history
from nts_xm_correlation import valid_measurement


def build(destination):
    destination=Path(destination)
    if destination.exists():raise ValueError('NEW_RECEIPT_DIRECTORY_REQUIRED')
    sources=[]
    def read(relative):
        raw=(ROOT/relative).read_bytes();sources.append(dict(path=relative,sha256=hashlib.sha256(raw).hexdigest()))
        return json.loads(raw.decode('utf-8-sig'))
    recovery=read('outputs/legacy_bounded_recovery.json')
    connector=read('outputs/github_recovery_connector_receipt.json')
    complete=(not recovery['local_search_truncated'] and not recovery['errors'] and
        all(r['status']=='PUBLIC_INDEX_ACCESSIBLE' and not r['pagination_link_present'] for r in recovery['github_public_indices']))
    missing=[('legacy_split_manifest_r20261014.json',recovery['known_original_hash_anchors']['split_manifest.json']),
        ('legacy_run_identity_r20261014.json',recovery['known_original_hash_anchors']['run_identity.json']),
        ('original_master_manifest.json',None),('original_holdout_reservation_manifest.json',None),
        ('original_cohort_20261019_manifest.json',None)]
    dispositions=[recovery_disposition(name,expected,recovery['candidates'],complete) for name,expected in missing]
    auth=read('research/studies/us30cash_m5_native_collection_activation_v1/authorization.json')
    plan=work_plan(dispositions,live_authority=auth)
    manager=CaptureManager();manager.load()
    manifest=read((manager.root/'collection_manifest.json').relative_to(ROOT).as_posix())
    boundary=read((manager.root/'activation_boundary.json').relative_to(ROOT).as_posix())
    proof=verify_ledgers()
    first=read('outputs/provenance_advance_first_sample.json');last=sample();delta=compare_samples(first,last)
    path=ROOT/'outputs/prospective_derivatives_v1'/manager.root.name/'quarantine.sqlite3'
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True);db.execute('BEGIN')
    if db.execute('SELECT digest FROM artifacts WHERE n=?',(proof['derived_rows']-1,)).fetchone()[0]!=proof['derived_head']:
        raise ValueError('DERIVED_PREFIX_CHANGED')
    comparisons=[dict(n=n,digest=d,body=json.loads(body)) for n,d,body in db.execute(
        "SELECT n,digest,body FROM artifacts WHERE n<? AND json_extract(body,'$.kind')='BAR_COMPARISON'",(proof['derived_rows'],))]
    db.close()
    comparison_summary=dict(total=len(comparisons),aggregate_exact=sum(r['body']['parity_exact'] for r in comparisons),
        exact_sequence=sum(r['body']['bid_sequence_coverage']['status']=='PASS_EXACT_NATIVE_BID_SEQUENCE_REFERENCE' for r in comparisons),
        completed_accepted_in_quarantine=proof['completed_bars'],rejected=proof['rejected_bars'],
        status='AGGREGATE_PARITY_IS_NOT_COMPLETE_SEQUENCE_PROOF',
        discrepancies=[dict(ledger_n=r['n'],evidence_hash=r['body']['evidence_hash'],
            seconds=r['body']['bucket']['timeframe_seconds'],native_open_msc=r['body']['bucket']['open_msc'],
            raw_bid_count=r['body']['bucket']['tick_volume'],
            native_bar_count=(r['body'].get('native_reference') or {}).get('bar',{}).get('tick_volume'),
            reference_bid_count=((r['body'].get('native_reference') or {}).get('bid_sequence_reference') or {}).get('bid_update_count'),
            parity_exact=r['body']['parity_exact'],reasons=r['body']['bid_sequence_coverage']['reasons']) for r in comparisons],
        reference_rows_adopted=0,admission=False)
    previous='research/studies/scientific_blockers_resolution_20261101_v4/'
    old_decisions={r['incident_id']:r for r in read(previous+'incidents.json')}
    old_facts={r['incident_id']:r for r in read(previous+'native_incident_facts.json')}
    windows=read(previous+'windows.json');network=read(previous+'network.json')
    new_context=read('outputs/provenance_context_delta.json')
    os_events=[e for group in windows for e in group['events']]
    network_events=[e for group in network for e in group['events']]
    new_events=[e for group in new_context for e in group['events']]
    os_events += [e for e in new_events if e['provider'].startswith('Microsoft-Windows-Kernel-') or e['provider']=='Microsoft-Windows-Power-Troubleshooter']
    network_events += [e for e in new_events if e['provider'] in ('Microsoft-Windows-NetworkProfile','Microsoft-Windows-WLAN-AutoConfig')]
    max_sequences={segment:c['native_sequence'] for segment,c in proof['state']['cursors'].items()}
    native_evidence={};by_sequence={}
    # Verify only facts in the sealed raw prefix, then retain prior adjudications
    # unless new OS events fall in their host-label windows.
    for segment,c in proof['state']['cursors'].items():
        with (manager.root/'segments'/segment/'journal.jsonl').open('rb') as stream:
            for _ in range(c['rows']):
                event=json.loads(stream.readline())['payload']['event']
                if event.get('native_line'):
                    row=json.loads(event['native_line'])['payload'];native_evidence[event['source_sha256']]=row
                    by_sequence[(segment,row['sequence'])]=row
    decisions=[];reused=0;new_facts=[]
    for p in sorted((manager.root/'continuity_incidents').glob('*.json')):
        r=json.loads(p.read_text());fact=r['fact']
        if fact['after']['sequence']>max_sequences.get(fact['segment'],-1):continue
        if seal(fact)!=r['incident_id']:raise ValueError('INCIDENT_FACT_CHANGED')
        actual=native_evidence.get(fact['source_record_hash'])
        if actual is None or any(actual.get(k)!=v for k,v in fact['after'].items()):raise ValueError('INCIDENT_SOURCE_NOT_VERIFIED')
        if fact['before'] is not None:
            actual_before=by_sequence.get((fact['segment'],fact['before']['sequence']))
            if actual_before is None or any(actual_before.get(k)!=v for k,v in fact['before'].items()):raise ValueError('INCIDENT_BEFORE_NOT_VERIFIED')
        before=fact['before'];after=fact['after']
        new_overlap=before is not None and any(before['receipt_host_gmt_seconds']*10**9<=iso_ns(e['host_utc_label'])<(after['receipt_host_gmt_seconds']+1)*10**9 for e in new_events)
        if r['incident_id'] in old_decisions and not new_overlap:
            if r!=old_facts[r['incident_id']]:raise ValueError('PUBLISHED_INCIDENT_CHANGED')
            decisions.append(old_decisions[r['incident_id']]);reused+=1
        else:
            decisions.append(enrich_network(adjudicate(r,os_events),r,network_events));new_facts.append(r)
    incident_status=dict(total=len(decisions),reused_prior_decisions=reused,new_or_materially_affected=len(decisions)-reused,
        kinds=dict(Counter(r['kind'] for r in decisions)),classifications=dict(Counter(r['classification'] for r in decisions)),
        coverage='ALL_GAPS_REMAIN_QUARANTINED_NO_BACKFILL')
    nts_folder=ROOT/'outputs/pc_a_prospective_utc/authenticated_utc'
    nts_state=read((nts_folder/'state.json').relative_to(ROOT).as_posix());nts_count=verify_history(nts_folder,nts_state)
    latest_measurements=[];head=nts_state['chain_head'];by_hash={}
    for p in nts_folder.glob('*.json'):
        if len(p.stem)==32:
            r=json.loads(p.read_text());by_hash[r['sha256']]=r
    for _ in range(min(3,nts_count)):
        r=by_hash[head];p=r['payload'];latest_measurements.append(dict(record_sha256=r['sha256'],
            observed_host_utc=p['observed_host_utc'],boot_identity=p.get('boot_identity'),
            started_uptime_ms=p.get('run_started_kernel_uptime_ms'),prior_due_ms=p.get('prior_due_kernel_uptime_ms'),
            trigger=p.get('trigger'),valid_authenticated_results=sum(x.get('status')=='AUTHENTICATED_MEASUREMENT' and valid_measurement(x.get('measurement',{})) for x in p['results'])))
        head=p['previous']
    health=dict(runtime=last,progress=delta,
        recovery=read('outputs/pc_a_stability/recovery_status.json'),
        watchdog=read('outputs/new_native_studies/us30cash_m5_native_20261030_01/watchdog_status.json'),
        restart=read('outputs/pc_a_stability/restart/status.json'),
        prior_actual_collector_restart=read('outputs/new_native_studies/us30cash_m5_native_20261030_01/restart_verification.json'),
        nts_chain_records=nts_count,nts_latest_records=latest_measurements,
        automatic_reports='EXISTING_MATURITY_EVERY_2S_AND_SUPERVISOR_HEALTH_RETAINED_NO_NEW_SERVICE')
    old_membership=read(previous+'membership.json')
    derived_legacy=dict(schema='identified-legacy-provenance-derivative/1',original=False,
        reason='EXISTING_PUBLISHED_METADATA_ONLY_NOT_RECONSTRUCTED_SPLIT_IDS',
        membership=old_membership,source_refs=[r for r in sources if r['path'].startswith(previous)],
        independent_data_proven=False)
    membership=dict(capture_id=manager.root.name,source_cursors=proof['state']['cursors'],
        raw_membership=[r['membership'] for r in proof['raw_segments']],
        activation=manifest['activation_utc'],boundary=boundary,
        raw_ticks=proof['processed_real_ticks_in_quarantine'],raw_heartbeats=proof['processed_real_heartbeats'],
        original_producer_manifest_sha256=sha(manager.root/'collection_manifest.json'),
        derived_head=proof['derived_head'],derived_rows=proof['derived_rows'],
        no_backfill=True,pre_boundary_adopted=0,old_cohorts_adopted=0,
        independence='PROSPECTIVE_CAPTURE_LINEAGE_VERIFIED_NOT_SCIENTIFIC_ADMISSION',
        admitted_intervals=[],dataset_hash=None,known_legacy_unknowns_retained=True)
    summary=dict(LEGACY_MANIFEST_RECOVERY=dispositions,
        IRRECOVERABLE_EVIDENCE='SCOPED_TO_ACCESSIBLE_SOURCES_NOT_GLOBAL_NONEXISTENCE_NO_AUTOMATIC_RETRY',
        NEW_CAPTURE_ID=manager.root.name,NEW_CAPTURE_PROVENANCE='VERIFIED_MANIFEST_NATIVE_BYTES_AND_DURABLE_PREFIXES_QUARANTINED',
        NO_BACKFILL_PROOF='POST_EOF_BOUNDARY_SOURCE_SEQUENCES_AND_UNCHANGED_MANIFEST_VERIFIED',
        NEW_CAPTURE_MEMBERSHIP='POST_BOUNDARY_PREFIX_VERIFIED_ADMITTED_MEMBERSHIP_EMPTY',
        COVERAGE_STATUS='QUARANTINED_GAPS_AND_SEQUENCE_DISCREPANCIES_NOT_FILLED',
        TEMPORAL_EVIDENCE='NATIVE_DIAGNOSTIC_ORDER_PLUS_AUTHENTICATED_NTS_RECEIPT_REFERENCES_GENERATION_UTC_UNVERIFIED',
        INCIDENT_ADJUDICATION=incident_status,CAUSAL_AUDIT='FAIL_GLOBAL_UNCHANGED',
        NEW_STUDY_READINESS='PC_A_ONLY_PREPARATION_CONTINUES_SCIENTIFIC_ADMISSION_BLOCKED',TRAINING_READINESS='BLOCKED',
        HARD_BLOCKER=['INCOMPLETE_NEW_CAPTURE_COVERAGE','EXACT_NATIVE_SEQUENCE_REFERENCE_DISCREPANCIES',
            'OWN_WARMUP_AND_MATURITY_NOT_REACHED','NATIVE_EVENT_UTC_UNVERIFIED',
            'FROZEN_ADMISSION_RULE_NEEDS_FUTURE_EXPLICIT_SCIENTIFIC_DECISION_IF_LEGACY_PROVENANCE_UNAVAILABLE'],
        NEXT_STATE='CONTINUE_PC_A_QUARANTINE_INDEPENDENT_TASKS_STOP_LEGACY_SEARCH_UNTIL_NEW_SOURCE_NO_AUTOMATIC_GATE_OVERRIDE',
        DISCOVERY_VALIDATION='BLOCKED',HISTORICAL_HOLDOUT='BLOCKED',FINAL_TEST='LOCKED',DEMO='DISABLED',LIVE_TRADING=False,
        training_calls=0,scoring_calls=0,protected_rows_opened=0,original_data_changed=False,
        snapshot_ecuador=datetime.now(timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('America/Guayaquil')).isoformat())
    destination.mkdir(parents=True)
    outputs=dict(summary=summary,legacy_recovery=recovery,github_connector=connector,work_plan=plan,
        derived_legacy_provenance=derived_legacy,membership=membership,health=health,
        bar_comparison_summary=comparison_summary,bar_comparison_evidence=comparisons,
        incident_status=incident_status,incident_decisions=decisions,new_incident_facts=new_facts,
        new_os_context=new_context,source_receipts=sources,
        prefix_receipt=dict(derived_head=proof['derived_head'],derived_rows=proof['derived_rows'],
            raw_integrity=proof['raw_and_derived_integrity'],raw_segments=proof['raw_segments'],
            old_raw_prefixes_verified=proof['old_raw_prefixes_verified'],old_version_prefix_retained=proof['old_version_prefix_retained']))
    for name,value in outputs.items():
        (destination/(name+'.json')).write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf8',newline='\n')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True)
    print(json.dumps(build(parser.parse_args().out),ensure_ascii=False,indent=2))
