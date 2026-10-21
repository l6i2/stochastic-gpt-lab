# TRAIN V2 family failure analysis

**Recorded:** 2026-10-21  
**Scope:** the single preregistered `HV2_ENTRY_SPREAD_ATR_ROUTER` rule on quality-v1 TRAIN.  
**Evidence:** [`TRAIN_V2_LOW_MEMORY_BENCHMARK.md`](TRAIN_V2_LOW_MEMORY_BENCHMARK.md) and its hash-bound result `outputs/bar_controller/research/train_entry_spread_atr_router.json` (SHA-256 `f18eeb27950c0d9fec01de0a49d669b604381d8c94f9356b67c1dfb5840d987`).

## Decision

```text
HYPOTHESIS_STATUS=REJECTED_FINAL_FOR_THIS_PREREGISTRATION
FAILURE_ANALYSIS=COMPLETE
NEXT_RESEARCH_FAMILY=NONE_ON_CURRENT_TRAIN
NEW_HYPOTHESES=0
DISCOVERY_VALIDATION=BLOCKED
FINAL_TEST=LOCKED
DEMO=DISABLED
LIVE_TRADING=false
```

The result rejects this frozen entry-friction router. It does not establish that spread or volatility has no predictive relationship in every population. A BUY-only story would be a post-result subgroup selection, and SELL did not meet the preregistered consistency gates. Neither is eligible for rescue or threshold changes.

## Gate diagnosis

| Question | Frozen result | Interpretation |
|---|---|---|
| BUY support | 3,641 signals; support gate passed | Low sample count did not cause the BUY failure. |
| BUY by fold | 3/4 positive (75%); fold concentration 35.8% | Both preregistered fold checks passed. This is insufficient by itself. |
| BUY by source block | 2 positive groups; largest share 79.7% | Failed the ≤50% concentration gate; effect was concentrated in one block. |
| BUY by session | 3 positive groups; largest share 70.1% | Failed the ≤50% concentration gate; not session-distributed. |
| SELL support | 4,036 signals; support gate passed | Low aggregate support did not cause the SELL failure. |
| SELL by fold | 2/4 positive (50%) | Failed the 70% minimum. Fold deltas also changed sign, so the side-specific policy is unstable. |
| SELL fold concentration | Largest positive-fold share 69.5% | Failed the ≤50% gate. |
| 25/75 robustness | BUY sign stable; SELL sign unstable | SELL fails the frozen quantile sensitivity diagnostic. No threshold sweep or replacement threshold was selected. |
| Latency 0/250/500 ms | BUY means 2.514/2.490/2.520; SELL 2.345/2.353/2.345 | Both sides passed the preregistered latency stability check. Latency is not the failure cause. |
| Month dependence | No separate month-level gate/report was produced for this V2 family | Month concentration is unknown for this result; it must not be retroactively inferred from block/session diagnostics. |
| Drawdown proxy | −37,092.63 vs −42,263.14 for the selected better fixed baseline | Passed the defined proxy gate. This is not account-level drawdown and does not compensate for concentration or instability failures. |
| Uncertainty | Signal-clustered intervals: BUY [−2.85, 7.75], SELL [−0.81, 5.69] | Both include zero; the observed effects do not establish a positive effect with this uncertainty measure. |

## Structural versus subgroup interpretation

The **preregistered router as a whole fails structurally as a deployable research candidate**: it does not satisfy side-specific robustness, and both side intervals include zero. The clearest subgroup issue is that BUY passes its fold/latency checks but fails independent block and session concentration. SELL independently fails fold direction, fold concentration, and 25/75 sensitivity. These are different failure modes, not grounds to retain the passing subset after observing results.

The source-block and session failures indicate dependence on particular portions of the observed sample. The current evidence does not identify a causal market regime explaining them. No post-hoc regime, month, or session rule is justified.

## Why no next family is registered on this TRAIN

R2–R4 already tested frozen intra-trade rules covering MAE recovery, TP proximity, low relative volume after favorable excursion, POC crossing, adverse EMA/structure, fixed loss duration, realized-volatility contraction, and HA/Stochastic/volume/profile/session conditions. All 16 were rejected on TRAIN. The V2 entry-friction router is the seventeenth tested hypothesis and is also rejected.

Although some feature combinations remain imaginable, defining another same-TRAIN family after these outcomes would increase adaptive reuse of the same observations. It would not be scientifically independent merely because its labels or thresholds differed. The unresolved isolation incident further blocks use of the existing Discovery Validation split. Therefore no new hypotheses are created, ranked, or scored in this round. The methodologically defensible next step is a separately preregistered prospective cohort analysis after the fixed cohort protocol matures; until then, the cohort remains unscored and candidate-free.

This conclusion preserves the existing cohort start rule and split boundaries. It does not authorize Discovery Validation, FINAL_TEST, Demo, or live execution.
