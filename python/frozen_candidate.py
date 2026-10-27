"""Validate and immutably register an externally reviewed candidate package.

This is a packaging tool, not a hypothesis generator or model trainer. It never
reads the future cohort, Discovery Validation, or FINAL_TEST.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

HEX64 = re.compile(r"^[0-9a-f]{64}$")
ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "docs/PROSPECTIVE_EVALUATION_PROTOCOL.md"
PROTECTED = {"validation", "discovery_validation", "discovery-validation", "final_test",
             "final-test", "finaltest", "future_validation_cohort"}
REQUIRED_HASHES = ("features_sha256", "code_sha256", "dataset_sha256", "policy_sha256",
                   "train_walk_forward_report_sha256")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_candidate(candidate: dict, evidence_path: Path) -> None:
    if candidate.get("status") != "DRAFT" or not candidate.get("candidate_id"):
        raise ValueError("Candidate must be a named DRAFT before freezing")
    if candidate.get("symbol") != "US30Cash" or candidate.get("timeframe") != "M5":
        raise ValueError("Only the frozen US30Cash M5 contract is allowed")
    if candidate.get("latency_ms") != 250:
        raise ValueError("Candidate latency must match the preregistered 250 ms primary")
    expected_contract = {
        "stochastic": {"K": 5, "D": 3, "slowing": 3, "trigger_line": "MAIN_K"},
        "buy": "previous <= 20 and current > 20",
        "sell": "previous >= 80 and current < 80",
        "tp": 240, "sl": 180, "time_exit_bars": 100,
    }
    if candidate.get("strategy_contract") != expected_contract:
        raise ValueError("Candidate may not change the frozen base strategy contract")
    if candidate.get("prospective_protocol_sha256") != sha256(PROTOCOL_PATH):
        raise ValueError("Candidate must bind the exact frozen prospective protocol")
    protocol_sidecar = PROTOCOL_PATH.with_name(PROTOCOL_PATH.name + ".sha256")
    if (not protocol_sidecar.is_file()
            or protocol_sidecar.read_text(encoding="ascii").split()[0] != sha256(PROTOCOL_PATH)):
        raise ValueError("Frozen prospective protocol sidecar is missing or invalid")
    if not candidate.get("policy") or not candidate.get("failure_criteria"):
        raise ValueError("Candidate policy and frozen failure criteria are required")
    for key in REQUIRED_HASHES:
        if not HEX64.fullmatch(str(candidate.get(key, ""))):
            raise ValueError(f"Missing or invalid SHA-256: {key}")
    model_hash = candidate.get("model_sha256")
    if model_hash is not None and not HEX64.fullmatch(str(model_hash)):
        raise ValueError("Invalid model SHA-256")
    if not isinstance(candidate.get("thresholds"), dict) or not candidate["thresholds"]:
        raise ValueError("Frozen candidate must provide its complete threshold object")
    if any(candidate.get(key) is not False for key in
           ("discovery_validation_used", "future_cohort_used", "final_test_used", "demo_enabled", "live_trading")):
        raise ValueError("Protected data and trading flags must all remain false")
    evidence_path = Path(evidence_path).resolve()
    if {part.casefold() for part in evidence_path.parts} & PROTECTED:
        raise ValueError("Candidate evidence path is in a protected cohort or split")
    if not evidence_path.is_file() or sha256(evidence_path) != candidate["train_walk_forward_report_sha256"]:
        raise ValueError("TRAIN walk-forward evidence is missing or its hash does not match")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence.get("status") not in {"PASS", "TRAIN_WALK_FORWARD_PASS"}:
        raise ValueError("Candidate requires an explicit passing TRAIN walk-forward report")


def freeze_candidate(candidate_path: Path, evidence_path: Path, output_dir: Path) -> tuple[Path, str]:
    source = Path(candidate_path).resolve()
    candidate = json.loads(source.read_text(encoding="utf-8"))
    validate_candidate(candidate, evidence_path)
    payload = dict(candidate)
    payload["status"] = "FROZEN"
    payload["candidate_frozen"] = True
    payload["evidence_path"] = "TRAIN_REPORT_HASH_BOUND"
    destination_dir = Path(output_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{candidate['candidate_id']}.json"
    if destination.exists() or destination.with_name(destination.name + ".sha256").exists():
        raise FileExistsError("Frozen candidate destination already exists; version instead of overwrite")
    temp = destination.with_name(destination.name + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    temp.replace(destination)
    digest = sha256(destination)
    destination.with_name(destination.name + ".sha256").write_text(f"{digest}  {destination.name}\n", encoding="ascii")
    return destination, digest
