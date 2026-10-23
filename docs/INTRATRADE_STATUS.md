# Intra-trade research status

## Paired clock attestation - client case 2026-10-23

[Clock attestation](CLOCK_ATTESTATION.md): 50 paired frames / 150 native readings, capture integrity PASS, native/Windows separation 0-125 ms. Host clock still differs from independent UTC quorum by about 207999.8 s. CLOCK_ATTESTATION FAIL; NATIVE_TO_UTC_MAPPING FAIL; no authorized segments. The unique converter preserves raw hashes, rejects ambiguity and double conversion, and exposes Ecuador/New York only from explicit UTC. ECUADOR_TIME_MAPPING PASS; NEW_YORK_TIME_MAPPING PASS; DST_HANDLING PASS for IANA views/ambiguity rejection, native DST evidence UNKNOWN. Runtime leaves normalized event/decision times null until independently attested. FUTURE_QUOTE_GUARD PASS with zero future tolerance. TEMPORAL_CAUSALITY FAIL under the stricter end-to-end evidence scope; CAUSAL_AUDIT FAIL. MAIN_K_PARITY PASS from existing exports; no script rerun or dataset rebuild. SESSION_CALENDAR PASS_WITH_RUNTIME_GUARD; DISCOVERY_VALIDATION BLOCKED; FINAL_TEST LOCKED; DEMO DISABLED; LIVE_TRADING=false. NEXT_STATE HARD_BLOCKER_CLOCK_ATTESTATION_AND_MAPPING.

This supersedes earlier clock snapshots; all sealed earlier evidence remains unchanged.

## Clock provenance diagnosed - host date 2026-10-23

[Timestamp/clock provenance audit](TIMESTAMP_CLOCK_PROVENANCE_AUDIT.md): primary cause A, local reference clock behind independent NTP + TLS UTC by about 207999.8 s (57 h 46 min 40 s). Retained US30Cash tick is past against independent UTC. Native clock export validated (24 rows, tester=0); FX raw labels track server time about UTC+2, mapping to UTC remains unverified. TimeCurrent follows Market Watch; TimeTradeServer depends on the bad client clock. No automatic time correction, quote offset, tolerance or dataset change. TIMESTAMP_NORMALIZATION FAIL; FUTURE_QUOTE_GUARD PASS; TEMPORAL_CAUSALITY PASS (invariants only); MAIN_K_PARITY PASS from existing exports. CAUSAL_AUDIT FAIL until trusted host clock and explicit native/UTC mapping are attested. SESSION_CALENDAR PASS_WITH_RUNTIME_GUARD; DISCOVERY_VALIDATION BLOCKED; FINAL_TEST LOCKED; DEMO DISABLED; LIVE_TRADING=false. NEXT_STATE HARD_BLOCKER_CLOCK_ATTESTATION_AND_MAPPING.

This supersedes earlier future-quote/cache hypotheses; earlier sealed evidence is preserved.

## Native parity execution validated — 2026-10-23

Native execution pk_41a2e93f is now validated: MAIN_K_PARITY PASS, 960 closed-bar rows (930 ready, 30 warmup), five fixtures; maximum independent reference error 1.4210854715202004e-14 at fixed tolerance 1e-10. Historical impact NONE. Native clocks confirm TimeCurrent=quote_time=1792799997, TimeGMT=1792753785, TimeTradeServer=1792760985 (+7200s). The quote is 46,212,469 ms ahead of capture GMT; this is not explained by server/local timezone or units. Feed/cache provenance remains unverified; quote rejection stays fail-closed. TEMPORAL_CAUSALITY PASS; CAUSAL_AUDIT FAIL. SESSION_CALENDAR PASS_WITH_RUNTIME_GUARD; DISCOVERY_VALIDATION BLOCKED; FINAL_TEST LOCKED; DEMO DISABLED; LIVE_TRADING=false. NEXT_STATE HARD_BLOCKER_FUTURE_NATIVE_QUOTE. Evidence: [native validation](../configs/main_k_native_evidence_20261023/validated_audit.json). No dataset, strategy, sealed metadata or earlier evidence was overwritten.

This checkpoint supersedes the pending-export checkpoint below.

## Latest MAIN_K / temporal audit — 2026-10-23

[Authoritative audit](MAIN_K_NATIVE_PARITY_AND_TIME_AUDIT.md): frozen production still uses native iStochastic 5/3/3 SMA Low/High MAIN_K, shift 1. All 128 native historical values in the 64-event TRAIN sample match the ratio-of-sums reference (max error 2.84e-14); historical impact NONE, no rebuild. Auxiliary metadata/legacy indicator fixture use an incompatible arithmetic Fast-K mean. Native five-fixture harness compiled 0 errors/0 warnings and deployed as `ResearchDiagnostics/pk_41a2e93f/MainKNativeParity`, but execution/clock exports are still absent. MAIN_K_PARITY FAIL (not yet evidenced); CAUSAL_AUDIT FAIL. Temporal invariants PASS; a future-dated native latest quote is quarantined, backend clock/cache origin pending MQL capture. Full suite 198 tests, 9 native skips. SESSION_CALENDAR PASS_WITH_RUNTIME_GUARD; Validation BLOCKED; FINAL_TEST LOCKED; DEMO DISABLED; LIVE_TRADING=false. NEXT_STATE HARD_BLOCKER_NATIVE_PARITY_AND_CLOCK_EXPORT_PENDING.

