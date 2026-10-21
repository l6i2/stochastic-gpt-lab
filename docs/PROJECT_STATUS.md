# Project status

## Current checkpoint — 2026-10-21 (TRAIN V2 audit resumed)

Rechecked branch `research/full-pipeline` at `6bb8bb3f73ef33f17294611616c1887db4c2ef9a`.
No protected split or prospective-cohort values were opened for scoring. The
TRAIN split manifest binds the quality-v1 TRAIN parquet to 11,714 signals; the
existing `TRAIN_HOLD_BASELINE_REPLAY_PASS` proves 23,428 paired FOLLOW/INVERT
paths and explicitly records no Validation/FINAL_TEST access. The V2 runner
requires four purged expanding folds and verifies the source hashes before
replay. This verifies its frozen inputs and control path, not V2 outcome
metrics.

The output `outputs/bar_controller/research/train_entry_spread_atr_router.json`
does not exist. Thus the preregistered router remains **not evaluated** (zero
completed hypotheses; one frozen family prepared), not statistically rejected
or accepted. Replaying requires scanning approximately 1.4 GB of quote tapes
for the eligible 2024/2025 blocks on a 4 GB host with about 0.4 GB free at
check time; earlier full attempts were stopped after paging/runtime. No
candidate is available. The user-requested broader trajectory/MFE/MAE,
erosion/recovery, and volume/profile hypothesis families are outside the
frozen one-family V2 protocol and were not tested or added post hoc.

Twenty focused router, source-isolation, and safety tests passed; Python
`compileall` passed. The collector task is enabled, its scheduled 09:45 local
run returned code 0, and the latest scheduler log reports
`CAUGHT_UP_WAITING_FOR_CLOSED_DAY` with `live_trading=false`; no scoring or
backfill was performed. The future cohort remains immature under its fixed
rule. The safety authorization gate and hypothetical shadow recorder are
tested, but there is no executable DEMO order adapter; both remain disabled.
`DISCOVERY_VALIDATION=BLOCKED`, `FINAL_TEST=LOCKED`, `DEMO=DISABLED`, and
`LIVE_TRADING=false`.

## Current checkpoint — 2026-10-21 (TRAIN V2 runner prepared; replay incomplete)

Work continued on `research/full-pipeline`. No Discovery Validation, FINAL_TEST,
or FUTURE_VALIDATION_COHORT values were scored; no Demo or live orders were
enabled. The 16 R2–R4 hypotheses remain rejected and were not reused.

A frozen TRAIN-only entry-spread/ATR router runner and exact quote replay were
added for the preregistered V2 protocol. Input membership is 11,714 quality-v1
TRAIN signals; the accepted baseline provenance records 23,428 matched virtual
FOLLOW/INVERT paths. The runner validates the previous TRAIN replay proof and
source manifest bindings, evaluates 0/250/500 ms with four purged expanding
TRAIN folds, and applies the preregistered support, fold, threshold, latency,
block/session concentration, and drawdown gates. It does not load Validation,
FINAL_TEST, or future-cohort data. Focused isolation, replay, and safety tests
pass (20 total); `compileall` passes.

The first full V2 replay was stopped after excessive paging on this 4 GB host.
A second tick-by-tick replay was also stopped for runtime. Its final result file
was not written, so this is **not** a rejection or a survival result. The
replay was then changed to use an exact per-quote-block extrema index and
chronological entry ordering, with unit tests for first-hit SL/TP/TIME_EXIT
semantics. The optimized full replay has not yet completed. Therefore
`TRAIN_RESEARCH=INCOMPLETE`, no candidate exists, and no candidate is frozen.
Next step: complete the same preregistered runner on the isolated Python 3.12
environment and verify its JSON artifact before any Validation use.

The project-local `.venv-router` contains the declared dependencies plus Numba;
no global Python was modified. `DEMO=DISABLED`, `FINAL_TEST=LOCKED`, and
`LIVE_TRADING=false`. The future cohort remains unscored and immature; the last
provided collector state was healthy at 263,727 ticks / 552 M5 bars through
2026-10-20 23:59:58.880 UTC, but its latest scheduler execution was not
reverified during this continuation.

