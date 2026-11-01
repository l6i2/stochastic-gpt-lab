"""Operational separation only. Cannot override frozen scientific admission."""
from .pretrain_contracts import seal


def recovery_disposition(name,expected_sha,candidates,search_complete):
    exact=[c for c in candidates if expected_sha and c['sha256']==expected_sha]
    if exact:
        return dict(name=name,status='EXACT_RECOVERY_HASH_MATCH',expected_sha256=expected_sha,
                    matches=exact,original_identity_claim_scope='MATCHED_PUBLISHED_HASH_ONLY')
    return dict(name=name,status='IRRECOVERABLE_IN_ACCESSIBLE_SEARCHED_SOURCES' if search_complete else 'UNRESOLVED_SEARCH_INCOMPLETE',
        expected_sha256=expected_sha,exact_original_recovered=False,
        missing_hash_is_not_reconstructable_from_counts=True,
        global_nonexistence_claim=False,automatic_retry=False,
        retry_only_if='NEW_SOURCE_BACKUP_OR_ACCESS_EVIDENCE')


def work_plan(recovery,*,live_authority):
    """Legacy failure does not disable already authorized quarantine operations."""
    if live_authority.get('collection_authorized') is not True:
        raise ValueError('EXISTING_COLLECTION_AUTHORIZATION_REQUIRED')
    if any(live_authority.get(k) is not False for k in
        ('dataset_admission_authorized','training_authorized','scoring_authorized','backfill_allowed')):
        raise ValueError('LIMITED_AUTHORITY_SCOPE_CHANGED')
    rows=[dict(task=name,status='CONTINUE_EXISTING_AUTHORIZED_QUARANTINE',requires_legacy_manifests=False)
          for name in ('RAW_NATIVE_CAPTURE','RAW_HASH_AND_IDENTITY_VERIFICATION','INCREMENTAL_NATIVE_BAR_COMPARISON',
            'CAUSAL_FEATURE_PREPARATION','MATURITY_AND_HEALTH_REPORTS','NTS_RECEIPT_CORRELATION','INCIDENT_MONITORING')]
    result=dict(schema='pc-a-independent-operational-plan/1',tasks=rows,
        legacy_recovery=recovery,legacy_originals_required_to_operate=False,
        frozen_scientific_admission_changed=False,admission='BLOCKED',
        scoring=False,training=False,new_cohort_activated=False,new_start_selected=False,
        historic_data_adopted=False,legacy_datasets_retired_from_candidate_inputs=True,
        scientific_future_decision='SEPARATE_PROSPECTIVE_PROVENANCE_RULE_IF_ORIGINAL_LEDGER_CANNOT_BE_RECOVERED; NOT_ACTIVATED',
        native_diagnostic_method='RETAIN_APPROVED_METHOD_NO_GENERATION_UTC_CLAIM',
        protected_roles=['DISCOVERY_VALIDATION','HISTORICAL_HOLDOUT','FINAL_TEST'])
    return dict(result,plan_sha256=seal(result))
