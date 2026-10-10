"""Schema for the causal HEIKIN_ASHI family (calculated by the EA)."""
HA_COLUMNS = [
    'ha_open', 'ha_high', 'ha_low', 'ha_close', 'ha_direction',
    'ha_body', 'ha_range', 'ha_body_percent', 'ha_upper_wick', 'ha_lower_wick',
    'ha_upper_wick_to_range', 'ha_lower_wick_to_range',
    *[f'ha_delta_close_{n}' for n in (1, 2, 3)],
    *[f'ha_delta_body_{n}' for n in (1, 2, 3)],
    'ha_body_expansion', 'ha_range_expansion',
    'ha_consecutive_bullish', 'ha_consecutive_bearish',
    *[f'ha_bullish_ratio_{n}' for n in (3, 5, 10, 20)],
    *[f'ha_bearish_ratio_{n}' for n in (3, 5, 10, 20)],
    *[f'ha_avg_body_{n}' for n in (3, 5, 10, 20)],
    *[f'ha_avg_range_{n}' for n in (3, 5, 10, 20)],
    'ha_body_vs_avg5', 'ha_body_vs_avg10',
    'ha_range_vs_avg5', 'ha_range_vs_avg10',
    'ha_no_lower_wick', 'ha_no_upper_wick', 'ha_small_body',
    'ha_bullish_strong', 'ha_bearish_strong', 'ha_indecision',
    'ha_changed_to_bullish', 'ha_changed_to_bearish',
    'ha_bullish_after_bearish_run', 'ha_bearish_after_bullish_run',
    'ha_bullish_run_before_signal', 'ha_bearish_run_before_signal',
]
HA_METADATA = ['ha_status', 'ha_seed_bar_open', 'ha_last_bar_open',
               'ha_bars_processed', 'ha_warmup_bars', 'ha_streak_left_censored']
HA_WARMUP = 256
HA_READY_BARS = HA_WARMUP + 20


def validate_ha(df):
    """Row invariants; sequential recurrence is tested on the shared native core."""
    import numpy as np
    errors = []
    def check(ok, message):
        if not bool(ok): errors.append('HEIKIN_ASHI: ' + message)
    def equal(a, b):
        return np.allclose(a, b, atol=1e-8, rtol=1e-9, equal_nan=True)
    check(df.ha_status.isin(['ready', 'warming_up', 'unavailable']).all(), 'invalid status')
    check(df.ha_warmup_bars.eq(HA_WARMUP).all(), 'invalid warmup')
    check((df.ha_seed_bar_open <= df.ha_last_bar_open).all(), 'seed after last bar')
    check(((df.ha_last_bar_open + 300)*1000-1 <= df.signal_time_msc).all(), 'future/open HA bar')
    check((df.ha_last_bar_open < df.entry_bar_open).all(), 'entry bar used as HA feature')
    check(df.ha_streak_left_censored.isin([0, 1]).all(), 'invalid streak censor flag')
    ready = df.ha_status.eq('ready')
    d = df[ready]
    check(d.ha_last_bar_open.eq(d.signal_bar_open).all(), 'HA not aligned with signal bar')
    check(d.ha_bars_processed.ge(HA_READY_BARS).all(), 'not enough prehistory')
    check(df.loc[df.ha_status.eq('warming_up'), 'ha_bars_processed'].lt(HA_READY_BARS).all(), 'incorrect warmup status')
    check(df.loc[~ready, HA_COLUMNS].isna().all().all(), 'unready values must be missing')
    required = [c for c in HA_COLUMNS if c not in [
        'ha_body_percent', 'ha_upper_wick_to_range', 'ha_lower_wick_to_range',
        'ha_body_expansion', 'ha_range_expansion', 'ha_body_vs_avg5',
        'ha_body_vs_avg10', 'ha_range_vs_avg5', 'ha_range_vs_avg10']]
    check(d[required].notna().all().all(), 'missing ready values')
    check(equal(d.ha_close, (d.open+d.high+d.low+d.close)/4), 'HA close formula')
    check(equal(d.ha_high, np.maximum(d.high, np.maximum(d.ha_open,d.ha_close))), 'HA high formula')
    check(equal(d.ha_low, np.minimum(d.low, np.minimum(d.ha_open,d.ha_close))), 'HA low formula')
    check(equal(d.ha_body, abs(d.ha_close-d.ha_open)), 'body formula')
    check(equal(d.ha_range, d.ha_high-d.ha_low), 'range formula')
    check(equal(d.ha_direction, np.sign(d.ha_close-d.ha_open)), 'direction formula')
    check(equal(d.ha_upper_wick, d.ha_high-np.maximum(d.ha_open,d.ha_close)), 'upper wick')
    check(equal(d.ha_lower_wick, np.minimum(d.ha_open,d.ha_close)-d.ha_low), 'lower wick')
    denom = d.ha_range.replace(0, np.nan)
    check(equal(d.ha_body_percent, 100*d.ha_body/denom), 'body percent')
    check(equal(d.ha_upper_wick_to_range, d.ha_upper_wick/denom), 'upper ratio')
    check(equal(d.ha_lower_wick_to_range, d.ha_lower_wick/denom), 'lower ratio')
    no_lower=d.ha_lower_wick.le(1e-10); no_upper=d.ha_upper_wick.le(1e-10)
    small=d.ha_range.gt(0)&d.ha_body.le(.25*d.ha_range)
    for name, expected in {
        'ha_no_lower_wick': no_lower, 'ha_no_upper_wick': no_upper,
        'ha_small_body': small,
        'ha_bullish_strong': d.ha_direction.eq(1)&no_lower&d.ha_body.ge(.5*d.ha_range),
        'ha_bearish_strong': d.ha_direction.eq(-1)&no_upper&d.ha_body.ge(.5*d.ha_range),
        'ha_indecision': small&~no_lower&~no_upper,
        'ha_bullish_after_bearish_run': d.ha_direction.eq(1)&d.ha_bearish_run_before_signal.gt(0),
        'ha_bearish_after_bullish_run': d.ha_direction.eq(-1)&d.ha_bullish_run_before_signal.gt(0),
        'ha_changed_to_bullish': d.ha_direction.eq(1)&d.ha_bullish_run_before_signal.eq(0),
        'ha_changed_to_bearish': d.ha_direction.eq(-1)&d.ha_bearish_run_before_signal.eq(0),
    }.items():
        check(equal(d[name], expected.astype(int)), name+' formula')
    for side, direction in [('bullish',1),('bearish',-1)]:
        run=d['ha_consecutive_'+side]; prior=d['ha_'+side+'_run_before_signal']
        check(equal(run, np.where(d.ha_direction.eq(direction), prior+1, 0)), side+' streak recurrence')
        check(((prior>=0)&(prior<d.ha_bars_processed)&(prior%1==0)).all(), side+' invalid prior streak')
        for n in (3,5,10,20):
            check(d[f'ha_{side}_ratio_{n}'].between(0,1).all(), side+' ratio range')
    for n in (3,5,10,20):
        check((d[f'ha_bullish_ratio_{n}']+d[f'ha_bearish_ratio_{n}']<=1+1e-9).all(), 'direction ratios sum')
        check(d[f'ha_avg_body_{n}'].ge(0).all() and d[f'ha_avg_range_{n}'].ge(0).all(), 'negative mean')
    return errors
