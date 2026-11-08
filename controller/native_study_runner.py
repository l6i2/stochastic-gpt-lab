"""Prepared future native-study runner. No present scientific grant exists.

No CLI, auto-execution, historical file reader or admission mechanism. The grant
allowlist is deliberately empty. Only a later explicit scientific authorization
may publish a hash-bound grant; a caller-supplied boolean cannot enable a fit.
Current tests exercise refusal before loaders and preparation, never fitting.
"""
import math
import warnings
from .pretrain_contracts import FEATURES, seal
from .native_study_design import fold_plan
from .pretrain_model_preparation import prepare_unfitted

from .training_admission_gate import AUTHORIZED_GRANT_HASHES,authorize_execution,validate_observed_bounds,validate_observed_limits


def bootstrap_contrasts(rows, first_admitted_observed_bar, last_admitted_observed_bar):
    """Future-only paired signal and fixed 451-bar block sensitivity.

    Called only after future authorization. No files or estimator access.
    Blocks stay anchored to admitted origin; the final partial block is kept.
    Empty blocks between signals participate in block resampling. Samples with
    no observations and degenerate bootstrap distributions are inconclusive.
    """
    import numpy as np
    if not rows or len({r['signal_id'] for r in rows})!=len(rows):
        raise ValueError('EMPTY_OR_DUPLICATE_EVALUATION')
    if any(b['arrival_index']<=a['arrival_index'] for a,b in zip(rows,rows[1:])):
        raise ValueError('EVALUATION_MUST_KEEP_NATIVE_ORDER')
    if (type(first_admitted_observed_bar) is not int or type(last_admitted_observed_bar) is not int
        or first_admitted_observed_bar<0 or last_admitted_observed_bar<first_admitted_observed_bar or any(
        type(r['observed_bar_index']) is not int or not first_admitted_observed_bar<=r['observed_bar_index']<=last_admitted_observed_bar for r in rows)):
        raise ValueError('UNBOUND_OBSERVED_BAR_ORIGIN')
    def drawdown(values):
        curve=np.cumsum(values)
        return float(np.max(np.maximum.accumulate(np.r_[0.,curve])[1:]-curve))
    out=[]
    block_count=(last_admitted_observed_bar-first_admitted_observed_bar)//451+1
    for side in ('BUY','SELL'):
        selected=[r for r in rows if r['side']==side]
        if not selected:
            raise ValueError('MISSING_SIDE_IN_FUTURE_EVALUATION')
        for baseline in ('follow','invert'):
            d=np.array([r['candidate']-r[baseline] for r in selected],dtype=float)
            if not np.isfinite(d).all():
                raise ValueError('NONFINITE_PAIRED_DIFFERENCE')
            sums=np.zeros(block_count);counts=np.zeros(block_count,dtype=int)
            for r,v in zip(selected,d):
                j=(r['observed_bar_index']-first_admitted_observed_bar)//451
                sums[j]+=v;counts[j]+=1
            rng=np.random.default_rng(20261030)
            signal=[];block=[]
            for _ in range(10000):
                signal.append(float(d[rng.integers(0,len(d),len(d))].mean()))
                indices=rng.integers(0,block_count,block_count)
                denominator=counts[indices].sum()
                block.append(float(sums[indices].sum()/denominator) if denominator else float('nan'))
            fold_effects=[sum(v for r,v in zip(selected,d) if r['fold']==f) for f in sorted({r['fold'] for r in selected})]
            positive=sum(max(v,0) for v in fold_effects)
            valid=bool(np.isfinite(signal).all() and np.isfinite(block).all())
            out.append(dict(side=side,baseline=baseline,folds=len(fold_effects),bootstrap_valid=valid,
                degenerate=bool(np.ptp(signal)==0 or (valid and np.ptp(block)==0)),
                signal_ci95=[float(x) for x in np.quantile(signal,[.025,.975])],
                signal_lower_9875=float(np.quantile(signal,.0125)),
                block451_lower_9875=float(np.quantile(block,.0125)) if valid else None,
                positive_fold_fraction=sum(v>0 for v in fold_effects)/len(fold_effects),
                max_positive_fold_share=max([max(v,0) for v in fold_effects])/positive if positive else 1.,
                candidate_drawdown=drawdown([r['candidate'] for r in selected]),
                baseline_drawdown=drawdown([r[baseline] for r in selected]),
                bootstrap_resamples=10000,seed=20261030,block_size=451,block_count=block_count))
    return dict(n=len(rows),sides={s:sum(r['side']==s for r in rows) for s in ('BUY','SELL')},
                contrasts=out,integrity_and_causal_admission_verified=False)


