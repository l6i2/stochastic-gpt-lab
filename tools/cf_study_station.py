"""Activate and supervise the separately authorized C+F quarantine producer."""
import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from controller.authorized_capture import sha, once, manager_lock, fresh_nts, bracket
from controller.isolated_observation import host_clock, atomic
from controller.pretrain_contracts import seal
from controller.cf_study import process_events, admission, bridge_allowed
from controller.native_database_snapshots import Store
from controller.exclusive_roles import verify_roles
from controller.cf_session_calendar import transition_review
from tools import native_database_snapshots as native

BASE = ROOT / 'outputs/us30cash_m5_native_observations'
PACKAGE = ROOT / 'research/studies/us30cash_m5_native_observations'
STUDY = 'US30CASH_M5_NATIVE_OBSERVATIONS_20261105_01'


class StudyStore(Store):
    def commit(self, events):
        original = self.state
        minimum = original.get('cf_exclusive_minimum_native_open_msc')
        if minimum is not None and any(e.get('kind') == 'DATABASE_SNAPSHOT_PAIR' and e['start_native_msc'] < (original['cf_exclusive_minimum_m1_open_msc'] if e['frame_seconds']==60 else minimum) for e in events):
            raise ValueError('PRE_CUTOFF_INTERVAL_REFUSED')
        working = copy.deepcopy(original)
        # Persist the sleep evidence actually checked by the native poll, without
        # changing the approved native producer or claiming an OnTick receipt.
        events = [dict(e,connected=True,sleep_record_id=working.get('last_sleep_record_id'))
                  if e['kind']=='LIVE_LATEST_STATE_POLL' else e for e in events]
        pending = working.pop('cf_pending_bridges', [])
        extras = process_events(working, events)
        self.state = working
        try:
            super().commit(events + pending + extras)
        except BaseException:
            self.state = original
            raise


class Producer(native.Producer):
    def __init__(self):
        index = json.loads((PACKAGE/'contract_sources.json').read_text())
        for name, digest in index['files'].items():
            if Path(name).name != name or sha(PACKAGE/name) != digest:
                raise ValueError('CF_APPROVED_CONTRACT_SOURCE_CHANGED')
        super().__init__()
        if self.manifest['contract_sha256'] != sha(PACKAGE/'contract.json'):
            self.close()
            raise ValueError('CF_MANIFEST_CONTRACT_CHANGED')
        self.roles = verify_roles(ROOT, self.manifest)
        if self.roles:
            self.store.state['cf_exclusive_minimum_native_open_msc'] = self.roles['minimum_native_open_msc']
            self.store.state['cf_exclusive_minimum_m1_open_msc'] = self.roles['minimum_m1_open_msc']
            self.store.commit([dict(kind='EXCLUSIVE_ROLE_BOUND',assignment=self.manifest['exclusive_role_assignment'],
                                   minimum_native_open_msc=self.roles['minimum_native_open_msc'],
                                   precut_data_adopted=False,training_authorized=False)])

    def identity(self):
        terminal = super().identity()
        if terminal.trade_allowed:
            raise RuntimeError('CF_TERMINAL_TRADING_MUST_REMAIN_DISABLED')
        return terminal

    def report(self, status, error=None):
        super().report(status, error)
        state = self.store.state
        context = state.get('cf_features', {})
        contract = json.loads((PACKAGE/'contract.json').read_text())
        contract_matches = sha(PACKAGE/'contract.json') == self.manifest['contract_sha256']
        seeds_bound = (context.get('own_run_bars', 0) >= 350
                       and (context.get('ha') or {}).get('count', 0) == context.get('own_run_bars')
                       and (context.get('atr') or {}).get('count', 0) == context.get('own_run_bars'))
        facts = dict(contract_approved=contract_matches, contract_changed=not contract_matches,
                     independence=bool(self.roles), nonoverlap=bool(self.roles), calendar=False,
                     coverage=status == 'ACTIVE_QUARANTINED' and context.get('own_run_bars', 0) > 0,
                     causality=bool(state.get('cf_offline_use_verified') and state.get('cf_full_feature_values') and seeds_bound),
                     seeds=seeds_bound,
                     warmup=context.get('own_run_bars', 0), signals=context.get('after_warmup_signals', 0),
                     post_bars=context.get('post_signal_bars', 0))
        value = dict(study_id=STUDY, contract_id=contract['contract_id'],
                     producer_id=self.manifest['producer_id'], dataset_id=self.manifest['dataset_id'],
                     capture_id=self.folder.name, status=status, error=error, process_id=os.getpid(),
                     clock=host_clock(), real_m1=state['accepted']['60'], real_m5=state['accepted']['300'],
                     consecutive_m5=facts['warmup'], numerically_adjacent_m5=state['consecutive_m5'], technical_warmup=facts['warmup'],
                     scientific_warmup=0, BUY=context.get('signals_buy', 0), SELL=context.get('signals_sell', 0),
                     consecutive_signals=facts['signals'], post_bars=facts['post_bars'], evaluable=0,
                     source_rows=state['source_records'], ledger_records=self.store.count, chain_head=self.store.head,
                     implementation_pin_sha256=self.active_pin,
                     epoch=state['epoch'], epochs=state['epochs'], membership='OWN_ID_AND_NATIVE_INTERVALS_QUARANTINED',
                     independence='VERIFIED_FORWARD_SCOPE_BY_EXPLICIT_DECISION' if self.roles else 'WAITING_RESERVATION_SCOPE_DECISION', calendar='PARTIAL_NO_CERTIFIED_TRANSITION',
                     exclusive_role_assignment=self.manifest.get('exclusive_role_assignment'),
                     exclusive_cutoff=self.manifest.get('role_cutoff'),
                     causality='NATIVE_PREFIX_AND_OFFLINE_USE_RECORDED_FULL_SEEDS_PENDING', dataset_hash=None,
                     activation=self.manifest['activation'], first_observation=state.get('cf_first_observation'),
                     facts=facts, **admission(facts), DEMO='DISABLED', LIVE_TRADING=False, PROTECTED_SCORING=False)
        atomic(BASE/'status.json', value)


