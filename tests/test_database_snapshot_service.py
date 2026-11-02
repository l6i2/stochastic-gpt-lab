import copy,unittest,tempfile
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
from controller.native_database_snapshots import new_state,start_epoch
from tools.native_database_snapshots import Producer


def clock(n=100):return dict(boot_id='b',uptime_ms=n,monotonic_ns=n*1000000,host_utc_label='2026-11-02T00:00:00+00:00',utc_certified=False)


class Service(unittest.TestCase):
    def test_accounted_slow_api_read_is_not_an_idle_poll_gap(self):
        with tempfile.TemporaryDirectory() as t:
            p=self.producer();s=new_state();start_epoch(s,dict(time_msc=360001),clock(),'start');s['last_tick']=479999
            s['last_completed_poll']=clock(100);s['next_open']={'60':600000,'300':600000};s['last_sleep_record_id']=7
            p.folder=Path(t);p.store=NS(state=s,commit=Mock());p.report=Mock();p.connect=Mock()
            epoch=s['epoch']
            with patch('tools.native_database_snapshots.host_clock',side_effect=[clock(101),clock(101),clock(12000),clock(12001),clock(12002)]),patch('tools.native_database_snapshots.last_sleep_record_id',return_value=7):p.poll()
            self.assertEqual(s['epoch'],epoch);self.assertEqual(s['last_completed_poll']['uptime_ms'],12001)

    def test_positive_windows_sleep_event_creates_new_cut(self):
        with tempfile.TemporaryDirectory() as t:
            p=self.producer();s=new_state();start_epoch(s,dict(time_msc=360001),clock(),'start');s['last_tick']=479999;s['last_sleep_record_id']=7
            p.folder=Path(t);p.store=NS(state=s,commit=Mock());p.report=Mock();p.connect=Mock()
            with patch('tools.native_database_snapshots.host_clock',return_value=clock(101)),patch('tools.native_database_snapshots.last_sleep_record_id',return_value=8):p.poll()
            records=p.store.commit.call_args.args[0]
            self.assertTrue(any(r['kind']=='NEW_OBSERVATION_EPOCH' and r['reason']=='WINDOWS_VERIFIED_SLEEP_EVENT' for r in records))
            self.assertEqual(s['consecutive_m5'],0)

    def test_cached_binding_avoids_global_scan_without_bypassing_identity(self):
        p=self.producer();process=Mock();process.is_running.return_value=True;process.exe.return_value='C:/Program Files/XM Global SC MT5 Terminal/terminal64.exe'
        with patch('psutil.Process',return_value=process):p.connect()
        p.oracle.connect.assert_not_called()
        p.oracle.mt5.account_info.return_value=NS(trade_mode=2,server='XMGlobalSC-MT5 5')
        with self.assertRaises(RuntimeError):p.identity()

    def producer(self):
        p=Producer.__new__(Producer);p.expected_step='0.01';p.active_pin='pin';p.restart=False
        api=Mock();api.account_info.return_value=NS(trade_mode=0,server='XMGlobalSC-MT5 5');api.terminal_info.return_value=NS(data_path='C:/terminal/20C285FE08971A9A2E814AAC44AFC9D2',connected=True)
        api.symbol_info.return_value=NS(chart_mode=0,trade_tick_size=.01);api.symbol_info_tick.return_value=NS(time_msc=480001,time=480,bid=100,ask=101,flags=2)
        p.oracle=NS(mt5=api,step='0.01',bound_pid=1,connect=Mock(),close=Mock());return p

    def test_real_or_changed_identity_is_never_used(self):
        p=self.producer();p.identity()
        for account in (NS(trade_mode=2,server='XMGlobalSC-MT5 5'),NS(trade_mode=0,server='OTHER')):
            p.oracle.mt5.account_info.return_value=account
            with self.assertRaisesRegex(RuntimeError,'IDENTITY'):p.identity()
        p=self.producer();p.expected_step='0.1'
        with self.assertRaisesRegex(RuntimeError,'GRID_CHANGED'):p.identity()

    def test_first_read_survives_verification_failure_but_no_bar_is_accepted(self):
        p=self.producer();s=new_state();start_epoch(s,dict(time_msc=360001),clock(),'start');s['last_tick']=479999
        p.store=NS(state=s,commit=Mock());p.report=Mock();rows=[dict(time=420,time_msc=420001,bid=100,ask=101,flags=2)]
        p.query=Mock(side_effect=[(rows,{'origin':'TERMINAL_DATABASE_QUERY'}),RuntimeError('SECOND_READ_TIMEOUT')])
        with patch('tools.native_database_snapshots.host_clock',return_value=clock(101)):p.poll()
        records=p.store.commit.call_args.args[0]
        self.assertTrue(any(r['kind']=='DATABASE_QUERY_OBSERVATION' and r['rows']==rows for r in records))
        self.assertTrue(any(r['kind']=='OBSERVATION_INTERRUPTION' for r in records))
        self.assertEqual(s['accepted']['60'],0);self.assertEqual(s['consecutive_m5'],0);self.assertIsNone(s['epoch'])

    def test_query_does_not_truncate_or_accept_outside_envelope(self):
        class Array(list):nbytes=160
        p=self.producer();p.identity=Mock();p.oracle.mt5.last_error.return_value=(1,'Success')
        p.oracle.mt5.copy_ticks_range.return_value=Array([dict(time=1,time_msc=999,bid=100,ask=101,last=0,volume=0,volume_real=0,flags=2)])
        with self.assertRaisesRegex(RuntimeError,'ENVELOPE'):p.query(1000,2000)
        p.oracle.mt5.copy_ticks_range.return_value=type('Oversize',(),{'nbytes':1600001,'__len__':lambda self:1})()
        with self.assertRaisesRegex(RuntimeError,'RESOURCE_CAP'):p.query(1000,2000)

    def test_exact_end_exclusion_is_explicit_and_first_observation_is_not_receipt(self):
        class Array(list):nbytes=160
        p=self.producer();p.identity=Mock();p.oracle.mt5.last_error.return_value=(1,'Success')
        p.oracle.mt5.copy_ticks_range.return_value=Array([dict(time=ms//1000,time_msc=ms,bid=100,ask=101,last=0,volume=0,volume_real=0,flags=2) for ms in [1000,2000]])
        rows,metadata=p.query(1000,2000)
        self.assertEqual(len(rows),1);self.assertEqual(metadata['excluded_exact_end_rows'],1)
        self.assertTrue(metadata['retrieval_may_include_server_downloads']);self.assertTrue(metadata['original_tick_receipt_unknown'])


if __name__=='__main__':unittest.main()