This checkpoint supersedes all earlier operational snapshots below; accepted data, producer hashes and sealed protocols remain unchanged.

## Authoritative operational checkpoint — 2026-10-23

[Current addendum and evidence](PROSPECTIVE_OPERATIONAL_ADDENDUM_20261023.md): `SESSION_CALENDAR=PASS_WITH_RUNTIME_GUARD` for operational containment; historical UTC calendar remains unverified. Guard READY, DST PARTIAL, holidays UNKNOWN. Causal audit FAIL (frozen metadata/native-trigger non-equivalence), manifest chain PARTIAL, drift NOT_READY. Collector active/HEALTHY, cohort NOT_MATURE, evaluator READY_BUT_GATED. DEMO executor and shadow READY_BUT_DISABLED; no orders. FINAL_TEST LOCKED; DEMO DISABLED; LIVE_TRADING=false. Full suite: 190 tests, 9 native skips. NEXT_STATE=HARD_BLOCKER.

All operational snapshots below are historical and superseded by the linked addendum; sealed scientific protocols remain unchanged.




## Current checkpoint — 2026-10-21 (prospective evaluation frozen; no scoring)

[`PROSPECTIVE_EVALUATION_PROTOCOL.md`](PROSPECTIVE_EVALUATION_PROTOCOL.md) now fixes the one-shot outcome metrics and PASS/FAIL/INCONCLUSIVE gates before prospective results. The raw-only maturity auditor found 2 days, 263,727 ticks, 552 bars, 29 BUY and 26 SELL support signals, zero invalid ticks/bars, and no missing capture days. These are counts/coverage metadata only. The cohort is not mature: minimum duration/support are unmet, and the verified XM server calendar, causal audit, frozen candidate, and complete pre-archive manifest chain are absent. No outcome, ranking, or candidate score was read.

The prospective protocol and metadata specification are SHA-256 pinned. Full verification passes: 163 unit tests, 9 skipped because `g++` is unavailable, plus compileall. No scoring or protected-split access occurred.

As of 2026-10-22, the prospective cohort has four complete UTC days, 545,461 raw ticks, 1,104 M5 bars, and 60 BUY / 61 SELL support signals. Latest tick: `2026-10-22T23:59:57.051Z`. It is still `NOT_MATURE`; the hash-pinned health report reports no labels or PnL read. Calendar hash changes now force a new health report. No hypotheses were created and no cohort scoring occurred.

The evaluator is `READY_BUT_GATED`; the hash-bound candidate packaging path is available but there is no candidate. Drift monitoring and shadow recording are fixture-tested; shadow is disabled and cannot send orders. `FINAL_TEST=LOCKED`, `DEMO=DISABLED`, `LIVE_TRADING=false`.

## Current checkpoint — 2026-10-21 (formal V2 failure analysis; research paused on current TRAIN)

The formal gate-by-gate analysis is in [`V2_FAILURE_ANALYSIS.md`](V2_FAILURE_ANALYSIS.md). This makes explicit that V2 month-level dependence was not separately measured, aggregate support was adequate, latency and the limited drawdown proxy passed, and rejection came from preregistered block/session concentration (BUY) and fold/threshold instability (SELL). Both clustered intervals include zero. No BUY-only rescue or threshold change is permitted.

There are 17 tested hypotheses across R2–R4 and V2, zero survivors, and no candidate. No new family is preregistered on this TRAIN: R2–R4 already covered the proposed intra-trade trajectory, erosion/recovery, momentum, volatility, volume/profile, HA, Stochastic and session themes. More same-sample exploration would be adaptive reuse, and Discovery Validation remains blocked by the unresolved isolation incident. The prospective cohort remains unscored and governed by its existing fixed maturity protocol.

`FINAL_TEST=LOCKED`, `DEMO=DISABLED`, `LIVE_TRADING=false`.

## Current checkpoint — 2026-10-21 (V2 evaluated on TRAIN; rejected)

`HV2_ENTRY_SPREAD_ATR_ROUTER` completed on 11,714 TRAIN signals, 23,428 paired
baseline paths, four frozen purged folds, and 70,284 exact latency/mode replay
outcomes. The full benchmark, exact output hashes, peak memory, and
normal/low-memory equality are in `docs/TRAIN_V2_LOW_MEMORY_BENCHMARK.md`.
Result status is `TRAIN_ROUTER_REJECTED`; no provisional candidate was frozen.