def activate():
    BASE.mkdir(parents=True, exist_ok=True)
    with manager_lock(BASE):
        if (BASE/'current.json').exists():
            return json.loads((BASE/'current.json').read_text())
        from tools.prospective_pipeline import NativeReference
        ref = NativeReference()
        try:
            ref.connect()
            if ref.mt5.terminal_info().trade_allowed:
                raise RuntimeError('CF_TRADING_NOT_DISABLED')
        finally:
            ref.close()
        authorization = PACKAGE/'authorization.json'
        contract = PACKAGE/'contract.json'
        approved = json.loads(contract.read_text())
        if approved['authority_sha256'] != sha(authorization):
            raise ValueError('CF_APPROVAL_RECEIPT_CHANGED')
        before = fresh_nts()
        cut = host_clock()
        after = fresh_nts()
        activation = bracket(before, after, cut)
        capture = 'dbsnap_' + uuid.uuid4().hex
        folder = BASE/capture
        folder.mkdir()
        once(folder/'activation_clock_evidence.json', dict(before=before, cut=cut, after=after, utc=activation))
        old = ROOT/'outputs/six_alternatives_experiment'
        pointer = json.loads((old/'current.json').read_text())
        original = json.loads((old/pointer['capture_id']/'manifest.json').read_text())
        sources = set(original['source_hashes']) | {'controller/cf_study.py','tools/cf_study_station.py'}
        manifest = dict(original, capture_id=capture, study_id=STUDY,
                        producer_id='cfprod_'+uuid.uuid4().hex, dataset_id=STUDY.lower()+'_dataset_01',
                        authorization_path=authorization.relative_to(ROOT).as_posix(),
                        authorization_sha256=sha(authorization), contract_sha256=sha(contract),
                        source_hashes={p:sha(ROOT/p) for p in sorted(sources)}, intent_clock=cut,
                        activation=activation, source='AUTHORIZED_C_F_NATIVE_DATABASE_OBSERVATIONS',
                        approved_calendar_receipts=[], maximum_trial_seconds=None,
                        previous_capture_membership_adopted=False, membership_role='QUARANTINED_EXCLUSIVE_ROLE_PENDING_NONOVERLAP')
        once(folder/'manifest.json', manifest)
        once(BASE/'current.json', dict(capture_id=capture, manifest_sha256=sha(folder/'manifest.json')))
        once(BASE/'role_ledger.json', dict(study_id=STUDY, capture_id=capture, activation=activation,
             role='NEW_STUDY_QUARANTINE_RESERVATION', exclusive_scientific_roles_verified=False,
             prior_reservations_modified=False, legacy_nonoverlap_verified=False, evidence=sha(contract)))
        atomic(BASE/'enabled.json', dict(enabled=True))
        return json.loads((BASE/'current.json').read_text())


def serve():
    native.BASE = BASE
    native.Store = StudyStore
    previous_boundary = native.boundary_reason
    producer = None
    def boundary(state, tick, clock, terminal_changed=False):
        reason = previous_boundary(state, tick, clock, terminal_changed=terminal_changed)
        # Calendar proofs must be hash-bound in this production manifest. No
        # current holiday/transition receipt is certified, so the list starts empty.
        for item in producer.manifest['approved_calendar_receipts']:
            path = (ROOT/item['path']).resolve()
            if not path.is_relative_to(ROOT) or sha(path) != item['sha256']:
                raise ValueError('CF_CALENDAR_RECEIPT_CHANGED')
            proof = json.loads(path.read_text())
            old = state.get('last_poll') or {}
            health = dict(same_boot=old.get('boot_id') == clock['boot_id'],
                          monotonic=old.get('monotonic_ns', 0) <= clock['monotonic_ns'],
                          connected=True, no_sleep=producer.store.state.get('last_sleep_record_id') == native.last_sleep_record_id(),
                          poll_gap_ms=clock['uptime_ms']-old.get('uptime_ms', 0))
            request=dict(proof,boundary_reason=reason,last_native_msc=state.get('last_tick'),
                         current_native_msc=tick['time_msc'],next_m5_open_msc=state['next_open'].get('300'),
                         expected_source_pin_sha256=producer.active_pin)
            reviewed=transition_review(request)
            if reviewed['bridge_allowed'] and all(health[k] for k in ('same_boot','monotonic','connected','no_sleep')) and health['poll_gap_ms']<=10000:
                start, end = proof['from_native_msc'], proof['to_native_msc']
                reason = None
                producer.store.state.setdefault('cf_pending_bridges', []).append(dict(kind='CF_VERIFIED_SESSION_TRANSITION', proof_sha256=item['sha256'], start=start, end=end,review=reviewed))
                for frame, opening in producer.store.state['next_open'].items():
                    if start <= opening < end:
                        producer.store.state['next_open'][frame] = end
        return reason
    native.boundary_reason = boundary
    producer = Producer()
    try:
        while json.loads((BASE/'enabled.json').read_text())['enabled']:
            producer.poll()
            if producer.store.state.get('cf_acquisition_complete'):
                atomic(BASE/'enabled.json', dict(enabled=False, reason='FROZEN_ACQUISITION_BOUNDARY_REACHED'))
                break
            time.sleep(2)
    finally:
        producer.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    parser.add_argument('--serve', action='store_true')
    args = parser.parse_args()
    if args.activate:
        print(json.dumps(activate()))
    elif args.serve:
        serve()
