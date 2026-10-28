# M5 recovery verified after XM terminal restart

On 2026-10-28 the user confirmed applying Max. bars in chart = 500000 and
restarting the project's XM MT5 installation. The read-only API independently
confirmed maxbars=500000 and a connected pinned DEMO environment. The scheduled
retry completed, and a fresh manual diagnostic independently reproduced it.

All **276** M5 bars derived deterministically from the original **79,211** ticks
for the native diagnostic day 2024-01-02 now match native CopyRates exactly:
OHLC and BID-update tick volume, zero tolerance, no differences, no missing or
out-of-range native bars. No raw segment was modified, replaced or backfilled.
This resolves the historical M5 availability and native reconstruction contrast
blocker for that day only. It does not certify broader historical coverage,
independent TRAIN data, UTC mapping, calendar coverage or causal acceptance.

The same raw archive `prospective_20261028T175047_3ac8b527` resumed after the
user-confirmed terminal restart with its original cursor and chain. All referenced
raw hashes and cursor continuity were verified. No new cohort identity was
allocated and no previous cohort segments were adopted. Windows reboot was not
performed. Fresh collector processes run every minute, with a same-user logon
trigger; Windows login and connected XM remain operational prerequisites.

The recent raw staging comparison covers 19 native bars. OHLC agrees, but three
tick-volume discrepancies remain. Re-querying cannot retroactively recover the
original prospective receipt evidence, so those records remain quarantined and
are not overwritten. This is not an accepted scientific prospective cohort.

The separate prepared MAIN_K metadata v3 retains its scoped native parity PASS;
legacy metadata remains incompatible and unchanged. Neither v3 nor a new
scientific cohort is activated. The independently paired clock attestation remains
valid for its captured interval, but no authorized native-to-UTC mapping exists.
Independent event-time provenance, applicable historical offset transitions and
an official versioned session/holiday calendar remain external evidence blockers.
No arbitrary timestamp shift or future tolerance is installed.

Post-restart targeted tests: **18 passed**, zero failures. No implementation code
changed after the last full suite: 264 total, 255 passed, 9 skipped for absent
g++. The updated evidence is separate from all prior immutable snapshots.

No manual action is required for the corrected chart limit or continued raw
capture. Scientific acceptance remains fail-closed. TRAINING_READINESS remains
BLOCKED_BY_RESEARCH_GOVERNANCE; BEST_CANDIDATE=NONE;
DISCOVERY_VALIDATION=BLOCKED; FINAL_TEST=LOCKED; DEMO=DISABLED;
LIVE_TRADING=false; ORDERS_SENT=0. The other project and WSL were untouched.