def execute(grant, load_admitted_rows, claim_single_attempt, *, model_sink=None):
    """Future-only dependency-injected execution; fail closed before any I/O.

    A grant must bind rows, plan, code/environment, protocol, admission receipt,
    exposure and membership. Durable single-attempt claim precedes data access.
    Failed convergence/single class is terminal; there are no retries or tuning.
    """
    from pathlib import Path
    manifest=authorize_execution(grant,Path(__file__).resolve().parents[1])
    required={'study_id','dataset_hash','protocol_hash','feature_whitelist_hash',
              'membership_hash','exposure_hash','admission_receipt_hash','code_head',
              'environment_hash','row_schema','plan_hash','dataset_first_observed_bar',
              'manifest_path','manifest_sha256','max_fits'}
    if set(grant)!=required or grant['row_schema']!='native-study-admitted-rows/1':
        raise ValueError('INVALID_FUTURE_GRANT_SCHEMA')
    validate_observed_limits(grant['dataset_first_observed_bar'],manifest.get('dataset_last_observed_bar'))
    claim_single_attempt(seal(grant))  # Must be an exclusive durable claim; never auto retry.
    rows=load_admitted_rows(grant)
    if seal(rows)!=grant['dataset_hash']:
        raise ValueError('ADMITTED_DATASET_HASH_MISMATCH')
    validate_observed_bounds(rows,grant['dataset_first_observed_bar'],manifest.get('dataset_last_observed_bar'))
    metadata=[]
    for r in rows:
        if set(r)!={'signal_id','side','decision','arrival_index','follow_exit','invert_exit',
                    'features','follow_pnl','invert_pnl','observed_bar_index'}:
            raise ValueError('UNKNOWN_OR_MISSING_ROW_FIELDS')
        if set(r['features'])!=set(FEATURES):
            raise ValueError('FEATURE_WHITELIST_MISMATCH')
        metadata.append({k:r[k] for k in ('signal_id','side','decision','arrival_index','follow_exit','invert_exit')})
    plan=fold_plan(metadata)
    if seal(plan)!=grant['plan_hash']:
        raise ValueError('PURGED_PLAN_CHANGED')
    by_id={r['signal_id']:r for r in rows}
    prepared=[]
    for fold in plan['folds']:
        for side in ('BUY','SELL'):
            train=[by_id[i] for i in fold['train_ids'] if by_id[i]['side']==side]
            evaluation=[by_id[i] for i in fold['evaluation_ids'] if by_id[i]['side']==side]
            finite=lambda r:all(v is not None and math.isfinite(v) for v in r['features'].values())
            valid=[r for r in train if finite(r)]
            if not evaluation or not valid:
                raise ValueError('INSUFFICIENT_FOLD_SIDE_SUPPORT_NOT_RUN')
            for r in train+evaluation:
                if any(v is None or not math.isfinite(v) for v in (r['follow_pnl'],r['invert_pnl'])):
                    raise ValueError('MISSING_OR_NONFINITE_PAIRED_OUTCOME')
            y=[int(r['follow_pnl']-r['invert_pnl']>0) for r in valid]
            if len(set(y))!=2:
                raise ValueError('SINGLE_CLASS_NOT_RUN_NO_PARAMETER_CHANGE')
            prepared.append((fold['fold'],side,valid,evaluation,y,[r for r in evaluation if finite(r)]))
    if len(prepared)>grant['max_fits']:
        raise ValueError('FIT_BUDGET_EXCEEDED_BEFORE_FIT')
    evaluation_counts={side:sum(len(evaluation) for _,group,_,evaluation,_,_ in prepared if group==side)
                       for side in ('BUY','SELL')}
    if sum(evaluation_counts.values())<200 or any(n<80 for n in evaluation_counts.values()):
        raise ValueError('INSUFFICIENT_PURGED_EVALUATION_SUPPORT_BEFORE_FIT')

    from sklearn.exceptions import ConvergenceWarning
    result=[]
    fit_count=0
    frozen_models={}
    for fold_number,side,valid,evaluation,y,good in prepared:
        estimator,_=prepare_unfitted(side)
        with warnings.catch_warnings():
            warnings.simplefilter('error',ConvergenceWarning)
            estimator.fit([[r['features'][f] for f in FEATURES] for r in valid],y)
        fit_count+=1
        if fold_number==4:
            frozen_models[side]=estimator
        probability={r['signal_id']:float(p[1]) for r,p in zip(good,
            estimator.predict_proba([[r['features'][f] for f in FEATURES] for r in good]))} if good else {}
        for r in evaluation:
            p=probability.get(r['signal_id'])
            follow=p is None or p>0.5
            result.append(dict(signal_id=r['signal_id'],side=side,fold=fold_number,
                observed_bar_index=r['observed_bar_index'],arrival_index=r['arrival_index'],
                probability=p,missing_features=p is None,action='FOLLOW' if follow else 'INVERT',
                candidate=r['follow_pnl'] if follow else r['invert_pnl'],
                follow=r['follow_pnl'],invert=r['invert_pnl']))
    # Preserve original chronology for drawdown and paired block resampling.
    result.sort(key=lambda r:r['arrival_index'])
    if model_sink is not None:
        model_sink(frozen_models,dict(selected_fold=4,selection='PREREGISTERED_LAST_FOLD_NOT_PERFORMANCE',
            grant_sha256=seal(grant),feature_order=list(FEATURES),fits=fit_count,additional_fits=0))
    return dict(rows=result,fits=fit_count,final_full_fit=False,attempt_terminal=True,
                missing_train_rows_retained_in_original_dataset=True,all_gates_unchanged=True)


