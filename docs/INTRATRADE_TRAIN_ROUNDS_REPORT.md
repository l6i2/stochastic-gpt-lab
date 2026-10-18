# TRAIN-only intra-trade rounds — 2026-10-18

Three preregistered rounds were replayed against quality-v1 TRAIN only, using
four chronological expanding purged folds, exact arrival-quote joins and
ordered quote tapes. Each fixed FOLLOW exit was compared with FOLLOW HOLD and
INVERT HOLD; all trade outcomes were retained. Latencies were 0/250/500 ms,
with 250 ms primary. No Discovery Validation outcomes were scored, compared,
or used for selection. The combined event CSV contains both TRAIN and
Validation; the first round runners loaded that shared source into a lookup
before restricting calculations to frozen TRAIN IDs. Therefore zero physical
read of Validation rows cannot be claimed, but no Validation values entered
the replay, walk-forward metrics, gates, or selection. I changed the loaders
after these runs to stream/filter by frozen TRAIN IDs before retaining rows.

## Results

| Round | Frozen hypotheses | Trigger counts | TRAIN survivors | Discovery Validation |
|---|---:|---|---:|---|
| R2 | 8 | 1,134–11,097 each | 0 | Not opened |
| R3 | 4 | 1,648–8,264 each | 0 | Not opened |
| R4 | 4 | 0–9,441 each | 0 | Not opened |

R2's largest pooled 250 ms walk-forward portfolio change was HYP-20261018-R2-006
(high-volatility adverse bar), +1.689 price units per signal versus FOLLOW HOLD.
It was negative in fold 1 and did not meet both-side consistency or session
robustness. HYP-R2-005 was positive in all four overall folds (+0.582 mean),
but BUY and SELL each had only two positive folds; it also failed the session
gate. No rule passed the complete preregistered gate set.

R3's strongest rule was HYP-20261018-R3-001 (MAE recovery). Its 250 ms policy
portfolio averaged -5.884 versus -6.967 for FOLLOW HOLD and -2.740 for
INVERT HOLD (paired improvement +1.084 versus FOLLOW). The overall paired
change was positive in all four folds and latency sensitivity was small, but
SELL was positive in only two of four folds. New York contributed 55.0% of
positive session-level change, exceeding the 50% concentration limit. It fails
the side and session gates and is not a candidate. The other three R3 rules
failed fold consistency and/or side/session robustness.

R4 tested adverse EMA alignment, adverse structure-break flags, a fixed
50-bar loss stop, and low-volatility profit protection. None passed. The
structure-break feature produced zero triggers in the frozen TRAIN snapshots,
so it failed support immediately. The fixed 50-bar loss stop was positive in
all four overall folds (+0.921 mean), but SELL was positive in only 2/4 folds
and it failed the session gate. Volatility contraction had the largest R4
pooled change (+1.690) but only two positive folds. No rule advances.

The filters were applied independently by BUY/SELL and require at least 70%
positive folds on both sides, at least two positive supported sessions and
source blocks, no fold/session/block above 50% of positive effect, adequate
support, sensitivity stability, and no severe drawdown deterioration. Full
criteria are in `INTRATRADE_R2_PROTOCOL.md`, `INTRATRADE_R3_PROTOCOL.md`,
and `INTRATRADE_R4_PROTOCOL.md`. The variable snapshot derivative still carries
its documented `PASS_INHERITED_VALIDATION` caveat; the aggregate row-by-row
validator was not completed.

## Frozen hypothesis hashes

| Hypothesis | SHA-256 |
|---|---|
| HYP-20261018-R2-001 | `bf8d2f1c5d1ab7fdd775f00a01833c9b355e5b3c5062a52ff376898af592b50e` |
| HYP-20261018-R2-002 | `6967d2d80e840a1d5c00f180c62aaf1c891baa099398e048818debb10a929551` |
| HYP-20261018-R2-003 | `abfed4eac54421015922b7dbd86905da6a2e0f63e8af6d562d9fd44d4740e27c` |
| HYP-20261018-R2-004 | `11f72c438eb5818c03b5524d519eb3e1122420b55c29cb9c8dc20e5951624ab7` |
| HYP-20261018-R2-005 | `e0634f52eba3f9bcde79a9a9fb49ade71b281d81fdcc6a6d00862d8490110d19` |
| HYP-20261018-R2-006 | `4cee56607423f6409b2eebf0811e4972022a966076422c7e72dfdf1d5f786fad` |
| HYP-20261018-R2-007 | `2d5dbaf9e8d05f3519f3aebe771b3a09546902f2389d2e8232ce35f431e014dc` |
| HYP-20261018-R2-008 | `fdbde0215d978756adc0ad6d70fe4748ef39f314d7b239d9101b56f762b9d2fe` |
| HYP-20261018-R3-001 | `67053c6eef4ed854dd82d14fc40865ba3dd2f2588ca571cd2b5fc3dc02a64d67` |
| HYP-20261018-R3-002 | `57aa4725eb2e47eafa68d685f13e23c3faa40bbda447a15ff7685b0076f80913` |
| HYP-20261018-R3-003 | `6d5e02a2b2edc748f64776f59fc6f0ce10551b5d3570a1baa14d2ec755d8eb8b` |
| HYP-20261018-R3-004 | `ef00cc2f1be142f767bfeac793356b1f96a2cf72f8b47afa300e6eed7384c9c5` |
| HYP-20261018-R4-001 | `a5f4e683cdff2c82b80f11a125a1ff07354e0c44cb764368bfac5ba62b877b0e` |
| HYP-20261018-R4-002 | `9fe7e1653ab8b4e223ebd8ca960c1cbbcbae19aeac6da700417be4d2c3dd5526` |
| HYP-20261018-R4-003 | `f4c4ba90fb40f543d7a01522d895bcbfddcf66517777f0f1426c4da3d3c1e791` |
| HYP-20261018-R4-004 | `d72077428848fbad53667977533c8563f7ab05e38413faf5a394b6d5991f535c` |

## Local run-manifest hashes

| Artifact | SHA-256 |
|---|---|
| R2 replay manifest | `d7cdc561030f1e8479c2af1b9d60b27447333b738ce0b159d5c5116387cdde25` |
| R2 walk-forward report | `4c49cfbb0d003afbb58b8ddf9640f07045ddf5ddb1dbabfd2867856187fc1cf6` |
| R3 replay manifest | `b17d7d153232fa09d6f89dcf4dd158abb0bfb640c7178fcc3f988cfe585c58ed` |
| R3 walk-forward report | `918d942ff6978be0b3fe12929504b10756627c3b1089d24544759191605b609b` |
| R4 replay manifest | `2813027a2909013f8c99d10c0d60f00227915e1ba5f1b9b3c5572908f6c20062` |
| R4 walk-forward report | `2e18eeb6724d138473f0df988589e9f1846c5dbe2b4a147ec709c1468b97c4ca` |

After R4, do not expand the rule family further against the same TRAIN folds
without a prospective, fixed search budget; doing so would increase adaptive
selection risk. No Validation score has been spent. Any future candidate must
still pass the reserved single Discovery Validation gate.

Small run manifests and fold reports remain local under
`outputs/bar_controller/research/round2/`, `round3/`, and `round4/`; per-trade quote replay
CSVs and source tick data are ignored and are not published. The summary,
hypothesis records, hashes, evaluators, tests, and protocols are suitable for
GitHub review. No candidate is frozen. `FINAL_TEST=LOCKED`, Demo is disabled,
and `LIVE_TRADING=false`.
