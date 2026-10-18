# Future cohort collector and Windows schedule

## Runtime components

- Collector: `python/future_validation_collector.py`.
- Runtime cohort directory: `outputs/future_validation_cohort/cohort_20261019/`
  (ignored by Git).
- Manifest template: `configs/future_validation_cohort_manifest.template.json`.
- Windows task wrapper: `scripts/run_future_validation_collector.ps1`.
- Task registration: `scripts/register_future_validation_task.ps1`.

The collector attaches only to the uniquely identified active XM terminal via
the existing read-only environment probe. It requires a connected DEMO account,
the matching MT5 Data Folder, and exact `US30Cash` availability. It supplies no
login credentials and calls no trade/order API. If these checks fail, it logs a
blocked attempt and retries on the next scheduled invocation.

The task runs under the current interactive Windows user, every 15 minutes
starting **2026-10-19 00:15 local computer time**. It does not poll or save
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
