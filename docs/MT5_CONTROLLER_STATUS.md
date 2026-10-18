# Controller verification status

## Latest checkpoint — 2026-10-18 (offline isolation audit; MT5 unchanged)

The TRAIN/Discovery Validation incident audit is POTENTIAL, not closed:
historical R2/R3 runner source bytes are absent even though their manifests
claim `validation_accessed=false`. The existing Discovery Validation split is
blocked pending a scientifically valid, independently auditable remediation.
No MT5, account, Strategy Tester, or EA action was taken. `FINAL_TEST=LOCKED`,
`DEMO=DISABLED`, and `LIVE_TRADING=false`. See
`docs/ISOLATION_INCIDENT_AUDIT.md` and `docs/PROJECT_STATUS.md`.

## Research checkpoint — 2026-10-18 (no MT5 action)

Three new intra-trade rounds (R2–R4; 16 hashed hypotheses) completed
TRAIN-only ordered-quote replay and four-fold purged evaluation. No hypothesis
passed all gates; no Discovery Validation score or FINAL_TEST access occurred.
No MT5 compile, tester run, account operation, or deployment was performed in
this continuation. `LIVE_TRADING=false`; Demo execution is disabled. See
`docs/INTRATRADE_TRAIN_ROUNDS_REPORT.md`.

## Authoritative checkpoint — 2026-10-16 (offline analysis; MT5 unchanged)

No MT5 or account interaction was needed for the offline quality-v1 entry
study, TRAIN HOLD replay, or dynamic EXIT discovery. The baseline runner
matched all 23,428 TRAIN virtual paths. The dynamic runner used 250 ms as its
primary latency (0/500 ms sensitivities); its purged TRAIN walk-forward failed
the predefined consistency gate, so no rule proceeds to Validation. The
validated history remains the four permitted XM DEMO Strategy Tester periods
through 2026-03-19; no orders were placed. `LIVE_TRADING=false`; DEMO execution
is disabled; FINAL_TEST remains locked.

## Authoritative checkpoint — 2026-10-16 (schema 3 history complete)

The MT5 XM DEMO historical runs are complete for the allowed periods only:
2023-12-20..31, 2024, 2025, and 2026-01-01..03-19. The four runs passed their
schema-3 event/snapshot/quote-path validators, causal invariance checks, and
frozen FOLLOW/INVERT baseline replay. The 2023 and 2024 logs contain tick
replacement/discard warnings; the outcome-blind quality gate excludes all
2023 data and a conservative date halo in 2024. 2025 and permitted 2026 have no
such warnings. Tester execution was DEMO with `LIVE_TRADING=false`; no real
trades were placed.

The source runs, tester logs, manifests, and quote paths remain local under
`outputs/bar_controller/runs/`; no large tick data or account information is
published. The local quality derivative is `outputs/bar_controller/research/
quality_v1/` and is recorded as `PASS_INHERITED_VALIDATION` with exact signal
membership, row counts, split inheritance, frozen parameters, and SHA-256
evidence. Its source validators were full PASS; the combined 2.4M-row validator
was stopped after severe Windows paging and is not represented as a completed
aggregate PASS.

The tester is not being relaunched. Next controller work is a local,
bounded-memory quote replay using the accepted per-block tapes; no tester UI
action or account change is needed. FINAL_TEST, Demo execution, and live trading
remain disabled.

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

This section supersedes the historical diagnostic below.
C1_ENV: recorded verified XM DEMO environment and read-only API evidence.
C2_COMPILE: deployed source matches repository; recorded clean 0/0 compile.
C3_HEADLESS_TESTER: cold-start operation verified by completed January smoke
and December 2023 exports; warm-instance failures below are historical.
C4_ARTIFACTS: accepted smoke/December nonce artifacts and hashes exist.
C5_HISTORY: INCOMPLETE. December 2023 PASS. Interrupted 2024 run
`r20261013T121405_09901cc2` recovered as FAIL, without completed test or export.
Replacement `r20261014T052944_07590da1` PASS after the frozen-universe endpoint-gap
remediation and completed-run revalidation. 2025 `r20261014T061439_70753a52`
tester PASS, acceptance retry with entry-clock endpoint contract v2; allowed 2026 pending.

The first strict membership validation correctly rejected 22 December 31 IDs
absent from frozen TRAIN/VALIDATION. `FROZEN_UNIVERSE_COVERAGE.json` now documents
the canonical end-date gap, pins original source hashes, and quarantines these
new observations from research without changing the frozen universe. Successful
tester evidence is reused for revalidation; no second 2024 backtest is launched.

CAUSAL_INVARIANCE: production fixture PASS, 156 snapshots across 257 columns,
future-only mutations and changed future targets. Finite fixture, not universal
proof. Producer hash matches the local quote-mark correction.
POSTPROCESS: pending all-block acceptance. CONTROLLER_C1_C5_COMPLETE not reached.
Quality audit implemented and tested; dynamic replay requirements documented
before new validation. Twenty focused existing tests and two new audit tests pass.

