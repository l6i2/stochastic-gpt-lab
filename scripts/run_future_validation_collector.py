"""Task Scheduler entrypoint with structured, single-process logging."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "python") not in sys.path:
    sys.path.insert(0, str(ROOT / "python"))

from future_validation_collector import COHORT_ROOT, collect_once  # noqa: E402


def main() -> int:
    cohort_root = COHORT_ROOT
    log_path = cohort_root / "scheduler.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        result = collect_once()
        exit_code = 2 if str(result.get("status", "")).startswith("BLOCKED") else 0
        output = json.dumps(result, sort_keys=True)
    except Exception as exc:  # Persist the error for health; Task Scheduler retries next interval.
        exit_code = 1
        output = json.dumps({"status": "COLLECTOR_ERROR", "error": f"{type(exc).__name__}: {exc}",
                             "live_trading": False}, sort_keys=True)
    record = {"started_utc": started, "exit_code": exit_code, "output": output}
    with log_path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")
        stream.flush()
    print(json.dumps(record, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
