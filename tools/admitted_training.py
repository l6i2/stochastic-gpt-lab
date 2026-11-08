"""Future exact-grant dispatch. Refuses before dataset I/O without authority."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from controller.training_admission_gate import authorize_execution
from controller.native_study_runner import execute,bootstrap_contrasts,acceptance
from controller.pretrain_contracts import seal


def freeze_bc_models(grant,models,binding,attempt,*,clock=None,nts=None):
    """Future grant-only immutable fold4 artifacts; never fits or selects models."""
    authorize_execution(grant,ROOT)  # Refuse before serialization or filesystem I/O.
    from controller.bc_study import STUDY
    if (grant['study_id']!=STUDY or set(models)!={'BUY','SELL'} or binding.get('selected_fold')!=4
            or binding.get('fits')!=8 or binding.get('additional_fits')!=0
            or binding.get('grant_sha256')!=seal(grant)):
        raise ValueError('INVALID_PREDEFINED_BC_MODEL_FREEZE')
    from controller.authorized_capture import once,sha,fresh_nts,bracket
    from controller.isolated_observation import host_clock
    from controller.pretrain_contracts import FEATURES
    if binding.get('feature_order')!=list(FEATURES):raise ValueError('FREEZE_FEATURE_ORDER_CHANGED')
    expected=ROOT/'outputs/admitted_native_studies'/grant['study_id'].lower()/'authorized_runs'/seal(grant)
    if Path(attempt).resolve()!=expected.resolve():raise ValueError('NON_AUTHORIZED_FREEZE_PATH')
    import joblib,os
    clock=clock or host_clock;nts=nts or fresh_nts
    before=nts();files={}
    for side in ('BUY','SELL'):
        path=Path(attempt)/(side+'_fold4.joblib')
        with path.open('xb') as stream:
            joblib.dump(models[side],stream);stream.flush();os.fsync(stream.fileno())
        files[path.name]=sha(path)
    cut=clock();after=nts()
    receipt=dict(schema='bc-frozen-models/1',models_sha256=files,binding=binding,
        freeze_clock=cut,freeze_utc=bracket(before,after,cut),code_head=grant['code_head'],
        protocol_hash=grant['protocol_hash'],environment_hash=grant['environment_hash'],
        EVAL_CONTEXT_active=False,EVAL_PROSPECTIVE_active=False,scoring_authorized=False,
        selection='FIXED_FOLD_4_NOT_PERFORMANCE',additional_fits=0)
    once(Path(attempt)/'freeze_clock_evidence.json',dict(before=before,cut=cut,after=after))
    once(Path(attempt)/'model_freeze.json',receipt)
    return receipt


def dispatch(grant):
    manifest=authorize_execution(grant,ROOT)
    # Identity is checked freshly, even if a dashboard identity observation is old.
    from tools.prospective_pipeline import NativeReference
    broker=NativeReference();broker.connect()
    try:
        account=broker.mt5.account_info()
        if account is None or account.trade_mode!=0:raise ValueError('REAL_OR_UNKNOWN_ACCOUNT_HARD_FAIL')
    finally:broker.close()
    attempt=ROOT/'outputs/admitted_native_studies'/grant['study_id'].lower()/'authorized_runs'/seal(grant)
    claimed=False
    def claim(identity):
        nonlocal claimed
        attempt.mkdir(parents=True,exist_ok=True)
        with (attempt/'attempt.json').open('x',encoding='utf8') as f:
            json.dump(dict(grant_sha256=identity,status='CLAIMED_SINGLE_ATTEMPT'),f)
        claimed=True
    def load(_):
        return json.loads((ROOT/manifest['dataset_path']).read_text())
    try:
        from controller.bc_study import STUDY
        kwargs={'model_sink':lambda models,binding:freeze_bc_models(grant,models,binding,attempt)} if grant['study_id']==STUDY else {}
        result=execute(grant,load,claim,**kwargs)
        metrics=bootstrap_contrasts(result['rows'],grant['dataset_first_observed_bar'],manifest['dataset_last_observed_bar'])
        metrics['integrity_and_causal_admission_verified']=True
        result.update(metrics=metrics,acceptance=acceptance(metrics),scientific_grant_sha256=seal(grant))
        with (attempt/'results.json').open('x',encoding='utf8') as f:json.dump(result,f,allow_nan=False,indent=2)
        return dict(training_executed=True,result_path=str(attempt/'results.json'),acceptance=result['acceptance'])
    except FileExistsError:
        if claimed:raise RuntimeError('RESULT_PATH_ALREADY_EXISTS_AFTER_CLAIM_NO_RETRY')
        return dict(training_executed=False,status='SINGLE_ATTEMPT_ALREADY_CLAIMED_NO_RETRY')
    except Exception as e:
        if attempt.exists():
            with (attempt/'terminal_failure.json').open('x',encoding='utf8') as f:json.dump(dict(type=type(e).__name__,message=str(e),retry_authorized=False),f)
        raise


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--grant',required=True)
    a=p.parse_args();print(json.dumps(dispatch(json.loads(Path(a.grant).read_text()))))
