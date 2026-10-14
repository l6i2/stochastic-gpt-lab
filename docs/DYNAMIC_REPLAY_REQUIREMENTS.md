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

Keep schema 2.0 evidence intact. A separate producer version must export:

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
