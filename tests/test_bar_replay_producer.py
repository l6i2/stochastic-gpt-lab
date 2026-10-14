import tempfile
import unittest
from pathlib import Path

from python.build_bar_replay_producer import ROOT, build, build_probe
from tests.test_intratrade_instrumentation import function_source


class ProducerTests(unittest.TestCase):
    def test_derivation_preserves_baseline_execution_functions(self):
        source = ROOT/'mt5/StochasticIntratradeResearchEA.mq5'
        baseline = source.read_text(encoding='utf-8-sig')
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp)/'ReplayEA.mq5'
            result = build(source, destination)
            derived = destination.read_text()
            for name in ('TickTrade', 'BarTrade', 'Capture', 'Excursion'):
                self.assertEqual(function_source(baseline, name), function_source(derived, name))
            self.assertIn('snapshot_done[100]', derived)
            self.assertIn('j<100;', derived)
            self.assertIn('replay_fill_quote.time_msc<=cutoff', derived)
            self.assertNotIn('execution_time_msc', function_source(derived, 'SnapField'))
            self.assertEqual(result['status'], 'PREPARED_NOT_DEPLOYED')
            with self.assertRaises(FileExistsError):
                build(source, destination)
            probe = Path(tmp)/'BarReplayProbe.mq5'
            build_probe(probe)
            fixture = probe.read_text()
            self.assertIn('execution_rows=0;', fixture)
            self.assertIn('FileClose(execution_out)', fixture)
            self.assertIn('#include "StochasticBarDecisionResearchEA.mq5"', fixture)

    def test_unknown_base_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'unknown.mq5'
            source.write_text('changed producer')
            with self.assertRaisesRegex(ValueError, 'hash differs'):
                build(source, Path(tmp)/'out.mq5')