## Latest checkpoint — 2026-10-18 (TRAIN/Validation incident unresolved)

The R2–R4 retrospective isolation audit found that the exact R2 and R3 runner
sources are not preserved in the audited Git history. Their manifests report
`validation_accessed=false`, and the published metrics are TRAIN-fold metrics,
but those assertions do not independently prove that no Validation value
influenced execution or decisions. Status is therefore
`DISCOVERY_VALIDATION_CONTAMINATION=POTENTIAL`; the incident is not closed and
the existing Discovery Validation split is blocked from any future use until a
scientifically valid, independently auditable remediation is established.

All 16 R2–R4 hypotheses remain rejected in TRAIN; no new round or hypothesis
was created. See `docs/ISOLATION_INCIDENT_AUDIT.md`,
`docs/R2_R4_FAILURE_ANALYSIS.md`, and
`docs/INTRATRADE_NEXT_RESEARCH_PROPOSAL.md`. TRAIN loaders now reject explicit
Validation/FINAL_TEST paths before I/O, with focused tests. `FINAL_TEST=LOCKED`,
`DEMO=DISABLED`, and `LIVE_TRADING=false`.

## Latest checkpoint — 2026-10-18 (three TRAIN-only dynamic-exit rounds rejected)

Continued on `research/full-pipeline` at the existing repo state. Audited the
rejected R1 HA/Stochastic rules and did not reuse or retune them. Preregistered
and SHA-256-froze eight R2 hypotheses, four new R3 hypotheses, and four new R4
hypotheses before their replays. All three rounds used quality-v1 TRAIN only,
four expanding purged folds,
verified quote arrivals, and 0/250/500 ms execution latency. All replayed
decisions were causal; no targets were used as features. No hypotheses passed
the complete side-specific consistency, support, concentration, session/block,
latency, and drawdown gates. Discovery Validation was not scored in these
rounds; no candidate exists. No Validation outcomes were scored or used. The
first runners loaded the combined event source before restricting computations
to TRAIN IDs, so physical zero-read cannot be claimed; loaders now stream/filter
by TRAIN membership. See `docs/INTRATRADE_TRAIN_ROUNDS_REPORT.md`.

The closest result was R3 MAE recovery: +1.084 mean paired change versus FOLLOW
HOLD, all four overall folds positive, and stable latency; however SELL was
positive in only 2/4 folds and New York accounted for 55.0% of positive session
change. Its policy mean remained below INVERT HOLD. It is rejected without
retuning. The data derivative remains `PASS_INHERITED_VALIDATION`; the
aggregate row-by-row validator was not completed. Raw per-trade replay CSVs
remain local and excluded from Git.

The R4 continuation also produced no candidate. Stop expanding rules against
these same walk-forward folds until there is a prospective fixed search budget;
more adaptive rounds would increase selection risk. The single Discovery
Validation score remains unspent.

`FINAL_TEST=LOCKED`; `DEMO=DISABLED`; `LIVE_TRADING=false`; no real or Demo
orders were placed. The full metrics, frozen hypothesis hashes, and
reproducibility manifests are in the round report and local
`outputs/bar_controller/research/round{2,3,4}/` artifacts.

## Authoritative checkpoint — 2026-10-16 (quality-v1 entry model scored)

The quality-v1 signal-time entry-direction experiment is complete. It used
11,714 TRAIN events and scored the frozen models once on 4,077
DISCOVERY_VALIDATION events after validating schema/provenance, temporal
features, split membership, label horizons, fixed parameters, and FOLLOW/INVERT
mapping. The CSV correctly retains EA event schema 1.1; its four history
sources are individually validated producer schema 3.0. The study used a fixed
59-feature whitelist, three classifier families, seed 20261013, and threshold
0.5. Four expanding purged folds used TRAIN only.