def acceptance(metrics):
    """Validate a future computed four-contrast report; no data/PnL reader.

    Unknown, degenerate or statistically invalid results cannot pass. Raw
    bootstrap computation must be independently validated before a future grant.
    """
    expected={(s,b) for s in ('BUY','SELL') for b in ('follow','invert')}
    rows=metrics['contrasts']
    if len(rows)!=4 or {(r['side'],r['baseline']) for r in rows}!=expected:
        raise ValueError('ALL_FOUR_UNIQUE_CONTRASTS_REQUIRED')
    if metrics['n']<200 or any(metrics['sides'][s]<80 for s in ('BUY','SELL')):
        return 'NOT_READY'
    if not metrics['integrity_and_causal_admission_verified']:
        return 'REJECTED'
    for r in rows:
        if r['folds']<3 or not r['bootstrap_valid'] or r['degenerate']:
            return 'INCONCLUSIVE'
        values=[r[k] for k in ('signal_lower_9875','block451_lower_9875',
            'positive_fold_fraction','max_positive_fold_share','candidate_drawdown','baseline_drawdown')]
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in values):
            return 'INCONCLUSIVE'
        if r['candidate_drawdown']<0 or r['baseline_drawdown']<0:
            raise ValueError('DRAWDOWN_MUST_BE_NONNEGATIVE_MAGNITUDE')
        if (r['signal_lower_9875']<=0 or r['block451_lower_9875']<=0 or
            r['positive_fold_fraction']<0.7 or r['max_positive_fold_share']>0.5 or
            r['candidate_drawdown']>1.2*r['baseline_drawdown']):
            return 'FAIL'
    return 'PASS_INTERNAL_RESEARCH_ONLY'
