"""Single fail-closed admission authority; no current scientific grants exist."""
import hashlib,json,subprocess
from pathlib import Path
from .pretrain_contracts import seal

from .scientific_authority import AUTHORIZED_GRANT_HASHES,ADMITTED_PACKAGE_HASHES
from .git_runtime import command as git_command
CHECKS=('independent_dataset','versioned_sealed','dataset_hash','complete_membership',
        'verified_coverage','contract_causality','frozen_whitelist','approved_protocol','approved_budget')


def snapshot_gate(maturity,broker,*,grant=None,root=None):
    """Read-only readiness, not a certificate made from self-declared booleans."""
    demo=broker.get('identity_verified') is True and broker.get('demo') is True
    reasons=[]
    if not demo:reasons.append('REAL_OR_UNKNOWN_ACCOUNT_HARD_FAIL')
    if not maturity.get('dataset_hash') or maturity.get('admitted_records',0)<=0:
        reasons.append('NO_INDEPENDENT_ADMITTED_SEALED_DATASET')
    if grant is not None and demo:
        try:
            authorize_execution(grant,root)
            return dict(TRAINING_ADMISSION_GATE='PASS_AUTHORIZED',reasons=[],package_complete=True,
                authorization_request_ready=False,authorization_requested=False,execution_permitted=True,
                training_executed=False,scientific_grants=len(AUTHORIZED_GRANT_HASHES))
        except PermissionError as e:
            if seal(grant) in ADMITTED_PACKAGE_HASHES:
                _verify_bundle(grant,root)
                return dict(TRAINING_ADMISSION_GATE='BLOCKED_AWAITING_EXPLICIT_TRAINING_AUTHORIZATION',
                    reasons=['NO_HASH_BOUND_SCIENTIFIC_AUTHORIZATION'],package_complete=True,
                    authorization_request_ready=True,authorization_requested=False,
                    execution_permitted=False,training_executed=False,scientific_grants=len(AUTHORIZED_GRANT_HASHES))
            reasons.append(str(e))
        except (ValueError,OSError) as e:reasons.append(str(e))
    reasons.extend(['COMPLETE_MEMBERSHIP_AND_COVERAGE_RECEIPTS_REQUIRED',
        'APPLICABLE_CONTRACT_CAUSALITY_NOT_ADMITTED','NO_HASH_BOUND_SCIENTIFIC_AUTHORIZATION'])
    return dict(TRAINING_ADMISSION_GATE='BLOCKED',reasons=reasons,
        package_complete=False,authorization_request_ready=False,authorization_requested=False,
        execution_permitted=False,training_executed=False,scientific_grants=len(AUTHORIZED_GRANT_HASHES))


def authorize_execution(grant,root):
    """No files (including protected inputs) are read before a trusted grant.

    The empty allowlist can only change in a later reviewed authorization commit.
    A hash-matched grant binds the admitted manifest, complete proof receipts,
    file bytes, protocol, whitelist, budget and current code revision.
    """
    if seal(grant) not in AUTHORIZED_GRANT_HASHES:
        raise PermissionError('NO_EXPLICIT_HASH_BOUND_SCIENTIFIC_GRANT')
    return _verify_bundle(grant,root)


def prepare_authorization_request(bundle,root):
    if seal(bundle) not in ADMITTED_PACKAGE_HASHES:
        raise PermissionError('NO_VERIFIED_COMPLETE_ADMISSION_PACKAGE')
    _verify_bundle(bundle,root)
    return dict(bundle,request_only=True,training_authorized=False,scoring_authorized=False)


def validate_observed_limits(first, last):
    if type(first) is not int or type(last) is not int or first<0 or last<first:
        raise ValueError('ADMITTED_OBSERVED_BOUNDS_MISSING_OR_INVALID')


def validate_observed_bounds(rows, first, last):
    """Reject missing bootstrap origins before any estimator can consume budget."""
    validate_observed_limits(first,last)
    if not isinstance(rows,list) or not rows:
        raise ValueError('EMPTY_ADMITTED_DATASET')
    previous=None
    for row in rows:
        index=row.get('observed_bar_index') if isinstance(row,dict) else None
        if type(index) is not int or not first<=index<=last:
            raise ValueError('ROW_OUTSIDE_ADMITTED_OBSERVED_BOUNDS')
        if previous is not None and index<=previous:
            raise ValueError('NONCHRONOLOGICAL_OBSERVED_BAR_INDEX')
        previous=index