No model beat FOLLOW-always on Validation. AUC was 0.488–0.501 and model mean
PnL ranged from -7.86 to -14.13 versus -3.81 for FOLLOW-always. The entry
direction hypothesis is rejected for promotion; no candidate exists. Results
and caveats are in `docs/QUALITY_DIRECTION_MODEL_REPORT.md`; local models and
metrics are under `outputs/models/quality_directional_v1/` and are excluded
from Git. The bounded replay runner independently rechecked the unchanged HOLD
baseline on all 11,714 quality-v1 TRAIN signals (23,428 FOLLOW/INVERT paths).
Exit reasons, quote indices/times, and PnL matched the validated source; source
quote tapes were hash-checked and rescanned for valid ordering and protected
boundaries. The local report is
`outputs/bar_controller/research/train_hold_replay.json`, status
`TRAIN_HOLD_BASELINE_REPLAY_PASS`.

Dynamic EXIT discovery then tested three frozen causal rules at 0/250/500 ms,
primary 250 ms, using TRAIN only. Expanding purged walk-forward selected rules
only on prior TRAIN data: 2/4 folds were positive, and the largest fold
contributed 69.7% of positive target-side change. The preregistered gate failed;
no rule proceeds to Validation and no candidate exists. Details:
`docs/DYNAMIC_EXIT_TRAIN_REPORT.md`. The entry-direction models were also
rejected for promotion. Neither experiment accessed FINAL_TEST. `LIVE_TRADING=false`;
no Demo execution occurred. The dynamic one-sided hypothesis is preserved as
`research/hypotheses/HYP-20261017-DYN-001.json` with status
`REJECTED_WALK_FORWARD_PRE_VALIDATION`; it was never evaluated on Validation.

## Authoritative checkpoint — 2026-10-16 (schema 3 history and quality gate)

The four permitted every-bar schema 3 blocks are complete and individually
validated: 2023-12-20..31, 2024, 2025, and 2026-01-01..03-19. The ordered quote
tapes cover 57,079,575 records; historical coverage stops before the protected
FINAL_TEST boundary (2026-03-20). The raw stream master is recorded as
`BUILT_NOT_PROMOTED`, with 2,480,241 snapshots and inherited TRAIN and
DISCOVERY_VALIDATION partitions.

The outcome-blind tick-quality derivative is at
`outputs/bar_controller/research/quality_v1/`. It excludes the entire 2023 block
(real-tick coverage warnings exceeded the preregistered 1% threshold) and 319
2024 signals whose feature/trade intervals overlap warned server dates plus the
two-day halo. It retains 15,791 event rows (7,398 BUY / 8,393 SELL), 2,388,383
snapshots, 2,388,383 targets, and 2,388,383 decision-arrival quotes. The filtered
parquets contain 1,810,478 TRAIN snapshots across 11,697 signals and 577,905
Discovery Validation snapshots across 4,074 signals. Artifacts and exclusions
have SHA-256 hashes in `tick_quality_manifest.json`.

Validation status is explicitly `PASS_INHERITED_VALIDATION`: all four source
blocks carry the full causal/schema-3 validator PASS; the derivative finalizer
recomputes exclusions and confirms exact event membership, inherited split
membership, frozen TP/SL/TIME_EXIT, row-count reconciliation, and hashes. A
second monolithic row-by-row validation of the 2.4M-row combined derivative was
stopped after Windows paged its multi-million-key maps and made no progress.
That aggregate validator did not finish, and this checkpoint does not claim a
second independent row-level PASS. The raw source proofs and deterministic
signal-level filter remain available for audit.

No hypothesis or model has been trained or validated from this derivative.
Existing schema-2 model/report code uses fixed-bar target deltas rather than
realizable ordered-quote policy replay; it is not valid promotion evidence for
schema 3. Next is to audit/implement a bounded TRAIN-only ordered-quote replay
and baseline parity path. FINAL_TEST remains locked; DEMO execution and live
trading remain disabled (`LIVE_TRADING=false`).

A feature-only TRAIN profile (1,810,478 rows / 11,697 signals) is available at
`outputs/gpt_research/train_schema3_quality_v1/`. It records descriptive
missingness and moments for Stochastic, volume, Heikin Ashi, profile, ATR,
spread and current virtual-position state. It read no targets or Validation
data and makes no edge, significance, or policy claim.

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

