import copy,unittest,importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('proposed_database_review',Path(__file__).resolve().parents[1]/'research/proposals/native_database_capture_v1/review.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);review=module.review


class ProposalTests(unittest.TestCase):
    def pair(self,n=10):
        rows=[dict(time=(1000+i//2)//1000,time_msc=1000+i//2,bid=100+i%3,ask=104,flags=2) for i in range(n)]
        a=dict(origin='TERMINAL_DATABASE_QUERY',rows=rows,start_msc=1000,end_msc=60000,
            query_start_ns=10,query_end_ns=20,boot_id='boot1',session_id='session1',error=None,connected=True)
        b=copy.deepcopy(a);b.update(query_start_ns=30,query_end_ns=40)
        return a,b

    def test_repeatable_snapshot_never_becomes_callback_proof(self):
        r=review(*self.pair());self.assertEqual(r['status'],'REPEATABLE_DATABASE_SNAPSHOT_ONLY')
        for k in ('callback_receipt_proven','event_generation_utc_proven','eligible_for_frozen_callback_warmup','producer_activation_allowed','dataset_admitted'):self.assertFalse(r[k])

    def test_identical_ticks_same_millisecond_keep_multiplicity(self):
        a,b=self.pair(2);a['rows'][1]=copy.deepcopy(a['rows'][0]);b['rows']=copy.deepcopy(a['rows'])
        r=review(a,b);self.assertEqual(r['first_rows'],2)
        b['rows'].pop();self.assertIn('DATABASE_REVISION_OR_PARTIAL_READ',review(a,b)['reasons'])

    def test_partial_download_and_late_revision_remain_quarantined(self):
        a,b=self.pair();a['rows']=a['rows'][:-1]
        self.assertEqual(review(a,b)['status'],'QUARANTINED')

    def test_disconnect_timeout_restart_reboot(self):
        for field,value in [('connected',False),('error','HISTORY_TIMEOUT'),('session_id','newsession'),('boot_id','newboot')]:
            a,b=self.pair();b[field]=value;self.assertEqual(review(a,b)['status'],'QUARANTINED')

    def test_no_data_is_not_calendar_certificate(self):
        a,b=self.pair(0);self.assertIn('EMPTY_NOT_PROOF_OF_MARKET_CLOSURE',review(a,b)['reasons'])

    def test_clock_regression_boundary_and_order_are_rejected(self):
        for mode in ('clock','boundary','order','units'):
            a,b=self.pair()
            if mode=='clock':b['query_end_ns']=0
            elif mode=='boundary':b['rows'][-1]['time_msc']=60000
            elif mode=='order':b['rows'].reverse()
            else:b['rows'][0]['time']=0
            with self.assertRaises(ValueError):review(a,b)

    def test_stress_preserves_all_rows_and_resource_limit_is_fail_closed(self):
        a,b=self.pair(20000);r=review(a,b);self.assertEqual(r['first_rows'],20000)
        with self.assertRaises(ValueError):review(a,b,max_rows=19999)

    def test_coalescing_is_a_counterexample_to_every_tick_guarantee(self):
        # Admissible EA schedule: first callback remains busy while ticks1,2 arrive.
        arrivals=[0,1,2,100];busy_until=-1;captured=[]
        for t in arrivals:
            if t>=busy_until:captured.append(t);busy_until=t+10
        self.assertEqual(captured,[0,100]);self.assertNotEqual(captured,arrivals)
        # A later DB snapshot can contain all4, without proving4 callback receptions.
        a,b=self.pair(4);r=review(a,b);self.assertEqual(r['first_rows'],4);self.assertFalse(r['callback_receipt_proven'])


if __name__=='__main__':unittest.main()
