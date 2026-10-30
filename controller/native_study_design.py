"""Pure planning of the proposed four chronological folds; never fits or scores.

Only supplied membership/horizon metadata are processed. No dataset path, price,
feature matrix, PnL, target value or active gate is consumed or returned.
"""


def fold_plan(signals):
    if len(signals) < 8:
        raise ValueError('INSUFFICIENT_STRUCTURAL_FOLD_SUPPORT')
    required = {'signal_id','side','decision','arrival_index','follow_exit','invert_exit'}
    seen = set()
    previous = (-1,-1)
    for s in signals:
        if set(s) != required or s['side'] not in ('BUY','SELL') or not isinstance(s['signal_id'],str) or not s['signal_id'] or s['signal_id'] in seen:
            raise ValueError('INVALID_OR_DUPLICATE_MEMBERSHIP')
        if any(type(s[k]) is not int or s[k]<0 for k in ('decision','arrival_index')):
            raise ValueError('INVALID_NATIVE_POSITION')
        position = (s['decision'],s['arrival_index'])
        if position <= previous or s['arrival_index'] <= previous[1]:
            raise ValueError('NONCHRONOLOGICAL_INPUT_NO_CORRECTIVE_SORT')
        previous = position
        seen.add(s['signal_id'])
        for k in ('follow_exit','invert_exit'):
            if s[k] is not None and (type(s[k]) is not int or s[k] < s['decision']):
                raise ValueError('INVALID_LABEL_HORIZON')
    n = len(signals)
    initial = n//2
    bounds = [initial+j*(n-initial)//4 for j in range(5)]

    def complete_before(s, boundary):
        exits = [s['follow_exit'],s['invert_exit']]
        return all(x is not None for x in exits) and (boundary is None or max(exits) < boundary)

    folds=[]
    for j in range(4):
        start, end=bounds[j:j+2]
        cutoff=signals[start]['decision']
        next_cutoff=signals[end]['decision'] if end<n else None
        train=[s['signal_id'] for s in signals[:start] if complete_before(s,cutoff)]
        evaluation=[s['signal_id'] for s in signals[start:end] if complete_before(s,next_cutoff)]
        folds.append(dict(fold=j+1,train_ids=train,evaluation_ids=evaluation,
                          purged_or_censored_train=start-len(train),
                          purged_or_censored_evaluation=end-start-len(evaluation),
                          evaluation_decision_start=cutoff,next_boundary=next_cutoff,
                          evaluation_sides={side:sum(s['signal_id'] in evaluation and s['side']==side for s in signals[start:end]) for side in ('BUY','SELL')}))
    return dict(folds=folds, internal_validation_only=True, training_authorized=False,
                scoring_authorized=False, scientific_support_gate='NOT_EVALUATED')
