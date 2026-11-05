import tempfile,unittest,json,sqlite3
from pathlib import Path
from controller.prospective_processor import Ledger
from controller.pretrain_contracts import seal
from controller.warmup_diagnostics import inspect

class WarmupDiagnosticTests(unittest.TestCase):
    def test_reopen_preserves_run_then_rejected_m5_resets_without_erasing_total(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'synthetic.sqlite3';ledger=Ledger(path)
            ledger.emit('SEGMENT',dict(segment='synthetic'))
            for i in range(3):
                evidence='synthetic_'+str(i);bar=dict(time=i*300,evidence_hash=evidence)
                ledger.emit('BAR_COMPARISON',dict(evidence_hash=evidence,bucket=dict(timeframe_seconds=300)))
                ledger.emit('CLOSED_AGGREGATE_BAR',dict(bar=bar,bar_hash=seal(bar)))
            ledger.state.update(own_bars=3,own_run_bars=3);ledger.commit();ledger.close()
            a=inspect(path);b=inspect(path)
            self.assertEqual(a,b);self.assertEqual(a['current_run'],3)
            self.assertEqual(a['scientific_warmup'],0)
            ledger=Ledger(path)
            ledger.emit('INCOMPLETE_BUCKET',dict(observed_bucket=dict(timeframe_seconds=300,open_msc=900000),reasons=['GAP']))
            ledger.state['own_run_bars']=0;ledger.commit();ledger.close()
            c=inspect(path);self.assertEqual(c['current_run'],0);self.assertEqual(c['completed_m5'],3)
            self.assertEqual(c['maximum_observed_run'],3);self.assertEqual(c['rejected_m5'],1)

    def test_self_consistent_counter_tampering_is_rejected_against_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'synthetic.sqlite3';ledger=Ledger(p)
            ledger.state['own_run_bars']=350;ledger.commit();ledger.close()
            with self.assertRaisesRegex(ValueError,'COUNTER_MISMATCH'):inspect(p)

if __name__=='__main__':unittest.main()