Preparatory every-bar producer: versioned derivation built outside the deployed
EA, clean 0-error/0-warning compile. Hashes and explicit NOT_DEPLOYED/NOT_RUN
gates are in `BAR_REPLAY_PREPARATION.json`. This is not a new causal acceptance
or an accepted historical dataset. The current C5 tester still uses schema 2.0.

FINAL_TEST=LOCKED; LIVE_TRADING=false; DEMO_EXECUTOR=NOT_IMPLEMENTED.

## Historical diagnostic (superseded)

2026-10-13: C1 verified against running XM, unique Data Folder
20C285FE08971A9A2E814AAC44AFC9D2. Read-only API reports connected DEMO,
US30Cash available. DEMO executor is NOT_IMPLEMENTED and disabled.
Two environment unit tests pass. CIM discovery timed out; psutil discovery works.

C2 PASS: active dedicated source and includes match repository working files.
MetaEditor compiled with 0 errors and 0 warnings; EX5 and SHA-256 recorded.

C3 FAIL: two documented /config launches (UTF-16 and ASCII) returned exit 0
without fresh tester logs, tester agent process, or nonce-named output artifacts.
The original XM PID 7880 remained active. This is consistent with an existing
instance ignoring startup configuration; causation needs a clean-start check.
No terminal process was terminated. No mouse/keyboard automation was used.

C4 and C5: source implemented, end-to-end acceptance BLOCKED by C3. The checkpoint
contains PENDING blocks 2023-12-20..31, 2024, 2025, and 2026-01-01..03-19.
History refuses execution without a validated smoke run and causal acceptance.
Eight controller tests pass. Existing profile future-perturbation test passes.
This proves the reference causal profile only; whole snapshot producer invariance
is NOT_VERIFIED and is a second acceptance blocker. Native g++ tests are unavailable.
No CONTROLLER_C1_C5_COMPLETE checkpoint was written.

MANUAL_ACTION: close XM normally once it is idle, then launch it with the saved
recovery.ini in run r20261013T112613_6b130b68. This is a clean-start diagnostic,
not an accepted smoke result. Do not select a different account.

After tester completion, from this worktree use:
`.venv\Scripts\python.exe -m controller.controller resume --run-id r20261013T112613_6b130b68`.
It verifies the source/binary and nonce, then runs split-aware validators. It will
not approve causality automatically or unlock history without the missing proof.

FINAL_TEST remains locked; live trading is false. DEMO_EXECUTOR=NOT_IMPLEMENTED.

## Continuation checkpoint — 2026-10-16

Real state audit: branch `research/full-pipeline`, HEAD `71667a86597adee298cbfd56c37c6be55c162b40` initially equal to origin; XM terminal is closed after Tester; no account settings changed. Existing schema 2 history checkpoints and postprocess manifest show four permitted blocks PASS, master schema 2 built with only TRAIN and DISCOVERY_VALIDATION partitions, 816 quarantined snapshot rows/169 purged, and descriptive TRAIN analysis only. This scheduled snapshot dataset does not model executable dynamic exits.

Schema 3 every-bar/quote-tape exporter is now compiled 0/0, future-invariance proof PASS (1,060 snapshots, 257 features, exact 404-record quote prefix), synthetic frozen-baseline replay PASS, and real Jan 2025 smoke PASS (611 events; 92,023 snapshots; 91,893 targets; 1,952,817 real ticks; 5,850 bars). Run `r20261016T154619_288daa1d` validated events, snapshots, quote path, trade index, baseline parity and source causal proof. Tester was DEMO, `LIVE_TRADING=false`, no trading calls.

Four full schema 3 history blocks remain. The postprocess/master/research stages must use the schema 3 quote tapes and avoid legacy lifetime-extrema delta labels. FINAL_TEST (from 2026-03-20) remains locked and DEMO execution remains disabled.

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

# Research controller checkpoint — 2026-10-18

TRAIN-only intra-trade dynamic exit exploration completed two preregistered
rounds (8 + 4 frozen hypotheses). Every policy used causal snapshots and the
validated ordered quote replay at 0/250/500 ms. No hypothesis met the complete
walk-forward and robustness gates; Discovery Validation and FINAL_TEST remain
unopened. No MT5 compile, tester run, account operation, or deployment was
performed in this research continuation. `LIVE_TRADING=false`; Demo execution
is disabled. Report: `docs/INTRATRADE_TRAIN_ROUNDS_REPORT.md`.


## Prospective cohort collector — 2026-10-18

A read-only collector for future US30Cash M5 data is prepared and its Windows Scheduled Task is registered as `StochasticGptLabFutureValidationCollector` (next run: 2026-10-19 00:15:15 local). It runs every 15 minutes under the current interactive user and requires the active XM terminal, DEMO trade mode, exact symbol, and matching Data Folder; it supplies no credentials and calls no order API. It only collects closed UTC days after a two-hour lag, with a fixed UTC start of 2026-10-19 and no backfill. The empty cohort manifest has been initialized and hashed. Setup did not connect to MT5 or execute the task. First collection is pending; no trade/Tester action occurred. `LIVE_TRADING=false`; DEMO execution disabled. See `docs/FUTURE_VALIDATION_COLLECTOR_PLAN.md`.
