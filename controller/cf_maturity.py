"""Frozen acquisition requirements; descriptive rates never authorize admission."""
def session_feasibility(schedule):
    """Conditional bounds from observed quote intervals, without an ETA."""
    capacities = [max(0,end//5-(start+4)//5)
                  for intervals in schedule['sessions']['QUOTE'].values()
                  for start,end in intervals]
    capacity = max(capacities,default=0)
    # At most one base signal per M5. The implementation allows a signal on
    # the warmup boundary itself. This is an optimistic bound, not a forecast.
    minimum_bars = 350-1+800+100
    runs = (minimum_bars+capacity-1)//capacity if capacity else None
    return dict(scope='CONDITIONAL_ON_OBSERVED_WEEKLY_QUOTE_METADATA',
                maximum_one_quote_run_m5=capacity,
                warmup_possible_without_session_bridge=capacity>=350,
                optimistic_minimum_total_m5=minimum_bars,
                minimum_quote_runs=runs,
                minimum_certified_bridges=runs-1 if runs else None,
                signal_frequency_demonstrated=False,calendar_eta=None,
                thresholds_modified=False,dataset_admitted=False)


def maturity(status):
    run=status.get('technical_warmup',0)
    signals=status.get('consecutive_signals',0)
    buy=status.get('BUY',0);sell=status.get('SELL',0)
    remaining=dict(warmup_m5=max(0,350-run),consecutive_signals=max(0,800-signals),
        post_m5=max(0,100-status.get('post_bars',0)),evaluable=max(0,200-status.get('evaluable',0)),
        BUY_evaluable=max(0,80-status.get('evaluable_BUY',0)),SELL_evaluable=max(0,80-status.get('evaluable_SELL',0)),
        BUY_folds=max(0,3-status.get('BUY_folds',0)),SELL_folds=max(0,3-status.get('SELL_folds',0)))
    return dict(requirements=dict(warmup_m5=350,signals=800,post_m5=100,evaluable=200,BUY=80,SELL=80,folds_each=3),
        remaining=remaining,technical_warmup=run,scientific_warmup=0,
        observed_market_bar_minutes=run*5,remaining_warmup_observed_bar_minutes=remaining['warmup_m5']*5,
        observed_signals_per_100_bars=(buy+sell)*100/run if run else None,
        rate_scope='DESCRIPTIVE_CURRENT_UNINTERRUPTED_CONTEXT_NOT_AN_INDEPENDENT_SAMPLE',
        calendar_eta=None,statistically_justified_eta=False,
        eta_reason='SESSION_TRANSITION_UNCERTIFIED_OR_SIGNAL_SAMPLE_IMMATURE_NO_CALENDAR_FORECAST',
        slowest_requirement='UNDETERMINED_SIGNAL_AND_COVERAGE_RATES_NOT_YET_ESTIMABLE',
        dataset_admitted=False,training_executed=False)
