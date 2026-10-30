"""In-memory structural preflight only. Never reads dataset rows or grants access.

An exposure ledger's completeness/authenticity cannot be proved by a boolean in
a manifest. A clean preflight still requires independent provenance review and
explicit study authorization. No consumer imports this as a production gate.
"""
import re


def preflight(candidate, exposures):
    required = {'study_id','role','instrument','domain_id','source_sha256',
                'signal_ids','feature_start','decision_start','decision_end','label_end',
                'path','ledger_sha256'}
    if set(candidate) != required:
        raise ValueError('MISSING_OR_UNKNOWN_MANIFEST_FIELDS')
    if candidate['role'] != 'TRAIN_NEW_PROPOSED':
        raise ValueError('PROTECTED_OR_LEGACY_ROLE')
    if not re.fullmatch(r'[a-z0-9_]+', candidate['study_id']):
        raise ValueError('INVALID_STUDY_ID')
    path = candidate['path'].replace('\\','/')
    parts = path.split('/')
    compact = re.sub('[^a-z0-9]', '', path.lower())
    if any(token in compact for token in ('validation','holdout','finaltest','futurecohort','pcacertification','prospective')):
        raise ValueError('PROTECTED_DATA_NAMESPACE')
    if '..' in parts or ':' in path or path.startswith('/') or not path.startswith(
            'outputs/new_native_studies/' + candidate['study_id'] + '/'):
        raise ValueError('UNAPPROVED_DATA_NAMESPACE')
    for key in ('source_sha256','ledger_sha256'):
        if not re.fullmatch('[0-9a-f]{64}', candidate[key]):
            raise ValueError('MISSING_HASH_BINDING')
    ids = candidate['signal_ids']
    if not isinstance(ids, list) or not ids or any(not isinstance(s,str) or not s for s in ids) or len(ids) != len(set(ids)):
        raise ValueError('MISSING_OR_DUPLICATE_SIGNAL_MEMBERSHIP')
    times = [candidate[k] for k in ('feature_start','decision_start','decision_end','label_end')]
    if any(type(t) is not int or t < 0 for t in times) or times != sorted(times):
        raise ValueError('INVALID_FULL_DEPENDENCY_INTERVAL')
    if not candidate['domain_id'] or not candidate['instrument'] or not exposures:
        raise ValueError('MISSING_EXPOSURE_EVIDENCE')
    required_exposure = {'instrument','domain_id','signal_ids','feature_start','label_end','role','source_sha256'}
    roles = set()
    for prior in exposures:
        if set(prior) != required_exposure:
            raise ValueError('INCOMPLETE_EXPOSURE_RECORD')
        if not re.fullmatch('[0-9a-f]{64}', prior['source_sha256']):
            raise ValueError('MISSING_EXPOSURE_SOURCE_HASH')
        if prior['source_sha256'] == candidate['source_sha256']:
            raise ValueError('PREVIOUSLY_EXPOSED_SOURCE')
        if not isinstance(prior['signal_ids'], list) or not prior['signal_ids'] or any(
                not isinstance(s,str) or not s for s in prior['signal_ids']) or len(prior['signal_ids']) != len(set(prior['signal_ids'])):
            raise ValueError('INCOMPLETE_EXPOSURE_MEMBERSHIP')
        if any(type(prior[k]) is not int or prior[k] < 0 for k in ('feature_start','label_end')) or prior['feature_start'] > prior['label_end']:
            raise ValueError('INVALID_EXPOSURE_INTERVAL')
        if set(ids) & set(prior['signal_ids']):
            raise ValueError('PREVIOUSLY_EXPOSED_SIGNAL')
        if prior['instrument'] != candidate['instrument']:
            continue
        roles.add(prior['role'])
        if prior['domain_id'] != candidate['domain_id']:
            raise ValueError('UNCOMPARABLE_TIME_DOMAINS')
        if times[0] <= prior['label_end'] and prior['feature_start'] <= times[-1]:
            raise ValueError('WARMUP_FEATURE_OR_LABEL_OVERLAP')
    if not {'TRAIN_EXHAUSTED','DISCOVERY_VALIDATION','HISTORICAL_HOLDOUT','FINAL_TEST','PROSPECTIVE_QUARANTINE'}.issubset(roles):
        raise ValueError('INCOMPLETE_PROTECTED_ROLE_LEDGER')
    return dict(structural_preflight='PASS', independence_certification='UNVERIFIED_LEDGER_AUTHENTICITY_AND_COMPLETENESS',
                dataset_rows_opened=0, training_authorized=False, scoring_authorized=False)