BUY passes fold and latency/threshold gates but fails block and session
concentration. SELL passes latency but fails fold direction, threshold
robustness, and fold/block/session concentration. Drawdown passes; both
signal-clustered intervals include zero. The rule is rejected without retuning.
The other user-listed intra-trade feature families are outside the frozen V2
preregistration and were not evaluated.

The JSON result binds the current runner/data hashes and records no Validation,
FINAL_TEST, or future-cohort access. `DISCOVERY_VALIDATION=BLOCKED`,
`FINAL_TEST=LOCKED`, `DEMO=DISABLED`, and `LIVE_TRADING=false`.

## Current checkpoint — 2026-10-21 (V2 entry-friction replay incomplete)

The TRAIN-only V2 router is preregistered in `docs/RESEARCH_PROTOCOL_V2.md`.
Its new runner tests a single signal-time `spread/ATR` regime policy, with BUY
and SELL separated, FOLLOW/INVERT baselines, 250 ms primary execution latency,
0/500 ms sensitivities, four expanding purged folds, and frozen rejection
gates. No prior R2–R4 rule was retuned. No held-out or future cohort data was
scored.

The full run did not finish: two earlier implementations were stopped after
excessive paging/runtime; the latest block-extrema implementation has unit
coverage but was not completed on the current host. No result JSON exists, so
record `ROUTER_V2=INCOMPLETE`, `HYPOTHESES_TESTED=0 completed (1 attempted)`,
and `CANDIDATE=NONE`. Do not interpret this as an outcome or run Discovery
Validation. Focused tests cover strict post-arrival fills, exact SL/TP/time
exit behavior, safe-block skipping, causal TRAIN boundary enforcement, and
isolation guards.

The runner’s accepted source baseline is `TRAIN_HOLD_BASELINE_REPLAY_PASS`:
11,714 signals and 23,428 quote-paired virtual paths. The latest user-provided
cohort status remains healthy but is not mature (two days accumulated against
the preregistered 16-week/four-month rule); no cohort scoring has occurred.
`FINAL_TEST=LOCKED`, `DEMO=DISABLED`, and `LIVE_TRADING=false`.

## Latest checkpoint — 2026-10-18 (isolation incident: potential contamination)

The R2/R3 manifests say `validation_accessed=false`, and their saved reports
contain TRAIN-fold metrics, but their exact runner sources are missing from the
audited Git history. Therefore the negative claim that Validation did not
influence any execution path or decision cannot be independently established.
`DISCOVERY_VALIDATION_CONTAMINATION=POTENTIAL`; the incident remains open and
use of the existing split is blocked pending an auditable scientific
remediation. The committed R4 runner source is recoverable and uses frozen
TRAIN IDs, but it does not close the R2/R3 gap.

The diagnostic grouped the 16 failures: support and prevalence failed for one
rule (R4-002, zero triggers); the overall fold gate failed for 14; the combined
BUY/SELL gate and multi-session gate failed for all 16; latency robustness
failed for four; multi-block robustness failed for six; and the drawdown proxy
failed for none. Threshold robustness was not tested because definitions were
frozen and no threshold sweeps were permitted. No new hypotheses or round were
created. Reports: `docs/ISOLATION_INCIDENT_AUDIT.md`,
`docs/R2_R4_FAILURE_ANALYSIS.md`, and
`docs/INTRATRADE_NEXT_RESEARCH_PROPOSAL.md`.

TRAIN source readers now fail closed on explicit Validation / FINAL_TEST paths.
Tests cover rejection before file reads. A combined shared event source still
has to be scanned to retain exact TRAIN IDs; the guard does not claim otherwise.
`FINAL_TEST=LOCKED`; `DEMO=DISABLED`; `LIVE_TRADING=false`.

## Latest checkpoint — 2026-10-18 (R2, R3, and R4 TRAIN gates failed)

Three new, frozen rounds were evaluated only on quality-v1 TRAIN. R2 contained
eight hypotheses covering profit erosion, stop distance, Stochastic zone
recovery, HA with relative volume, ATR regime, value-area edges, and session
close. R3 contained four distinct definitions for MAE recovery, TP proximity,
low-volume profit protection, and adverse POC crossing. R4 contained EMA,
structure, 50-bar loss-stop, and volatility-contraction rules. All used the existing
four expanding purged folds and 0/250/500 ms quote replay. Hypothesis SHA-256s
and results are in `docs/INTRATRADE_TRAIN_ROUNDS_REPORT.md`.

R2: 0/8 passed all preregistered gates. R3: 0/4 passed. R4: 0/4 passed. R3 MAE recovery was
positive in all four overall folds, but SELL was positive in only 2/4 and the
New York session contributed 55.0% of the positive session effect; the policy
also remained below the INVERT-always mean. None proceeds to Discovery
Validation, no candidate is frozen, and no rule was retuned. The R4 fixed
50-bar loss stop was positive in all four overall folds but failed SELL and
session consistency; the structure-break rule had zero triggers. The 250 ms
primary latency and 0/500 ms sensitivities remain unchanged.

