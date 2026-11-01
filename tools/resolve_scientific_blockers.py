"""Adjudicate existing evidence only; no probes, conversions, backfill or grants."""
from collections import Counter
from datetime import datetime,timezone
import hashlib,json,re,sqlite3,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'python'),str(ROOT/'tools')]
from controller.scientific_blockers import adjudicate,known_membership,iso_ns,receipt_sampling,enrich_network
from controller.pretrain_contracts import seal
from tools.verify_prospective_operation import verify_ledgers
from controller.authorized_capture import CaptureManager
from authenticated_utc_station import verify_history
from nts_xm_correlation import valid_measurement


def build(out):
    out=Path(out)
    if out.exists():raise ValueError('NEW_EVIDENCE_DIRECTORY_REQUIRED')
    receipts=[]
    def read(path):
        p=ROOT/path;raw=p.read_bytes()
        receipts.append(dict(path=path,sha256=hashlib.sha256(raw).hexdigest()))
        return json.loads(raw.decode('utf-8-sig'))
    prior='research/studies/scientific_preparation_closure_20261101_v2/'
    prior_membership=read(prior+'membership.json')
    base=read('research/studies/us30cash_m5_native_pretrain_v1/exposure_ledger.json')
    diagnostic=read('research/studies/us30cash_m5_native_pretrain_v1/known_exposed_signal_membership.json')
    membership=known_membership(base,diagnostic['signals'],prior_membership['published_censored_nonmember_ids'])
    freeze_path=ROOT/'docs/DATASET_FREEZE.md';raw=freeze_path.read_bytes()
    receipts.append(dict(path='docs/DATASET_FREEZE.md',sha256=hashlib.sha256(raw).hexdigest()))
    match=re.search(r'First/last signal server time: ([0-9. :]+) / ([0-9. :]+)',raw.decode())
    if not match:raise ValueError('DECLARED_MASTER_BOUNDARY_NOT_FOUND')
    membership['master_declared_signal_label_envelope']=dict(first=match[1].strip(),last=match[2].strip(),
        domain='LEGACY_SERVER_NATIVE_UNRECONCILED',converted_to_utc=False,
        scope='PUBLISHED_DECLARATION_NOT_ROW_MEMBERSHIP_OR_SPLIT_ASSIGNMENT')
    # Only inspect names of missing manifests, never protected data content.
    patterns=('*split*manifest*.json','*master*manifest*.json','*cohort*manifest*.json')
    membership['local_original_manifest_name_matches']=sorted({p.relative_to(ROOT).as_posix() for pattern in patterns for p in (ROOT/'outputs').rglob(pattern)})
    membership['reachable_git_manifest_paths']=subprocess.check_output(['git','log','--all','--format=','--name-only','--',*patterns],cwd=ROOT,text=True).splitlines()
    windows=read('outputs/scientific_blockers_windows_context.json')
    events=[e for provider in windows for e in provider['events']]
    network=read('outputs/scientific_blockers_network_context.json')
    network_events=[e for provider in network for e in provider['events']]
    manager=CaptureManager();manager.load()
    proof=verify_ledgers()  # New-prefix verification justified by incident/source joins.
    native_by_hash={};native_by_sequence={};receipt_windows=[]
    boot_by_segment={r['segment']:r['boot_id'] for r in proof['raw_segments']}
    for segment,cursor in proof['state']['cursors'].items():
        with (manager.root/'segments'/segment/'journal.jsonl').open('rb') as stream:
            for _ in range(cursor['rows']):
                record=json.loads(stream.readline());event=record['payload']['event']
                if event.get('native_line'):
                    row=json.loads(event['native_line'])['payload']
                    native_by_hash[event['source_sha256']]=row
                    native_by_sequence[(segment,row['sequence'])]=row
                    receipt_windows.append(receipt_sampling(row,event['receipt_clock'],boot_by_segment[segment]))
    decisions=[];original_incidents=[]
    for p in sorted((manager.root/'continuity_incidents').glob('*.json')):
        incident=read(p.relative_to(ROOT).as_posix());fact=incident['fact']
        after=native_by_hash.get(fact['source_record_hash'])
        if after is None:continue  # A later live-prefix incident is outside this sealed audit.
        before=fact['before']
        expected=native_by_sequence.get((fact['segment'],before['sequence'])) if before else None
        for observed,actual in ((fact['after'],after),(before,expected)):
            if observed is not None and (actual is None or any(actual.get(k)!=v for k,v in observed.items())):
                raise ValueError('INCIDENT_NOT_BOUND_TO_VERIFIED_NATIVE_BYTES')
        decisions.append(enrich_network(adjudicate(incident,events),incident,network_events));original_incidents.append(incident)
    dbpath=ROOT/'outputs/prospective_derivatives_v1'/manager.root.name/'quarantine.sqlite3'
    db=sqlite3.connect(dbpath.resolve().as_uri()+'?mode=ro',uri=True)
    db.execute('BEGIN')
    anchor=db.execute('SELECT digest FROM artifacts WHERE n=?',(proof['derived_rows']-1,)).fetchone()[0]
    if anchor!=proof['derived_head']:raise ValueError('DERIVED_AUDIT_PREFIX_CHANGED')
    derived=[dict(n=n,digest=d,body=json.loads(body)) for n,d,body in db.execute(
        "SELECT n,digest,body FROM artifacts WHERE n<? AND json_extract(body,'$.kind')='INCIDENT'",(proof['derived_rows'],))]
    db.close()
    incident_summary=dict(raw_facts=len(decisions),raw_kinds=dict(Counter(r['kind'] for r in decisions)),
        classifications=dict(Counter(r['classification'] for r in decisions)),
        gap_classifications=dict(Counter(r['classification'] for r in decisions if r['kind']=='CALLBACK_TIMER_GAP')),
        derived_records=len(derived),derived_reasons=dict(Counter(r['body']['reason'] for r in derived)),
        derived_unique_source_observations=len({r['body']['source']['native_hash'] for r in derived}),
        all_derived_sources_in_verified_prefix=all(r['body']['source']['native_hash'] in native_by_hash for r in derived),
        gap_coverage_restored=False,missing_broker_events='UNKNOWN',backfill=False)
    # Verify new authenticated records, reuse the existing calibration (no refit).
    folder=ROOT/'outputs/pc_a_prospective_utc/authenticated_utc'
    state=read((folder/'state.json').relative_to(ROOT).as_posix())
    nts_count=verify_history(folder,state)
    records={}
    for p in folder.glob('*.json'):
        if len(p.stem)==32:
            r=json.loads(p.read_text());records[r['sha256']]=r
    ordered=[];head=state['chain_head']
    while head!='0'*64:
        ordered.append(records[head]);head=records[head]['payload']['previous']
    ordered.reverse()
    calibration=read('outputs/pc_a_prospective_utc/clock_calibration.json')
    prefix=[]
    for r in ordered:
        prefix.append(r)
        if r['sha256']==calibration['nts_chain_head']:break
    if not prefix or prefix[-1]['sha256']!=calibration['nts_chain_head']:
        raise ValueError('CALIBRATION_NOT_IN_NTS_CHAIN')
    source_sha=hashlib.sha256((ROOT/'python/nts_clock_calibration.py').read_bytes()).hexdigest()
    key=hashlib.sha256((''.join(r['sha256'] for r in prefix)+source_sha).encode()).hexdigest()
    if key!=calibration['input_key']:raise ValueError('CALIBRATION_INPUT_KEY_MISMATCH')
    cached=read('outputs/pc_a_prospective_utc/calibration_snapshots/'+key+'.json')
    if seal(cached['payload'])!=cached['sha256'] or cached['payload']!=calibration['calibration']:
        raise ValueError('CALIBRATION_HASH_MISMATCH')
    measurements=[(r,x['measurement']) for r in ordered for x in r['payload']['results']
        if x.get('status')=='AUTHENTICATED_MEASUREMENT' and valid_measurement(x.get('measurement',{}))]
    clock_changes=[dict(record_id=e['record_id'],old=e['fields']['OldTime'],new=e['fields']['NewTime'],
        wall_step_ns=iso_ns(e['fields']['NewTime'])-iso_ns(e['fields']['OldTime']))
        for e in events if e['provider']=='Microsoft-Windows-Kernel-General' and e['id']==1 and 'OldTime' in e['fields']]
    temporal=dict(nts_chain_head=state['chain_head'],nts_records_verified=nts_count,
        valid_authenticated_measurements=len(measurements),nts_capture_provenance='PINNED_CLIENT_VERIFICATION_AT_CAPTURE_AND_LOCAL_HASH_CHAIN_NOT_BROKER_TIME_AUTHENTICATION',
        clock_changes=clock_changes,calibration_reused=True,calibration_source_sha256=source_sha,
        calibration_input_key=key,calibration_groups=len(cached['payload']['groups']),
        calibration_dispositions=dict(Counter(g['affine_status'] for g in cached['payload']['groups'])),
        calibration_barriers=dict(Counter(reason for r in cached['payload']['barriers'] for reason in r['reasons'])),
        latest_measurements=[dict(record_sha256=r['sha256'],capture_id=m['capture_id'],origin=m['origin'],
            boot_identity=r['payload'].get('boot_identity'),offset_ns=m['offset_server_minus_host_ns'],
            rtt_ns=m['rtt_monotonic_ns'],server_error_ns=m['server_advertised_error_ns'],
            qpc=m.get('receive_clock_observation'),uptime_ms=m.get('receive_kernel_uptime_ms_interval'),
            uncertainty_scope=m['uncertainty_scope']) for r,m in measurements[-4:]],
        authenticated_utc_to_broker_generation_mapping=False,certified_native_event_intervals=[],
        prospective_ticks=proof['processed_real_ticks_in_quarantine'],
        receipt_sampling=dict(rows=len(receipt_windows),
            scope='LOCAL_COUNTER_CALL_ORDER_ONLY_NOT_POINT_RECEIPT_UTC',
            widest_windows=sorted(receipt_windows,key=lambda r:r['observation_window_width_ms'],reverse=True)[:10],
            source='mt5/ProspectiveUtcObserver.mq5 Record: read counter before TimeGMT; controller/isolated_observation.py pump: receipt counter after complete line read'),
        verified_relations=['NATIVE_SEQUENCE_AND_RAW_DERIVED_PREFIX_IDENTITY','OBSERVED_LOCAL_COUNTER_ELAPSED_GAPS',
            'AUTHENTICATED_NTS_EXCHANGES_AT_RECORDED_OBSERVATIONS','WINDOWS_RECORDED_WALL_CLOCK_STEPS',
            'CAUSALLY_ORDERED_NTS_ACTIVATION_BRACKET_RETAINED_NOT_REMEASURED'],
        unresolved=['BROKER_GENERATION_TO_UTC_INDEPENDENT_LINK','HISTORICAL_SERVER_TIME_MAPPING',
            'CALIBRATED_RECEIPT_COUNTER_ERROR_AND_WITHIN_SEGMENT_OSCILLATOR_BOUND','EXACT_HISTORICAL_SYMBOL_CALENDAR'])
    # Sanitized terminal-log evidence: no account numbers, network names or raw messages.
    terminal=Path.home()/'AppData/Roaming/MetaQuotes/Terminal/20C285FE08971A9A2E814AAC44AFC9D2'
    log_evidence=[]
    for sub in ('Logs','MQL5/Logs'):
        for day in ('20261031','20261101'):
            p=terminal/sub/(day+'.log')
            if not p.exists():continue
            raw=p.read_bytes();text=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig',errors='replace')
            entries=[]
            for line in text.splitlines():
                types=[name for name,pattern in [('DISCONNECT',r'disconnect|connection lost'),('CONNECT',r'connected to|authorized on|connection restored'),('OBSERVER_STOP',r'StartProspectiveUtcObserver.*(removed|stop|unload)')] if re.search(pattern,line,re.I)]
                if types:
                    label=re.search(r'\b\d{2}:\d{2}:\d{2}(?:\.\d+)?\b',line)
                    entries.append(dict(kinds=types,log_time_label=label.group(0) if label else None,line_sha256=hashlib.sha256(line.encode()).hexdigest()))
            log_evidence.append(dict(relative_terminal_path=sub+'/'+day+'.log',file_sha256=hashlib.sha256(raw).hexdigest(),events=entries,
                time_semantics='UNVERIFIED_LOG_LABEL_NOT_USED_AS_UTC_OR_EXACT_GAP_BOUNDARY'))
    source_gaps=[dict(requirement='ORIGINAL_SPLIT_MEMBERSHIP',missing='Exact IDs and purged boundaries, not counts or declared dates',source='Original producer of stochastic_master_v1 at ced3b6d9e469dadf76a4771049c994e476f19329; master/split manifests with frozen source hash'),
        dict(requirement='HOLDOUT_AND_OPEN_ROLE_MEMBERSHIP',missing='Exact reservations, role closure, comparable domain and dependency membership',source='Original dataset governance owner and original reservation/split manifests'),
        dict(requirement='XM_EVENT_UTC',missing='Independent link from broker event creation to authenticated UTC with bounded error',source='XM server-specific timestamp provenance/trace, or independently timestamped matched events with demonstrated identity and bounded generation/transport relation; NTS receipt or similar prices alone insufficient'),
        dict(requirement='HISTORICAL_CALENDAR',missing='Server-specific sessions, DST and exceptions over admitted periods',source='XM server/symbol historical session and exception records'),
        dict(requirement='UNKNOWN_GAP_CAUSE',missing='Per-callback scheduler/network trace; logged connection state does not identify root cause',source='Windows/MT5 diagnostic traces from the actual past interval, if retained; absence may be irreversible without a scientific acquisition decision')]
    summary=dict(MEMBERSHIP_VERIFIED='PUBLISHED_NATIVE_INTERVALS_IDS_AND_NEW_CAPTURE_PREFIX_ONLY',
        MEMBERSHIP_UNKNOWN='ORIGINAL_PROTECTED_SPLITS_AND_OPEN_ROLES',
        TEMPORAL_MAPPING_VERIFIED='SEQUENCE_RECEIPT_COUNTER_RELATIONS_NTS_EXCHANGES_AND_ACTIVATION_BRACKET_ONLY',
        TEMPORAL_MAPPING_UNRESOLVED=temporal['unresolved'],
        INCIDENTS_ADJUDICATED=incident_summary,CAUSAL_FEATURE_AUDIT='PRIOR_SYNTHETIC_NATIVE_PROOF_RETAINED_NO_NEW_REAL_FEATURES_GLOBAL_FAIL',
        INCIDENTS_UNRESOLVED=dict(root_cause_not_definitive=sum(r['classification']!='VERIFIED_CAUSE' for r in decisions),
            gap_coverage_unresolved=sum(r['kind']=='CALLBACK_TIMER_GAP' for r in decisions),
            verified_contributor_is_not_full_gap_resolution=True),
        DATASET_ADMISSION='BLOCKED',TRAINING_READINESS='BLOCKED',
        BLOCKERS_CLOSED=['AMBIGUOUS_INCIDENT_COUNTS_SEPARATED_RAW_DERIVED_AND_REPEATS',
            'PER_INCIDENT_CAUSE_CLASSIFICATION_WITH_SOURCE_AND_OS_REFERENCES',
            'MASTER_DECLARED_OUTER_SIGNAL_LABELS_RECOVERED_NOT_SPLIT_IDS',
            'CONCRETE_WINDOWS_CLOCK_DISCONTINUITIES_IDENTIFIED'],
        BLOCKERS_REMAINING=source_gaps,DATASET_HASH=None,admitted_intervals=[],
        actual_fits=0,actual_scoring=0,protected_rows_read=0,original_data_changed=False,
        DISCOVERY_VALIDATION='BLOCKED',HISTORICAL_HOLDOUT='BLOCKED',FINAL_TEST='LOCKED',DEMO='DISABLED',LIVE_TRADING=False,
        NEXT_STATE='CONTINUE_QUARANTINE_PRESERVE_GAPS_RECOVER_ORIGINAL_PROVENANCE_BEFORE_ADMISSION',
        host_utc_label=datetime.now(timezone.utc).isoformat(),
        ecuador_time=datetime.now(timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('America/Guayaquil')).isoformat())
    out.mkdir(parents=True)
    for name,value in dict(membership=membership,incidents=decisions,incident_summary=incident_summary,
        native_incident_facts=original_incidents,derived_incident_prefix=derived,
        windows=windows,network=network,temporal=temporal,mt5_log_evidence=log_evidence,
        source_requirements=source_gaps,source_receipts=receipts,summary=summary,
        prefix_receipt=dict(raw_and_derived_integrity=proof['raw_and_derived_integrity'],
            source_cursors=proof['state']['cursors'],derived_head=proof['derived_head'],derived_rows=proof['derived_rows'],
            processed_source_records=proof['processed_source_records'],processed_ticks=proof['processed_real_ticks_in_quarantine'],
            real_feature_causal_checks=proof['real_feature_causal_checks'],admitted=0)).items():
        (out/(name+'.json')).write_text(json.dumps(value,sort_keys=True,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    return summary


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True)
    print(json.dumps(build(p.parse_args().out),ensure_ascii=False,indent=2))
