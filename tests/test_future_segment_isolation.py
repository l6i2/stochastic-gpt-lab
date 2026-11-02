"""Regression: an old quarantine must not stop later native diagnostics."""
import unittest
from controller.prospective_processor import Processor,initial_state
from controller.native_sequence_coverage import summarize_reference
from test_isolated_observation import clock


class FutureSegmentTests(unittest.TestCase):
    def test_valid_later_segment_progresses_without_admitting_broken_cohort(self):
        state=initial_state();events=[];references={}
        p=Processor(state,lambda k,v:events.append((k,v)),lambda t,s:references[(t,s)],'1',
            dict(warmup=350,signals=800,post_bars=100,evaluable=200,each_side=80),lambda:clock())
        def close(start,segment,reference_count):
            quotes=[dict(time=start//1000,time_msc=start+i,bid=100,ask=101,flags=2) for i in range(reference_count)]
            bucket=dict(timeframe_seconds=300,open_msc=start,open=100,high=100,low=100,close=100,
                tick_volume=4,segment=segment,issues=[],bid_sequence_sha256=summarize_reference(quotes[:4],start,start+300000,'1')['bid_sequence_sha256'])
            references[(start//1000,300)]=dict(bar=dict(time=start//1000,open=100,high=100,low=100,close=100,tick_volume=reference_count),
                bid_sequence_reference=summarize_reference(quotes,start,start+300000,'1'))
            p.close_bucket(bucket,dict(time_msc=start+300000),dict(native_time_msc=start+300000),clock())
        p.segment('old','old_manifest_hash');close(300000,'old',5)
        self.assertEqual(state['own_bars'],0)
        p.segment('future','new_manifest_hash');close(900000,'future',4)
        self.assertEqual(state['own_bars'],1)
        self.assertEqual(state['own_run_bars'],1)
        self.assertEqual(sum(k=='CAUSAL_PREFIX_FEATURES' for k,v in events),1)
        self.assertFalse(state['protocol_stream_unbroken'])
        self.assertEqual(p.maturity()['evaluable_total'],0)
        self.assertEqual(p.maturity()['admitted_records'],0)
        self.assertEqual(state['after_warmup_signals'],0)