No FINAL_TEST outcome or held-out Validation metric was analyzed or scored.
The first runners loaded the combined event CSV before restricting all
calculations to frozen TRAIN IDs, so physical zero-read of Validation rows
cannot be claimed; loaders now stream/filter by TRAIN membership. No Demo/live execution
occurred; `LIVE_TRADING=false`. Historical quality caveat remains:
`PASS_INHERITED_VALIDATION`, without a separate completed aggregate row-level
validator.

After R4 the rule search is stopped on this reused TRAIN fold set to avoid
unbounded adaptive hypothesis selection. No Discovery Validation score has
been spent; new research needs a fixed prospective search budget or additional
permitted data.

## Authoritative checkpoint — 2026-10-16 (entry model rejected; dynamic replay pending)

A signal-time entry-direction model study was completed on the quality-v1
event table (event schema 1.1, from validated schema 3.0 blocks): 11,714 TRAIN
events and a single score on 4,077 Discovery Validation events. Its 59 fixed
causal features, three fixed classifiers, and 0.5 threshold did not outperform
FOLLOW-always; discrimination was near chance. It is rejected for promotion;
no candidate exists. Four expanding walk-forward folds were purged and used
TRAIN only. See `docs/QUALITY_DIRECTION_MODEL_REPORT.md`.

This entry-direction comparison does not test dynamic intra-trade decisions.
The memmap quote replay kernel now has synthetic tests for baseline parity,
strictly post-arrival fills, latency and barrier precedence, and protected
boundaries. Its bounded TRAIN runner rechecked all 23,428 virtual HOLD paths
from the 11,714 quality-v1 TRAIN signals; all matched the frozen exit, quote,
time, and PnL evidence. Report:
`outputs/bar_controller/research/train_hold_replay.json`.

Dynamic EXIT TRAIN discovery used the user-selected 250 ms primary execution
latency and 0/500 ms sensitivities. The three fixed HA/Stochastic rules were
replayed on 1,810,478 causal snapshots. A four-fold expanding, purged
walk-forward passed in only 2/4 folds; the largest fold contributed 69.7% of
positive change. The frozen gate failed, so Validation was not opened and no
candidate exists. See `docs/DYNAMIC_EXIT_TRAIN_REPORT.md`. FINAL_TEST is locked;
`LIVE_TRADING=false`; DEMO execution remains disabled.

The rejected one-sided hypothesis is preserved and hashed at
`research/hypotheses/HYP-20261017-DYN-001.json`; it was not sent to Validation.

## Authoritative checkpoint — 2026-10-16 (schema 3 every-bar master)

Schema 3 every-bar/ordered-quote history is complete for all allowed dates:
2023-12-20..31, 2024, 2025, and 2026-01-01..03-19. All four raw blocks passed
their intra-trade causal, FOLLOW/INVERT, frozen exit, split, quote-arrival, and
baseline replay validators. The master is `BUILT_NOT_PROMOTED` and contains
2,480,241 snapshots; no FINAL_TEST data was read.

The separately hashed quality derivative is
`outputs/bar_controller/research/quality_v1/`. The frozen tick-quality rule
excludes 210 2023 signals and 319 2024 signals on time-window evidence alone.
The derivative contains 15,791 events (7,398 BUY; 8,393 SELL), 2,388,383
snapshots, the same number of complete targets and decision-arrival quotes,
1,810,478 TRAIN rows (11,697 signals), and 577,905 Discovery Validation rows
(4,074 signals). Its status is `PASS_INHERITED_VALIDATION`: source block causal
passes plus exact filter/split membership, frozen parameters, count checks, and
artifact hashes. The combined full validator was interrupted after its
multi-million-key in-memory indexes triggered sustained paging; no independent
aggregate row-by-row PASS is claimed.

The every-bar producer now supplies state trajectories, quote paths, trade
indices, and strictly-after-cutoff arrival quotes. The existing replay kernel
has only synthetic fixtures and HOLD/EXIT actions; it has no bounded dataset
runner. Existing schema-2 hypothesis/ML reports estimate fixed-bar outcomes,
not executable dynamic exits, so they are not being used. Research has started
with schema/quality and TRAIN membership audit only; no outcome-based TRAIN
discovery, validation, walk-forward, or candidate is claimed yet. A feature-only
TRAIN profile (1,810,478 rows / 11,697 signals) is available at
`outputs/gpt_research/train_schema3_quality_v1/`. It profiles causal Stochastic,
volume, Heikin Ashi, Volume Profile, ATR, spread, and virtual-position fields;
it read no targets or Validation rows and makes no outcome or edge claim. Next
is a bounded-memory TRAIN-only quote replay reproducing HOLD before evaluating
any policy. FINAL_TEST is locked; Demo and live execution remain disabled.

