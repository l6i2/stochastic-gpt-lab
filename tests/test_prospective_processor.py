import copy,json,math,sqlite3,tempfile,unittest
from pathlib import Path
from controller.prospective_processor import Processor,Ledger,initial_state
from controller.pretrain_contracts import seal
from test_isolated_observation import clock
from python.native_metadata_v3 import main_k
from controller.native_sequence_coverage import summarize_reference

REQ=dict(warmup=350,signals=800,post_bars=100,evaluable=200,each_side=80)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.state=initial_state();self.events=[];self.native={}
        self.p=Processor(self.state,lambda kind,body:self.events.append(dict(kind=kind,**copy.deepcopy(body))),lambda t,s:self.native.get((t,s)),'1',REQ,lambda:clock(999999999))
        self.p.segment('segment_a','hash')

    def row(self,stamp,uptime,price=100,flags=2,kind='ONTICK_LATEST_QUOTE',connected=True):
        row=dict(time_msc=stamp,time=stamp//1000,bid=price,ask=price+1,flags=flags,kind=kind,connected=connected,callback_uptime_ms=uptime)
        self.p.event(row,dict(native_time_msc=stamp,native_sequence=uptime,segment='segment_a'),clock(uptime+1));return row

    def closed(self,i,close=None,volume=10):
        t=900000+i*300000;close=close if close is not None else 100+5*math.sin(i*.6)
        bar=dict(time=t//1000,open=close,high=close+5,low=close-5,close=close,tick_volume=volume)
        # Exact integer grid; fixtures use integral prices.
        bar={k:(int(v) if k!='time' else v) for k,v in bar.items()}
        bucket=dict(timeframe_seconds=300,open_msc=t,**{k:bar[k] for k in ('open','high','low','close','tick_volume')},first_ref={},last_ref={},segment='segment_a',tick_size='1',issues=[])
        self.native[(t//1000,300)]=self.reference(bucket,bar)
        self.p.close_bucket(bucket,dict(time_msc=t+300000),dict(native_time_msc=t+300000),clock(i+1))

    def reference(self,bucket,bar):
        start=bucket['open_msc'];prices=[bar['open'],bar['high'],bar['low']]+[bar['close']]*(bucket['tick_volume']-3)
        rows=[dict(time_msc=start+i,time=(start+i)//1000,bid=p,ask=p+1,flags=2) for i,p in enumerate(prices)]
        proof=summarize_reference(rows,start,start+bucket['timeframe_seconds']*1000,'1')
        bucket['bid_sequence_sha256']=proof['bid_sequence_sha256']
        return dict(bar=bar,kind='SYNTHETIC_NATIVE_ORACLE',bid_sequence_reference=proof)

    def test_no_bar_from_heartbeats_or_first_partial(self):
        self.row(0,1,kind='HEARTBEAT');self.assertEqual(self.state['own_bars'],0)
        self.row(300001,2);self.row(600001,3)
        self.assertEqual(self.state['own_bars'],0)
        self.assertTrue(any(e['kind']=='INCOMPLETE_BUCKET' for e in self.events))

    def test_native_mismatch_does_not_fill_or_emit_bar(self):
        self.closed(0);self.assertEqual(self.state['own_bars'],1)
        n=sum(e['kind']=='CLOSED_AGGREGATE_BAR' for e in self.events)
        bucket=dict(timeframe_seconds=300,open_msc=1200000,open=100,high=105,low=95,close=100,tick_volume=10,segment='segment_a',issues=[])
        self.native[(1200,300)]=dict(bar=dict(time=1200,open=100,high=105,low=95,close=100,tick_volume=11))
        self.p.close_bucket(bucket,dict(time_msc=1500000),{},clock())
        self.assertEqual(sum(e['kind']=='CLOSED_AGGREGATE_BAR' for e in self.events),n)
        self.assertEqual(self.state['own_run_bars'],0)

    def test_missing_native_reference_quarantines_bucket(self):
        self.row(300001,1);self.row(600001,2);self.row(900001,3)
        self.assertEqual(self.state['own_bars'],0)

    def test_gap_disconnect_and_time_regression_record_incidents(self):
        self.row(300001,1);self.row(305001,20000,connected=False);self.row(300000,20001)
        reasons=[e['reason'] for e in self.events if e['kind']=='INCIDENT']
        self.assertIn('CALLBACK_GAP_TWO_EXISTING_TIMERS',reasons);self.assertIn('DISCONNECTED',reasons);self.assertIn('NATIVE_TIME_REGRESSION_NO_SORT',reasons)

    def test_main_k_reuses_frozen_adapter_and_prefix_stability(self):
        for i in range(40):self.closed(i)
        features=[e for e in self.events if e['kind']=='CAUSAL_PREFIX_FEATURES']
        bars=[e['bar'] for e in self.events if e['kind']=='CLOSED_AGGREGATE_BAR']
        self.assertEqual([e['values']['stoch_k'] for e in features],list(main_k(bars)))
        snapshot=copy.deepcopy(features)
        for i in range(40,50):self.closed(i,1000)
        self.assertEqual(snapshot,[e for e in self.events if e['kind']=='CAUSAL_PREFIX_FEATURES'][:40])

    def test_atr_ha_own_seed_and_no_premature_ready(self):
        for i in range(350):self.closed(i)
        f=[e for e in self.events if e['kind']=='CAUSAL_PREFIX_FEATURES']
        self.assertIsNone(f[13]['values']['ATR']);self.assertIsNotNone(f[14]['values']['ATR'])
        self.assertIsNone(f[274]['values']['ha_direction']);self.assertIsNotNone(f[275]['values']['ha_direction'])
        self.assertEqual(f[-1]['closed_bar_count'],350)
        self.assertFalse(f[-1]['scientific_causality_certified'])
        self.assertEqual(self.p.maturity()['evaluable_total'],0)
        self.assertLessEqual(len(self.state['history']),351)

    def test_signal_threshold_equality_and_no_future_input(self):
        for previous,current,side in [(20,21,'BUY'),(80,79,'SELL'),(20,20,None),(80,80,None)]:
            self.setUp();self.state['previous_k']=previous
            # Seven bars produce K=100*(close-low)/(high-low).
            history=[dict(time=i*300,open=current,high=100,low=0,close=current,tick_volume=1) for i in range(6)]
            # Valid positive OHLC for frozen adapter: translate by 100.
            history=[dict(b,open=b['open']+100,high=200,low=100,close=b['close']+100) for b in history]
            self.state['history']=history;self.state['own_run_bars']=7
            self.p.features(dict(time=1800,open=current+100,high=200,low=100,close=current+100,tick_volume=1,segment='s'),'bar',{'native_time_msc':2100000},clock())
            got=[e['side'] for e in self.events if e['kind']=='MAIN_K_SIGNAL']
            self.assertEqual(got,[side] if side else [])

    def test_800_100_stop_counter_cannot_become_evaluable(self):
        self.state['after_warmup_signals']=800
        for i in range(110):self.closed(i)
        self.assertEqual(self.state['post_signal_bars'],100)
        self.assertEqual(sum(e['kind']=='DIAGNOSTIC_STOP_BOUNDARY' for e in self.events),1)
        self.assertEqual(self.p.maturity()['evaluable_buy'],0);self.assertEqual(self.p.maturity()['evaluable_sell'],0)

    def test_segment_change_resets_seeds_and_does_not_merge(self):
        self.closed(0);self.p.segment('segment_b','hash2')
        self.assertEqual(self.state['own_run_bars'],0);self.assertIsNone(self.state['ha']);self.assertIsNone(self.state['atr'])
        self.assertFalse(self.state['protocol_stream_unbroken'])

    def test_future_feature_cutoff_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'FEATURE_FUTURE'):self.p.features(dict(time=900,open=100,high=101,low=99,close=100,tick_volume=1),'x',{'native_time_msc':1199999},clock())

    def test_gap_does_not_restart_or_extend_800_100_selection(self):
        self.state['after_warmup_signals']=800;self.p.incident('GAP',{})
        for i in range(110):self.closed(i)
        self.assertEqual(self.state['post_signal_bars'],0)

    def test_receipt_clock_regression_rejected(self):
        self.row(300001,100)
        with self.assertRaisesRegex(ValueError,'RECEIPT_CLOCK'):self.p.event(dict(kind='HEARTBEAT',callback_uptime_ms=101,connected=True),{},clock(50))

    def test_ledger_restart_idempotence_and_append_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'state.sqlite';a=Ledger(path);a.state['source_records']=1;a.emit('TEST',{'signal_id':'stable'});a.commit();head=a.head;a.close()
            b=Ledger(path);self.assertEqual(b.head,head);self.assertEqual(b.state['source_records'],1)
            with self.assertRaises(sqlite3.IntegrityError):b.db.execute('DELETE FROM artifacts')
            b.close()

    def test_checkpoint_tamper_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'state.sqlite';a=Ledger(path);a.commit();a.close()
            db=sqlite3.connect(path);db.execute("UPDATE checkpoint SET body='{}'");db.commit();db.close()
            with self.assertRaisesRegex(ValueError,'CHECKPOINT_CHANGED'):Ledger(path)

    def test_first_800_are_capped_then_exact_100_bar_horizon(self):
        i=0
        while self.state['after_warmup_signals']<800 and i<4000:
            t=900000+i*300000;price=110 if (i//4)%2==0 else 190
            bar=dict(time=t//1000,open=price,high=200,low=100,close=price,tick_volume=10)
            bucket=dict(timeframe_seconds=300,open_msc=t,open=price,high=200,low=100,close=price,tick_volume=10,segment='segment_a',issues=[])
            self.native[(t//1000,300)]=self.reference(bucket,bar)
            self.p.close_bucket(bucket,dict(time_msc=t+300000),dict(native_time_msc=t+300000),clock(i+1));i+=1
        self.assertEqual(self.state['after_warmup_signals'],800)
        for j in range(105):self.closed(i+j)
        self.assertEqual(self.state['after_warmup_signals'],800)
        self.assertEqual(self.state['post_signal_bars'],100)
        self.assertEqual(sum(e['kind']=='DIAGNOSTIC_STOP_BOUNDARY' for e in self.events),1)
        self.assertEqual(self.p.maturity()['evaluable_total'],0)

    def test_sql_transaction_failure_preserves_previous_cursor(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'state.sqlite';a=Ledger(path);a.state['source_records']=1;a.commit();head=a.head
            a.db.execute("CREATE TRIGGER abort_batch BEFORE INSERT ON artifacts WHEN NEW.body LIKE '%BAD_EVENT%' BEGIN SELECT RAISE(ABORT,'SIMULATED_DISK_BATCH_FAILURE'); END")
            a.state['source_records']=2;a.emit('BAD_EVENT',{})
            with self.assertRaises(sqlite3.IntegrityError):a.commit()
            a.close();b=Ledger(path)
            self.assertEqual(b.head,head);self.assertEqual(b.state['source_records'],1);b.close()


if __name__=='__main__':unittest.main()
