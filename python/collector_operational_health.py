"""Read-only runtime status alongside the hash-frozen capture-data health checker."""
from __future__ import annotations

import json
from pathlib import Path

from future_validation_collector import COHORT_ROOT, health


def operational_health(*, cohort_root: Path = COHORT_ROOT, environment_status=None) -> dict:
    if environment_status is None:
        from controller.mt5_env import status
        environment_status = status
    try:
        environment = environment_status()
    except Exception:
        environment = {}
    result = health(cohort_root, environment_status=lambda: environment)
    ready = (environment.get("SAFE_FOR_RESEARCH") is True
             and environment.get("CONNECTED") is True
             and environment.get("ACCOUNT_MODE") == "DEMO"
             and environment.get("US30Cash_AVAILABLE") is True)
    result["runtime_ready"] = ready
    result["runtime_status"] = "READY" if ready else "BLOCKED_ENVIRONMENT"
    result["capture_data_health"] = result["collector_status"]
    log = Path(cohort_root) / "scheduler.log"
    if log.is_file():
        try:
            lines = [line for line in log.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
            if lines:
                result["last_attempt_utc"] = json.loads(lines[-1]).get("started_utc")
        except (OSError, ValueError, AttributeError):
            result["runtime_ready"] = False
            result["runtime_status"] = "BLOCKED_SCHEDULER_LOG"
    return result


if __name__ == "__main__":
    print(json.dumps(operational_health(), indent=2, sort_keys=True))