## Current authoritative checkpoint — 2026-10-14 (all base history accepted)

This section supersedes operational statements in older sections below.
Base history: December 2023 PASS; 2024 PASS (`r20261014T052944_07590da1`);
2025 PASS (`r20261014T061439_70753a52`); January 1–March 19 2026 PASS
(`r20261014T070800_6a2dbe02`). No accepted native block was repeated.
The interrupted old 2024 attempt remains rejected and preserved.

Frozen membership is unchanged: 16,320 known signals, ten observed boundary
purges, 47 endpoint-gap quarantines, and two end-of-data censored nonmembers.
The latter two are quarantined with pinned allowed-source evidence; no future
outcome or original protected purge reason is inferred. See the two membership
contract JSON documents. All raw evidence remains available locally.

Postprocess is RUNNING with bounded streaming and SQLite uniqueness checks.
The earlier dense attempt exhausted available memory and was stopped; its
partial outputs were archived, not accepted or deleted. Final consolidation,
combined validation and quality audit have not yet passed.

The separate schema 3 producer adds every-bar states, an ordered quote tape
and trade indices. Baseline strategy functions are preserved. Preview compile
was 0/0; the first deployed compile timed out without a success summary and
was rejected. A fresh compile is being retried with a longer timeout. Native
schema 3 causal proof, smoke/history and dynamic master remain pending.

No new hypothesis validation, model training, walk-forward, robustness result
or candidate is claimed. Legacy future excursion labels and unusable breakout
features remain excluded from promotion. FINAL_TEST=LOCKED;
LIVE_TRADING=false; DEMO_EXECUTOR=NOT_STARTED.

## Current authoritative checkpoint — 2026-10-14

Older sections below are historical, not the current execution plan. The master
request now authorizes safe bounded reruns. December 2023 PASS. Recovery of
2024 run `r20261013T121405_09901cc2` found no completion/artifact evidence and
marked it FAIL. Replacement `r20261014T052944_07590da1` is PASS after revalidating
the existing completed artifacts without another backtest. 2025 run
`r20261014T061439_70753a52` is active; 2026 through March 19 pending. Evidence preserved.

The local quote-mark correction is already deployed and matches the compiled
source and causal proof. Twenty focused existing tests and two quality-audit
tests pass. No new master, hypothesis validation or model results exist yet.

Dynamic research is gated by `DYNAMIC_REPLAY_REQUIREMENTS.md`. Scheduled offsets
lack ordered executable post-decision quotes. Lifetime-extrema increments are
not future path excursions; derived recovery labels are excluded from promotion
research. Strict breakout flags whose reference window includes the current
bar are excluded until corrected and versioned. No candidate can be promoted
using the prototype support-only hypothesis checks.

FINAL_TEST=LOCKED; LIVE_TRADING=false; DEMO disabled; no candidate promoted.

Preparation while C5 runs: `build_bar_replay_producer` derives a separate schema
3.0 producer with every-bar states and a separate first-post-decision quote
table. Baseline execution functions are preserved; preview compilation is 0/0.
It has not been deployed, causally accepted or used for historical exports.
The schema 3 validator requires contiguous bar coverage, baseline-lifetime
agreement and complete, finite, strictly post-cutoff execution rows. None of
this makes the incomplete C5 history or dynamic master ready.

The new inclusive 2024 export has 7,412 signals versus 7,390 in the frozen source.
The 22 additional IDs all occur December 31, a day missing from that source due
to the old exclusive ToDate endpoint. Frozen 2025 has the same endpoint gap.
The explicit hash-verified contract in `FROZEN_UNIVERSE_COVERAGE.json` preserves
all raw evidence while excluding these noncanonical IDs from research. It does
not add observations to TRAIN/VALIDATION, move boundaries, or select by outcome.
Other unexplained nonmember IDs still fail closed. The 2024 block now passes both
validators and causal acceptance; C5 remains incomplete until 2025/2026 pass.

2025 tester PASS: 7,200 signals versus 7,175 in the frozen source. Endpoint
contract v2 uses actual entry time, preserving the old v1 checkpoint. The 25
additional entries on December 31 include a signal whose cutoff is December 30
23:59:59.999. The other ten nonmember signals are genuine TRAIN-boundary purges.
Revalidation reuses this completed export; no additional 2025 tester run is needed.

Date: 2026-10-13. Branch: `research/full-pipeline`. Current remote base: `fc178e7577f2c372194fedd295805cff3932440a`.

## INTRA_A — instrumentation

