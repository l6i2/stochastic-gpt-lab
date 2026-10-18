# R2–R4 TRAIN failure analysis

**Scope:** 16 frozen hypotheses, four chronological purged TRAIN folds per
hypothesis, 250 ms primary latency, and 0 / 250 / 500 ms sensitivity. This is
an after-the-fact diagnostic of the already completed TRAIN results; it was not
used to alter a definition, threshold, ranking, or decision. Discovery
Validation and FINAL_TEST are excluded. See
[`ISOLATION_INCIDENT_AUDIT.md`](ISOLATION_INCIDENT_AUDIT.md) for the unresolved
source-provenance limitation.

## Gate failure counts

| Preregistered gate | Hypotheses failing (of 16) | Interpretation |
|---|---:|---|
| Trigger support | 1 | R4-002 produced zero triggers; remaining 15 met the aggregate minimum. |
| Trigger prevalence | 1 | Same zero-trigger R4-002 rule. |
| Overall walk-forward consistency / concentration | 14 | Most rules were not positive and sufficiently distributed across the four folds. A positive pooled mean alone did not pass. |
| Both-side walk-forward | 16 | Every rule failed at least one BUY or SELL support / consistency / concentration condition. |
| Latency robustness | 4 | R2-001, R2-002, R4-001, and R4-002 failed the fixed 0/250/500 ms stability rule. |
| Drawdown proxy | 0 | None breached the predefined relative drawdown gate. This proxy is not a full account-level drawdown model. |
| Multiple source blocks | 6 | Positive effect was not demonstrated across enough eligible source blocks. |
| Multiple sessions | 16 | No rule met the minimum positive-session count and concentration limit. |

## Failure patterns

- **Fold instability:** 14/16 failed the overall fold consistency/concentration
  gate. Apparent pooled gains were often carried by too few folds. The strongest
  examples still failed independent checks: R3-001 was positive in all four
  overall folds but failed SELL consistency and session concentration; R4-003
  was positive in all four overall folds but failed side and session gates.
- **BUY / SELL disagreement:** all 16 failed the combined side-specific gate.
  R3-001 was positive for BUY in 4/4 folds but SELL in 2/4; R4-003 SELL was
  positive in 2/4. Several R2 policies had only 2/4 positive folds on each
  side. These are not accepted as a common policy edge.
- **Session dependence:** all 16 failed the predeclared multi-session gate.
  For R3-001, New York supplied 55% of positive session-level change, above the
  50% cap. The other policies did not demonstrate the required distributed
  supported-session gains.
- **Source-block dependence:** six failed the multi-block gate. This indicates
  weak transfer across eligible year/source blocks even where aggregate
  trigger support was adequate.
- **Latency sensitivity:** four failed the fixed latency gate. The others
  passed this specific sensitivity test; that does not rescue their fold,
  side, or session failures.
- **Sample support:** 15/16 met the aggregate trigger minimum. R4-002 had zero
  triggers and is a feature/support failure, not evidence of a null effect at
  adequate sample size. Side and per-fold support was a separate limiting gate
  for multiple otherwise frequent rules.
- **Month concentration:** a descriptive diagnostic grouped the 250 ms paired
  deltas by UTC signal month across the available 20 eligible months. Per rule,
  positive-month counts ranged from 0/20 (R4-002) to 14/20 (R3-003 and
  R4-004); most rules were positive in only 10–14 months, with negative monthly
  means still present. Monthly stability was not a preregistered gate and these
  counts were not used to choose among rules. They reinforce the already
  observed temporal instability but are exploratory.
- **Threshold fragility:** no threshold sweep was performed, by design. Each
  rule used one frozen definition. Therefore threshold sensitivity is
  **untested**, not passed. No threshold may be adjusted using these results.
- **Drawdown:** all 16 passed the existing drawdown-proxy gate. It cannot offset
  the other failed gates, and the proxy is not equivalent to portfolio sizing,
  capital, or account drawdown.

## Round-specific context

R2's largest reported pooled change was HYP R2-006 at +1.689 price units per
signal versus FOLLOW HOLD; it failed fold, side, and session robustness. R2-005
was positive in all four overall folds (+0.582) but did not pass side/session
robustness. R3-001 had +1.084 mean paired change versus FOLLOW HOLD, but its
SELL and session checks failed and its policy portfolio remained below INVERT
HOLD. R4-003 averaged +0.921 and was positive in four overall folds, but failed
side/session robustness. R4-004's +1.690 pooled result had only two positive
folds. These are diagnostics, not candidates.

## Decision

All 16 are rejected; do not revive them, adjust their thresholds, or recombine
their best-performing conditions. No candidate exists. Because the isolation
incident remains potentially contaminated, no Discovery Validation score may
be spent on this round or used to decide the next one.