def _verify_bundle(grant,root):
    root=Path(root).resolve()
    required={'study_id','dataset_hash','protocol_hash','feature_whitelist_hash','membership_hash',
        'exposure_hash','admission_receipt_hash','code_head','environment_hash','row_schema',
        'plan_hash','dataset_first_observed_bar','manifest_path','manifest_sha256','max_fits'}
    if set(grant)!=required or grant['row_schema']!='native-study-admitted-rows/1' or type(grant['max_fits']) is not int or not 0<grant['max_fits']<=8:
        raise ValueError('INVALID_SCIENTIFIC_GRANT_SCHEMA_OR_BUDGET')
    prefix='outputs/admitted_native_studies/'+grant['study_id'].lower()+'/'
    def admitted_path(relative):
        if not isinstance(relative,str) or '\\' in relative or not relative.startswith(prefix) or '..' in relative.split('/'):
            raise ValueError('NON_ADMITTED_OR_PROTECTED_NAMESPACE')
        p=(root/relative).resolve()
        if not p.is_relative_to(root/prefix) or any(part.is_symlink() or (hasattr(part,'is_junction') and part.is_junction()) for part in (root/relative,*list((root/relative).parents)[:-1])):
            raise ValueError('DATA_PATH_ESCAPE')
        return p
    manifest_path=admitted_path(grant['manifest_path'])
    raw=manifest_path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=grant['manifest_sha256']:raise ValueError('ADMISSION_MANIFEST_CHANGED')
    m=json.loads(raw)
    if m.get('role')!='TRAIN_NEW_ADMITTED' or m.get('quarantine') is not False:
        raise ValueError('QUARANTINE_OR_PROTECTED_DATASET_NOT_ADMITTED')
    if set(m.get('checks',{}))!=set(CHECKS) or any(m['checks'][k] is not True for k in CHECKS):
        raise ValueError('INCOMPLETE_SCIENTIFIC_ADMISSION_RECEIPTS')
    progress=m.get('maturity',{})
    required_counts={'own_warmup':350,'consecutive_signals':800,'post_signal_bars':100,'evaluable_total':200,'BUY':80,'SELL':80,'BUY_folds':3,'SELL_folds':3}
    if set(progress)!=set(required_counts) or any(type(progress[k]) is not int or progress[k]<n for k,n in required_counts.items()) or progress['consecutive_signals']!=800 or progress['post_signal_bars']!=100:
        raise ValueError('FROZEN_MATURITY_NOT_MET')
    for k in ('study_id','dataset_hash','protocol_hash','feature_whitelist_hash','membership_hash',
              'exposure_hash','admission_receipt_hash','code_head','environment_hash',
              'row_schema','plan_hash','dataset_first_observed_bar','max_fits'):
        if m.get(k)!=grant[k]:raise ValueError('GRANT_RECEIPT_BINDING_MISMATCH_'+k)
    if m.get('account_mode')!='DEMO' or m.get('live_trading') is not False:
        raise ValueError('REAL_OR_UNKNOWN_ACCOUNT_HARD_FAIL')
    if m.get('protected_sets')!={'DISCOVERY_VALIDATION':'BLOCKED','HISTORICAL_HOLDOUT':'LOCKED','FINAL_TEST':'LOCKED'}:
        raise ValueError('PROTECTED_GATE_CHANGED')
    from .bc_study import STUDY as BC_STUDY
    if grant['study_id']==BC_STUDY:
        package=root/'research/studies/bc_train_future_eval_v1'
        documents=(('contract.json','protocol_hash'),('feature_whitelist.json','feature_whitelist_hash'))
    else:
        package=root/'research/studies/us30cash_m5_native_pretrain_v1'
        documents=(('PROTOCOL_ES.md','protocol_hash'),('feature_model_whitelist.json','feature_whitelist_hash'))
    for name,key in documents:
        if hashlib.sha256((package/name).read_bytes()).hexdigest()!=grant[key]:raise ValueError('FROZEN_PROTOCOL_OR_WHITELIST_CHANGED')
    head=subprocess.check_output(git_command('rev-parse','HEAD'),cwd=root,text=True).strip()
    if head!=grant['code_head']:
        subprocess.run(git_command('merge-base','--is-ancestor',grant['code_head'],head),cwd=root,check=True,capture_output=True)
        changed=subprocess.check_output(git_command('diff','--name-only',grant['code_head'],head),cwd=root,text=True).splitlines()
        if set(changed)-{'controller/scientific_authority.py','configs/scientific_training_grant.json'}:
            raise ValueError('REVIEWED_CODE_CHANGED_OUTSIDE_EXPLICIT_AUTHORITY_COMMIT')
    if subprocess.check_output(git_command('status','--porcelain','--untracked-files=normal'),cwd=root,text=True).strip():
        raise ValueError('REVIEWED_WORKTREE_NOT_CLEAN')
    validate_observed_limits(grant['dataset_first_observed_bar'],m.get('dataset_last_observed_bar'))
    if not m.get('files') or m.get('dataset_path') not in m['files']:raise ValueError('DATASET_FILE_INDEX_MISSING')
    for relative,digest in m['files'].items():
        if hashlib.sha256(admitted_path(relative).read_bytes()).hexdigest()!=digest:raise ValueError('ADMITTED_FILE_HASH_CHANGED')
    receipt_keys={'membership_hash','exposure_hash','admission_receipt_hash','environment_hash'}
    if set(m.get('receipts',{}))!=receipt_keys:raise ValueError('REQUIRED_RECEIPT_PATHS_MISSING')
    for key,path in m['receipts'].items():
        if m['files'].get(path)!=grant[key]:raise ValueError('RECEIPT_NOT_BOUND_TO_INDEX_'+key)
    import platform
    from importlib.metadata import version
    environment=json.loads(admitted_path(m['receipts']['environment_hash']).read_text())
    if environment!={'python':platform.python_version(),'numpy':version('numpy'),'scikit-learn':version('scikit-learn')}:
        raise ValueError('RUNTIME_ENVIRONMENT_CHANGED')
    rows=json.loads(admitted_path(m['dataset_path']).read_text())
    if seal(rows)!=grant['dataset_hash']:
        raise ValueError('CANONICAL_DATASET_HASH_MISMATCH')
    validate_observed_bounds(rows,grant['dataset_first_observed_bar'],m.get('dataset_last_observed_bar'))
    return m
