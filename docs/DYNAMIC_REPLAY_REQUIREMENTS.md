# Dynamic replay acceptance gate

This gate is declared before any new intra-trade hypothesis validation. It does
not change the frozen entry trigger, TP 240, SL 180, TIME_EXIT 100, splits, or
FOLLOW/INVERT semantics. FINAL_TEST remains locked; execution remains disabled.

## Current source limitations

The schema 2.0 schedule at bars 1,2,3,5,10,15,20,30,50 is not a complete
decision path. It cannot support tick-triggered protection, dynamic reversal,
or arbitrary bar-by-bar decisions. A mark observed before a completed-bar
decision is not an executable fill after that decision. Do not equate its PnL
with the realizable PnL of an early exit.

The current future excursion labels subtract running extrema at the snapshot
from terminal running extrema. These are increments in lifetime extrema,
not the maximum favorable/adverse movement of quotes after the snapshot.
They cannot label future drawdown/recovery faithfully. The recovery label
derived from these increments is unavailable for promotion research.

`recent_high_break` and `recent_low_break` currently compare the current bar
against a window containing that bar. They cannot detect a strict break and
must be excluded until a versioned, past-window feature has been tested.

## Required versioned extension

Keep schema 2.0 evidence intact. A separate producer version must first declare
its policy class. A bar-boundary HOLD/EXIT-only class can use complete per-bar
states, actual first-next-quote fills and frozen baseline exit events; it must
not be presented as a tick-triggered or reversal simulation. The broader kernel
requires an ordered quote stream. Required evidence for the broader class is:

- Every completed-bar decision state while each baseline virtual trade is open,
  including bars beyond 50 through its frozen exit, with exact cutoff and
  ordered decision sequence.
- A shared ordered bid/ask quote stream, with millisecond timestamps and a
  sequence number for equal timestamps. It must cover every replay interval,
  including after the original trade exits when a predeclared reverse policy
  would remain open. No inference of intrabar order from OHLC is permitted.
- The first available quote strictly after each decision cutoff. BUY exits use
  bid and SELL exits use ask; reverse entries use the opposite executable side.
  Missing quotes, gaps and censored continuation must be explicit.
- Separate future targets computed from the actual post-cutoff path, rather
  than differences of lifetime extrema. Future columns never enter features.

Bound the policy class and its maximum horizon before export; never extend
through a protected split boundary. If a counterfactual cannot be observed
within its allowed partition, censor it without examining protected data.
Reconstruct the frozen HOLD baseline exactly before comparing new policies.

## Acceptance evidence

Require baseline event parity, source/include/binary hashes, clean 0/0 compile,
future-only input perturbation with unchanged past states, changed future-label
positive control, and replay fixtures for spread, gaps, equal timestamps,
TP/SL ordering, time exit, decision/fill ordering and censoring. Validate split
membership and label horizons independently. Regenerate only data necessary
for this new version; do not overwrite accepted schema 2.0 blocks.

Do not freeze or validate dynamic policies until this gate passes. Existing
intra-trade prototype hypothesis support checks are not a substitute for the
project's bootstrap, multiplicity, walk-forward and robustness gates.

## Data-quality exclusions declared before new validation

The accepted December 2023 log reports real ticks discarded for 1,230 of 9,635
minute bars, with generated-tick substitution. This is HIGH severity for path
generalization. Do not infer raw-tick microstructure or sub-minute execution
advantages from a block with any reported generated-tick substitution. Keep
its evidence and disclose it; do not drop individual losing observations.
Any coarse bar-policy analysis must retain an explicitly labeled synthetic-tick
sensitivity report and cannot claim verified real-market execution fidelity.
Apply this rule consistently to every year, before inspecting policy outcomes.

Real volume is zero throughout accepted December snapshots. Until verified
nonzero trade-volume coverage exists, exclude real-trade-volume hypothesis
families; tick activity and relative tick volume must retain their actual names.
Unavailable profile/HA features use an explicit missing policy frozen before
validation, never outcome-dependent imputation.

## Preparatory code, not accepted replay evidence

`python/quote_replay.py` is an experimental kernel with synthetic fixtures for
strictly post-cutoff execution, bid/ask spread, gap SL, fixed TP, time-exit
precedence, censoring and protected-boundary rejection. It has no dataset or
promotion CLI and does not make the missing production trajectory available.
It supports HOLD/EXIT only, requires independently validated ordered coverage,
and must pass baseline parity on actual exports before policy evaluation.
Execution-delay, spread/slippage stress and missing-quote policies must be
frozen before validation. No candidate can be inferred from its unit tests.

Temporal calibration and walk-forward training now purge complete signal groups
whose observed label horizons reach the next fold. Calibration folds with no
remaining training support fail rather than silently leak future labels.

The current preparation revision additionally exports every observed bid/ask
quote as little-endian `<qddi` records (28 bytes: millisecond time, bid, ask,
observed bar index). Record position is the quote sequence. A separate trade
index binds native entries and exits to exact quote indices. The CSV previously
called execution quotes records decision-arrival quotes; these are not policy
fills. A real policy fill must use a strictly later sequence and its predeclared
latency. Binary path validation replays frozen SL/TP/time exit, gap prices,
MFE/MAE, entry/exit times and observed-bar lifetimes before acceptance.
