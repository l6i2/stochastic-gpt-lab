"""Explicit research exporter allowlist and isolated evidence namespaces."""
BASE_EA = 'StochasticIntratradeResearchEA'
BAR_EA = 'StochasticBarDecisionResearchEA'
BASE_OUTPUTS = ('stochastic_events.csv', 'stochastic_events.csv.audit.json',
                'intratrade_snapshots.csv', 'intratrade_snapshot_targets.csv',
                'intratrade_snapshots.csv.audit.json')
PROFILES = {
    BASE_EA: dict(folder='StochasticIntratradeResearch', namespace='controller',
                  schema='2.0', outputs=BASE_OUTPUTS),
    BAR_EA: dict(folder='StochasticBarDecisionResearch', namespace='bar_controller',
                 schema='3.0', outputs=BASE_OUTPUTS + ('bar_execution_quotes.csv',)),
}


def profile(ea=BASE_EA):
    if ea not in PROFILES:
        raise RuntimeError('SECURITY_GATE: only explicitly allowed research exporters are supported')
    return PROFILES[ea]