**Status: source and compiler checks pass; smoke evidence rejected.** The independent `mt5/StochasticIntratradeResearchEA.mq5` exports open virtual FOLLOW/INVERT states at offsets 1, 2, 3, 5, 10, 15, 20, 30, and 50. It retains `LIVE_TRADING=false`, requires Strategy Tester with optimization OFF and `TICK_QUOTES`, uses the same unchanged `ResearchCore.mqh`, and does not call trading APIs. The dedicated EA and both includes are in the active XM data folder. XM MetaEditor build 6257 compiled that exact copy with 0 errors and 0 warnings; evidence is in the local-only `outputs/verification/metaeditor_intratrade_compile.log`.

Static regression tests confirm that the base signal thresholds and the `TickTrade`/`BarTrade` execution routines are unchanged. Validator and frozen-hypothesis tests verify snapshot cutoffs, separate targets, no final-test IDs, and single-use validation. `python -m compileall -q python tests` passes. The full suite passes: 54 tests, 9 skipped because `g++` is unavailable.

## MT5 smoke test gate

**Status: REJECTED; do not use these artifacts.** MT5 produced snapshot, target, audit, entry CSV, and tester log files in the local Agent-127.0.0.1-3000 `MQL5/Files` directory on 2026-10-13. The tester log identifies the run period as 2026-10-01 through 2026-10-12. This is after the protected FINAL_TEST boundary (`final_test_start_signal_time_msc=1773980099999`, 2026-03-20). The tester also loaded `Experts\StochasticResearch\StochasticIntratradeResearchEA.ex5`, not the dedicated EA at `Experts\StochasticIntratradeResearch\StochasticIntratradeResearchEA.ex5`. Consequently this is neither an allowed discovery smoke run nor evidence for the newly deployed binary. The generated files remain in the tester agent folder and were not copied into the repository or used for research.

The structural validator initially returned PASS without split Parquet arguments. That only checks schema and timestamp/label separation; it did not verify inherited signal membership. The validator now marks split membership as unverified and reports `final_test_accessed: null` for a structural-only pass. Pipeline validation supplies TRAIN and DISCOVERY_VALIDATION membership and rejects unknown IDs. Do not treat the structural-only result as a dataset approval.

The correct deployed EA and includes now exist in the active XM Data Folder under `MQL5/Experts/StochasticIntratradeResearch/`; XM MetaEditor build 6257 compiled that exact copy with 0 errors and 0 warnings. No additional smoke run has been started. To accept smoke evidence, run only a short pre-boundary period such as 2024-01-01 through 2024-01-31, select the dedicated folder's EA, and validate with both inherited TRAIN and DISCOVERY_VALIDATION membership files. Existing bounded historical presets stop at 2026-03-19; the requested period after 2026-03-20 must remain excluded.

## Data and evaluation limitations

The snapshot CSV and target CSV are separate. The exporter writes causal features only through the completed-bar cutoff and delays targets until closure; end-of-data records remain censored. Profile windows are recomputed at snapshot time and cached for paired FOLLOW/INVERT rows on that bar.

The current source records scheduled snapshot states and terminal labels, not the full ordered quote path after each snapshot. Therefore a decision policy that exits at a later tick or reverses direction cannot yet be faithfully simulated; `REVERSE_DIRECTION` is marked unavailable until that path is exported. The fixed-bar-3 HOLD, EARLY_EXIT, and +60 PROTECT_PROFIT comparisons are predeclared and research-only. They cannot create or promote a candidate.

No raw blocks, master snapshots, TRAIN analysis, intra-trade hypotheses, model metrics, or walk-forward metrics exist yet. `NO CANDIDATE`; FINAL_TEST remains locked and DEMO execution remains disabled.

## 2025 annual run audit — 2026-10-13

The requested `US30Cash`, M5, real-tick, optimization-OFF, `LIVE_TRADING=false` test completed for 2025-01-01..2025-12-31. The entry audit reports 7,175 signals (3,338 BUY; 3,837 SELL), no fatal/abort, and the baseline event CSV matches the canonical 2025 event hash. The intra-trade audit reports 116,929 snapshots and 116,825 targets; offsets are +1 14,302, +2 14,228, +3 14,135, +5 13,935, +10 13,387, +15 12,916, +20 12,437, +30 11,545, +50 10,044. FOLLOW has 58,428 snapshots; INVERT has 58,501.

**Rejected for research.** Split-aware `validate_intratrade_dataset.py` fails because current MFE does not bound current unrealized PnL. A full streaming audit found 207 MFE-bound violations, 0 MAE-bound violations, 0 future timestamp violations, 0 FOLLOW/INVERT side-mapping violations, 0 duplicate snapshot IDs, and no monotonic MFE/MAE regressions. The export's mark quote was reconstructed from bar close and bar spread while excursion tracking used actual ticks. That can create a mark PnL larger than observed MFE. No raw data was canonicalized, no master/split/research was built, and no FINAL_TEST data was opened.

