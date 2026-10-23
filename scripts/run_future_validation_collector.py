"""Task Scheduler entrypoint with structured, single-process logging."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import hashlib
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "python") not in sys.path:
    sys.path.insert(0, str(ROOT / "python"))

from future_validation_collector import COHORT_ROOT, collect_once  # noqa: E402
from future_cohort_health import (  # noqa: E402
    HEALTH_NAME, HEALTH_PROTOCOL, SESSION_CALENDAR, _manifest_chain_status, build_health_report,
    write_health_report,
)
from future_cohort_health import __file__ as health_module_file  # noqa: E402


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _health_report_matches(current_health: dict, *, manifest_hash: str,
                           metadata_hash: str, health_code_hash: str,
                           calendar_hash: str, candidate_hash: str | None,
                           causality_audit_hash: str | None,
                           manifest_chain_status: str) -> bool:
    """Do not let a changed calendar or gate input reuse a stale maturity report."""
    return (current_health.get("cohort_manifest_sha256") == manifest_hash
            and current_health.get("metadata_spec_sha256") == metadata_hash
            and current_health.get("health_code_sha256") == health_code_hash
            and current_health.get("session_calendar_config_sha256") == calendar_hash
            and current_health.get("candidate_sha256") == candidate_hash
            and current_health.get("causality_audit_sha256") == causality_audit_hash
            and current_health.get("manifest_chain_status") == manifest_chain_status)


def _archive_current_manifest(cohort_root: Path) -> None:
    """Retain immutable snapshots from this deployment onward, without rewriting old history."""
    source = cohort_root / "cohort_manifest.json"
    sidecar = cohort_root / "cohort_manifest.sha256"
    if not source.is_file() or not sidecar.is_file() or sidecar.read_text(encoding="ascii").strip() != _digest(source):
        raise ValueError("Cannot archive an unverified cohort manifest")
    manifest = json.loads(source.read_text(encoding="utf-8"))
    history = cohort_root / "manifest_history"
    history.mkdir(parents=True, exist_ok=True)
    digest = _digest(source)
    snapshot = history / f"{digest}.json"
    ledger = history / "chain.jsonl"
    if ledger.is_file():
        records = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        records = []
    if snapshot.exists():
        if _digest(snapshot) != digest:
            raise ValueError("Existing immutable manifest snapshot was altered")
        if not records or records[-1].get("sha256") != digest:
            raise ValueError("Existing manifest snapshot is not the latest hash-chain entry")
        return
    previous = manifest.get("previous_manifest_sha256")
    anchor = not records
    if records and previous != records[-1].get("sha256"):
        raise ValueError("Manifest hash chain does not link to its previous archived state")
    temp = snapshot.with_suffix(".tmp")
    temp.write_bytes(source.read_bytes())
    os.replace(temp, snapshot)
    record = {"sha256": digest, "previous_manifest_sha256": previous,
              "snapshot": snapshot.name, "baseline_anchor": anchor}
    with ledger.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")


def _frozen_candidate_path() -> Path | None:
    directory = ROOT / "outputs/prospective/candidates"
    candidates = sorted(path for path in directory.glob("*.json")
                       if path.with_name(path.name + ".sha256").is_file()) if directory.is_dir() else []
    if len(candidates) > 1:
        return None  # Ambiguity leaves the maturity gate false; collection continues without ranking.
    return candidates[0] if candidates else None


def main() -> int:
    cohort_root = COHORT_ROOT
    log_path = cohort_root / "scheduler.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        result = collect_once()
        if (COHORT_ROOT / "cohort_manifest.json").is_file():
            _archive_current_manifest(COHORT_ROOT)
            manifest_hash = _digest(COHORT_ROOT / "cohort_manifest.json")
            calendar_hash = _digest(SESSION_CALENDAR) if SESSION_CALENDAR.is_file() else ""
            health_path = COHORT_ROOT / HEALTH_NAME
            candidate_path = _frozen_candidate_path()
            candidate_hash = _digest(candidate_path) if candidate_path else None
            audit_path = ROOT / "outputs/prospective/causality_audit.json"
            audit_path_hash = _digest(audit_path) if audit_path.is_file() else None
            health_is_current = False
            if health_path.is_file():
                try:
                    current_health = json.loads(health_path.read_text(encoding="utf-8"))
                    health_sidecar = health_path.with_name(health_path.name + ".sha256")
                    health_is_current = (health_sidecar.is_file()
                                         and health_sidecar.read_text(encoding="ascii").strip() == _digest(health_path)
                                         and _health_report_matches(
                                             current_health,
                                             manifest_hash=manifest_hash,
                                             metadata_hash=_digest(HEALTH_PROTOCOL),
                                             health_code_hash=_digest(Path(health_module_file)),
                                             calendar_hash=calendar_hash,
                                             candidate_hash=candidate_hash,
                                             causality_audit_hash=audit_path_hash,
                                             manifest_chain_status=_manifest_chain_status(
                                                 COHORT_ROOT, manifest_hash)[0]))
                except (OSError, json.JSONDecodeError):
                    health_is_current = False
            if not health_is_current:
                report = build_health_report(
                    cohort_root=COHORT_ROOT,
                    frozen_candidate_path=candidate_path,
                    causality_audit_path=audit_path,
                )
                health_file, health_hash = write_health_report(report, COHORT_ROOT)
                result["health_report"] = health_file.name
                result["health_report_sha256"] = health_hash
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