This section supersedes operational next-step statements in historical sections
below. December 2023 PASS. Interrupted 2024 run `r20261013T121405_09901cc2`
was recovered and rejected: no completed test or accepted artifacts. Replacement
`r20261014T052944_07590da1` is PASS after completed-run revalidation;
2025 run `r20261014T061439_70753a52` completed the tester; 2026-01-01..03-19 pending.
Acceptance is being retried on
the existing artifacts with endpoint contract v2, which classifies by entry
time (including a previous-bar cutoff one millisecond before midnight).
Accepted December evidence was preserved and not rerun. Postprocess is pending.

The local quote-mark correction matches the deployed compiled producer and
existing causal checkpoint. Twenty focused existing tests and two quality-audit
tests pass. `controller.data_quality` is prepared; it fails closed until all
historical blocks pass. `DYNAMIC_REPLAY_REQUIREMENTS.md` records pre-validation
exclusions and the ordered quote/decision extension required before dynamic
policy research. No new hypotheses or models have been validated.

FINAL_TEST=LOCKED; LIVE_TRADING=false; DEMO disabled; no candidate promoted.
The master objective does not guarantee that a credible candidate exists.

Preparatory schema 3 code and compile evidence are recorded in
`BAR_REPLAY_PREPARATION.json`; no rollout or research result is claimed.
Calibration/walk-forward helpers now purge label horizons across folds.

Coverage remediation: the frozen 2024/2025 source files end December 30. The
correct inclusive 2024 controller export contains 22 additional December 31
signals. They are retained in evidence but quarantined from research to preserve
the exact frozen signal universe, not mislabeled as boundary-purged signals.
`FROZEN_UNIVERSE_COVERAGE.json` pins the source hashes and exclusion dates before
new hypothesis validation. No split boundaries or memberships are changed.

## FASE 0 — baseline audit: COMPLETE

Repository: `l6i2/stochastic-gpt-lab`, isolated branch `research/full-pipeline`, audit baseline `d8f639578a409acd941ec35b6d5349a66d7007c4`. The pre-existing deletion of `mt5/StochasticResearchEA.mq5` in the user's original worktree remains untouched. No files in `asistente-trader-ia` were accessed or changed.

The completed XM DEMO smoke test used US30Cash M5, real ticks, optimization off, 2026-10-01 through 2026-10-11 server time. MT5 reported 888,125 ticks and 1,932 M5 bars. The audit contains 200 signals and 200 rows (95 BUY, 105 SELL), schema 1.1, `aborted=false`, and no fatal error. Each signal has both FOLLOW and INVERT virtual outcomes. CSV and a fastparquet round-trip both passed validation: 200 rows, 329 columns, 5 censored rows. The raw smoke dataset remains local and is not published.

The active XM MetaEditor build 6257 log reports 0 errors and 0 warnings; the `.ex5` exists. The deployed MQ5 and include files match the audited source. `LIVE_TRADING=false`; no trading operations were performed.

## FASE 1 — Python environment: PASS WITH NATIVE-TEST LIMIT

A project-local `.venv` uses isolated CPython 3.12.10 x64 via portable `uv`. System Python and PATH were not changed. NumPy 1.26.4, pandas 2.2.3, PyArrow 14.0.2, fastparquet 2026.9.0, scikit-learn 1.9.1, joblib 1.6.0, and the read-only MetaTrader5 Python API 5.0.5572 are available. `uv pip check` and `compileall` pass. The full unittest suite passes: 36 tests run, 27 pass, 9 native C++ tests skipped because `g++` is absent (702 seconds on this host).

After the final confidence-interval status correction, the three hypothesis-evaluation tests and `compileall` were rerun and passed. The full suite was not rerun after this small classification change.

PyArrow wheels crash on this host's CPU without SSE4.2; the new `python/parquet_io.py` selects fastparquet as the safe fallback. No global compiler or Python installation was added.

## FASE 2 — MT5 compilation: VERIFIED

The EA and two includes are together in the active XM terminal's `MQL5/Experts/StochasticResearch/`. Sanitized compiler evidence is `outputs/verification/metaeditor_compile.log` (0 errors, 0 warnings). No MQL5 logic or parameters were changed.

## FASE 3 — history coverage: MEASURED