The exporter was minimally changed to mark each snapshot from the last observed bid/ask at or before the cutoff; Stochastic logic, parameters, and tick/bar exit routines were left intact. The dedicated XM MetaEditor compile log reports 0 errors and 0 warnings. Focused Python tests are being run. Per the instruction not to start the Tester again yet, the corrected 2025 block has not been rerun. A corrected 2025 preset and bounded presets for 2023-12-20..31, 2024, and 2026-01-01..2026-03-19 are prepared under `outputs/verification/intratrade_export_plan/corrected/` and the `.set` files are copied to the active XM `MQL5/Profiles/Tester` folder. The 2026 range ends before the protected FINAL_TEST boundary.

**Next required run:** start only `intratrade_2025_quote_markfix_20261013.set` (dedicated expert path) and stop after it finishes. Do not build the intratrade master or analyze hypotheses until the corrected 2025 export passes validation. Remaining bounded blocks stay queued.

## 2026-10-16 continuation: schema 3 dynamic replay gate

Authoritative local HEAD at audit start: `71667a86597adee298cbfd56c37c6be55c162b40`, branch `research/full-pipeline`, equal to `origin/research/full-pipeline`. Four schema 2 blocks (Dec 20–31 2023, 2024, 2025, and 2026-01-01..03-19) are PASS. The schema 2 master and TRAIN descriptive analysis exist, but the scheduled snapshots and legacy excursion deltas are not a faithful dynamic exit policy dataset; they remain descriptive only.

The separate schema 3 exporter is now compiled on the active XM installation (0 errors, 0 warnings; EA SHA `f2e9bf43cbbdc716148847fe53e1f3dd14b21393775ccc809d05cb5e134cb88d`; EX5 SHA `2943e6fc9d35798dd00b3565f7f4b9695346944b7686a4202b54c5617cf55ecd`). The updated causal probe passed 1,060 snapshots × 257 features under future-only input mutation; 404 quote records through the cutoff were byte-identical. Baseline replay passed both fixtures. This is synthetic causality/fixture evidence, not historical acceptance.

A real US30Cash M5 real-tick Tester smoke for 2025-01-01..31 passed: 611 signals, 92,023 every-bar snapshots (offsets 1..100 while open), 91,893 terminal targets, 1,952,817 ticks and 5,850 bars; event and schema 3 validators, exact HOLD baseline replay, and causal-hash verification all pass. `LIVE_TRADING=false`, optimization OFF, DEMO account in Tester, no trading APIs. Run ID `r20261016T154619_288daa1d`. The accepted raw run is local in `outputs/bar_controller/runs/`; the source manifest records the run identity and hashes.

**Next:** run the four complete permitted schema 3 blocks under the isolated `bar_controller` namespace. Then validate all tapes, build schema 3 master and split partitions, run data-quality and TRAIN-only dynamic replay research, freeze hypotheses, validate once on DISCOVERY_VALIDATION, and run walk-forward/ML/robustness. No dynamic hypothesis has been tested, no candidate exists. FINAL_TEST stays locked; DEMO stays disabled; live trading stays false.

### Schema 3 history progress — 2026-10-16

The allowed 2023-12-20..31 block has completed and passed event, snapshot, quote-tape and frozen baseline replay validation. Run `r20261016T155454_92027a5b`: 450,741 ordered quotes, 420 indexed virtual trades, 38,084 decision arrivals; 3,683 snapshots, with no future-boundary access. The 2024 full-year schema 3 block is now running; 2025 and 2026-01-01..03-19 remain pending. Keep the documented December generated-tick substitution warning in all reports.

## 2026-10-16 schema 3 history checkpoint — 2023 and 2024 PASS

The December 20–31, 2023 block (`r20261016T155454_92027a5b`) and full 2024 block (`r20261016T155802_b5bf64eb`) now pass event, every-bar snapshot, execution-quote, quote-tape replay, split-membership and causal-hash gates. The 2024 block contains 7,412 events (3,469 BUY / 3,943 SELL), 1,230,856 snapshots and 1,230,712 targets; 7,388 signals are assigned to TRAIN. Twenty-two noncanonical boundary signals were explicitly quarantined and excluded from the split. The every-bar and quote path preserves strictly post-arrival execution for the frozen HOLD baseline. No policy research or candidate has started.

The 2024 XM Tester log records 22,612,580 tick records and 70,875 M5 bars, but also 208 minute bars where invalid/mismatching real ticks were discarded and MT5 generated replacement ticks. This block is accepted structurally and causally with that data-quality caveat; it does not represent uninterrupted broker-real-tick coverage. `LIVE_TRADING=false`, Tester account DEMO, and no trading actions occurred. The 2025 block (`r20261016T165620_b7a3933a`) is running; 2026-01-01..03-19 is queued. FINAL_TEST and DEMO execution remain locked.

## 2026-10-16 schema 3 history checkpoint — 2025 PASS; 2026 in progress

