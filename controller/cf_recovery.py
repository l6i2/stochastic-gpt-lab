"""Read-only recovery of the active C+F SQLite checkpoint and observation ledger."""
import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from .authorized_capture import once, sha
from .exclusive_roles import verify_roles
from .isolated_observation import GENESIS, atomic
from .pretrain_contracts import seal


def classify(event):
    reason = event.get('reason')
    if reason in ('WINDOWS_VERIFIED_SLEEP_EVENT', 'WINDOWS_SLEEP_DURING_QUERY'):
        return 'SLEEP'
    if reason == 'XM_DISCONNECTED':
        return 'XM_DISCONNECT'
    if event.get('kind') == 'CF_VERIFIED_SESSION_TRANSITION' and event.get('review', {}).get('bridge_allowed') is True:
        return 'MARKET_CLOSED'
    return 'UNKNOWN_INTERRUPTION'


def classify_boot(events):
    # Event 41 means an unclean restart. It does not identify the power source.
    if any(e['provider'] == 'Microsoft-Windows-Kernel-Power' and e['id'] == 41 for e in events):
        return 'UNKNOWN_INTERRUPTION'
    boots = [index for index,e in enumerate(events) if e['provider'] == 'Microsoft-Windows-Kernel-General' and e['id'] == 12]
    if len(boots) != 1:
        return 'UNKNOWN_INTERRUPTION'
    shutdowns = [index for index,e in enumerate(events[:boots[0]]) if e['provider'] == 'Microsoft-Windows-Kernel-General' and e['id'] == 13]
    if len(shutdowns) != 1:
        return 'UNKNOWN_INTERRUPTION'
    intents = [e.get('intent', '').lower() for e in events[:shutdowns[0]] if e['provider'] == 'User32' and e['id'] == 1074]
    if not intents:
        return 'UNKNOWN_INTERRUPTION'
    if intents[-1] in ('restart', 'reiniciar', 'reinicio'):
        return 'WINDOWS_RESTART'
    if intents[-1] in ('power off', 'shutdown', 'apagar', 'apagado'):
        return 'NORMAL_SHUTDOWN'
    return 'UNKNOWN_INTERRUPTION'


