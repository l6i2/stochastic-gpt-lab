#!/usr/bin/env python3
"""Descriptive TRAIN analysis; no threshold search, trading rules or optimization."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from heikin_ashi import HA_COLUMNS
from research import (FEATURE_COLUMNS, PROFILE_PREFIXES, chronological_split,
                      purge_at_boundary, read_dataset, validate, walk_forward)

GROUP_FEATURES = ['volume_percentile_20','volume_percentile_50','volume_percentile_100',
                 'relative_volume_5','relative_volume_10','relative_volume_20','relative_volume_50','relative_volume_100',
                 'volume_expansion','ATR_percentile_20','ATR_percentile_50','ATR_percentile_100',
                 *[p+'distance_price_to_'+v for p in PROFILE_PREFIXES for v in ('POC','VAH','VAL')]] + ['ha_body_expansion']


def fit_deciles(train):
    # Edges depend only on TRAIN features; repeated values reduce the number of bins.
    edges={}
    for column in GROUP_FEATURES:
        if column not in train: continue
        values=train[column].dropna()
        edges[column]=np.unique(values.quantile(np.linspace(.1,.9,9)).to_numpy()).tolist() if len(values) else []
    return edges


def bins(values, edges):
    if not edges: return pd.Series('unavailable',index=values.index)
    out=pd.Series(np.searchsorted(edges,values.to_numpy(),side='left')+1,index=values.index).astype(str)
    out[values.isna()]='missing'
    return out


def stats(df):
    pair=df.follow_PnL.notna()&df.invert_PnL.notna()
    d=df.loc[pair]
    result={'signals':len(df),'complete_pairs':len(d),'censored_pairs':int((~pair).sum()),
            'follow_complete':int(df.follow_PnL.notna().sum()),'invert_complete':int(df.invert_PnL.notna().sum()),
            'follow_mean_available':df.follow_PnL.mean(),'invert_mean_available':df.invert_PnL.mean(),
            'follow_mean_paired':d.follow_PnL.mean(),'invert_mean_paired':d.invert_PnL.mean(),
            'directional_advantage_mean':d.directional_advantage.mean(),
            'directional_advantage_median':d.directional_advantage.median(),
            'follow_win_rate_paired':(d.follow_PnL>0).mean() if len(d) else np.nan,
            'invert_win_rate_paired':(d.invert_PnL>0).mean() if len(d) else np.nan,
            'advantage_ties':int(d.directional_advantage.eq(0).sum())}
    for side in ('follow','invert'):
        result[side+'_losses']=int((df[side+'_PnL']<0).sum())
        result[side+'_ties']=int(df[side+'_PnL'].eq(0).sum())
        result[side+'_MFE_mean']=df.loc[df[side+'_PnL'].notna(),side+'_MFE'].mean()
        result[side+'_MAE_mean']=df.loc[df[side+'_PnL'].notna(),side+'_MAE'].mean()
    return result


def report(df, edges, folder):
    folder.mkdir(parents=True,exist_ok=False)
    populations={'ALL':df,'BUY':df[df.follow_side.eq('BUY')],'SELL':df[df.follow_side.eq('SELL')]}
    pd.DataFrame([{'population':name,**stats(d)} for name,d in populations.items()]).to_csv(folder/'summary.csv',index=False)
    groups=[]; correlations=[]
    for population,d in populations.items():
        for feature in list(edges)+['NY_hour','trend_alignment']:
            if feature=='NY_hour': group=d.NY_hour.astype(str)
            elif feature=='trend_alignment':
                group=pd.Series(np.select([d.bull_alignment.eq(1),d.bear_alignment.eq(1)],['bull','bear'],default='mixed'),index=d.index)
                group[d.bull_alignment.isna()|d.bear_alignment.isna()]='missing'
            else: group=bins(d[feature],edges[feature])
            for label,index in group.groupby(group).groups.items():
                groups.append({'population':population,'feature':feature,'bin':label,**stats(d.loc[index])})
        for feature in [c for c in FEATURE_COLUMNS if c in d]:
            for outcome in ('follow_PnL','invert_PnL','directional_advantage'):
                pair=d[[feature,outcome]].dropna()
                pearson=spearman=np.nan
                if len(pair)>2 and pair[feature].nunique()>1 and pair[outcome].nunique()>1:
                    pearson=pair[feature].corr(pair[outcome])
                    spearman=pair[feature].rank().corr(pair[outcome].rank())
                correlations.append({'population':population,'feature':feature,'outcome':outcome,'n':len(pair),'pearson':pearson,'spearman':spearman})
    pd.DataFrame(groups).to_csv(folder/'groups.csv',index=False)
    pd.DataFrame(correlations).to_csv(folder/'correlations.csv',index=False)
    # All causal numeric features get descriptive deciles, independently of outcome.
    df[[c for c in FEATURE_COLUMNS if c in df]].quantile(np.linspace(0,1,11)).rename_axis('quantile').to_csv(folder/'feature_deciles.csv')
    df[[c for c in FEATURE_COLUMNS if c in df]].isna().mean().rename('missing_fraction').to_csv(folder/'missingness.csv')
    ha_interactions(df, edges, folder)
    pd.DataFrame({s:df[s+'_exit_reason'].value_counts() for s in ('follow','invert')}).fillna(0).to_csv(folder/'exit_reasons.csv')



def ha_interactions(df, edges, folder):
    """Fixed small set of descriptive pairs. No Cartesian search or rule selection."""
    if not set(HA_COLUMNS).issubset(df.columns):
        return  # schema 1.0 remains readable; HA cannot be reconstructed from signal rows
    direction=df.ha_direction.map({1:'bullish', -1:'bearish', 0:'doji'}).fillna('missing')
    streak=df.ha_consecutive_bullish.fillna(0)-df.ha_consecutive_bearish.fillna(0)
    # Fixed short/medium/long run descriptions, not fitted thresholds.
    streak_group=pd.Series(np.select([streak.abs().eq(0),streak.abs().eq(1),streak.abs().between(2,3),streak.abs().between(4,7)],['0','1','2-3','4-7'],default='8+'),index=df.index)
    streak_group=direction+':'+streak_group
    transition=pd.Series(np.select([df.ha_changed_to_bullish.eq(1),df.ha_changed_to_bearish.eq(1),df.ha_direction.eq(0)],['to_bullish','to_bearish','doji'],default='unchanged'),index=df.index)
    strength=pd.Series(np.select([df.ha_bullish_strong.eq(1),df.ha_bearish_strong.eq(1),df.ha_indecision.eq(1)],['bullish_strong','bearish_strong','indecision'],default='other'),index=df.index)
    for series in (streak_group, transition, strength):
        series.loc[~df.ha_status.eq('ready')]='missing'
    pairs=[('ha_direction','signal_original',direction,df.follow_side),
           ('ha_direction','relative_volume_20',direction,bins(df.relative_volume_20,edges['relative_volume_20'])),
           ('ha_streak','relative_volume_20',streak_group,bins(df.relative_volume_20,edges['relative_volume_20'])),
           ('ha_body_expansion','volume_expansion',bins(df.ha_body_expansion,edges['ha_body_expansion']),bins(df.volume_expansion,edges['volume_expansion'])),
           ('ha_transition','volume_percentile_20',transition,bins(df.volume_percentile_20,edges['volume_percentile_20'])),
           ('ha_strength','ATR_percentile_20',strength,bins(df.ATR_percentile_20,edges['ATR_percentile_20']))]
    for prefix in PROFILE_PREFIXES:
        for level in ('POC','VAH','VAL'):
            feature=prefix+'distance_price_to_'+level
            pairs.append(('ha_direction',feature,direction,bins(df[feature],edges[feature])))
        state=pd.Series(np.select([df[prefix+'inside_value_area'].eq(1),df[prefix+'above_value_area'].eq(1),df[prefix+'below_value_area'].eq(1)],['inside','above','below'],default='missing'),index=df.index)
        pairs.append(('ha_transition',prefix+'value_area_state',transition,state))
    rows=[]
    for population, subset in [('ALL',df),('BUY',df[df.follow_side.eq('BUY')]),('SELL',df[df.follow_side.eq('SELL')])]:
        for left_name,right_name,left,right in pairs:
            groups=pd.DataFrame({'left':left.loc[subset.index],'right':right.loc[subset.index]})
            for (a,b),index in groups.groupby(['left','right'],dropna=False).groups.items():
                rows.append({'population':population,'ha_feature':left_name,'context_feature':right_name,
                             'ha_group':a,'context_group':b,**stats(subset.loc[index])})
    pd.DataFrame(rows).to_csv(folder/'ha_interactions.csv',index=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dataset',type=Path); p.add_argument('--output',type=Path,default=Path('outputs/analysis'))
    p.add_argument('--train',type=float,default=.6);p.add_argument('--validation',type=float,default=.2)
    p.add_argument('--evaluate',choices=['TRAIN','DISCOVERY_VALIDATION','FINAL_TEST'],default='TRAIN')
    p.add_argument('--hypotheses-file',type=Path,help='Frozen TRAIN hypotheses required for evaluation; hashed into manifest')
    p.add_argument('--unlock-final-test',action='store_true',help='Explicit one-time held-out evaluation')
    p.add_argument('--walk-forward',action='store_true');p.add_argument('--wf-initial',type=int,default=200);p.add_argument('--wf-step',type=int,default=100)
    args=p.parse_args()
    try:
        if args.output.exists(): raise ValueError('Output directory exists; choose a new run directory')
        if args.evaluate!='TRAIN' and not args.hypotheses_file:
            raise ValueError('Evaluation requires --hypotheses-file with frozen TRAIN hypotheses')
        if args.evaluate=='FINAL_TEST' and not args.unlock_final_test:
            raise ValueError('FINAL_TEST is locked; explicit --unlock-final-test required')
        if args.walk_forward and args.evaluate!='TRAIN': raise ValueError('Walk-forward is a discovery operation; use TRAIN')
        hypotheses=None
        if args.hypotheses_file:
            raw=args.hypotheses_file.read_bytes()
            if not raw.strip(): raise ValueError('Hypotheses file must not be empty')
            hypotheses=hashlib.sha256(raw).hexdigest()
        df=read_dataset(args.dataset)
        audit=json.loads(Path(str(args.dataset)+'.audit.json').read_text())
        errors=validate(df,audit)
        if errors: raise ValueError('; '.join(errors))
        parts=chronological_split(df,args.train,args.validation)
        validation_start=int(parts['DISCOVERY_VALIDATION'].signal_time_msc.iloc[0]);test_start=int(parts['FINAL_TEST'].signal_time_msc.iloc[0])
        train,purged_train=purge_at_boundary(parts['TRAIN'],validation_start)
        discovery,purged_validation=purge_at_boundary(parts['DISCOVERY_VALIDATION'],test_start)
        if train.empty: raise ValueError('TRAIN empty after purging overlapping labels; use more history')
        edges=fit_deciles(train)
        selected={'TRAIN':train,'DISCOVERY_VALIDATION':discovery,'FINAL_TEST':parts['FINAL_TEST']}[args.evaluate]
        if selected.empty: raise ValueError('Selected partition empty after purging')
        args.output.mkdir(parents=True)
        manifest={'schema_version':str(df.schema_version.iloc[0]),'dataset_sha256':hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
                  'fractions':{'TRAIN':args.train,'DISCOVERY_VALIDATION':args.validation,'FINAL_TEST':1-args.train-args.validation},
                  'counts':{k:len(v) for k,v in parts.items()},'validation_start_msc':validation_start,'final_test_start_msc':test_start,
                  'purged_train':purged_train,'purged_validation':purged_validation,'evaluated':args.evaluate,
                  'hypotheses_sha256':hypotheses,'decile_edges_fitted_on':'TRAIN','decile_edges':edges,
                  'warning':'Descriptive associations only. Overlapping trades are dependent; no threshold optimization or significance claims.'}
        (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
        if args.hypotheses_file: (args.output/'frozen_hypotheses.txt').write_bytes(args.hypotheses_file.read_bytes())
        report(selected,edges,args.output/args.evaluate)
        if args.walk_forward:
            # The FINAL_TEST partition never enters any fold. Purge last fold at its boundary too.
            pool=pd.concat([parts['TRAIN'],parts['DISCOVERY_VALIDATION']])
            count=0
            for i,(training,validation,meta) in enumerate(walk_forward(pool,args.wf_initial,args.wf_step),1):
                validation,last_purged=purge_at_boundary(validation,test_start);meta['final_boundary_purged']=last_purged
                if training.empty or validation.empty: continue
                fold=args.output/f'walk_forward_{i:03d}';fold.mkdir()
                fold_edges=fit_deciles(training)
                report(training,fold_edges,fold/'TRAIN');report(validation,fold_edges,fold/'DISCOVERY_VALIDATION')
                (fold/'manifest.json').write_text(json.dumps({**meta,'edges':fold_edges,'training_signals':len(training),'validation_signals':len(validation)},indent=2)+'\n');count+=1
            if count==0: raise ValueError('No nonempty walk-forward folds after purging; adjust sizes or add history')
        print(f'Descriptive {args.evaluate} report: {args.output}. FINAL_TEST '+('explicitly evaluated.' if args.evaluate=='FINAL_TEST' else 'not explored.'))
        return 0
    except (ValueError,OSError,ImportError,KeyError,TypeError) as exc:
        print(f'Analysis failed: {exc}',file=sys.stderr);return 1


if __name__=='__main__': raise SystemExit(main())