The full 2025 block (`r20261016T165620_b7a3933a`) passed the dataset, schema 3 intra-trade, quote-tape/baseline replay, split-membership and causal-hash gates. It contains 7,200 Stochastic events (3,353 BUY / 3,847 SELL), 1,030,335 snapshots and 1,029,573 targets. The validator assigns 4,628 signals to TRAIN and 2,521 to DISCOVERY_VALIDATION, with 10 purged and 25 noncanonical boundary signals quarantined. Replay verified 26,768,356 ordered quote records, 14,400 indexed virtual trades and 1,030,335 decision arrivals; fills are strictly after decision arrival. FINAL_TEST access is false. The Tester/agent log contains no tick-discard or tick-price mismatch warnings for this block.

The only remaining permitted block is running: `r20261016T174747_38d1ddfb`, 2026-01-01 through the exclusive 2026-03-20 boundary (last included date 2026-03-19). It is US30Cash M5, real ticks, optimization OFF, compiled producer hash unchanged, and LIVE_TRADING=false. Master construction and research remain gated until this block passes and the complete data-quality audit is reviewed.

## 2026-10-16 schema 3 history complete; quality policy frozen before research

All permitted historical blocks passed their event, intra-trade, ordered-quote baseline replay, split-membership and causal proof gates: 2023-12-20..31 (`r20261016T155454_92027a5b`), 2024 (`r20261016T155802_b5bf64eb`), 2025 (`r20261016T165620_b7a3933a`) and 2026-01-01..03-19 (`r20261016T174747_38d1ddfb`). Combined: 16,379 event rows, 2,488,888 snapshots, 2,487,309 targets and 57,079,575 quote records. All audit manifests say `LIVE_TRADING=false`; no FINAL_TEST access occurred.

The raw historical runs remain intact. A pre-outcome data-quality policy is now encoded in `python/tick_quality_gate.py` and tested. The 2023 tester log reports 665 minute bars with no real ticks and 1,230 of 9,635 minute bars with real ticks discarded (plus tick-price/volume mismatches); this exceeds the frozen 1% quality threshold, so all 210 signals from that block are ineligible for research. The 2024 log reports 208 of 354,053 minute bars with discarded/mismatched ticks on six server dates. A conservative two-server-day halo around each warning date, applied to feature windows and open-trade intervals without inspecting returns, excludes 319 signals. 2025 and 2026 logs have no tick replacement/mismatch warnings and remain eligible. The preview counts come from event timestamps and trade interval bounds only; no target or PnL columns are read.

Next: build the complete raw schema 3 master and inherited partitions, then create and validate a separately hashed quality-eligible TRAIN/ DISCOVERY_VALIDATION derivative. Begin GPT/ML research only from its TRAIN partition. FINAL_TEST is still locked; no policy candidate or Demo execution exists.


## Future validation isolation — 2026-10-18

Dynamic-policy research is paused outside TRAIN. The contaminated legacy Discovery Validation remains blocked and is not repurposed. A separate raw-only prospective cohort is preregistered at `outputs/future_validation_cohort/cohort_20261019/`, with fixed start `2026-10-19T00:00:00Z`, no backfill, its own hash-chained manifest, and false TRAIN/evaluation permissions. TRAIN readers reject its path before I/O; any future derivation/evaluation requires a separate frozen protocol and explicit authorization. The scheduled collector is read-only and captures closed-day US30Cash M5 quotes/bars. No validation rows, FINAL_TEST rows, outcomes, or cohort data were used in hypothesis work. No new hypotheses were created.
## 2026-10-19 continuation — no candidate; V2 preregistered

The previously reported TRAIN-only R2–R4 rounds remain rejected (16/16); no
Discovery Validation was evaluated for those rounds, and the legacy isolation
incident remains POTENTIAL, so Discovery Validation stays blocked. A single
new, methodologically distinct entry quote-friction router has been frozen in
`docs/RESEARCH_PROTOCOL_V2.md` and
`research/hypotheses_v2/HV2_ENTRY_SPREAD_ATR_ROUTER.json`, with hashes. It has
not been run. Required verified quote-tape/fold pairing is not yet established;
there is no candidate and no basis to open any holdout. `FINAL_TEST=LOCKED`,
`DEMO=DISABLED`, `LIVE_TRADING=false`.
## Current project gate — 2026-10-22

Historical TRAIN work has tested 17 hypotheses total; none survived and no
candidate is frozen. No further hypothesis search is permitted without a
methodologically distinct preregistration or genuinely new permitted data.
The independent prospective cohort is still collection-only: 4 complete UTC
days, 545,461 ticks, 1,104 M5 bars, and 60 BUY / 61 SELL support signals in its
metadata health report. No labels or outcomes were read. The report is
`NOT_MATURE`; the calendar is unverified and the hash-chain prefix before its
audit anchor is unverifiable. Discovery Validation remains blocked and
FINAL_TEST remains locked. `DEMO=DISABLED`; `LIVE_TRADING=false`.
