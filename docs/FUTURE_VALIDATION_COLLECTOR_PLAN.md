# Future cohort collector and Windows schedule

## Runtime components

- Collector: `python/future_validation_collector.py`.
- Runtime cohort directory: `outputs/future_validation_cohort/cohort_20261019/`
  (ignored by Git).
- Manifest template: `configs/future_validation_cohort_manifest.template.json`.
- Windows task wrapper: `scripts/run_future_validation_collector.py`.
- Task registration: `scripts/register_future_validation_task.ps1`.

The collector attaches only to the uniquely identified active XM terminal via
the existing read-only environment probe. It requires a connected DEMO account,
the matching MT5 Data Folder, and exact `US30Cash` availability. It supplies no
login credentials and calls no trade/order API. If these checks fail, it logs a
blocked attempt and retries on the next scheduled invocation.

The task runs under the current interactive Windows user, every 15 minutes
starting at the next quarter-hour after registration. It does not poll or save
partial live bars. The collector advances only by complete UTC calendar days,
after a two-hour safety lag, and catches up missed closed days on a later run.
Repeated invocations on the same day return without duplicating segments.

## Segment and manifest behavior

Each day is built in a same-volume staging directory and atomically renamed
into `raw/YYYYMMDD/` only after both tick and bar queries succeed. Tick requests
are partitioned into non-overlapping one-hour UTC intervals; their API end time
is one millisecond before the next interval. Every day records counts and
first/last tick times, including empty market days. Existing day directories
are never overwritten. The collector verifies the manifest sidecar and every
listed SHA-256 before appending. A failure never marks a segment complete or
advances its cursor.

If a process is interrupted while a day is staged, a `.pending-*` directory may
remain. It is excluded from the manifest and is not consumed by any pipeline;
the next run can collect into a new staging directory. Do not manually add
pending files to the manifest. Investigate a persistent pending directory as a
collection error.

The hash chain is an audit aid, not a digital signature. Runtime data and logs
are excluded from Git to prevent accidental publication of broker market data
or local machine information.

## Setup and operation

With the project virtual environment present, the initial setup is:

```powershell
.\.venv\Scripts\python.exe python\future_validation_collector.py prepare
.\scripts\register_future_validation_task.ps1
```

To inspect the sealed cohort without contacting MT5:

```powershell
.\.venv\Scripts\python.exe python\future_validation_collector.py status
```

The task's stdout and exit code are appended to the ignored runtime
`scheduler.log`. A query/API failure exits nonzero; Task Scheduler retries at
the next interval. This automation collects raw observations only. It does not
build events or features, create hypotheses, run research, score candidates,
or access either legacy holdout.

## Current health — 2026-10-19

The enabled task now invokes the project `.venv` Python directly, avoiding a
PowerShell process that remained running after writing its log. Latest
environment probe identifies the active XM terminal and data folder, confirms
DEMO, connection, and `US30Cash`. Health has 0 tick/bar rows, no successful
capture, `WAITING_FIRST_CAPTURE`, no error, and the unchanged cursor
`2026-10-19T00:00:00Z`. A manual run returned
`CAUGHT_UP_WAITING_FOR_CLOSED_DAY`; this is expected because the fixed-start
day is not complete and settled. The first eligible collection is no earlier
than **2026-10-20 02:00 UTC** (2026-10-19 21:00 CDT), at the next 15-minute
task tick. Before then, the collector exits without initializing MT5 and
never backfills. No cohort rows have been captured.


## First eligible capture — 2026-10-21

The maturity rule was unchanged. The first eligible day (2026-10-19) was
captured at 2026-10-20 02:00:17.688 UTC; the next day (2026-10-20) was
captured at 2026-10-21 02:00:15.277 UTC. This follows the daily cursor in order
from the fixed start and performs no backfill. The manifest reports 129,508 +
134,219 = 263,727 ticks and 276 + 276 = 552 M5
bars; latest timestamp is 2026-10-20T23:59:58.880Z. Each day's tick and bar
SHA-256 matches its manifest entry, and the manifest sidecar matches manifest
SHA-256 `77fd6d09235144590183897211db6efbc8d8871e5451ef56728028974f1f26d3`.
Health is `HEALTHY`, with no errors, no duplicate or missing UTC days, DEMO
account mode, connected XM terminal, and the exact symbol available. The
scheduled task is enabled, Ready, last result 0, and continues every 15
minutes. This capture is raw-only and remains inaccessible to TRAIN scoring;
no backfill, evaluation, or trading was performed. Runtime data and logs stay
local and ignored by Git.

## Prospective health gate — 2026-10-21

`python/future_cohort_health.py` now verifies segment hashes/counts, timestamps,
quote/bar validity, fixed Stochastic signal support, UTC weeks/months, NY-based
session counts, causal regime/volatility counts, and expected M5 gaps when a
verified server calendar is present. The Task Scheduler wrapper archives each
new manifest and writes a separate hash-pinned health report when capture or
health inputs change. It never reads outcomes.

The permitted metadata-only audit reports **2 captured days**, **263,727
ticks**, **552 M5 bars**, **29 BUY / 26 SELL support signals**, zero invalid
ticks/bars, zero missing UTC capture days, and latest raw tick
`2026-10-20T23:59:58.880Z`. Health report SHA-256 is
`a42ecdc9142807d1a2b9ad32c4f347d0fa76d4e2adcb0d0b250b2d12706101ce`.
`COHORT_MATURE=false`: duration, signal/session/regime support, candidate, and
causality-audit gates are incomplete; the exact XM server calendar is
unverified; and the old manifest versions were overwritten before immutable
snapshot archiving began. No performance field was read or calculated.

The prospective protocol and metadata-only specification now have committed
SHA-256 sidecars, which the candidate freezer, evaluator, and health gate
require. The health report confirms `metadata_spec_frozen=true`; it remains
`NOT_MATURE`. At 2026-10-21 15:50 CDT, Task Scheduler reports the collector
`Ready`, last scheduled result `0` at 15:45:45, next run 16:00:00. The latest
wrapper log entry also exited `0` with `CAUGHT_UP_WAITING_FOR_CLOSED_DAY`;
it collected no new segment because the next UTC day is not yet eligible.

Future snapshots will be checked against an immutable chain from the current
audit anchor. This does not claim to reconstruct overwritten pre-deployment
versions; the frozen maturity gate remains closed while that prefix is
unverified. The calendar template is intentionally unverified and therefore
fails gap acceptance until the exact XM server schedule is sourced and hashed.
