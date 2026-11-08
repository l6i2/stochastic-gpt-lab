import copy
import csv
import hashlib
import json
from pathlib import Path
import unittest

from controller.cf_atr_candidate import advance, initial_state, restore
from controller.pretrain_contracts import seal

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT/'research/studies/us30cash_m5_native_observations/weekend_20261107'


class AtrCandidateTests(unittest.TestCase):
    def rows(self):
        receipt = json.loads((FIXTURE/'synthetic_receipt.json').read_bytes())
        path = FIXTURE/'cfweek_382ad54e_oracle.csv'
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),receipt['export_sha256'])
        with path.open(encoding='utf-8-sig') as stream:
            return list(csv.DictReader(stream))

    def test_every_native_value_and_checkpoint_boundary_is_exact(self):
        rows = self.rows()
        state = initial_state()
        compared = 0
        for i,row in enumerate(rows):
            bar = {key:float(row[key]) for key in ('open','high','low','close')}
            bar['time'] = int(row['time'])
            saved = copy.deepcopy(state)
            value = advance(state,bar,str(i),(bar['time']+300)*1000)
            self.assertEqual(saved,state)
            snapshot = json.loads(json.dumps(dict(state=state,state_sha256=seal(state))))
            restarted = advance(restore(snapshot),bar,str(i),(bar['time']+300)*1000)
            self.assertEqual(value,restarted)
            state = value
            if i >= 13:
                compared += 1
                self.assertEqual(state['value'],float(row['atr']),str(i))
        self.assertEqual(compared,287)
        self.assertEqual(state['seed_bar_hash'],'0')

    def test_future_open_duplicate_and_changed_checkpoint_are_rejected(self):
        bar = dict(time=300,open=2.,high=3.,low=1.,close=2.)
        empty = initial_state()
        with self.assertRaisesRegex(ValueError,'NOT_AVAILABLE'):
            advance(empty,bar,'first',599999)
        self.assertEqual(empty,initial_state())
        state = advance(empty,bar,'first',600000)
        with self.assertRaisesRegex(ValueError,'DUPLICATE_OR_OUT_OF_ORDER'):
            advance(state,bar,'first',600000)
        checkpoint = dict(state=state,state_sha256=seal(state))
        checkpoint['state']['previous_close'] = 999.
        with self.assertRaisesRegex(ValueError,'CHECKPOINT_CHANGED'):
            restore(checkpoint)

    def test_future_mutation_preserves_all_earlier_values(self):
        def run(mutate):
            state = initial_state()
            prefix = []
            for i in range(60):
                high = 1e8 if mutate and i >= 30 else 10.+i%7
                bar = dict(time=300*(i+1),open=5.,high=high,low=1.,close=6.)
                state = advance(state,bar,str(i),(bar['time']+300)*1000)
                if i < 30:
                    prefix.append(state)
            return prefix
        self.assertEqual(run(False),run(True))