MT5's local `MaxBars` was raised from 100,000 to 1,000,000 for this history audit, with a local backup kept outside the repository. The read-only terminal query returned 701,578 US30Cash M5 bars from server time 2011-08-10 00:00 through 2026-10-13 08:05. The next start position returned no more bars.

MT5 returned current bar/tick epochs about three hours ahead of the computer's UTC clock. XM documents GMT+2 in winter and GMT+3 in summer; the EA's existing default is `DST_EU`. UTC values in `outputs/history_coverage.json` are therefore labeled estimates derived by subtracting the seasonal offset, not raw broker timestamps. XM's published server offset is documented at [XM Help Center](https://www.xm.com/mena/help-center/trading-platforms).

Monthly real-tick queries from 2010-01 through 2023-11 returned no ticks; partial December 2023 begins at server time 2023-12-20 12:06:50.263. Every month from January 2024 through October 2026 (partial through Oct 13) had ticks. Intramonth missing intervals were not exhaustively classified. M5 candles extend much further than usable real ticks, so real-tick historical blocks must begin no earlier than 2023-12-20. Coverage details are in `outputs/history_coverage.json`.

## CHECKPOINT_A — historical data: COMPLETE WITH DATA WARNINGS

Four bounded Strategy Tester blocks cover all monthly real ticks returned by the active XM terminal: partial Dec 20–31, 2023; 2024; 2025; and Jan 1–Oct 13, 2026. Each used US30Cash M5, Every tick based on real ticks, optimization OFF, DEMO tester, and `LIVE_TRADING=false`. Each audit reports `aborted=false`; each canonical dataset passes `validate_dataset.py` with schema 1.1 (329 columns). The first 2025 export exposed a real serialization defect: 10-decimal formatting rounded one Stochastic value just below 80 to 80.0. The EA's numeric serializer was changed to 16 decimals without changing the strategy, recompiled to 0 errors/0 warnings, and the corrected export passed validation.

| Block | Signals | BUY | SELL | Tester data warning |
|---|---:|---:|---:|---|
| 2023-12-20..2023-12-31 | 210 | 96 | 114 | 106,168 mismatched tick prices across 1,230 minute bars; tester generated ticks for affected minutes |
| 2024 | 7,390 | 3,458 | 3,932 | 210 minute bars had real ticks discarded; generated ticks used |
| 2025 | 7,175 | 3,338 | 3,837 | None reported |
| 2026-01-01..2026-10-13 | 5,647 | 2,746 | 2,901 | None reported |

The canonical blocks contain 20,422 signals (9,638 BUY and 10,784 SELL), including 31 rows censored at end of data. `outputs/history/validation_status.csv` records both the initial failed 2025 export and its passing corrected rerun. Raw CSVs and tester logs remain local and are not published. Warnings for 2023 and 2024 are retained and materially limit claims about those intervals.

## CHECKPOINT_B — master dataset: BUILT, LOCAL

`python/build_master_dataset.py` verified the four canonical block audits, manifests, schema, strategy constants, chronological ordering, monotonic timestamps, symbol and signal uniqueness, causal features, and the real-tick/optimization/live-trading settings. No boundary duplicates were found. It wrote `outputs/master/stochastic_master.csv`, `stochastic_master.parquet`, `master_audit.json`, and `master_manifest.json`; SHA-256 of the Parquet master: `e2c05a24551078efb584cc4732b796846f3b98793d21978522b36be141de59c1`.

The chronological partition is 60/20/20 by signal count. The purged outputs contain 12,243 TRAIN and 4,077 DISCOVERY_VALIDATION signals. A standalone FINAL_TEST file was not written and its rows have not been analyzed; the full master necessarily contains the chronological tail and the split manifest records its protected boundary. The analyzer requires a frozen-hypothesis file for validation and an explicit unlock flag for any FINAL_TEST evaluation. No such unlock has been used.

`tests/test_master.py` checks safe configuration enforcement and confirms that the builder writes TRAIN/VALIDATION but no separate FINAL_TEST Parquet. Its first real-data build found a CSV/Parquet parsing-parity issue; the CSV reader and parity check were corrected, and the successful build round-tripped all 20,422 rows.

