"""Snapshot existing PRE_TRAIN evidence into a new directory, never mutate it.

Uses the existing automatic maturity producer. Does not add services, execute
MT5 probes, open historical datasets, train, score or grant authorization.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from controller.pretrain_package import verify_package
from controller.pretrain_contracts import seal, temporal_dependencies
from controller.scientific_preparation import reconcile, training_plan, progress_projection
from controller.native_feature_diagnostic import resume
from controller.feature_availability_review import GROUPS
from tools.verify_prospective_operation import verify_ledgers, sample


def build(destination):
    destination=Path(destination)
    if destination.exists():
        raise ValueError('NEW_IMMUTABLE_REPORT_DIRECTORY_REQUIRED')
    receipts=[]
    def read(relative):
        p=ROOT/relative
        raw=p.read_bytes()
        receipts.append(dict(path=relative,sha256=hashlib.sha256(raw).hexdigest()))
        return json.loads(raw)
    package='research/studies/us30cash_m5_native_pretrain_v1/'
    verified=verify_package()
    base=read(package+'exposure_ledger.json')
    overlays=[read('research/studies/us30cash_m5_dataset_maturity_20261031_v1/exposure.json')['audit_overlay_entry'],
              read('research/studies/strategy_diagnostic_preparation_20261101_v1/exposure_overlay.json')['audit_entry']]
    known=read(package+'known_exposed_signal_membership.json')
    original_membership=read(package+'dataset_membership.json')
    prior_membership=read('research/studies/us30cash_m5_dataset_maturity_20261031_v1/membership.json')
    censored_metadata=read('docs/CENSORED_MEMBERSHIP_QUARANTINE.json')
    for p in sorted((ROOT/'research/studies/us30cash_m5_native_collection_readiness_v1').glob('*.json')):
        read(p.relative_to(ROOT).as_posix())
    protocol=read(package+'scientific_authorization_package.json')
    read(package+'package_hashes.json')
    activation_dir=ROOT/'research/studies/us30cash_m5_native_collection_activation_v1'
    for p in sorted(activation_dir.glob('*.json')):
        read(p.relative_to(ROOT).as_posix())
    activation=json.loads((activation_dir/'collection_manifest.json').read_text())
    native=resume()  # Verifies prior capture bytes; never run a new terminal.
    prefix=read('outputs/pc_a_certification/native_features/latest.json')
    oracle=read('research/studies/us30cash_m5_prospective_pipeline_20261031_v1/native_oracle.json')
    current=sample()
    integrity=verify_ledgers()  # Durable prefixes may advance while live capture runs.
    m=progress_projection(current['derived'])
    read('outputs/prospective_derivatives_v1/deployment_pin_current.json')
    membership=dict(capture_id=m['raw_capture_id'], activation=activation,
        original_reserved_membership=original_membership,
        known_exposed_signal_ids=known['signals'],
        published_censored_nonmember_ids=[r['signal_id'] for r in censored_metadata['ids']],
        published_censored_membership_disposition=censored_metadata['classification'],
        prior_maturity_membership=prior_membership,
        source_prefixes=integrity['raw_segments'],
        processed_records=integrity['processed_source_records'],
        processed_real_ticks=integrity['processed_real_ticks_in_quarantine'],
        derived_chain_head=integrity['derived_head'], derived_rows=integrity['derived_rows'],
        old_prefixes_retained=integrity['old_version_prefix_retained'],
        old_raw_prefixes_verified=integrity['old_raw_prefixes_verified'],
        disposition='QUARANTINED_NOT_SCIENTIFICALLY_INDEPENDENT_CERTIFIED',
        admitted_intervals=[], admitted_signal_ids=[], dataset_hash=None,
        complete_legacy_membership=False, original_roles_not_silently_closed=True)
    ledger=reconcile(base,overlays,receipts.copy())
    features=dict(dependencies=temporal_dependencies(),groups=GROUPS,
        synthetic_prefix_evidence=native,
        synthetic_field_status_counts=dict(Counter(r['semantic_disposition'] for r in prefix['result']['fields'])),
        native_indicator_oracle=oracle,
        live_feature_causal_status=integrity['real_feature_causal_status'],
        seed_membership='PENDING_OWN_PROSPECTIVE_HISTORY',
        structure_break_flags='FROZEN_INCLUSIVE_WINDOW_ALWAYS_FALSE_NOT_WHITELISTED_NO_STRATEGY_CHANGE',
        profile='PAST_TICK_WINDOW_ONLY_COMPLETENESS_REQUIRES_REAL_COVERAGE_NOT_CURRENT_WHITELIST',
        session_features='NOT_WHITELISTED_NATIVE_TO_UTC_UNVERIFIED',
        global_causal_audit='FAIL_UNCHANGED')
    plan=training_plan(protocol['PROTOCOL_HASH'],protocol['FEATURE_WHITELIST_HASH'])
    statistical=dict(protocol_hash=protocol['PROTOCOL_HASH'],budget=protocol['TRAINING_BUDGET'],
        acceptance_criteria=protocol['ACCEPTANCE_CRITERIA'],package_integrity=verified,
        unchanged=True,actual_training_calls=0,actual_scoring_calls=0,
        future_execution_adapter='IMPLEMENTED_EMPTY_GRANT_ALLOWLIST_NO_DATA_IO_OR_FIT_CALLED',
        validation_remaining='REAL_ADMITTED_INPUT_INTEGRATION_AND_RESAMPLING_COVERAGE_REVIEW_BEFORE_AUTHORIZATION')
    summary=dict(snapshot_host_utc=datetime.now(timezone.utc).isoformat(),
        snapshot_ecuador=datetime.now(timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('America/Guayaquil')).isoformat(),
        code_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        STUDY_PACKAGE='VERIFIED_PRE_TRAIN_INCOMPLETE_EVIDENCE',
        EXPOSURE_LEDGER='LOCAL_METADATA_RECONCILED_ORIGINAL_FORKS_PRESERVED_LEGACY_INCOMPLETE',
        MEMBERSHIP='RAW_DURABLE_PREFIX_VERIFIED_SCIENTIFIC_INDEPENDENCE_UNPROVEN',
        FEATURE_CAUSALITY='SYNTHETIC_NATIVE_PREFIX_VERIFIED_LIVE_PENDING_GLOBAL_FAIL',
        TEMPORAL_DEPENDENCIES='ALL_SIX_WHITELIST_FEATURES_EXPLICIT_12_GROUPS_REVIEWED',
        STATISTICAL_PROTOCOL='HASH_VERIFIED_UNCHANGED_ONE_FAMILY_EIGHT_FUTURE_FITS_ZERO_AUTHORIZED',
        TRAINING_RUNNER_READY='PREPARED_LOCKED_ZERO_FITS_NO_SCIENTIFIC_GRANTS',
        PROSPECTIVE_COLLECTION=m['raw_collector_status'], M5_PROCESSOR=m['status'],
        DATASET_MATURITY=m['dataset_maturity'],
        BLOCKERS_REQUIRING_NEW_DATA=['REAL_TICKS_AND_EXACT_NATIVE_BAR_PARITY','350_OWN_CLOSED_M5_AND_RECURSIVE_SEEDS',
            '800_CONSECUTIVE_BASE_SIGNALS_PLUS_100_OBSERVED_M5','200_EVALUABLE_80_BUY_80_SELL_3_FOLDS_PER_SIDE'],
        BLOCKERS_REQUIRING_EXISTING_EVIDENCE=base['missing']+['ADJUDICATE_EXISTING_GAPS_WITHOUT_RESETTING_BOUNDARY',
            'NATIVE_EVENT_UTC_PROVENANCE_AND_EXACT_CALENDAR_NOT_PROVEN'],
        BLOCKERS_REQUIRING_CODE=[],
        FUTURE_EXECUTION_VALIDATION=['REAL_ADMITTED_DATA_ADAPTER_INTEGRATION','BOOTSTRAP_DEPENDENCE_AND_COVERAGE_REVIEW_BEFORE_GRANT'],
        TRAINING_READINESS='BLOCKED', authorization_package_created=False,
        authorization_requested=False, DATASET_HASH=None, admitted_records=0,
        protected_rows_opened=0,training_calls=0,scoring_calls=0,
        DISCOVERY_VALIDATION='BLOCKED',HISTORICAL_HOLDOUT='BLOCKED',FINAL_TEST='LOCKED',
        DEMO='DISABLED',LIVE_TRADING=False,
        NEXT_STATE='CONTINUE_EXISTING_QUARANTINED_CAPTURE_NO_AUTOMATIC_ADMISSION_OR_TRAINING')
    destination.mkdir(parents=True)
    inventory=[dict(r,bytes='VERIFIED_SHA256_SNAPSHOT',scientific_scope='PARTIAL_NOT_DATA_ADMISSION') for r in receipts]
    for name,value in dict(exposure=ledger,membership=membership,features=features,inventory=inventory,
                           protocol=statistical,training_plan=plan,progress=m,
                           integrity=integrity,runtime=current,summary=summary,source_receipts=receipts).items():
        (destination/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf8',newline='\n')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True)
    print(json.dumps(build(parser.parse_args().out),ensure_ascii=False,indent=2))
