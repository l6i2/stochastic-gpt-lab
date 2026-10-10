import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd
from fixtures import dataset, audit
from ha_reference import candles, reference
from heikin_ashi import HA_COLUMNS, HA_METADATA
from research import validate, REQUIRED_V1
from analyze_dataset import fit_deciles, ha_interactions

ROOT=Path(__file__).resolve().parents[1]
BASE='3844d04079145865a43d1fce0a17240b34c69d69'

class HeikinAshiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.binary=Path(cls.tmp.name)/'ha_native'
        subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(ROOT/'tests/ha_native.cpp'),'-o',str(cls.binary)],check=True)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def native(self,raw,cutoff=None):
        cutoff=int((raw.time.iloc[-1]+300)*1000-1) if cutoff is None else int(cutoff)
        payload=raw[['time','open','high','low','close']].to_csv(sep=' ',header=False,index=False)
        out=subprocess.run([str(self.binary),str(cutoff)],input=payload,text=True,capture_output=True,check=True).stdout
        names=['time','count','seed','raw_open','raw_close','ready','censored']+HA_COLUMNS
        return pd.read_csv(io.StringIO(out),names=names).replace(np.finfo(float).max,np.nan)

    def test_seed_and_recurrence(self):
        raw=candles(4);got=self.native(raw)
        self.assertAlmostEqual(got.raw_open.iloc[0],(raw.open.iloc[0]+raw.close.iloc[0])/2)
        for i in range(1,4):
            self.assertAlmostEqual(got.raw_open.iloc[i],(got.raw_open.iloc[i-1]+got.raw_close.iloc[i-1])/2)
        self.assertTrue(got.ha_open.isna().all())

    def test_all_54_features_match_independent_past_only_oracle(self):
        raw=candles(500);got=self.native(raw);expected=reference(raw,(raw.time.iloc[-1]+300)*1000-1)
        np.testing.assert_allclose(got[HA_COLUMNS],expected[HA_COLUMNS],rtol=1e-9,atol=1e-9,equal_nan=True)
        np.testing.assert_array_equal(got.censored,expected.ha_streak_left_censored)

    def test_warmup_and_single_seed_persist(self):
        got=self.native(candles(400))
        self.assertTrue(got.loc[:274,'ha_open'].isna().all())
        self.assertTrue(got.loc[275:,'ha_open'].notna().all())
        self.assertEqual(got.seed.nunique(),1)
        self.assertEqual(got['count'].iloc[-1],400)

    def test_future_perturbation_and_entry_bar_excluded(self):
        raw=candles(330);signal_index=300;cutoff=(raw.time.iloc[signal_index]+300)*1000-1
        original=self.native(raw,cutoff)
        changed=raw.copy();changed.loc[signal_index+1:,['open','high','low','close']]*=999
        pd.testing.assert_frame_equal(original,self.native(changed,cutoff))
        self.assertEqual(len(original),signal_index+1)
        self.assertEqual(original.time.iloc[-1],raw.time.iloc[signal_index])
        self.assertNotIn(raw.time.iloc[signal_index+1],original.time.tolist())
        # Even when later bars become closed, the earlier output is invariant.
        pd.testing.assert_frame_equal(self.native(raw).iloc[:301],self.native(changed).iloc[:301])

    def test_ratios_and_streaks_use_only_closed_history(self):
        raw=candles(320);got=self.native(raw)
        directions=np.sign(got.raw_close-got.raw_open)
        for i in range(275,len(got)):
            for n in (3,5,10,20):
                self.assertAlmostEqual(got[f'ha_bullish_ratio_{n}'].iloc[i],(directions.iloc[i-n+1:i+1]==1).mean())
            count=0
            for j in range(i,-1,-1):
                if directions.iloc[j]!=1:break
                count+=1
            self.assertEqual(got.ha_consecutive_bullish.iloc[i],count)

    def test_doji_zero_range_and_duplicate_bar(self):
        raw=candles(300);raw[['open','high','low','close']]=1000.
        got=self.native(raw)
        self.assertEqual(got.ha_direction.iloc[-1],0)
        self.assertTrue(np.isnan(got.ha_body_expansion.iloc[-1]))
        self.assertEqual(got.ha_small_body.iloc[-1],0)
        duplicate=pd.concat([raw,raw.iloc[[-1]]],ignore_index=True)
        pd.testing.assert_frame_equal(got,self.native(duplicate))

    def test_initialization_influence_decays_before_ready(self):
        raw=candles(300);changed=raw.copy()
        changed.loc[0,['open','high','low','close']]+=1000
        a=self.native(raw);b=self.native(changed)
        self.assertGreater(abs(a.raw_open.iloc[0]-b.raw_open.iloc[0]),999)
        np.testing.assert_allclose(a.raw_open.iloc[256:],b.raw_open.iloc[256:],rtol=0,atol=1e-10)

    def test_long_streak_not_truncated_to_rolling_window(self):
        raw=candles(400)
        op=1000+np.arange(400)*2
        raw['open']=op;raw['high']=op+8;raw['low']=op-2;raw['close']=op+4
        got=self.native(raw)
        self.assertEqual(got.ha_consecutive_bullish.iloc[-1],400)
        self.assertEqual(got.ha_bullish_run_before_signal.iloc[-1],399)
        self.assertEqual(got.censored.iloc[-1],1)

    def test_validator_rejects_future_misaligned_or_unwarmed_ha(self):
        self.assertEqual(validate(dataset(),audit(100)),[])
        for column,value in [('ha_last_bar_open',1704067500),('ha_bars_processed',100),('ha_warmup_bars',1),('ha_close',999999)]:
            d=dataset();d.loc[0,column]=value
            self.assertTrue(any('HEIKIN_ASHI' in e for e in validate(d)),column)
        d=dataset();d.loc[0,'ha_status']='warming_up';d.loc[0,'ha_bars_processed']=20;d.loc[0,HA_COLUMNS]=np.nan
        self.assertEqual(validate(d),[])

    def test_fixed_interactions_and_train_only_edges(self):
        d=dataset();edges=fit_deciles(d.iloc[:60]);changed=d.copy();changed.loc[60:,'ha_body_expansion']=1e9
        self.assertEqual(edges,fit_deciles(changed.iloc[:60]))
        with tempfile.TemporaryDirectory() as tmp:
            ha_interactions(d,edges,Path(tmp));report=pd.read_csv(Path(tmp)/'ha_interactions.csv')
            self.assertEqual(set(report.population),{'ALL','BUY','SELL'})
            pairs=report[['ha_feature','context_feature']].drop_duplicates()
            self.assertEqual(len(pairs),30)
            for name in ('relative_volume_20','volume_expansion','volume_percentile_20','vp_30m_distance_price_to_POC','vp_session_value_area_state','ATR_percentile_20'):
                self.assertIn(name,set(report.context_feature))
            self.assertIn('follow_mean_paired',report);self.assertIn('invert_mean_paired',report)

    def test_schema_10_backward_compatibility(self):
        d=dataset()[REQUIRED_V1].copy();d['schema_version']='1.0';a=audit(len(d));a['schema_version']='1.0'
        self.assertEqual(validate(d,a),[])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'legacy.csv';d.to_csv(path,index=False);Path(str(path)+'.audit.json').write_text(json.dumps(a))
            subprocess.run([sys.executable,str(ROOT/'python/analyze_dataset.py'),str(path),'--output',str(Path(tmp)/'report')],check=True,capture_output=True,text=True)
            self.assertFalse((Path(tmp)/'report/TRAIN/ha_interactions.csv').exists())

    def test_stochastic_core_and_execution_unchanged(self):
        original=subprocess.check_output(['git','show',BASE+':mt5/ResearchCore.mqh'],cwd=ROOT,text=True)
        self.assertEqual(original,(ROOT/'mt5/ResearchCore.mqh').read_text())
        old=subprocess.check_output(['git','show',BASE+':mt5/StochasticResearchEA.mq5'],cwd=ROOT,text=True)
        new=(ROOT/'mt5/StochasticResearchEA.mq5').read_text()
        # Entire virtual execution implementation is byte-for-byte identical.
        self.assertEqual(old[old.index('void OpenTrade'):old.index('bool Buffer')],new[new.index('void OpenTrade'):new.index('bool Buffer')])
        for needle in ('int side=ResearchSignal(previous,current);if(side==0)return;','input bool LIVE_TRADING=false;','K_PERIOD=5,D_PERIOD=3,SLOWING=3,TIME_EXIT_BARS=100','TP_DISTANCE=240.0,SL_DISTANCE=180.0'):
            self.assertIn(needle,new)
        self.assertLess(new.index(' UpdateHA(ResearchSignalCutoff'),new.index(' int side=ResearchSignal'))
        for forbidden in ('OrderSend','CTrade'):
            self.assertNotIn(forbidden,new)

if __name__=='__main__':unittest.main()
