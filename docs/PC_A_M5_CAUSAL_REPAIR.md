# PC A M5 and causal repair — 2026-10-28

## Reproduced cause of historical M5 absence

The pinned XMGlobalSC-MT5 5 terminal reports `maxbars=100000`. Asking CopyRates
for 2024-01-02 returns one bar at native epoch 1748623500 (May 2025), outside the
requested interval. A historical M1 request likewise returned an out-of-range
bar. Recent M5 requests return valid bars. The old archive correctly filtered
out-of-range results; zero retained bars did not mean zero underlying ticks.
The terminal's chart-history limit is the diagnosed limiting condition, subject
to a post-change verification rather than an assumed successful repair.

MetaQuotes documents that Python CopyRates is limited by chart history and
"Max. bars in chart": [official reference](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py).
Changing that setting is the outstanding manual operation: Tools → Options →
Charts → Max. bars in chart = 500000; accept and restart only the pinned XM
terminal. Desktop automation opened Options but repeatedly rejected its controls
with `element ... is not available in cached app state`; no authentication,
security or Algo Trading setting was changed.

`retry_m5_repair.py` runs after scheduled raw collection. At maxbars below 500000
it records WAITING, leaving capture operational. Once the new value is observed,
it repeats the bounded comparison, up to three attempts with deadlines. A
completed retry means execution completed, never scientific acceptance. Results
remain under `outputs/pc_a_data_repair/latest.json` and `chart_limit_retry.json`.

## Deterministic native-domain derivation

The immutable 79,211 historical ticks produce **276** nonempty M5 BID-update
bars in the diagnostic native day. No empty bucket or boundary-partial bar is
filled. Prices use integer units of the observed native tick size 0.01. Every
raw timestamp is retained; no UTC mapping is installed. All raw quote rows are
preserved. Derived BID volume counts the native BID-update flag, excluding
ASK-only events. This accounting is explicit and remains subject to native
comparison; raw quote count is a separate measurement.

The latest committed audit compared **18** fully acquired recent bars: all
OHLC fields matched exactly and **3** tick-volume comparisons failed. Historical
OHLC could not be contrasted because no native historical reference was returned
in range. Therefore the reconstruction is PARTIAL/QUARANTINED, not accepted data.

Independent re-queries of discrepant recent windows found: 696 archived ticks
versus 699 later ticks/native volume in one bar; 1131 versus 1132 in another;
and a separate bar with 1223 ticks versus native volume 1225. Some native flags
also changed between live archive and later historical queries. These show
late-arrival/revision/completeness uncertainty; the original archive is not
rewritten. ASK-only differences explain two other discrepancies, but do not
repair the remaining three. No new receipt time is attributed to redownloaded
ticks and no retrospective segment is inserted into the prospective archive.

## Metadata and temporal evidence

`native_metadata_v3.py` is a new streaming ratio-of-sums MAIN_K adapter. Against
the existing sealed native export it matches 930 ready rows and 30 warmup rows
across all five fixture families within the existing fixed 1e-10 tolerance.
The maximum observed error is approximately 1.11e-16. Seven closed bars are
required and a zero slowing denominator returns 100, as the native fixture does.
The separate v3 prepared spec binds this adapter and native evidence. Frozen
v1/v2 files, strategy, crossings, regime/support/duration thresholds and legacy
counts are unchanged. Prepared v3 activation remains forbidden until mapping,
calendar and causal prerequisites pass. Legacy metadata incompatibility remains
FAIL; MAIN_K-v3 compatibility is a scoped PASS, not full operational acceptance.

The retained independently paired clock capture passes its original interval.
All 150 native quotes appear after the receipt upper bound if treated as UTC.
The observed +7200-second candidate removes those violations in this interval,
but does not prove independent event UTC identity or historical/DST transitions.
It remains a diagnostic hypothesis. Authorized mapping segments stay empty;
no quote timestamps were shifted and future tolerance remains zero. See
`PC_A_TIME_PROVENANCE_REQUIREMENTS.md` for the missing evidence, which does not
require the old PC. Global CAUSAL_AUDIT remains FAIL.

## Capture, restart and cohort isolation

The original raw collector code/hash and raw manifests are preserved. Scheduled
invocations use fresh processes, verify the chain and resume the same native
cursor; no orphan files are adopted. Stop/resume was verified previously and the
current modified controller was resumed successfully. The scheduler now has a
same-user logon trigger as well as its one-minute trigger, limited privileges,
hidden Python, IgnoreNew overlap handling and verified local backup. A Windows
reboot itself was not performed; terminal restart after the chart change remains
to be observed. Logged-in Windows and connected XM DEMO remain prerequisites.

`pc_a_new_cohort_activation_plan_v1.json` prepares a distinct future cohort:
actual independently attested activation UTC; no adoption of old cohort or PC A
raw staging; no backfill; frozen closed-day plus two-hour settlement lag; new
hash chain and code/mapping/spec seals; unchanged maturity definition. It is
explicitly not active. Previous continuity is UNVERIFIED, not asserted globally
irrecoverable. Current raw staging cannot be relabeled as accepted prospective
evidence because initial quote freshness and UTC no-backfill are unproven.

## Verification and gates

264 tests ran: 255 passed, 9 skipped because g++ is absent. Native scalar-core
tests were not run. Python compileall, pip check, static no-order scan, retained
MAIN_K evidence seals and git diff check passed. The new tests include boundary
and gap handling, flag accounting, exact price-grid comparison, future-prefix
causality, five-family metadata parity and preservation of frozen thresholds.

No fit, adaptive hypothesis search, features, labels, PnL, outcome evaluation,
validation or final-test inspection ran. TRAINING_READINESS remains
BLOCKED_BY_RESEARCH_GOVERNANCE. BEST_CANDIDATE=NONE,
DISCOVERY_VALIDATION=BLOCKED, FINAL_TEST=LOCKED, DEMO=DISABLED,
LIVE_TRADING=false, ORDERS_SENT=0. Only this project's pinned installation and
repository were used. The other project and WSL remain untouched.

Next state: maintain raw capture and automatically recheck M5 after the single
chart-limit action; keep scientific acceptance blocked pending native historical
comparison, independent UTC event provenance and a versioned session calendar.
