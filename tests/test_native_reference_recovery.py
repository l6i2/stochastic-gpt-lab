import unittest
import numpy as np
from unittest.mock import Mock,patch
from types import SimpleNamespace
from tools.prospective_pipeline import NativeReference


class NativeReferenceRecoveryTests(unittest.TestCase):
    def test_last_milliseconds_kept_but_exact_next_boundary_excluded(self):
        api=self.api();api.TIMEFRAME_M5=5;api.TIMEFRAME_M1=1;api.COPY_TICKS_ALL=0
        api.copy_rates_range=Mock(return_value=np.array([(300,100.,101.,100.,101.,2)],dtype=[('time','i8'),('open','f8'),('high','f8'),('low','f8'),('close','f8'),('tick_volume','i8')]))
        ticks=np.array([(599,599500,100.,101.,2),(599,599999,101.,102.,2),(600,600000,102.,103.,2)],dtype=[('time','i8'),('time_msc','i8'),('bid','f8'),('ask','f8'),('flags','i8')])
        api.copy_ticks_range=Mock(return_value=ticks);ref=NativeReference();ref.mt5=api;ref.step='0.01'
        with patch('tools.prospective_pipeline.host_clock',return_value={}):r=ref(300,300)
        self.assertEqual(r['bid_sequence_reference']['bid_update_count'],2)
        self.assertEqual(r['bid_sequence_reference']['last_reference_native_msc'],599999)
        self.assertEqual(r['excluded_exact_end_boundary_ticks'],1)
        self.assertEqual(api.copy_ticks_range.call_args.args[2].timestamp(),600)
        self.assertEqual(len(ticks),3)
        self.assertTrue(r['not_used_to_fill_missing_raw'])

    def api(self,mode=0,step=.01):
        return SimpleNamespace(initialize=Mock(return_value=True),shutdown=Mock(),
            terminal_info=Mock(return_value=SimpleNamespace(data_path='C:/data/20C285FE08971A9A2E814AAC44AFC9D2')),
            account_info=Mock(return_value=SimpleNamespace(server='XMGlobalSC-MT5 5',trade_mode=mode)),
            symbol_info=Mock(return_value=SimpleNamespace(chart_mode=0,trade_tick_size=step)))

    def process(self,pid):
        return SimpleNamespace(pid=pid,info={'exe':'C:/Program Files/XM Global SC MT5 Terminal/terminal64.exe'})

    def test_terminal_pid_change_rebinds_validated_demo_without_launching(self):
        old=self.api();fresh=self.api();ref=NativeReference();ref.mt5=old;ref.step='0.01';ref.bound_pid=1
        with patch.dict('sys.modules',{'MetaTrader5':fresh}),patch('psutil.process_iter',return_value=[self.process(2)]):
            ref.connect()
        old.shutdown.assert_called_once();fresh.initialize.assert_called_once()
        self.assertEqual(ref.bound_pid,2);self.assertEqual(ref.step,'0.01')

    def test_same_process_does_not_reinitialize_per_bar(self):
        api=self.api();ref=NativeReference();ref.mt5=api;ref.step='0.01';ref.bound_pid=1
        with patch.dict('sys.modules',{'MetaTrader5':api}),patch('psutil.process_iter',return_value=[self.process(1)]):ref.connect()
        api.initialize.assert_not_called();api.shutdown.assert_not_called()

    def test_real_unknown_and_grid_changes_cannot_become_reference(self):
        for mode,step in ((2,.01),(None,.01),(0,.1)):
            api=self.api(mode,step);ref=NativeReference();ref.step='0.01'
            with patch.dict('sys.modules',{'MetaTrader5':api}),patch('psutil.process_iter',return_value=[self.process(2)]):
                with self.assertRaises(ValueError):ref.connect()
            self.assertIsNone(ref.mt5);api.shutdown.assert_called_once()

    def test_missing_api_state_releases_handle_and_does_not_query_bar(self):
        api=self.api();api.account_info.return_value=None;api.copy_rates_range=Mock()
        ref=NativeReference();ref.mt5=api;ref.step='0.01'
        with patch('tools.prospective_pipeline.host_clock',return_value={}):r=ref(300,300)
        self.assertIsNone(r['bar']);self.assertIn('API_UNAVAILABLE',r['error'])
        self.assertIsNone(ref.mt5);api.shutdown.assert_called_once();api.copy_rates_range.assert_not_called()

    def test_absent_or_duplicate_pinned_terminals_do_not_initialize(self):
        for processes in ([],[self.process(1),self.process(2)]):
            api=self.api();ref=NativeReference()
            with patch.dict('sys.modules',{'MetaTrader5':api}),patch('psutil.process_iter',return_value=processes):
                with self.assertRaises(ValueError):ref.connect()
            api.initialize.assert_not_called()
