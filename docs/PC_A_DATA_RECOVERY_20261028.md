# PC A data recovery and raw archival

The old PC is no longer a prerequisite for collecting new raw evidence. A separate
native-domain quarantine archive was activated on PC A at
2026-10-28T17:50:47.091197Z, ID `prospective_20261028T175047_3ac8b527`.
This is a staging archive, **not an accepted prospective validation cohort**.
The previous cohort's continuity remains UNVERIFIED. No old segments were adopted.
The frozen start, collector, metadata, maturity definition, splits and strategy
remain unchanged.

## What ran

GitHub branch HEAD initially matched `6abac62be37e48e8a8844c10512ae4f787d4495f`.
The public releases and Actions artifact endpoints returned zero entries. A bounded
filename search in this chat, the 2026-10-27 Codex workspace and top-level relevant
Downloads/Documents backup names found no usable old raw datasets or cohort state.
This is an accessible-scope search, not proof that no backup exists elsewhere.
Other project directories and WSL were not opened or modified.

The new historical archive `historical_20261028T175047_e97ee981` downloaded the
documented TRAIN diagnostic day **2024-01-02 in the native broker domain**:
79,211 ticks in 96 consecutive 15-minute query windows. MT5 returned zero M5 bars.
The range checkpoint completed; coverage/quality and UTC normalization did not.
This is a NEW_HISTORICAL_DATA_VERSION in raw quarantine, not an accepted rebuilt
research dataset. It does not establish independence from the exhausted TRAIN.
No signals, snapshots, labels, PnL or features were generated from it.

Native data and receipt UTC are stored separately. UTC datetime API arguments
encode numeric native query bounds only; they are not a demonstrated timezone
conversion. Enclosing seconds are queried and unchanged native milliseconds
partition windows. Legitimate identical tick rows retain their multiplicity.
The latest tick millisecond stays open until a later quote arrives. M5 has its
own complete-bar cursor. Each query is bounded to 15 minutes, each invocation to
16 windows (historical diagnostic: 96), with a 600-second child-process deadline.

The initial quote's freshness was unproven. A native cursor after that quote
does **not** prove that every acquired event occurred after activation UTC.
Late broker arrivals, replay/cache provenance, historical offset transitions,
holiday schedules and native-to-UTC mapping remain unverified. Consequently the
archive cannot prove prospective no-backfill in UTC, provide maturity/support
counts or enter training. There is no timestamp shift or added tolerance.
Human UTC views remain available through the existing verified-mapping API,
which continues to reject unverified mapping evidence.

## Operation

From the repository, run `tools/research_station.ps1 -Action <action>`.
Actions: `start`, `stop`, `resume`, `verify`, `collect`, `validate`, `reports`,
`historical`. Validation here means raw file hashes, collector identity, chain,
cursor continuity and closed scientific gates; it does not certify causal data.
`historical` resumes only the fixed diagnostic scope, not a new date range.

Task `StochasticGPTLab_PC_A_RawQuarantine_v1` runs every minute using the pinned
venv under the logged-in interactive user with limited privileges. It requires
the same XM DEMO terminal and server; it has no credentials or trading API.
The task ignores overlapping instances; an OS file lock serializes manual and
scheduled invocations. Failures preserve the last committed cursor. Orphan
files after an interrupted commit are never adopted. Stop disables future
scheduled invocations; an in-progress bounded invocation may finish.
The terminal must remain connected and this Windows user logged in. This is
not unattended operation across Windows logoff or loss of connectivity.

Primary: `outputs/pc_a_raw_archive/`; verified secondary local copy:
`outputs/pc_a_raw_backup/`. Each immutable compressed segment has SHA-256, query
and receipt bounds, and a chained entry digest. The backup is on the same disk;
there is no verified independent disaster-recovery backup. Raw data stay out of
GitHub. Published manifests are immutable snapshots of a growing local archive.

## Scientific and controller gates

C1: connected pinned XM DEMO verified. C2: existing exact-source EX5 seals and
zero-error/zero-warning compile records retained. C3: headless tester not rerun:
the running terminal and missing sealed split manifest prevent safe cold start.
C4: compiler artifacts verified; accepted tester datasets absent. C5: diagnostic
tick acquisition passes, M5/history reconstruction remains blocked.
No existing terminal was terminated to manufacture tester evidence.

The sealed clock probe remains PASS for its captured interval, 50 frames / 150
rows. No repeated probe was needed. Native MAIN_K parity retains its sealed PASS
(960 rows, 930 ready, five fixture families). Frozen metadata still FAILS native
equivalence; prepared metadata v2 stays inactive because its operational clock,
calendar and causal prerequisites are not satisfied. Original seals are preserved.

The chronological, BUY/SELL, FOLLOW/INVERT and purged walk-forward implementation
and its tests are present (`train_quality_direction_model.py`,
`train_intratrade_models.py`, `evaluate_train_exit_walkforward.py`,
`evaluate_train_intratrade_round2_wf.py`). A complete verified input dataset,
original split membership and admissible independent research data are absent.
No adaptive search or fit was run. TRAINING_PIPELINE=BLOCKED;
TRAINING_READINESS=BLOCKED_BY_RESEARCH_GOVERNANCE. Downloading the same historical
period does not create a new hypothesis budget.

BEST_CANDIDATE=NONE; DISCOVERY_VALIDATION=BLOCKED; FINAL_TEST=LOCKED;
DEMO=DISABLED; LIVE_TRADING=false; ORDERS_SENT=0. XM DEMO market-data access does
not enable the project's disabled DEMO execution gate.

Next state: autonomous native raw quarantine capture, awaiting demonstrable feed
timestamp provenance/mapping and a versioned causally admissible data contract.
No request for files from the old PC and no manual action is required to keep
the raw archive operating. Scientific gates cannot be removed by this controller.
