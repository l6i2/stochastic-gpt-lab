import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from controller.native_diagnostic import configuration,assert_diagnostic,inspect,DATA_NAME,SERVER
from controller.native_reconciliation import bars_from_tape,capture_rates


class NativeDiagnosticTests(unittest.TestCase):
    def test_fixed_technical_period_only(self):
        assert_diagnostic('2024-01-02','2024-01-02')
        for a,b in [('2024-01-01','2024-01-02'),('2025-08-20','2025-08-21'),('2026-03-20','2026-03-21')]:
            with self.assertRaises(ValueError):assert_diagnostic(a,b)

    def test_reproducible_local_no_optimization_no_orders_configuration(self):
        c=configuration('diag_123456abcdef')
        for value in ('Model=4','Optimization=0','UseCloud=0','UseRemote=0','AllowLiveTrading=0','AllowDllImport=0','ShutdownTerminal=1','ToDate=2024.01.03','Expert=NativeDiagnostic\\NativeTesterDiagnosticEA.ex5'):
            self.assertIn(value,c)
        with self.assertRaises(ValueError):configuration('../evil')

    def test_checkpoint_hash_tampering_rejected_before_runtime_read(self):
        import controller.native_diagnostic as module
        with tempfile.TemporaryDirectory() as directory,patch.object(module,'BASE',Path(directory)):
            rid='diag_123456abcdef';f=Path(directory)/'runs'/rid;f.mkdir(parents=True)
            (f/'run_manifest.json').write_text(json.dumps(dict(status='COMPLETE',artifacts={'private.csv':'0'*64})))
            (f/'private.csv').write_text('changed')
            with self.assertRaisesRegex(ValueError,'ARTIFACT_CHANGED'):inspect(rid)

    def test_duplicate_quotes_and_empty_minutes_are_preserved(self):
        rows=np.array([(1000,10.,12.),(1000,10.,13.),(2000,11.,13.),(121000,9.,11.)],dtype=[('time_msc','i8'),('bid','f8'),('ask','f8')])
        bars=bars_from_tape(rows,60)
        self.assertEqual([b['time'] for b in bars],[0,120]);self.assertEqual(bars[0]['observed_quotes'],3)
        self.assertEqual((bars[0]['open'],bars[0]['high'],bars[0]['low'],bars[0]['close']),(10.,11.,10.,11.))

    def test_wrong_range_api_response_rejected_before_csv_write(self):
        rows=np.array([(1748949840,)],dtype=[('time','i8')]);fake=types.SimpleNamespace(
            initialize=lambda **kw:True,shutdown=lambda:None,terminal_info=lambda:types.SimpleNamespace(data_path='C:/'+DATA_NAME),
            account_info=lambda:types.SimpleNamespace(trade_mode=0,server=SERVER),copy_rates_range=lambda *args:rows,TIMEFRAME_M1=1,TIMEFRAME_M5=5)
        with tempfile.TemporaryDirectory() as directory,patch.dict(sys.modules,{'MetaTrader5':fake}):
            with self.assertRaisesRegex(ValueError,'OUT_OF_RANGE'):capture_rates({'TERMINAL_PATH':'not-launched'},Path(directory))
            self.assertEqual(list(Path(directory).iterdir()),[])

    def test_future_training_rejects_diagnostic_namespace_before_io(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
        from train_event_source import assert_train_only_source_path
        with self.assertRaises(ValueError):assert_train_only_source_path(Path('outputs/pc_a_certification/native_tester/data.csv'))

    def test_wrapper_keeps_frozen_source_and_has_no_trading_calls(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/'mt5/NativeTesterDiagnosticEA.mq5').read_text()
        self.assertIn('#include "StochasticBarDecisionResearchEA.mq5"',text)
        self.assertIn('FrozenOnTick();',text)
        for name in ('OrderSend(', 'OrderSendAsync(', 'CTrade ', 'CopyTicks('):self.assertNotIn(name,text)


if __name__=='__main__':unittest.main()
