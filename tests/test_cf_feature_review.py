import copy
import unittest
from controller.cf_feature_review import seed_check
from controller.prospective_processor import Processor,initial_state
from tools.cf_own_indicator_oracle import build_source


class CfFeatureReviewTests(unittest.TestCase):
    def test_own_seed_atr_and_ha_boundaries_without_later_inputs(self):
        state=initial_state();outputs=[]
        processor=Processor(state,lambda kind,body:outputs.append(body),None,'0.01',dict(warmup=350,signals=800,post_bars=100,evaluable=200,each_side=80),lambda:dict(boot_id='synthetic',monotonic_ns=0))
        for i in range(350):
            bar=dict(time=300*(i+1),open=100,high=102+i%4,low=98,close=101, tick_volume=5,segment='synthetic')
            state['own_run_bars']+=1
            processor.features(bar,'first' if i==0 else str(i),dict(native_time_msc=(bar['time']+300)*1000),{})
            result=seed_check(state,'first')
            self.assertEqual(result['ATR_INITIALIZED'],i+1>=15)
            self.assertEqual(result['HA_READY'],i+1>=276)
            self.assertEqual(result['warmup_ready'],i+1>=350)
            self.assertEqual(outputs[-1]['feature_cutoff_native_msc'],(bar['time']+300)*1000-1)
        corrupt=copy.deepcopy(state);corrupt['atr']['seed_bar_hash']='prior_epoch'
        with self.assertRaises(ValueError):seed_check(corrupt,'first')
        corrupt=copy.deepcopy(state);corrupt['ha']['count']-=1
        with self.assertRaises(ValueError):seed_check(corrupt,'first')

    def test_empty_epoch_refuses_old_recursive_seed(self):
        self.assertFalse(seed_check(initial_state(),None)['seeds_bound'])
        bad=initial_state();bad['ha']={'seed_bar_hash':'old'}
        with self.assertRaises(ValueError):seed_check(bad,None)

    def test_own_oracle_copies_only_real_supplied_minutes_no_dummy_bar(self):
        bars=[dict(time=300*(i+1),open=100,high=102,low=98,close=101,tick_volume=5) for i in range(15)]
        minutes=[dict(row,time=row['time']+m*60,tick_volume=1) for row in bars for m in range(5)]
        text=build_source(dict(native_m5=bars,native_m1=minutes),'test_run')
        self.assertIn('ArrayResize(bars,15);ArrayResize(minutes,75)',text)
        self.assertIn('CopyBuffer(atr,0,0,15,a)==15',text)
        self.assertNotIn('ArrayResize(bars,500)',text)
        self.assertNotIn('i<499',text)
        self.assertIn('bars[i].tick_volume,DoubleToString(k[i]',text)
        self.assertIn('"ha_open","ha_high","ha_low","ha_close"',text)
        self.assertIn('DoubleToString(ha.bars[0].h,16)',text)
        self.assertEqual(text.count('ZeroMemory(minutes['),75)
        with self.assertRaises(ValueError):build_source(dict(native_m5=bars[:-1],native_m1=minutes[:-5]),'test_run')
        with self.assertRaises(ValueError):build_source(dict(native_m5=bars,native_m1=minutes[:-1]),'test_run')


class FeaturePersistenceTests(unittest.TestCase):
    def test_serialized_context_and_future_mutation_preserve_prefix(self):
        import json
        def run(mutate=False, restart=False):
            state=initial_state()
            outputs=[]
            def processor():
                return Processor(state,lambda kind,body:outputs.append(body),None,'0.01',
                    dict(warmup=350,signals=800,post_bars=100,evaluable=200,each_side=80),
                    lambda:dict(boot_id='synthetic',monotonic_ns=0))
            worker=processor()
            prefix=None
            for i in range(300):
                if restart and i==150:
                    state=json.loads(json.dumps(state))
                    worker=processor()
                bar=dict(time=300*(i+1),open=100.,high=110.+i%7,low=90.,close=102.,
                         tick_volume=5,segment='synthetic')
                if mutate and i>=276:
                    bar.update(open=1e8,high=1e9,low=1.,close=1e7)
                state['own_run_bars']+=1
                worker.features(bar,'first' if i==0 else str(i),
                                dict(native_time_msc=(bar['time']+300)*1000),{})
                if i==275:prefix=copy.deepcopy(outputs)
            return prefix,state
        baseline,final=run()
        restored,restored_final=run(restart=True)
        mutated,_=run(mutate=True)
        self.assertEqual(baseline,restored)
        self.assertEqual(final,restored_final)
        self.assertEqual(baseline,mutated)
        self.assertTrue(seed_check(final,'first')['HA_READY'])

if __name__=='__main__':unittest.main()
