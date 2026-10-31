"""Produce a new immutable maturity snapshot without reading protected datasets."""
import argparse
from datetime import datetime,timezone
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from controller.authorized_capture import CaptureManager,STATION,sha
from controller.dataset_maturity import audit_segment
from controller.isolated_observation import host_clock
from controller.pretrain_contracts import seal,verify_chain

PACKAGE=ROOT/'research/studies/us30cash_m5_native_pretrain_v1'


def inspect():
    index=json.loads((PACKAGE/'package_hashes.json').read_text())
    if seal(index['files'])!=index['root_sha256']:raise ValueError('FROZEN_PACKAGE_INDEX_CHANGED')
    for name,expected in index['files'].items():
        if Path(name).name!=name or sha(PACKAGE/name)!=expected:raise ValueError('FROZEN_PACKAGE_FILE_CHANGED_'+name)
    ledger=json.loads((PACKAGE/'exposure_ledger.json').read_text());verify_chain(ledger['entries'],ledger['chain_head'])
    manager=CaptureManager();manifest=manager.load();runtime=json.loads((manager.root/'runtime_state.json').read_text())
    segments=[]
    for name in runtime['segments']:
        if Path(name).name!=name:raise ValueError('INVALID_SEGMENT_NAME')
        segments.append(audit_segment(manager.root/'segments'/name))
    first=segments[0]
    if first['manifest_file_sha256']!=manifest['initial_segment_manifest_sha256']:raise ValueError('INITIAL_MANIFEST_CHANGED')
    now=host_clock();boundary=json.loads((manager.root/'activation_boundary.json').read_text())
    activation=manifest['activation_utc'];start=datetime.fromisoformat(activation['utc_estimate'])
    end=datetime.fromisoformat(now['host_utc_label']);days=max(0,(end.date()-start.date()).days-1)
    same_boot=now['boot_id']==boundary['clock']['boot_id']
    elapsed=now['uptime_ms']-boundary['clock']['uptime_ms'] if same_boot else None
    good=sum(s['coverage']['short_callback_intervals_ms'] for s in segments);gaps=sum(s['coverage']['gap_intervals_ms'] for s in segments)
    totals={key:sum(s['counts'].get(key,0) for s in segments) for key in ('ONTICK_LATEST_QUOTE','HEARTBEAT','EXCLUDED_PRE_CUT_METADATA')}
    plan=json.loads((PACKAGE/'prospective_collection_plan.json').read_text());authorization=json.loads((PACKAGE/'scientific_authorization_package.json').read_text());accept=authorization['ACCEPTANCE_CRITERIA']
    thresholds=dict(warmup_own_closed_m5=int(re.search(r'MINIMUM_(\d+)_CLOSED',plan['warmup']).group(1)),consecutive_base_signals=int(re.search(r'FIRST_(\d+)_',plan['acquisition_stop']).group(1)),post_last_entry_m5=int(re.search(r'THEN_(\d+)_',plan['acquisition_stop']).group(1)),minimum_evaluable_total=accept['minimum_evaluation_signals'],minimum_evaluable_buy=accept['minimum_each_side'],minimum_evaluable_sell=accept['minimum_each_side'],minimum_folds_each_side=accept['minimum_evaluable_folds_per_side'],minimum_utc_days=None)
    features=json.loads((PACKAGE/'temporal_dependencies.json').read_text())
    features['live_status']=[dict(feature=f['feature'],status='NO_NEW_STUDY_FEATURE_BYTES_OR_DECISION_CONTEXT',closed_availability='NOT_OBSERVABLE_WITH_HEARTBEATS_ONLY' if totals['ONTICK_LATEST_QUOTE']==0 else 'NOT_CAPTURED_BY_RAW_OBSERVER',seed_status='UNBOUND' if f['full_seed_required'] else 'MISSING_POST_START_CLOSED_BARS',minimum_input_bars=f['minimum_input_bars'],admitted=False) for f in features['features']]
    overlay_body=dict(ledger_sequence=len(ledger['entries']),previous=ledger['chain_head'],kind='MATURITY_RAW_METADATA_AUDIT_ONLY',capture_id=manifest['capture_id'],collection_manifest_sha256=sha(manager.root/'collection_manifest.json'),observed_host_clock=now,rows_inspected=sum(s['verified_rows'] for s in segments),source_membership_sha256=seal([s['membership'] for s in segments]),signals_opened=0,labels_opened=0,protected_rows_opened=0,scoring=False,independence_certified=False)
    entry=dict(overlay_body,entry_sha256=seal(overlay_body));verify_chain(ledger['entries']+[entry],entry['entry_sha256'])
    status=json.loads((manager.root/'collector_status.json').read_text());supervisor=json.loads((STATION/'supervisor_status.json').read_text())
    watchdog=json.loads((STATION/'watchdog_status.json').read_text());recovery=json.loads((ROOT/'outputs/pc_a_stability/recovery_status.json').read_text(encoding='utf-8-sig'))
    latest=segments[-1];last_age=now['uptime_ms']-latest['last_callback_uptime_ms'] if latest['boot_id']==now['boot_id'] and latest['last_callback_uptime_ms'] is not None else None
    ntsbase=ROOT/'outputs/pc_a_prospective_utc/authenticated_utc';ntsstate=json.loads((ntsbase/'state.json').read_text());ntsrecord=json.loads((ntsbase/ntsstate['last_record']).read_text())
    result=dict(NEW_CAPTURE_ID=manifest['capture_id'],CAPTURE_START_UTC=activation['utc_estimate'],CAPTURE_START_ECUADOR=start.astimezone(__import__('zoneinfo').ZoneInfo('America/Guayaquil')).isoformat(),CAPTURE_START_UTC_INTERVAL=[activation['utc_lower'],activation['utc_upper']],
        TOTAL_CAPTURE_DURATION=dict(host_uptime_elapsed_ms=elapsed,basis='SAME_BOOT_WINDOWS_UPTIME_INCLUDES_SUSPENSION_NOT_EVENT_UTC' if same_boot else 'MULTI_BOOT_NO_UNJUSTIFIED_COUNTER_SUM',observed_callback_envelope_ms=sum(s['callback_envelope_ms'] for s in segments),short_callback_support_ms=good,gap_interval_ms=gaps),
        COMPLETE_UTC_DAYS=0,complete_host_calendar_days_between_partial_end_dates=days,TICKS=totals['ONTICK_LATEST_QUOTE'],M1_BARS=0,M5_BARS=0,BUY_SIGNALS=0,SELL_SIGNALS=0,
        count_scope='VERIFIED_NEW_CAPTURE_RECORDS_ONLY_NOT_MARKET_SIGNAL_ABSENCE',bar_and_signal_generation='NOT_RUN_NO_BAR_FEATURE_RECORDER_OR_ADMITTED_REPLAY',HEARTBEATS=totals['HEARTBEAT'],NATIVE_SESSIONS=len({s['source_session'] for s in segments}),SEGMENTS=len(segments),RESTARTS=runtime['restarts'],COMPLETE_TRADING_SESSIONS=0,
        COVERAGE_STATUS='OBSERVED_HEARTBEAT_SUPPORT_ONLY_ALL_QUARANTINED',CLOCK_STATUS='ACTIVATION_NTS_BRACKET_VERIFIED_BROKER_EVENT_UTC_MAPPING_UNVERIFIED',CAUSAL_STATUS='FAIL_GLOBAL_FEATURE_BYTES_AND_SEEDS_MISSING',EXPOSURE_LEDGER='CHAIN_VERIFIED_COMPLETENESS_PARTIAL',MEMBERSHIP_STATUS='POST_CUT_RAW_IDS_VERIFIED_SCIENTIFIC_INDEPENDENCE_NOT_PROVEN',DATASET_MATURITY='NOT_READY',DATASET_HASH=None,ADMISSIBLE_RECORDS=0,QUARANTINED_RAW_RECORDS=sum(s['verified_rows'] for s in segments),TRAINING_READINESS='BLOCKED',HARD_BLOCKER=['NO_PROSPECTIVE_MARKET_TICKS_BARS_OR_FEATURES','INSUFFICIENT_FROZEN_WARMUP_AND_SIGNAL_SUPPORT','INCOMPLETE_LEGACY_MEMBERSHIP_AND_COMPARABLE_TIME_DOMAINS','UNRESOLVED_COVERAGE_GAPS_AND_NATIVE_EVENT_UTC_PROVENANCE','DATASET_ADMISSION_AND_TRAINING_NOT_AUTHORIZED'],NEXT_STATE='CONTINUE_EXISTING_QUARANTINED_CAPTURE_NO_BACKFILL_NO_COMPLETION_DATE',DISCOVERY_VALIDATION='BLOCKED',HISTORICAL_HOLDOUT='BLOCKED',FINAL_TEST='LOCKED',DEMO='DISABLED',LIVE_TRADING=False)
    return dict(result=result,clock=now,segments=segments,requirements=dict(protocol_sha256=sha(PACKAGE/'PROTOCOL_ES.md'),authorization_package_sha256=sha(PACKAGE/'scientific_authorization_package.json'),collection_plan_sha256=sha(PACKAGE/'prospective_collection_plan.json'),thresholds=thresholds,deficits=dict(warmup_own_m5=thresholds['warmup_own_closed_m5'],base_signals=thresholds['consecutive_base_signals'],post_entry_m5=thresholds['post_last_entry_m5'],evaluable_total=thresholds['minimum_evaluable_total'],evaluable_buy=thresholds['minimum_evaluable_buy'],evaluable_sell=thresholds['minimum_evaluable_sell'],evaluable_folds_each_side=thresholds['minimum_folds_each_side']),evaluation_not_run_no_labels=True,thresholds_changed=False,completion_date_estimate=None),features=features,
        membership=dict(raw_intervals=[dict(segment=s['segment'],session=s['source_session'],boot_id=s['boot_id'],**s['membership']) for s in segments],native_event_intervals=[],signal_ids=[],feature_dependencies=[],label_intervals=[],admitted_dataset_id=None,dataset_hash=None,role='EXCLUSIVE_PROVISIONAL_QUARANTINE_RESERVATION_NOT_SCIENTIFIC_COHORT',old_reservation_closure='FORWARD_ONLY_VERIFIED_BY_ACTIVATION_DECISIONS',protected_membership_completeness=False),
        exposure=dict(legacy_file_sha256=sha(PACKAGE/'exposure_ledger.json'),legacy_chain_head=ledger['chain_head'],legacy_completeness_verified=ledger['completeness_verified'],legacy_missing=ledger['missing'],forward_closure_evidence_sha256=sha(manager.root/'collection_manifest.json'),audit_overlay_entry=entry,overlay_scope='AUDIT_ACCESS_METADATA_NOT_REPLACEMENT_OF_FROZEN_LEDGER',no_protected_data_read=True),
        monitors=dict(collector_status=status['status'],last_callback_age_ms=last_age,supervisor_status=supervisor['status'],supervisor_uptime_age_ms=now['uptime_ms']-supervisor['clock']['uptime_ms'] if supervisor['clock']['boot_id']==now['boot_id'] else None,watchdog=watchdog,recovery=recovery,no_installation_or_power_tests_repeated=True),
        clock_evidence=dict(activation=activation,latest_nts_record_sha256=sha(ntsbase/ntsstate['last_record']),nts_statuses=[r['status'] for r in ntsrecord['payload']['results']],native_event_utc_certified=False,full_utc_day_coverage_certified=False),
        manifests=dict(collection_manifest_sha256=sha(manager.root/'collection_manifest.json'),frozen_package_root_sha256=index['root_sha256'],decision_chain_head=manifest['decision_chain_head'],integrity='VERIFIED_AT_DURABLE_PREFIX_SNAPSHOT',no_originals_modified=True))


def main(out):
    data=inspect();out=Path(out)
    out.mkdir(parents=True,exist_ok=False)
    for name,value in data.items():(out/(name+'.json')).write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf8',newline='\n')
    hashes={p.name:sha(p) for p in out.iterdir() if p.is_file()}
    (out/'hashes.json').write_text(json.dumps(dict(files=hashes,root_sha256=seal(hashes)),indent=2,sort_keys=True)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(data['result'],indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args();main(args.out)
