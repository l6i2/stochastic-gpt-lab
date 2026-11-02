"""Future exact-grant dispatch. Refuses before dataset I/O without authority."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from controller.training_admission_gate import authorize_execution
from controller.native_study_runner import execute,bootstrap_contrasts,acceptance
from controller.pretrain_contracts import seal


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
        result=execute(grant,load,claim)
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
