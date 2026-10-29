# PC A remaining-blocker audit — 2026-10-28 (America/Guayaquil)

## Scope and preserved results

The original 79,211-tick historical diagnostic and its 276 exact native M5
contrasts remain unchanged. A fresh check still matches native OHLC and BID
volume exactly. Native MAIN_K and the prepared v3 metadata adapter retain their
verified parity. No approved native fixture or 150-row clock probe was rerun.
Original raw files, prior manifests and all previous scientific contracts remain
intact. New queries and derivations are separate evidence versions, not repairs
inserted into the prospective archive.

## Volume classification

The three requested native M5 windows were queried three times each. Comparisons
preserve row multiplicity, canonical numeric payload and separately analyze flags.
The exact original immutable segment membership is verified by SHA-256; a shorter
working snapshot was excluded before classification because it did not cover all
windows. Its draft is retained locally with an exclusion record.

| Native bar epoch (not UTC-normalized) | Original BID updates | Later BID updates | Native bar volume | Classification |
|---|---:|---:|---:|---|
| 1793217000 | 696 | 698 | 699 | Original undercoverage; one remaining tick/bar reference inconsistency |
| 1793218200 | 1131 | 1132 | 1132 | Original undercoverage relative to later broker history |
| 1793219100 | 1223 | 1225 | 1225 | Original undercoverage relative to later broker history |
| 1793220300 | 1543 | 1546 | 1546 | Additional undercoverage found in the enlarged audit |

The original three comparisons were stable over three repeat queries; the
supplemental fourth window was also checked three times. Earlier diagnostic
counts of 699 later ticks for the first window differ from the current 698,
while its native bar still reports 699. This supports reference/history
instability, not an invented explanation for network or broker internals.

The missing payload timestamps identify affected native five-minute buckets and
specific missing events. They do not certify corresponding UTC intervals.
Coverage and volume quality are affected. In the expanded comparison of 102 M5
bars, OHLC still agrees and four volume comparisons fail. OHLC agreement does
not prove complete ticks or causal volume features. No original values are
corrected. Missing original receipt evidence cannot be recovered by downloading
later history; these windows remain ineligible for accepted prospective data.
Late delivery, cache synchronization and broker revision cannot be uniquely
distinguished from these observations alone.

## What the clock evidence proves

The retained sealed attestation remains PASS **for its original interval**.
It binds Windows UTC, native TimeGMT/TimeLocal/TimeCurrent/TimeTradeServer and
tick timestamps over 50 frames / 150 records. It establishes the observed native
clock relationships in that capture, including server-minus-GMT +7200 seconds.
It does not establish independent UTC identity of each broker event, historical
offset/DST intervals or future clock precision. No mapping segment is authorized.

Because current event provenance was still unresolved, 50 additional read-only
Python quote/receipt measurements were necessary. They preserve monotonic/UTC
receipt brackets and native time/time_msc, with a three-host NTP quorum and TLS
Date corroboration. Units agree, but a receipt timestamp is not an event timestamp.
The observed native-minus-local-receipt range is evidence, not a forced offset.
There is no conversion installed, timestamp rewrite or future tolerance.

That measurement exposed a new current-clock problem: the local clock was
outside the diagnostic NTP interval by approximately 0.208–0.351 seconds, and
Windows Time reported leap indicator 3 (unsynchronized), despite a running
Automatic service. Unprivileged resync returned access denied 0x80070005.

The existing repair was executed through normal Windows UAC, with a bounded
collector pause, no process termination, recorded maintenance boundaries and
same-identity resume. Resync exited 0 and Windows Time then reported leap 0 / a
synchronized stratum. The first boundary log contained UTC but unavailable
monotonic values on Windows PowerShell's .NET runtime; it is **not** evidence of
an exact clock step. The future wrapper now uses Stopwatch ticks/frequency.
No timestamps were retrospectively changed or fabricated to fill that limitation.

A separate post-maintenance NTP/TLS diagnostic still placed local UTC outside
its interval by approximately 0.186–0.249 seconds. Therefore Windows service
synchronization is restored, but a new precise clock attestation is **not**
claimed. The approved earlier attestation is not extended to the current epoch.
Repeated probes cannot substitute for independent broker-event provenance.

## Calendar, sessions and DST

The existing legacy runtime policy belongs to `XMGlobal-MT5 10`; the active PC A
server is `XMGlobalSC-MT5 5`. They are not interchangeable. The approved current
native session export observes quotes Monday–Friday 00:00–23:00 and trade
sessions 00:05–22:55, Friday 00:05–22:50, in native labels. It is a weekly snapshot,
not an authoritative historical UTC/holiday calendar.

The official [XM equity-index page](https://www.xm.com/equity-indices) directs
users to their account for trading hours. The timezone FAQ is dynamically served
and could not be revalidated as readable content; direct read-only retrievals
were rejected. Third-party XM-branded mirrors, another broker's announcements
and an underlying futures exchange calendar were excluded as proof for this
exact server's US30Cash contract. No login or message to XM was attempted.

Pinned tzdata 2026.5 independently computes Europe/Nicosia and America/New_York
transitions for 2024 and 2026, including differing transition weeks. These are
human timezone diagnostics only: the broker's applicable historical DST rule
and holiday/early-close exceptions remain unverified. No EU/US rule or fixed
server offset is imposed on events. Runtime clock/calendar, server identity,
snapshot expiry, DST refresh, holiday-unknown and future-quote guards continue
to reject missing or mismatched evidence. Unknown sessions are not inferred from
the existence or absence of bars.

## Result and limits

Full suite: 268 tests, 259 passed, 9 skipped because g++ is absent. Compileall,
pip check, static no-order scan, retained parity seals and diff check passed.
The PowerShell maintenance wrapper passed parsing and its initial repair
pause/resume path executed successfully; its corrected future Stopwatch logging
was parsed, not rerun as a claimed attestation. New tests distinguish missing
multiplicity, quote revision, flag-only changes and unresolved tick/bar volume.

The collector is running read-only in raw quarantine with verified original
hashes and cursor continuity. Scientific completeness remains FAIL. The old
cohort is UNVERIFIED; a separate new scientific cohort is still prepared but
not activated and may not adopt this staging archive. New raw-query evidence
has a verified same-disk backup; no independent disaster-recovery backup is
claimed. No feature/label/PnL evaluation, adaptive training or protected split
inspection occurred. The other project and WSL were untouched.

HARD_BLOCKER: independent exact-server broker-event UTC provenance, bounded
historical mapping/transition evidence and an authoritative server-specific
calendar. Current precise clock attestation is also unverified. No remaining
safe software change can manufacture those facts. Capture continues while these
scientific acceptance gates remain closed: DISCOVERY_VALIDATION=BLOCKED,
FINAL_TEST=LOCKED, DEMO=DISABLED, LIVE_TRADING=false, BEST_CANDIDATE=NONE.
