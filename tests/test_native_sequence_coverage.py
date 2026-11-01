import copy,json,unittest,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from controller.native_sequence_coverage import summarize_reference,compare_bucket,append_quote
from controller.prospective_processor import Processor,initial_state
from controller.isolated_observation import GENESIS
from test_isolated_observation import clock
from tools.prospective_pipeline import NativeReference,active_code_pin,feature_fragment_hash
from controller.authorized_capture import sha


class CoverageTests(unittest.TestCase):
    def rows(self,prices):
        return [dict(time=300,time_msc=300000+i,bid=p,ask=p+1,flags=2) for i,p in enumerate(prices)]

    def test_same_ohlc_volume_different_path_is_not_complete(self):
        raw=self.rows([100,105,95,100]);reference=self.rows([100,95,105,100])
        a=summarize_reference(raw,300000,600000,'1');b=summarize_reference(reference,300000,600000,'1')
        bucket=dict(timeframe_seconds=300,open_msc=300000,open=100,high=105,low=95,close=100,tick_volume=4,bid_sequence_sha256=a['bid_sequence_sha256'],segment='s',issues=[])
        events=[];p=Processor(initial_state(),lambda k,v:events.append((k,v)),lambda *_:dict(bar=dict(time=300,open=100,high=105,low=95,close=100,tick_volume=4),bid_sequence_reference=b),'1',dict(warmup=350,signals=800,post_bars=100,evaluable=200,each_side=80),lambda:clock())
        p.close_bucket(bucket,dict(time_msc=600000),dict(native_time_msc=600000),clock())
        comparison=next(v for k,v in events if k=='BAR_COMPARISON')
        self.assertTrue(comparison['parity_exact'])
        self.assertIn('BID_SEQUENCE_HASH_MISMATCH',comparison['bid_sequence_coverage']['reasons'])
        self.assertFalse(any(k=='CLOSED_AGGREGATE_BAR' for k,v in events))

    def test_exact_sequence_is_only_reference_parity(self):
        rows=self.rows([100,105,95,100]);proof=summarize_reference(rows,300000,600000,'1')
        bucket=dict(open_msc=300000,timeframe_seconds=300,tick_volume=4,bid_sequence_sha256=proof['bid_sequence_sha256'])
        result=compare_bucket(bucket,proof)
        self.assertEqual(result['status'],'PASS_EXACT_NATIVE_BID_SEQUENCE_REFERENCE')
        self.assertFalse(result['scientific_admission']);self.assertFalse(result['independent_utc_certification'])
        self.assertEqual(proof['reference_rows_adopted_as_prospective'],0)

    def test_missing_extra_and_modified_quotes_reject(self):
        rows=self.rows([100,105,95,100]);proof=summarize_reference(rows,300000,600000,'1')
        bucket=dict(open_msc=300000,timeframe_seconds=300,tick_volume=4,bid_sequence_sha256=proof['bid_sequence_sha256'])
        for other in (rows[:-1],rows+[{**rows[-1],'time_msc':300009}],self.rows([100,106,95,100])):
            self.assertNotEqual(compare_bucket(bucket,summarize_reference(other,300000,600000,'1'))['status'],'PASS_EXACT_NATIVE_BID_SEQUENCE_REFERENCE')

    def test_missing_reference_and_legacy_bucket_fail_closed(self):
        bucket=dict(open_msc=300000,timeframe_seconds=300,tick_volume=1)
        self.assertIn('BID_SEQUENCE_REFERENCE_MISSING',compare_bucket(bucket,None)['reasons'])
        proof=summarize_reference(self.rows([100]),300000,600000,'1')
        self.assertIn('BID_SEQUENCE_HASH_MISMATCH',compare_bucket(bucket,proof)['reasons'])

    def test_native_order_and_range_never_corrected(self):
        rows=self.rows([100,101]);original=copy.deepcopy(rows)
        with self.assertRaisesRegex(ValueError,'OUT_OF_ORDER'):summarize_reference(list(reversed(rows)),300000,600000,'1')
        with self.assertRaisesRegex(ValueError,'OUTSIDE_REQUEST'):summarize_reference(rows,300001,600000,'1')
        self.assertEqual(rows,original)

    def test_ask_only_quotes_do_not_count_as_bid_volume(self):
        rows=self.rows([100,101]);rows[0]['flags']=4
        proof=summarize_reference(rows,300000,600000,'1')
        self.assertEqual(proof['bid_update_count'],1);self.assertEqual(proof['all_reference_ticks'],2)
        self.assertEqual(proof['bid_sequence_sha256'],append_quote(GENESIS,rows[1],'1'))

    def test_equal_native_timestamps_preserve_array_order(self):
        rows=self.rows([100,101]);rows[1]['time_msc']=rows[0]['time_msc']
        a=summarize_reference(rows,300000,600000,'1');b=summarize_reference(list(reversed(rows)),300000,600000,'1')
        self.assertNotEqual(a['bid_sequence_sha256'],b['bid_sequence_sha256'])

    def test_live_event_path_emits_only_verified_completed_bucket(self):
        all_rows=[dict(time=(300000+i*5000)//1000,time_msc=300000+i*5000,bid=100+i%7,ask=101+i%7,flags=2,kind='ONTICK_LATEST_QUOTE',callback_uptime_ms=i*5000+100,connected=True) for i in range(121)]
        calls=[]
        def oracle(opening,seconds):
            calls.append((opening,seconds));rows=[r for r in all_rows if opening*1000<=r['time_msc']<(opening+seconds)*1000]
            prices=[r['bid'] for r in rows]
            return dict(bar=dict(time=opening,open=prices[0],high=max(prices),low=min(prices),close=prices[-1],tick_volume=len(rows)),bid_sequence_reference=summarize_reference(rows,opening*1000,(opening+seconds)*1000,'1'))
        state=initial_state();events=[];p=Processor(state,lambda k,v:events.append((k,v)),oracle,'1',dict(warmup=350,signals=800,post_bars=100,evaluable=200,each_side=80),lambda:clock())
        p.segment('fixture','hash')
        for row in all_rows:p.event(row,dict(native_time_msc=row['time_msc']),clock(row['callback_uptime_ms']+1))
        self.assertEqual(state['own_bars'],1);self.assertEqual(state['own_run_bars'],1)
        self.assertNotIn((300,300),calls)
        self.assertEqual(state['after_warmup_signals'],0)

    def api(self,ticks=True):
        rows=self.rows([100,105,95,100]);dtype=[('time','i8'),('time_msc','i8'),('bid','f8'),('ask','f8'),('flags','u4')]
        array=np.array([tuple(r[k] for k,_ in dtype) for r in rows],dtype=dtype)
        rates=np.array([(300,100.,105.,95.,100.,4)],dtype=[('time','i8'),('open','f8'),('high','f8'),('low','f8'),('close','f8'),('tick_volume','i8')]);calls=[]
        fake=SimpleNamespace(TIMEFRAME_M5=5,TIMEFRAME_M1=1,COPY_TICKS_ALL=0,account_info=lambda:SimpleNamespace(server='XMGlobalSC-MT5 5',trade_mode=0),terminal_info=lambda:SimpleNamespace(data_path='C:/data/20C285FE08971A9A2E814AAC44AFC9D2'),symbol_info=lambda _:SimpleNamespace(chart_mode=0,trade_tick_size=1),copy_rates_range=lambda *args:rates,copy_ticks_range=lambda *args:(calls.append(args) or array) if ticks else None)
        ref=NativeReference();ref.mt5=fake;ref.step='1';return ref,calls,fake

    def test_native_api_reference_is_same_interval_and_never_raw_input(self):
        ref,calls,_=self.api()
        with patch('tools.prospective_pipeline.host_clock',return_value=clock()):result=ref(300,300)
        self.assertEqual(len(calls),1);self.assertEqual(calls[0][1].timestamp(),300)
        self.assertEqual(calls[0][2].microsecond,999000);self.assertEqual(int(calls[0][2].timestamp()),599)
        self.assertTrue(result['not_used_to_fill_missing_raw'])
        self.assertEqual(result['bid_sequence_reference']['reference_rows_adopted_as_prospective'],0)

    def test_unavailable_reference_does_not_certify(self):
        ref,_,_=self.api(ticks=False)
        with patch('tools.prospective_pipeline.host_clock',return_value=clock()):result=ref(300,300)
        self.assertIsNone(result['bid_sequence_reference'])

    def test_reference_resource_guard_rejects_whole_response(self):
        ref,_,fake=self.api();fake.copy_ticks_range=lambda *_:SimpleNamespace(nbytes=16*1024*1024+1)
        with patch('tools.prospective_pipeline.host_clock',return_value=clock()):result=ref(300,300)
        self.assertIn('RESOURCE_GUARD',result['error']);self.assertIsNone(result['bar'])

    def test_versioned_pin_keeps_origin_pin_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);origin=base/'deployment_pin.json';origin.write_text('{"version":1}')
            pins=base/'deployment_pins';pins.mkdir();new=pins/'new.json';new.write_text('{"version":2}')
            (base/'deployment_pin_current.json').write_text(json.dumps(dict(file='new.json',sha256=sha(new))))
            with patch('tools.prospective_pipeline.BASE',base):path,pin=active_code_pin()
            self.assertEqual(path,new);self.assertEqual(pin['version'],2);self.assertEqual(origin.read_text(),'{"version":1}')

    def test_pin_pointer_hash_and_traversal_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);(base/'deployment_pins').mkdir();(base/'deployment_pins/new.json').write_text('{}')
            for ref in (dict(file='../elsewhere.json',sha256='x'),dict(file='new.json',sha256='x')):
                (base/'deployment_pin_current.json').write_text(json.dumps(ref))
                with patch('tools.prospective_pipeline.BASE',base),self.assertRaises(ValueError):active_code_pin()

    def test_unchanged_feature_fragment_reuses_only_same_calculation(self):
        source='class Processor:\n    def features(self):\n        return 1\n'
        original=feature_fragment_hash(source)
        self.assertEqual(original,feature_fragment_hash(source+'\ndef helper():\n    return 2\n'))
        self.assertNotEqual(original,feature_fragment_hash(source.replace('return 1','return 2')))


if __name__=='__main__':unittest.main()