## CHECKPOINT_C — TRAIN analysis and descriptive walk-forward: COMPLETE

Descriptive analysis is restricted to TRAIN. The report includes ALL/BUY/SELL summaries, feature correlations, deciles, missingness, exits, and fixed Heikin-Ashi/volume/profile interaction tables. Five expanding temporal folds use TRAIN plus DISCOVERY_VALIDATION only; FINAL_TEST is excluded. Fold metrics include BUY/SELL counts, PnL, win rate, profit factor, and drawdown proxy. No thresholds have been optimized and no candidate has been selected.

## CHECKPOINT_D — hypotheses frozen: COMPLETE

One TRAIN-derived BUY-only hypothesis is registered and SHA-256 frozen. Its causal condition is Stochastic BUY plus bullish Heikin-Ashi at signal time; its target is paired FOLLOW minus INVERT PnL. It is side-specific by design and does not make a claim about SELL.

## CHECKPOINT_E — discovery validation: COMPLETE; HYPOTHESIS INCONCLUSIVE

The frozen BUY hypothesis was evaluated once on purged DISCOVERY_VALIDATION: 865 paired BUY observations, mean directional advantage −1.04 price units, with a week-cluster bootstrap 95% interval [−23.96, 22.87]. The interval crosses zero, so the result is INCONCLUSIVE under the project's uncertainty rule; it is not promoted. The result and hypothesis hash are local. FINAL_TEST was not read or evaluated.

## CHECKPOINT_F — walk-forward: BASELINE COMPLETE; ML INCOMPLETE

Five expanding descriptive folds were completed across TRAIN plus DISCOVERY_VALIDATION. The three-model ML walk-forward exceeded the practical runtime of this older CPU and was stopped after the base TRAIN fits; saved base models were scored on validation. This limitation is recorded in the local ML manifest rather than inferred as a pass.

## CHECKPOINT_G — model comparison: COMPLETE; NO CANDIDATE

All three simple classifiers were trained on 12,228 paired TRAIN labels and scored once on 4,070 paired DISCOVERY_VALIDATION outcomes (features: 225 causal columns; fixed 0.5 policy threshold). Validation ROC AUC: Logistic Regression 0.493, Random Forest 0.49, HistGradientBoosting 0.508. The model-switch policy mean PnL was −7.29, −1.81, and −2.30 respectively, against FOLLOW-always −3.83 and INVERT-always −8.50 on identical rows. These results are exploratory; the weak discrimination, incomplete ML walk-forward, and absent validated hypothesis prevent a candidate freeze. No model was selected or promoted.

## CHECKPOINT_H onward

No candidate is frozen, so `WAITING_FINAL_TEST_AUTHORIZATION` has not been reached. FINAL_TEST remains locked. Demo architecture and execution remain pending; no live or Demo trading occurred. Do not open FINAL_TEST or enable Demo execution until the promotion prerequisites exist, then stop and request explicit authorization before any held-out evaluation.

## Round-two research checkpoint

Round-two entry investigation, ten frozen hypotheses, one DISCOVERY_VALIDATION evaluation, fixed interaction analysis, and four controlled entry classifiers are documented in `docs/ROUND2_STATUS.md`. No hypothesis or model survived the predefined criteria. Intra-trade snapshot research is blocked because the frozen event dataset has no intervening open-position tick/bar path. FINAL_TEST remains unopened; Demo remains disabled.

## INTRA_A — intra-trade exporter compiled; smoke run rejected

The separate `mt5/StochasticIntratradeResearchEA.mq5` and schema 2.0 snapshot validator are ready. The exact deployed EA in the active XM data folder compiled in MetaEditor build 6257 with 0 errors and 0 warnings; regression tests assert that the frozen Stochastic thresholds and the base `TickTrade`/`BarTrade` routines are unchanged. `LIVE_TRADING=false`; no order APIs exist; the EA refuses chart/live use, optimization, and non-TICK_QUOTES mode.

