import copy,json,sqlite3,tempfile,unittest
from pathlib import Path
from controller.native_database_snapshots import Store,new_state,start_epoch,boundary_reason,assess,apply_result


def clock(n=100,boot='b'):
    return dict(boot_id=boot,uptime_ms=n,monotonic_ns=n*1000000,host_utc_label='2026-11-02T00:00:00+00:00',utc_certified=False)

def ticks():return [dict(time=300,time_msc=300000+i,bid=p,ask=p+1,flags=2) for i,p in enumerate([100,105,95,101])]
BAR=dict(time=300,open=100,high=105,low=95,close=101,tick_volume=4)


class DatabaseSnapshots(unittest.TestCase):
    def test_exact_native_view_is_not_callback_or_scientific_warmup(self):
        rows=ticks();r=assess(rows,rows,BAR,300000,600000,'1')
        self.assertEqual(r['status'],'VERIFIED_DATABASE_VIEW_ONLY')
        self.assertFalse(r['scientific_warmup_eligible']);self.assertFalse(r['callback_receipt_proven'])

    def test_missing_duplicate_equal_ohlc_volume_still_rejected(self):
        rows=ticks();changed=copy.deepcopy(rows);changed[1]=copy.deepcopy(changed[0])
        r=assess(rows,changed,BAR,300000,600000,'1');self.assertIn('DATABASE_CHANGED_BETWEEN_READS',r['reasons'])
        self.assertEqual(r['status'],'REJECTED_QUARANTINED')

    def test_native_volume_ohlc_and_error_fail_closed(self):
        for bar,error in ((dict(BAR,tick_volume=5),None),(dict(BAR,high=106),None),(BAR,'TIMEOUT'),(None,None)):
            rows=ticks();self.assertEqual(assess(rows,rows,bar,300000,600000,'1',error)['status'],'REJECTED_QUARANTINED')

    def test_first_partial_excluded_and_restart_has_fresh_boundary(self):
        s=new_state();e=start_epoch(s,dict(time_msc=450001),clock(),'startup')
        self.assertEqual(s['next_open']['300'],600000);s['consecutive_m5']=7
        e=start_epoch(s,dict(time_msc=950001),clock(200),'restart')
        self.assertEqual(s['next_open']['300'],1200000);self.assertEqual(s['consecutive_m5'],0);self.assertTrue(e['backfill'] is False)

    def test_continuity_epoch_reasons(self):
        s=new_state();start_epoch(s,dict(time_msc=300000),clock(),'start')
        for tick,c,change,expected in ((300001,clock(110),True,'TERMINAL_PID_CHANGED'),(300001,clock(110,'newboot'),False,'WINDOWS_BOOT_CHANGED'),(300001,clock(99),False,'MONOTONIC_REGRESSION'),(300001,clock(10101),False,'POLL_GAP_TWO_EXISTING_5S_TIMERS'),(299999,clock(110),False,'NATIVE_CLOCK_REGRESSION'),(420000,clock(110),False,'NATIVE_MINUTE_GAP_SESSION_CAUSE_UNKNOWN')):
            self.assertEqual(boundary_reason(s,dict(time_msc=tick),c,terminal_changed=change),expected)
        self.assertIsNone(boundary_reason(s,dict(time_msc=300000),clock(110))) # no tick is not a market-closure assertion

    def test_consecutive_bar_counters_do_not_enter_original_warmup(self):
        s=new_state()
        for i in range(350):apply_result(s,300,300000+i*300000,dict(status='VERIFIED_DATABASE_VIEW_ONLY'))
        self.assertEqual(s['consecutive_m5'],350);self.assertEqual(s['scientific_warmup'],0)
        apply_result(s,300,105300000,dict(status='REJECTED_QUARANTINED'));self.assertEqual(s['consecutive_m5'],0)

    def test_atomic_restart_and_append_only_chain(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'snapshots.sqlite3';store=Store(p);store.state['accepted']['300']=2;store.commit([dict(kind='TEST')]);head=store.head;store.close()
            store=Store(p);self.assertEqual(store.head,head);self.assertEqual(store.state['accepted']['300'],2)
            with self.assertRaises(sqlite3.DatabaseError):store.db.execute("UPDATE records SET body='{}'")
            store.close()


if __name__=='__main__':unittest.main()
