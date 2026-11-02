"""Read-only streaming verification; exports metadata, never raw snapshot rows."""
import argparse,json,sqlite3,sys
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from controller.pretrain_contracts import seal
from controller.isolated_observation import GENESIS
from controller.native_database_snapshots import assess
from controller.authorized_capture import sha


def audit(out):
    out=Path(out).resolve()
    if out.exists():raise ValueError('NO_OVERWRITE')
    if not (out.is_relative_to(ROOT/'outputs') or out.is_relative_to(ROOT/'research/studies')):raise ValueError('OUTPUT_NAMESPACE_REFUSED')
    base=ROOT/'outputs/native_database_snapshots_v1';pointer=json.loads((base/'current.json').read_text());folder=base/pointer['capture_id']
    if sha(folder/'manifest.json')!=pointer['manifest_sha256']:raise ValueError('ORIGIN_MANIFEST_CHANGED')
    db=sqlite3.connect((folder/'snapshots.sqlite3').resolve().as_uri()+'?mode=ro',uri=True);db.execute('BEGIN')
    state_body,state_hash=db.execute('SELECT body,digest FROM state WHERE id=1').fetchone();state=json.loads(state_body)
    if seal(state)!=state_hash:raise ValueError('CHECKPOINT_CHANGED')
    head=GENESIS;n=0;pending={};counts=Counter();accepted=Counter();rejected=Counter();pairs=[];epochs=[];orphaned=0;legacy=0;current_run=0;maximum=0;last_m5=None;last=None
    for index,previous,digest,body in db.execute('SELECT * FROM records ORDER BY n'):
        row=json.loads(body)
        if index!=n or previous!=head or seal(dict(previous=previous,payload=row))!=digest:raise ValueError('CHAIN_CHANGED')
        if row.get('admitted') is not False or row.get('quarantine') is not True:raise ValueError('ADMISSION_SCOPE_CHANGED')
        head=digest;n+=1;last=row;kind=row['kind'];counts[kind]+=1
        if kind in ('NEW_OBSERVATION_EPOCH','OBSERVATION_INTERRUPTION'):
            orphaned+=sum(len(v) for v in pending.values());pending={};current_run=0;last_m5=None
            epochs.append(dict(n=index,kind=kind,reason=row['reason'],epoch=row.get('epoch'),clock=row.get('activation_clock',row.get('clock')),first_complete_open=row.get('first_complete_open')))
        if kind=='DATABASE_QUERY_OBSERVATION':
            o=row['observation'];key=(row['epoch'],row['frame_seconds'],o['start_native_msc'],o['end_native_exclusive_msc']);pending.setdefault(key,[]).append(row)
        if kind=='DATABASE_SNAPSHOT_PAIR':
            key=(row['epoch'],row['frame_seconds'],row['start_native_msc'],row['end_native_exclusive_msc']);reads=pending.pop(key,[])
            if len(reads)!=2:raise ValueError('MISSING_QUERY_OBSERVATIONS')
            one,two=[r['observation'] for r in reads]
            if one['origin']!='TERMINAL_DATABASE_QUERY' or two['origin']!='TERMINAL_DATABASE_QUERY':raise ValueError('FALSE_ORIGIN')
            if one['read_start']['boot_id']!=two['read_end']['boot_id'] or one['read_end']['monotonic_ns']>two['read_start']['monotonic_ns']:raise ValueError('QUERY_ORDER_OR_BOOT_CHANGED')
            result=row['assessment'];strict=one.get('tick_size') is not None
            if strict:
                if one['tick_size']!=two['tick_size']:raise ValueError('GRID_CHANGED')
                computed=assess(reads[0]['rows'],reads[1]['rows'],row['native_bar'],key[2],key[3],one['tick_size'],one['query_error'] or two['query_error'] or ('ERROR' if 'QUERY_ERROR_OR_PARTIAL_READ' in result['reasons'] else None))
                if computed!=result:raise ValueError('ASSESSMENT_NOT_REPRODUCIBLE')
            else:legacy+=1
            if seal(reads[0]['rows'])!=result['first_sha256'] or seal(reads[1]['rows'])!=result['second_sha256']:raise ValueError('SNAPSHOT_BYTES_CHANGED')
            frame=str(row['frame_seconds']);ok=result['status']=='VERIFIED_DATABASE_VIEW_ONLY';(accepted if ok else rejected)[frame]+=1
            if frame=='300':
                current_run=(current_run+1 if last_m5 is not None and key[2]==last_m5+300000 else 1) if ok else 0
                last_m5=key[2] if ok else None;maximum=max(maximum,current_run)
            pairs.append(dict(n=index,epoch=key[0],frame_seconds=key[1],start_native_msc=key[2],end_native_exclusive_msc=key[3],rows=result['rows'],bid_updates=result['bid_updates'],status=result['status'],reasons=result['reasons'],strict_recomputed=strict,first_sha256=result['first_sha256'],second_sha256=result['second_sha256'],first_observation=one,verification_observation=two,native_bar=row['native_bar']))
    if not last or last['kind']!='CHECKPOINT' or last['state_hash']!=state_hash:raise ValueError('UNBOUND_CHECKPOINT')
    db.close()
    for frame in ('60','300'):
        if accepted[frame]!=state['accepted'][frame] or rejected[frame]!=state['rejected'][frame]:raise ValueError('COUNTER_MISMATCH')
    if current_run!=state['consecutive_m5'] or maximum!=state['max_consecutive_m5']:raise ValueError('CONTINUITY_COUNTER_MISMATCH')
    out.mkdir(parents=True)
    def write(name,value):(out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf8',newline='\n')
    summary=dict(capture_id=folder.name,snapshot_ecuador=datetime.now(timezone.utc).astimezone(ZoneInfo('America/Guayaquil')).isoformat(),origin_manifest_sha256=sha(folder/'manifest.json'),verified_records=n,chain_head=head,accepted=dict(accepted),rejected=dict(rejected),consecutive_m5_database_view=current_run,maximum_consecutive_m5_database_view=maximum,epochs=epochs,legacy_pairs_without_explicit_grid=legacy,unpaired_query_observations=orphaned+sum(len(v) for v in pending.values()),scientific_warmup=0,dataset_admitted=False,callback_receipt_proven=False,event_generation_utc_proven=False,training_executed=False,scoring_executed=False,raw_rows_exported=0,record_counts=dict(counts))
    write('summary.json',summary);write('pairs.json',pairs);write('checkpoint_receipt.json',dict(state_hash=state_hash,state=state,chain_head=head,verified_records=n))
    write('audit_complete.json',dict(chain_head=head,verified_records=n,source_sha256=sha(Path(__file__)),files={name:sha(out/name) for name in ('summary.json','pairs.json','checkpoint_receipt.json')}))
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);a=p.parse_args();print(json.dumps(audit(a.out),indent=2))
