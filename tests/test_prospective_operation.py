import copy,unittest
from tools.verify_prospective_operation import compare_samples


class OperationTests(unittest.TestCase):
    def samples(self):
        first=dict(capture_id='cap',clock=dict(boot_id='b',monotonic_ns=1000000000),raw=dict(totals=dict(source_records=10,tick_callbacks=0)),derived=dict(raw_records_processed=10,process_id=1),native_cache=dict(connected=True,cached_quote_native_msc=100),worker=dict(processing_workers=1,unexpected_processes=0,processes=[dict(pid=1,cpu_seconds=1)]))
        last=copy.deepcopy(first);last['clock']['monotonic_ns']+=20000000000;last['raw']['totals']['source_records']+=4;last['derived']['raw_records_processed']+=4;last['worker']['processes'][0]['cpu_seconds']+=.1
        return first,last

    def test_real_heartbeat_progress_is_not_market_pipeline_pass(self):
        a,b=self.samples();result=compare_samples(a,b)
        self.assertEqual(result['observed_heartbeat_ingestion'],'PASS_REAL_RECORD_PROGRESS')
        self.assertEqual(result['end_to_end_market_pipeline'],'NOT_DEMONSTRATED_NO_MARKET_TICK_PROGRESS')
        self.assertFalse(result['scientific_admission']);self.assertFalse(result['market_closed_certified'])

    def test_quote_cache_is_not_a_new_tick(self):
        a,b=self.samples();b['native_cache']['cached_quote_native_msc']+=100
        self.assertEqual(compare_samples(a,b)['real_tick_delta'],0)

    def test_tick_growth_still_requires_real_bars_and_features(self):
        a,b=self.samples();b['raw']['totals']['tick_callbacks']=1
        self.assertEqual(compare_samples(a,b)['end_to_end_market_pipeline'],'REQUIRES_REAL_BAR_FEATURE_SIGNAL_EVIDENCE')

    def test_stopped_or_duplicate_worker_never_ingestion_pass(self):
        for owner,extra in ((0,0),(1,1)):
            a,b=self.samples();b['worker'].update(processing_workers=owner,unexpected_processes=extra)
            self.assertEqual(compare_samples(a,b)['observed_heartbeat_ingestion'],'NOT_DEMONSTRATED')

    def test_counter_regression_and_capture_change_fail(self):
        a,b=self.samples();b['raw']['totals']['source_records']=0
        with self.assertRaisesRegex(ValueError,'COUNTER_REGRESSION'):compare_samples(a,b)
        a,b=self.samples();b['capture_id']='other'
        with self.assertRaisesRegex(ValueError,'CAPTURE_ID_CHANGED'):compare_samples(a,b)

    def test_disconnection_is_reported_without_inventing_closure(self):
        a,b=self.samples();a['native_cache']['connected']=False
        self.assertEqual(compare_samples(a,b)['immediate_cause'],'NO_NEW_TICKS_WITH_BROKER_DISCONNECTION_OBSERVED')

    def test_cpu_and_clock_domains(self):
        a,b=self.samples();self.assertAlmostEqual(compare_samples(a,b)['worker_cpu_one_core_average_percent'],.5)
        b['clock']['boot_id']='new'
        self.assertIsNone(compare_samples(a,b)['sample_elapsed_monotonic_seconds'])
        self.assertIsNone(compare_samples(a,b)['worker_cpu_one_core_average_percent'])


if __name__=='__main__':unittest.main()
