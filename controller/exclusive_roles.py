"""Forward-only scientific role assignment; never recovers unknown legacy bounds."""
import json
from pathlib import Path
from .authorized_capture import sha
from .pretrain_contracts import seal
from .isolated_observation import GENESIS


def role_chain(entries):
    head=GENESIS; result=[]
    for entry in entries:
        digest=seal(dict(previous=head,payload=entry))
        result.append(dict(previous=head,digest=digest,payload=entry));head=digest
    return result


def validate_roles(value, manifest):
    head=GENESIS
    for row in value['ledger']:
        if row['previous']!=head or seal(dict(previous=head,payload=row['payload']))!=row['digest']:
            raise ValueError('ROLE_CHAIN_CHANGED')
        head=row['digest']
    close,assign=[row['payload'] for row in value['ledger']]
    if close['kind']!='CLOSE_ALL_PRIOR_FUTURE_INGRESS' or close['scope']!='PC_A_US30Cash_ALL_PRIOR_RESERVATIONS':
        raise ValueError('INCOMPLETE_RESERVATION_SCOPE')
    if assign['kind']!='ASSIGN_EXCLUSIVE_FORWARD_ROLE' or assign['study_id']!=manifest['study_id'] or assign['dataset_id']!=manifest['dataset_id'] or assign['capture_id']!=manifest['capture_id'] or assign['producer_id']!=manifest['producer_id']:
        raise ValueError('ROLE_IDENTITY_MISMATCH')
    if close['cutoff_hash']!=assign['cutoff_hash'] or assign['cutoff_hash']!=seal(value['cutoff']):
        raise ValueError('ROLE_BOUNDARY_CHANGED')
    if value['cutoff']['clock']['boot_id']!=value['authorization_observed_clock']['boot_id'] or value['cutoff']['clock']['monotonic_ns']<=value['authorization_observed_clock']['monotonic_ns']:
        raise ValueError('CUT_NOT_AFTER_AUTHORIZATION')
    if value['precut_data_adopted'] or value['legacy_bounds_recovered'] or value['training_authorized']:
        raise ValueError('ROLE_AUTHORITY_EXCEEDED')
    return dict(exclusive=True,minimum_native_open_msc=value['cutoff']['minimum_native_open_msc'],
                minimum_m1_open_msc=(value['cutoff']['native_anchor']['time_msc']//60000+1)*60000,
                cutoff_clock=value['cutoff']['clock'],ledger_head=head)


def verify_roles(root, manifest):
    ref=manifest.get('exclusive_role_assignment')
    if not ref:return None
    path=(Path(root)/ref['path']).resolve()
    if not path.is_relative_to(Path(root).resolve()) or sha(path)!=ref['sha256']:
        raise ValueError('ROLE_ASSIGNMENT_CHANGED')
    value=json.loads(path.read_text())
    auth=(Path(root)/value['authorization_path']).resolve()
    if not auth.is_relative_to(Path(root).resolve()) or sha(auth)!=value['authorization_sha256']:
        raise ValueError('ROLE_AUTHORIZATION_CHANGED')
    authorization=json.loads(auth.read_text())
    if authorization['scope']!='ALL_PRIOR_RESERVATIONS_FUTURE_PC_A_US30CASH_INGRESS_CLOSED_EXCLUSIVE_C_F_AFTER_NEW_CUT' or authorization['training_authorized'] is not False:
        raise ValueError('ROLE_AUTHORIZATION_SCOPE_CHANGED')
    if authorization['observed_clock']!=value['authorization_observed_clock']:
        raise ValueError('ROLE_AUTHORIZATION_CLOCK_CHANGED')
    return validate_roles(value,manifest)
