# Next intra-trade research proposal

**Decision: `NEXT_RESEARCH_FAMILY=NONE` for the current dataset and split.**

R2–R4 already covered adverse excursion/profit erosion, recovery, momentum and
Stochastic deterioration, volatility, session, and Volume Profile / POC
conditions. Sixteen frozen rules produced no survivor, with persistent
BUY/SELL and session inconsistency. Adding a new combination on the same TRAIN
folds would expand the adaptive search after seeing these results. A different
feature combination alone would not make the experiment methodologically
independent.

The TRAIN / Discovery Validation isolation incident is also unresolved. Keep
the existing Discovery Validation partition blocked. Do not evaluate a
candidate on it, reassign old observations, alter boundaries, or start another
TRAIN hypothesis round against the same outcomes.

## Prospective remediation before any new family

The only acceptable next research path proposed here is a new, forward-collected
cohort with a fresh preregistration and immutable source provenance. Before
collection begins, the protocol must fix the objective, inclusion rules,
feature whitelist, side-specific analysis, minimum support, time latency,
folds, multiplicity budget, success/failure criteria, and the untouched future
evaluation interval. The new cohort must not reuse the existing potentially
contaminated Validation rows as a clean holdout, and no existing split boundary
may be moved to improve results.

After the new data and audit trail exist, a distinct question could study
whether a small, prespecified market-state taxonomy changes the value of a
trajectory-based exit policy, with BUY and SELL evaluated independently. This
is only a candidate research direction, not a preregistered hypothesis or an
authorization to run. Regime definitions must be causal, low-dimensional, and
fixed before outcomes are observed. The policy must be compared against FOLLOW
HOLD, INVERT HOLD, and the fixed no-intervention baseline, across purged
chronological folds and latency sensitivity.

## Current gates

```text
NEW_ROUND=NOT_CREATED
NEW_HYPOTHESES=0
DISCOVERY_VALIDATION=BLOCKED
FINAL_TEST=LOCKED
DEMO=DISABLED
LIVE_TRADING=false
```

No human decision is requested now. Revisit only after the incident has a
documented, independently auditable remediation and the prospective protocol
can be frozen before any new outcomes are examined.
