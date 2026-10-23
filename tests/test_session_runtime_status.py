from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
from session_runtime_status import read_session_runtime


class SessionRuntimeStatusTests(unittest.TestCase):
    def test_read_only_runtime_never_treats_fresh_quotes_as_permission(self):
        now=datetime(2026,10,23,8,tzinfo=timezone.utc)
        for mode,delta,expected in ((4,0,'FRESH_QUOTES_OBSERVED'),(4,60,'NO_FRESH_QUOTES'),(0,0,'SYMBOL_UNAVAILABLE_OR_DISABLED'),(4,-1,'INVALID_TIMESTAMP_UNITS')):
            with self.subTest(mode=mode,delta=delta):
                class Fake:
                    initialize=lambda self,**kw: True
                    shutdown=lambda self: None
                    terminal_info=lambda self: SimpleNamespace(connected=True,data_path=str(ROOT/'work/mock-terminal'))
                    account_info=lambda self: SimpleNamespace(trade_mode=0,server='XMGlobal-MT5 10')
                    symbol_info=lambda self,symbol: SimpleNamespace(trade_mode=mode)
                    symbol_info_tick=lambda self,symbol: SimpleNamespace(time=int(now.timestamp())-max(delta,0),time_msc=int(now.timestamp()*1000)-delta*1000,bid=40000,ask=40001)
                result=read_session_runtime(environment_status=lambda:{'SAFE_FOR_RESEARCH':True,'TERMINAL_PATH':'fixture',
                    'DATA_FOLDER':str(ROOT/'work/mock-terminal')},mt5_module=Fake(),now_utc=now)
                self.assertFalse(result['allowed'])
                self.assertEqual(result['quote_market_state'],expected)
                self.assertEqual(result['orders_sent'],0)
                self.assertEqual(result['clock_reference_status'],'UNVERIFIED')

    def test_unverified_environment_does_not_attach(self):
        class Forbidden:
            def initialize(self,**kw):
                raise AssertionError('must not attach')
        result=read_session_runtime(environment_status=lambda:{'SAFE_FOR_RESEARCH':False},mt5_module=Forbidden())
        self.assertFalse(result['allowed'])