MT5 generated an intra-trade run dated 2026-10-01 through 2026-10-12, which is after the protected 2026-03-20 FINAL_TEST boundary. Its tester log also shows the stale EA path `Experts\\StochasticResearch\\StochasticIntratradeResearchEA.ex5`, rather than the dedicated deployment path. Those files remain in the local tester-agent folder, were not copied into the repo, and are rejected for research. A structural-only validator pass did not verify split membership; the validator now reports the held-out status as unknown unless TRAIN and DISCOVERY_VALIDATION membership are supplied. The Jan 2024 smoke preset and historical tester configuration plan remain local; 2026 historical export stops on March 19. `docs/INTRATRADE_STATUS.md` records the blocked status and rerun requirements.

No intra-trade hypotheses or models were evaluated. No candidate exists. FINAL_TEST remains locked and DEMO execution remains disabled.

## INTRA_B — 2025 intra-trade annual audit: FAIL, rerun prepared

The 2025 real-tick export completed with 7,175 signals, 116,929 snapshots, and 116,825 targets. It failed the strict dataset validator: 207 snapshot rows have current unrealized PnL larger than recorded current MFE. The cause is mark-price reconstruction from bar close plus bar spread while excursions use actual tick quotes. Other full-scan checks found unique snapshot IDs, no current-MAE bound failures, no future timestamp violations, and correct FOLLOW/INVERT mapping. The dataset was not canonicalized and was not used for research.

A minimal exporter correction now uses the last observed bid/ask quote at the snapshot cutoff. The dedicated XM MetaEditor compile is clean (0 errors, 0 warnings), and the corrected annual preset is ready. No Tester rerun has started because the operator explicitly said not to rerun yet. The only next manual Tester run is the corrected 2025 preset. If it passes, run the remaining allowed periods: Dec 20–31, 2023; 2024; and Jan 1–Mar 19, 2026. Do not run on/after Mar 20, 2026. FINAL_TEST remains locked; no intra-trade master, hypothesis evaluation, model, or candidate exists.

## 2026-10-16 authoritative continuation checkpoint

Repo branch remains `research/full-pipeline`; initial HEAD was `71667a86597adee298cbfd56c37c6be55c162b40` and matched origin. Local changes from the preceding run were preserved and reviewed. Four schema 2 history blocks are accepted through 2026-03-19 and the protected boundary is 2026-03-20. Their master and descriptive TRAIN analysis are not dynamic-policy evidence.

Schema 3 producer `StochasticBarDecisionResearchEA` compiled in active XM MetaEditor build 6257 with 0 errors/0 warnings. Production-code future-mutation proof: 1,060 snapshots, 257 features, 404 quote-prefix records unchanged; baseline replay fixtures pass. The real Jan 2025 smoke passed in run `r20261016T154619_288daa1d`: 611 signals, 92,023 every-bar snapshots, 91,893 targets, 1,952,817 ticks, 5,850 M5 bars; dataset, snapshot, baseline replay and causal validators all PASS. `LIVE_TRADING=false`; Tester account DEMO; no execution was enabled.

Schema 3 history is not complete. Next safe action is to run only the four permitted blocks (2023-12-20..31, 2024, 2025, 2026-01-01..03-19) using the bar producer and isolated namespace. After all pass, build and quality-audit the schema 3 master, inherit only frozen TRAIN/VALIDATION membership, exclude quarantined nonmembers, and keep FINAL_TEST unmaterialized. Existing schema 2 analysis remains descriptive only; dynamic GPT/ML research has not started. FINAL_TEST locked, DEMO disabled, LIVE false.

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


## Prospective validation cohort checkpoint — 2026-10-18

Legacy `DISCOVERY_VALIDATION` remains `BLOCKED` because isolation cannot be proven; `FINAL_TEST` remains `LOCKED`. TRAIN-specific CSV/target loaders and research runner entrypoints reject protected split paths before file I/O. Pipeline stages that depend on contaminated legacy validation fail closed. Combined raw-source ingestion retains only frozen TRAIN signal IDs. The future cohort is excluded from hypothesis generation and selection by policy and TRAIN-reader guards.

