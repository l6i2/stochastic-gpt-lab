import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import pandas as pd
from fixtures import dataset, audit
from research import (FEATURE_COLUMNS, PROFILE_PREFIXES, causal_profile, chronological_split,
                      purge_at_boundary, validate, walk_forward, read_dataset)
from analyze_dataset import fit_deciles, bins, stats

ROOT=Path(__file__).resolve().parents[1]

class ResearchTests(unittest.TestCase):
    def test_actual_shared_mql_scalar_core(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary=Path(tmp)/'core_test'
            subprocess.run(['g++','-Wall','-Wextra','-Werror','-std=c++17',str(ROOT/'tests/core_test.cpp'),'-o',str(binary)],check=True)
            subprocess.run([str(binary)],check=True)

    def test_contract_and_audit(self):
        d=dataset();self.assertEqual(validate(d,audit(len(d))),[])
        a=audit(len(d));a['signals']+=1
        self.assertIn('Audit signal/row count mismatch',validate(d,a))

    def test_duplicate_monotonic(self):
        d=dataset();d.loc[1,'signal_id']=d.loc[0,'signal_id']
        self.assertTrue(any('Duplicate' in e for e in validate(d)))
        self.assertTrue(any('Non-monotonic' in e for e in validate(dataset().iloc[::-1])))

    def test_exact_strategy_constants(self):
        for key in ('stoch_k_period','stoch_d_period','stoch_slowing','tp_distance','sl_distance','time_exit_bars'):
            d=dataset();d.loc[0,key]+=1
            self.assertTrue(any(key in e for e in validate(d)),key)

    def test_signal_and_mapping(self):
        d=dataset();d.loc[0,'stoch_k']=20
        self.assertTrue(any('exit from' in e for e in validate(d)))
        d=dataset();d.loc[0,'invert_side']='BUY'
        self.assertTrue(any('INVERT mapping' in e for e in validate(d)))
        d=dataset();d['trigger_line']='SIGNAL_D';d['stoch_d']=d.stoch_k;d['stoch_d_prev']=d.stoch_k_prev
        self.assertEqual(validate(d),[])

    def test_future_entry_features_and_profiles_rejected(self):
        for key in ('feature_max_time_msc','vp_30m_window_end_msc','vp_30m_last_tick_msc'):
            d=dataset();d.loc[0,key]=d.loc[0,'signal_time_msc']+1000
            self.assertTrue(validate(d),key)
        d=dataset();d.loc[0,'entry_time_msc']=d.loc[0,'signal_time_msc']
        self.assertTrue(any('Entry' in e for e in validate(d)))

    def test_profile_future_perturbation_invariance(self):
        ticks=pd.DataFrame({'time_msc':[1,2,3,4,5,100],'bid':[100,100,110,120,120,99999]})
        a=causal_profile(ticks,1,5,10)
        ticks.loc[5,'bid']=-999
        self.assertEqual(a,causal_profile(ticks,1,5,10))
        self.assertEqual(a,{'POC':105.,'VAL':100,'VAH':130,'last_tick_msc':5,'ticks_used':5})
        self.assertIsNone(causal_profile(ticks,200,300))

    def test_profile_real_volume_not_tick_counts(self):
        ticks=pd.DataFrame({'time_msc':[1,2,3],'bid':[100.,100.,200.],'last':[100.,100.,200.],'volume_real':[0.,0.,50.],'flags':[2,2,32]})
        self.assertEqual(causal_profile(ticks,1,3)['POC'],105.)
        self.assertEqual(causal_profile(ticks,1,3,real=True)['POC'],205.)
        ticks['volume_real']=0
        self.assertIsNone(causal_profile(ticks,1,3,real=True))

    def test_splits_and_purge(self):
        d=dataset();parts=chronological_split(d)
        self.assertEqual([len(p) for p in parts.values()],[60,20,20])
        boundary=int(parts['DISCOVERY_VALIDATION'].signal_time_msc.iloc[0])
        train=parts['TRAIN'];train.loc[59,'follow_exit_time']=boundary
        clean,count=purge_at_boundary(train,boundary)
        self.assertEqual((len(clean),count),(59,1))
        with self.assertRaises(ValueError):chronological_split(d.iloc[::-1])
        with self.assertRaises(ValueError):chronological_split(d,.8,.3)

    def test_walk_forward_excludes_final_and_purges(self):
        d=dataset();parts=chronological_split(d);pool=pd.concat([parts['TRAIN'],parts['DISCOVERY_VALIDATION']])
        final_ids=set(parts['FINAL_TEST'].signal_id)
        folds=list(walk_forward(pool,40,10));self.assertEqual(len(folds),4)
        for train,val,_ in folds:
            self.assertFalse(set(train.signal_id)&final_ids);self.assertFalse(set(val.signal_id)&final_ids)
            self.assertLess(train[['follow_exit_time','invert_exit_time']].max().max(),val.signal_time_msc.min())

    def test_train_edges_invariant_to_future_outcomes(self):
        d=dataset();a=fit_deciles(chronological_split(d)['TRAIN'])
        d.loc[60:,'tick_volume']=1e9;d.loc[60:,'volume_percentile_20']=-999;d.loc[60:,'follow_PnL']=1e9
        self.assertEqual(a,fit_deciles(chronological_split(d)['TRAIN']))
        self.assertFalse(any('PnL' in c or 'entry_' in c or 'spread'==c for c in FEATURE_COLUMNS))

    def test_losses_ties_and_censoring_retained(self):
        d=dataset();d.loc[0,'follow_PnL']=0;d.loc[0,'follow_exit_price']=d.loc[0,'follow_entry_price'];d.loc[0,'follow_exit_reason']='TIME_EXIT';d.loc[0,'follow_bars_in_trade']=100;d.loc[0,'directional_advantage']=-d.loc[0,'invert_PnL']
        d.loc[1,'follow_exit_reason']='END_OF_DATA';d.loc[1,['follow_PnL','directional_advantage']]=float('nan')
        self.assertEqual(validate(d),[])
        s=stats(d);self.assertEqual(s['signals'],100);self.assertEqual(s['censored_pairs'],1);self.assertEqual(s['follow_ties'],1);self.assertGreater(s['follow_losses'],0)

    def test_ea_static_safety_and_causality_guards(self):
        s=(ROOT/'mt5/StochasticResearchEA.mq5').read_text()
        for forbidden in ('OrderSend','CTrade','OrderSendAsync','PositionOpen'):
            self.assertNotIn(forbidden,s)
        for required in ('LIVE_TRADING=false','!MQLInfoInteger(MQL_TESTER)','MQLInfoInteger(MQL_OPTIMIZATION)','CopyTicksRange(sym,ticks,COPY_TICKS_ALL,(ulong)start,(ulong)end)','ticks[j].time_msc>to','CopyBuffer(handle,buffer,1,n,a)','CopyRates(sym,PERIOD_M5,1,350,rates)','if(!newbar)return','MODE_SMA,STO_LOWHIGH','K_PERIOD=5,D_PERIOD=3,SLOWING=3'):
            self.assertIn(required,s)

    def test_cli_end_to_end_and_final_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);csv=root/'events.csv';d=dataset();d.to_csv(csv,index=False)
            Path(str(csv)+'.audit.json').write_text(json.dumps(audit(len(d))))
            cmd=[sys.executable,str(ROOT/'python/validate_dataset.py'),str(csv)]
            subprocess.run(cmd,check=True,capture_output=True,text=True)
            cmd=[sys.executable,str(ROOT/'python/analyze_dataset.py'),str(csv),'--output',str(root/'report')]
            subprocess.run(cmd,check=True,capture_output=True,text=True)
            self.assertTrue((root/'report/TRAIN/summary.csv').exists())
            self.assertFalse((root/'report/FINAL_TEST').exists())
            summary=pd.read_csv(root/'report/TRAIN/summary.csv')
            self.assertEqual(int(summary.iloc[0].signals),60)
            result=subprocess.run(cmd[:-1]+[str(root/'locked'),'--evaluate','FINAL_TEST'],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            hypotheses=root/'hypotheses.md';hypotheses.write_text('Frozen synthetic test hypothesis; no market evidence.')
            subprocess.run(cmd[:-1]+[str(root/'final'),'--evaluate','FINAL_TEST','--unlock-final-test','--hypotheses-file',str(hypotheses)],check=True,capture_output=True,text=True)
            self.assertTrue((root/'final/FINAL_TEST/summary.csv').exists())

    def test_duplicate_csv_header_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'bad.csv';path.write_text('signal_id,signal_id\na,b\n')
            with self.assertRaises(ValueError):read_dataset(path)

if __name__=='__main__': unittest.main()
