# Temporal semantics, evidence intake and data-free preparation

## Findings from primary documentation

Ticks, bars, receipt clocks and session labels are different claims. The
[Python tick API](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py)
and [bar API](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py)
describe returned time as UTC. These are generic interface claims; neither
identifies XMGlobalSC-MT5 5 or certifies its captured US30Cash records. The
approved capture's native quote labels are inconsistent with treating them
directly as contemporaneous UTC. A timezone encoding, broker clock error,
stale/replayed state or other provenance issue cannot be uniquely selected from
that observation. No automatic offset or tolerance is justified.

[TimeCurrent](https://www.mql5.com/en/docs/dateandtime/timecurrent) describes the
last known server quote time. It is not a separately authenticated UTC clock.
[TimeTradeServer](https://www.mql5.com/en/docs/dateandtime/timetradeserver) is
client-calculated and depends on the PC clock; it is not an independent second
server clock vote. [TimeGMT](https://www.mql5.com/en/docs/dateandtime/timegmt) is
calculated from the computer's local time/DST configuration. In the strategy
tester it follows simulated server time, so replaying a tester cannot supply
the missing independent historical UTC anchor.

[MqlTick](https://www.mql5.com/en/docs/constants/structures/mqltick) distinguishes
seconds and milliseconds for the last price update, but its structure has no
independently authenticated broker-event ID or timezone field. A hash identifies
a preserved artifact, not the actual UTC of the market event. Repeated identical
quotes or milliseconds require explicit uniqueness/multiplicity evidence when
matching an independent event record.

[SymbolInfoSessionQuote](https://www.mql5.com/en/docs/marketinformation/symbolinfosessionquote)
and [SymbolInfoSessionTrade](https://www.mql5.com/en/docs/marketinformation/symbolinfosessiontrade)
return weekday session times of day with the date component disregarded. A
current weekly table does not contain dated historical exceptions. The
[XM public index page](https://www.xm.com/equity-indices) directs clients to their
account for hours. No public source found in this bounded investigation certifies
US30Cash historical holidays/DST for this exact server. Other servers, mirrors,
other brokers and underlying futures calendars are not substituted.

Bounded connected-mail searches also found no qualifying exact-server dated
calendar. Only candidate headers were inspected; setup notices, statements and
marketing were not adopted as event/calendar proof. Private bodies, credentials,
recipient addresses and message identifiers are not included in this repository.

## Demonstrated scope versus hypotheses

The approved 50-frame/150-record capture and hashes are reused. It demonstrates
timestamp unit consistency and the observed native clock relationships within
that interval. Its separate host UTC attestation covers receipt-clock evidence
for that interval, not event UTC identity or later clock precision. Current
TimeTradeServer minus TimeGMT observations must not be counted as independent
corroborating authorities. Previous evidence and reports remain immutable; this
document refines the interpretation without rewriting captured values.

The 276 native M5 contrasts prove native aggregation/grid consistency on the
diagnostic historical day, not UTC bar opening times. Repeated session patterns
and IANA DST transitions can test a hypothesis after its scope is independently
anchored; they cannot distinguish a genuine timestamp encoding from missing
ticks, a changed trading schedule, holidays or a clock problem by themselves.
There is no authorized historical mapping segment and no calendar PASS.

The prior three re-query discrepancies and the fourth discovered window remain
classified as original undercoverage relative to later history. One later
tick/bar reference inconsistency also remains. Their preserved artifacts, hashes
and raw payload multiplicities are reused; no identical re-query was repeated.
They are not equivalent prospective evidence, even where OHLC agrees. No later
records are inserted into the original archive.

## Automated evidence preparation and retrieval

`tools/prepare_temporal_evidence.py prepare` creates four local templates:
`tick_event`, `bar_time`, `historical_mapping`, `calendar`. They request immutable
source hashes, exact server/symbol, independently authenticated authority,
bounded UTC applicability and evidence specific to the claim. A bar claim
requires bar-open semantics; a calendar claim requires dated exception coverage.
An event claim requires an unambiguous binding between native and independent
records; a historical mapping requires evidenced transition boundaries.

`tools/prepare_temporal_evidence.py fetch-public --url <https URL>` saves an
immutable local document and receipt/hash from the explicitly allowlisted primary
hosts. It uses no account, cookies, credentials, form submission or access bypass.
Redirects outside those hosts, credential URLs and oversized documents fail.
Successful downloads still say NOT_SEMANTICALLY_VERIFIED. Raw HTML stays local;
GitHub receives receipts and factual paraphrases, not complete website copies.

`tools/prepare_temporal_evidence.py inspect --bundle <local JSON>` verifies source
hash/path containment and required evidence fields. A complete structure returns
STRUCTURALLY_COMPLETE_REVIEW_REQUIRED, never scientific PASS. A self-declared
verified/PASS field cannot authorize mapping, calendar or cohort activation.
Semantic validation must establish the actual source authenticity and event/date
binding; structural completeness alone does not do so. The tool does not modify
the frozen converter, calendar, strategy, metadata spec or activation protocol.

No additional probe is needed to rediscover the observed +7200 relationship.
The missing acquisition is a source independently identifying UTC for the same
broker event, or authoritative exact-server dated semantics and applicability.
That source is not exposed by the presently available Python tick/session API.
A native probe can preserve what the terminal reports; it cannot manufacture
independent provenance. No message or support request was sent on the user's
behalf and no files from the old PC are requested.

## Research preparation without blocked data

The preparation command parses source and inventories hashes for the causal
checks, streaming TRAIN membership filter, native metadata adapter, baseline and
purged walk-forward components. It does not import/execute model runners, read
datasets, select features from data, fit models or evaluate labels. The legacy
model runner includes a validation-scoring path; it is explicitly not exposed
by this preparation CLI. Only prepare/inspect/public-fetch actions exist.

The shared TRAIN input guard now rejects PC A raw archives, raw backups,
reconstruction/forensic directories, evidence backups and temporal intake paths
before CSV I/O. This is an intentional input-isolation hardening, versioned in
the source manifest. It changes no strategy parameter, frozen split membership,
indicator threshold or hypothesis budget. Existing legacy entry points are not
represented as newly authorized training; TRAIN remains exhausted.

Affected regression tests: **44 passed**, zero skipped/failed. This includes the
intake, TRAIN path guard, native converter, runtime session guard, causal-time
checks and volume classification. Approved native fixtures and the full suite
were not unnecessarily rerun. The previous complete result remains 259 passed /
9 skipped; it is not relabeled as a new full-suite run. Compileall, static no-order
checks, retained native evidence seals and diff checks were verified.

The source audit verifies 363 prior-manifest files unchanged and identifies only
the reviewed TRAIN guard implementation change; new files are separately covered
by the new versioned source manifest. The collector remains read-only in its
existing raw quarantine identity/cursor. No old cohort or staging archive is
promoted, no scientific cohort is activated and no prospective backfill is made.
Original event UTC no-backfill remains unproven; mechanical cursor continuity
must not be confused with scientific prospective eligibility.

HARD_BLOCKER: independent exact-server event UTC/date applicability, bounded
historical mapping/transition evidence, authoritative session/exception coverage
and current precise clock acceptance. TRAINING_READINESS remains
BLOCKED_BY_RESEARCH_GOVERNANCE. DISCOVERY_VALIDATION=BLOCKED,
FINAL_TEST=LOCKED, DEMO=DISABLED, LIVE_TRADING=false. The other project and WSL
remain untouched.