The independent `FUTURE_VALIDATION_COHORT` protocol is preregistered with a fixed no-backfill start of `2026-10-19T00:00:00Z`, after the last frozen TRAIN signal (`2025-08-19T08:04:59.999Z`) and after historical source data. Its manifest is initialized and hashed; evaluation and TRAIN access are false. Raw US30Cash M5 bars/ticks are captured only after UTC-day close and a two-hour lag. A Windows Task Scheduler job is registered every 15 minutes starting 2026-10-19 00:15 local time under the interactive user, to attach to XM DEMO read-only. It does not backfill, create features/labels, or call trading APIs. First actual collection has not yet occurred.

Focused isolation and collector tests: 16 PASS; `compileall` PASS. Full suite: 130 PASS, 9 skipped because native `g++` is unavailable. `LIVE_TRADING=false`; DEMO execution remains disabled; no trade or Tester run was initiated. Evaluation of the future cohort is not authorized by this preparation. See `docs/FUTURE_VALIDATION_PROTOCOL.md` and `docs/FUTURE_VALIDATION_COLLECTOR_PLAN.md`.
## 2026-10-19 continuation — preparation state

The prospective cohort task is registered and healthy as a scheduler entry,
but has not yet captured a complete, settled cohort day: zero rows, no
successful collection, and cursor still at `2026-10-19T00:00:00Z`. The active
XM terminal is verified connected in DEMO with `US30Cash` available. Fixed
maturity gates are now published in `docs/FUTURE_VALIDATION_READINESS_RULE.md`.
A TRAIN-only
quote-friction router was preregistered in the V2 protocol and has not been
evaluated because paired quote-tape/fold inputs are not yet verified. There is
no credible or frozen candidate. A hash-bound, explicitly authorized,
single-use future evaluator and pure Demo safety gates are implemented and
covered with synthetic tests; they were not run on the actual cohort.
`DEMO_EXECUTOR=NOT_READY` (no candidate or MT5 order adapter).
`SHADOW_MODE=READY_BUT_DISABLED` (hypothetical recorder only, not connected to
MT5). `DISCOVERY_VALIDATION=BLOCKED`; `FINAL_TEST=LOCKED`; `DEMO=DISABLED`;
`LIVE_TRADING=false`.

## Collector activation check — 2026-10-19

One manual collection attempt returned `CAUGHT_UP_WAITING_FOR_CLOSED_DAY`;
zero rows were written and the fixed cursor was unchanged, so NO_BACKFILL
passes. Code now checks the UTC closed-day/settlement cutoff before initializing
MT5, avoiding unnecessary API attach attempts. The prior PowerShell scheduled
wrapper lingered after logging; the task now runs the project virtualenv Python
entrypoint directly. The task is Enabled/Ready, its last test run exited 0,
and it is scheduled every 15 minutes. Earliest eligible data capture is
2026-10-20 02:00 UTC, subject to the next scheduler tick.

## Future validation first settled capture — 2026-10-21

The first eligible instant was 2026-10-20 02:00 UTC, after the 2026-10-19
UTC day closed and its two-hour settlement lag elapsed. The collector captured
2026-10-19 at 2026-10-20 02:00:17.688 UTC, then captured 2026-10-20 at
2026-10-21 02:00:15.277 UTC. This sequential daily collection is within the
fixed cohort start and did not backfill: 263,727 ticks and 552 M5 bars across
both days. Latest observation is 2026-10-20T23:59:58.880Z. Manifest and all four compressed segment hashes
verify; manifest SHA-256 is
`77fd6d09235144590183897211db6efbc8d8871e5451ef56728028974f1f26d3`.
Collector health is `HEALTHY`, with no errors, active XM DEMO connection and
`US30Cash` available. The scheduled task is Enabled/Ready, last result 0, and
remains on its 15-minute cadence. Runtime cohort data remains local and is not
used for scoring, feature generation, or hypothesis selection.

TRAIN research remains incomplete: the preregistered V2 quote-friction router
has not been evaluated because paired quote-tape/fold inputs are not verified;
no best candidate exists. `DEMO_EXECUTOR=NOT_READY`,
`SHADOW_MODE=READY_BUT_DISABLED`, legacy `DISCOVERY_VALIDATION=BLOCKED`,
`FINAL_TEST=LOCKED`, `DEMO=DISABLED`, and `LIVE_TRADING=false`.