def snapshot(db_path, previous=None):
    """Check the saved prefix and committed suffix in one SQLite read transaction."""
    old = previous or {}
    n = old.get('records', 0)
    head = old.get('chain_head', GENESIS)
    observation = old.get('last_observation')
    pending = old.get('pending_interruption')
    events = []
    verified_m5 = old.get('TOTAL_VERIFIED_M5', 0)
    covered = dict(old.get('last_covered_intervals', {}))
    with closing(sqlite3.connect(Path(db_path).resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.execute('BEGIN')
        if n and db.execute('SELECT digest FROM records WHERE n=?', (n-1,)).fetchone() != (head,):
            raise ValueError('CF_RECOVERY_PREFIX_CHANGED')
        if n and 'last_covered_intervals' not in old:
            n, head, verified_m5 = 0, GENESIS, 0
            observation = pending = None
        for index, prior, digest, body in db.execute('SELECT n,previous,digest,body FROM records WHERE n>=? ORDER BY n', (n,)):
            row = json.loads(body)
            if index != n or prior != head or seal(dict(previous=prior, payload=row)) != digest:
                raise ValueError('CF_RECOVERY_CHAIN_CHANGED')
            if row.get('quarantine') is not True or row.get('admitted') is not False:
                raise ValueError('CF_RECOVERY_SCOPE_CHANGED')
            kind = row['kind']
            if kind == 'CF_M1_M5_PARITY' and row.get('matched') is True:
                verified_m5 += 1
            if kind == 'DATABASE_SNAPSHOT_PAIR' and row['assessment']['status'] == 'VERIFIED_DATABASE_VIEW_ONLY':
                covered[str(row['frame_seconds'])] = dict(start_native_msc=row['start_native_msc'],
                    end_native_exclusive_msc=row['end_native_exclusive_msc'], record=index, record_hash=digest)
            if kind in ('NEW_OBSERVATION_EPOCH', 'OBSERVATION_INTERRUPTION', 'CF_VERIFIED_SESSION_TRANSITION'):
                if kind != 'OBSERVATION_INTERRUPTION' or pending is None:
                    event = dict(record=index, record_hash=digest, kind=kind, reason=row.get('reason'),
                                 classification=classify(row), previous_observation=observation,
                                 clock=row.get('activation_clock', row.get('clock')),
                                 epoch=row.get('epoch'), backfill=False)
                    events.append(event)
                    pending = event if kind == 'OBSERVATION_INTERRUPTION' else None
            if kind == 'LIVE_LATEST_STATE_POLL':
                observation = dict(clock=row['read_end'], native_msc=row['native_quote']['time_msc'], record=index)
            n += 1
            head = digest
        saved = db.execute('SELECT body,digest FROM state WHERE id=1').fetchone()
        last = db.execute('SELECT previous,digest,body FROM records WHERE n=?', (n-1,)).fetchone()
        if not saved or not last:
            raise ValueError('CF_RECOVERY_CHECKPOINT_MISSING')
        state = json.loads(saved[0])
        checkpoint = json.loads(last[2])
        if (last[1] != head or seal(dict(previous=last[0], payload=checkpoint)) != head
                or seal(state) != saved[1] or checkpoint.get('kind') != 'CHECKPOINT'
                or checkpoint.get('state_hash') != saved[1]):
            raise ValueError('CF_RECOVERY_CHECKPOINT_UNBOUND')
    context = state.get('cf_features', {})
    current = dict(records=n, chain_head=head, checkpoint_hash=saved[1], epoch=state['epoch'],
                   last_observation=observation, pending_interruption=pending,
                   last_covered_intervals=covered,
                   last_verified_native_open_msc=state['last_verified'], next_open=state['next_open'],
                   accepted=state['accepted'], rejected=state['rejected'],
                   TOTAL_VERIFIED_M5=verified_m5, CURRENT_CONSECUTIVE_M5=context.get('own_run_bars',0),
                   SCIENTIFICALLY_ELIGIBLE_M5=0, seed_state=dict(atr=context.get('atr'), ha=context.get('ha')),
                   maturity=dict(signals=context.get('after_warmup_signals',0), post_bars=context.get('post_signal_bars',0)))
    return current, events


def recover(root, clock, windows_events):
    base = root/'outputs/us30cash_m5_native_observations'
    pointer = json.loads((base/'current.json').read_text())
    name = pointer['capture_id']
    if Path(name).name != name or not name.startswith('dbsnap_'):
        raise ValueError('CF_RECOVERY_INVALID_CAPTURE')
    folder = base/name
    manifest_path = folder/'manifest.json'
    if sha(manifest_path) != pointer['manifest_sha256']:
        raise ValueError('CF_RECOVERY_MANIFEST_CHANGED')
    manifest = json.loads(manifest_path.read_text())
    if not verify_roles(root, manifest):
        raise ValueError('CF_RECOVERY_EXCLUSIVE_ROLE_REQUIRED')
    package = root/'research/studies/us30cash_m5_native_observations'
    if sha(package/'contract.json') != manifest['contract_sha256'] or sha(root/manifest['authorization_path']) != manifest['authorization_sha256']:
        raise ValueError('CF_RECOVERY_CONTRACT_OR_AUTHORITY_CHANGED')
    pin_ref = json.loads((folder/'runtime_pin_current.json').read_text())
    if Path(pin_ref['file']).name != pin_ref['file']:
        raise ValueError('CF_RECOVERY_PIN_PATH_CHANGED')
    pin_path = folder/'source_versions'/pin_ref['file']
    pin = json.loads(pin_path.read_text())
    if sha(pin_path) != pin_ref['sha256'] or pin['origin_manifest_sha256'] != pointer['manifest_sha256'] or any(sha(root/p) != h for p,h in pin['source_hashes'].items()):
        raise ValueError('CF_RECOVERY_SOURCE_PIN_CHANGED')
    receipts = base/'recovery'
    receipts.mkdir(exist_ok=True)
    latest = receipts/'latest.json'
    previous = None
    if latest.exists():
        saved = json.loads(latest.read_text())
        previous = saved['receipt']
        if seal(previous) != saved['sha256'] or previous['capture_id'] != name or previous['manifest_sha256'] != pointer['manifest_sha256']:
            raise ValueError('CF_RECOVERY_SAVED_RECEIPT_CHANGED')
    current, events = snapshot(folder/'snapshots.sqlite3', previous)
    current.update(capture_id=name, manifest_sha256=pointer['manifest_sha256'], role_assignment=manifest['exclusive_role_assignment'],
                   source_pin_sha256=pin_ref['sha256'], clock=clock, calendar='PARTIAL_NO_CERTIFIED_TRANSITION',
                   dataset_admission='WAITING_FOR_EVIDENCE', physical_power_cycle_proven=False,
                   backfill=False, training_executed=False, live_trading=False)
    for event in events:
        earlier = event['previous_observation']
        later = event['clock']
        if earlier and later:
            old_clock = earlier['clock']
            same_boot = old_clock['boot_id'] == later['boot_id']
            if same_boot:
                event['observation_gap_ns'] = max(0, later['monotonic_ns']-old_clock['monotonic_ns'])
            else:
                event['boot_transition_observed'] = True
                os_evidence = windows_events(old_clock['host_utc_label'], later['host_utc_label'])
                event['windows_evidence'] = os_evidence
                event['classification'] = classify_boot(os_evidence)
                event['host_wall_gap_seconds'] = (datetime.fromisoformat(later['host_utc_label'])-datetime.fromisoformat(old_clock['host_utc_label'])).total_seconds()
        target = receipts/('event_'+str(event['record'])+'_'+event['record_hash']+'.json')
        if not target.exists():
            once(target, event)
    current['latest_transition'] = events[-1] if events else previous.get('latest_transition') if previous else None
    current['last_boot_transition'] = next((event for event in reversed(events) if event.get('boot_transition_observed')),
                                           previous.get('last_boot_transition') if previous else None)
    atomic(latest, dict(receipt=current, sha256=seal(current)))
    return current
