"""Read-only recovery receipt for the active B+C reservation; old C+F stays closed."""
import json,sqlite3
from contextlib import closing
from pathlib import Path
from .authorized_capture import sha,once
from .isolated_observation import GENESIS,atomic
from .pretrain_contracts import seal


def recover(root,clock,windows_events):
    root=Path(root);base=root/'outputs/bc_train_future_eval_v1';package=root/'research/studies/bc_train_future_eval_v1'
    activation=json.loads((package/'activation.json').read_bytes());pointer=json.loads((base/'current.json').read_bytes())
    if sha(package/'activation.json')!=pointer['manifest_sha256']:raise ValueError('BC_RECOVERY_ACTIVATION_CHANGED')
    for file,digest in activation['source_hashes'].items():
        if sha(root/file)!=digest:raise ValueError('BC_RECOVERY_PRODUCER_SOURCE_CHANGED')
    if sha(package/'authorization.json')!=activation['authorization_sha256'] or sha(package/'contract.json')!=activation['contract_sha256']:
        raise ValueError('BC_RECOVERY_AUTHORITY_OR_CONTRACT_CHANGED')
    old=root/'outputs/us30cash_m5_native_observations'
    if json.loads((old/'enabled.json').read_bytes()).get('enabled') is not False:raise ValueError('OLD_CF_INGRESS_REOPENED')
    saved=json.loads((package/'cf_preservation_verification.json').read_bytes())
    for file,digest in activation['old_immutable_hashes'].items():
        if sha(root/file)!=digest:raise ValueError('OLD_CF_IMMUTABLE_MANIFEST_CHANGED')
    old_pointer=json.loads((old/'current.json').read_bytes())
    with closing(sqlite3.connect((old/old_pointer['capture_id']/'snapshots.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)) as db:
        tail=db.execute('SELECT n,digest FROM records ORDER BY n DESC LIMIT 1').fetchone()
        if tail!=(saved['old_records']-1,saved['old_chain_head']):raise ValueError('OLD_CF_CLOSED_HEAD_CHANGED')
    head=GENESIS;count=0
    with closing(sqlite3.connect((base/'ledger.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)) as db:
        db.execute('BEGIN')
        for n,parent,digest,body in db.execute('SELECT n,previous,digest,body FROM artifacts ORDER BY n'):
            if n!=count or parent!=head or seal(dict(previous=parent,payload=json.loads(body)))!=digest:
                raise ValueError('BC_RECOVERY_CHAIN_CHANGED')
            count+=1;head=digest
        checkpoint=db.execute('SELECT body,digest FROM checkpoint WHERE id=1').fetchone()
        state=json.loads(checkpoint[0])
        if seal(state)!=checkpoint[1] or json.loads(body).get('state_hash')!=checkpoint[1]:raise ValueError('BC_RECOVERY_STATE_CHANGED')
    folder=base/'recovery';folder.mkdir(exist_ok=True);last=folder/'latest.json'
    previous=json.loads(last.read_bytes()) if last.exists() else None
    changed=bool(previous and previous['clock']['boot_id']!=clock['boot_id'])
    result=dict(status='PASS_BC_CHECKPOINT_INTEGRITY_ONLY',clock=clock,dataset_id=activation['dataset_id'],
        chain_head=head,records=count,checkpoint_hash=checkpoint[1],native_floor=state['bc']['floor'],
        next_interval=state['bc']['cursor'],old_cf_preserved=True,old_cf_ingress_closed=True,
        boot_transition_observed=changed,physical_power_cycle_proven=False,
        native_resume_proven=False,training_executed=False,live_trading=False)
    if changed:
        logs=windows_events(previous['clock']['host_utc_label'],clock['host_utc_label'])
        once(folder/('boot_'+previous['clock']['boot_id']+'_'+clock['boot_id']+'.json'),
            dict(previous=previous,current=result,windows_events=logs,coverage_not_inferred_from_reboot=True))
    atomic(last,result);return result
