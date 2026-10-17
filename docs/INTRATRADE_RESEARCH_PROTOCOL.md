# Intra-trade research protocol (round 2)

## Current schema 3 checkpoint (2026-10-16)

### Fixed entry-direction study (preregistered before Discovery Validation)

The quality-v1 event table keeps the EA event schema `1.1`; its provenance is
the four accepted schema `3.0` historical blocks and their causal validators.
Do not describe the event rows themselves as schema 3. The entry-direction
study asks whether signal-time context can choose between the frozen FOLLOW
and INVERT outcomes. It is a separate, fixed-exit entry decision and does not
claim to evaluate a dynamic intra-trade exit policy.

The one planned comparison uses the outcome-blind quality-v1 events, frozen
TRAIN and DISCOVERY_VALIDATION memberships, the existing `ROUND2_BASE_FEATURES`
plus its fixed ten interaction features, and three fixed classifiers:
logistic regression, random forest, and histogram gradient boosting (seed
20261013). The target is `directional_advantage > 0`; threshold is 0.5. Compare
against FOLLOW-always and INVERT-always on the same complete-label cases. Keep
censored rows in the coverage counts and never discard losses. Validation is
scored once; there is no threshold/model selection after seeing it. Expanding
purged walk-forward folds use TRAIN only. No candidate is promoted by this
study; dynamic quote replay and policy robustness remain separate gates.

### Dynamic EXIT discovery contract

The TRAIN-only rule family consists of the first open-trade snapshot where
(1) `ha_direction * virtual_side < 0`, (2)
`(stoch_k - stoch_d) * virtual_side < 0`, or (3) both are true. Missing inputs
do not trigger an exit. Rules use only signal-time-causal snapshot fields;
decision features and mark time must be no later than the decision cutoff.
Execution is at the first quote strictly after the arrival quote plus latency;
an intervening frozen SL, TP, or TIME_EXIT takes precedence. The primary
latency is 250 ms, with fixed sensitivities of 0 and 500 ms.

Discovery selects at most one rule using TRAIN only: maximize mean paired PnL
change among FOLLOW-mode SELL-position trades at 250 ms; exact ties use the
fixed rule order HA, Stochastic K/D, then both. BUY and INVERT are not selection
targets and are still reported; the frozen candidate leaves those paths at the
baseline. Walk-forward refits this same selection rule inside each expanding,
purged TRAIN fold and reports its untouched later fold. Only the single
full-TRAIN-selected rule can be tested once on DISCOVERY_VALIDATION, after the
walk-forward and minimum-support/uncertainty gates pass. The hypothesis,
dataset, feature contract, selection rule, and code hash must be recorded
before that score. The 0/500 ms results are sensitivity checks and cannot
replace the 250 ms primary result.

The old schema-2 limitations below describe historical evidence only. The
allowed schema-3 every-bar blocks now provide rows for each observed open-trade
bar, ordered quote tapes, per-trade quote-index bounds, and exact decision
arrival quotes. All four permitted raw blocks individually passed full source
validation and frozen-HOLD replay. A quality-gated derivative excludes all
2023 rows and 319 2024 warning-window signals before research; see
`docs/PROJECT_STATUS.md` and `outputs/bar_controller/research/quality_v1/`.

The derivative's validation is inherited from those block proofs plus exact
membership, split, frozen-parameter, row-count and hash checks. The monolithic
combined validator was interrupted after paging; do not describe it as an
aggregate row-by-row PASS. Only its TRAIN/Discovery Validation partitions are
eligible for discovery. The legacy schema-2 trainer's fixed-bar calculation
is descriptive, not an executable policy backtest.

The bounded-memory HOLD replay is implemented and matched all 23,428 frozen
TRAIN virtual paths against the source exit, quote, timestamp, and PnL records.
The three-rule dynamic EXIT discovery was also replayed on TRAIN at the frozen
latencies. Its expanding, purged walk-forward was positive in 2/4 folds and
failed the predefined consistency and fold-concentration gates. Therefore no
dynamic rule is eligible for DISCOVERY_VALIDATION and no candidate exists.
Dynamic reversal remains unsupported until reverse-entry and post-original-exit
quote paths are validated. FINAL_TEST remains locked.

## Status and data gate

The frozen entry dataset has one record per Stochastic signal and terminal FOLLOW/INVERT summaries. It does not contain intervening state. The separate `StochasticIntratradeResearchEA.mq5` is prepared to export actual open-trade snapshots at +1, +2, +3, +5, +10, +15, +20, +30, and +50 completed bars. It compiles, but no snapshot block has been run or validated yet.

The exporter records scheduled states from the completed M5 bar, bid close, recorded bar spread, running virtual MFE/MAE, M5 OHLC/volume, Stochastic, Heikin Ashi, EMA/ATR, structure, session, and causal Volume Profile fields. Provenance includes `signal_id`, snapshot offset/time, feature cutoff, and virtual mode/side. Outputs are schema 2.0 snapshots and separately written future targets. They must be generated by Strategy Tester using the unchanged strategy core, real ticks, and `LIVE_TRADING=false`; the entry and exit simulation routines remain unchanged.

## Snapshot contract

One row per `(signal_id, virtual_mode, snapshot_bar)` only when the virtual position remains open at that completed bar. `feature_max_time_msc <= snapshot_time_msc`; the mark quote time is also no later than the cutoff. Split membership is inherited from the original signal ID. Features are as-of snapshot only; future labels are stored separately and excluded from the training whitelist. Export must stop before the FINAL_TEST boundary, and discovery tools refuse unknown split IDs.

The fixed reversal label is one only when MFE at snapshot is at least 60 price units and MFE at snapshot minus final directional PnL is at least 120, or the fixed trade exits at SL. Targets also report TP/SL after snapshot, future directional PnL, additional favorable/adverse excursion, profit erosion, and recovery after drawdown. Hypothesis files are hashed before validation; validation is single-use. End-of-data states are censored.

The current export contains scheduled states and terminal labels, not the ordered post-snapshot tick path. Early exit at a fixed scheduled bar can be compared descriptively; dynamic tick exits and reverse-direction TP/SL cannot be faithfully simulated until ordered future quotes are added. No policy is eligible for promotion from this source alone.

## Operational guard

This is research-only. No dynamic exit, position reversal, skip, or trade execution policy may be deployed from these analyses. Baseline remains the existing fixed TP 240, SL 180, TIME_EXIT 100 behavior. `LIVE_TRADING=false`; DEMO execution remains disabled, and FINAL_TEST remains locked until its explicit authorization gate.
