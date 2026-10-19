"""Single-use, read-only evaluator for an explicitly authorized future cohort.

No CLI run is part of preparation. Inputs must be frozen and the evaluator
will refuse absent authorization, immature data, hash mismatches, and reuse.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COHORT = ROOT / "outputs/future_validation_cohort/cohort_20261019"
REQUIRED_COLUMNS = {"signal_id", "side", "decision", "candidate_pnl", "follow_pnl", "invert_pnl"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _refuse_protected_path(path: Path) -> None:
    protected = {"validation", "discovery_validation", "discovery-validation",
                 "final_test", "final-test", "finaltest"}
    if {part.casefold() for part in path.parts} & protected:
        raise ValueError("Evaluator refuses legacy Validation/FINAL_TEST paths")


def _summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("Evaluation cohort has no rows")
    ids = [row["signal_id"] for row in rows]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("Signal IDs must be nonempty and unique")
    result: dict[str, Any] = {"n": len(rows)}
    for label, key in (("candidate", "candidate_pnl"), ("follow", "follow_pnl"), ("invert", "invert_pnl")):
        values = [float(row[key]) for row in rows]
        result[f"{label}_mean_pnl"] = mean(values)
        result[f"{label}_win_rate"] = sum(value > 0 for value in values) / len(values)
    result["candidate_minus_follow"] = result["candidate_mean_pnl"] - result["follow_mean_pnl"]
    result["candidate_minus_invert"] = result["candidate_mean_pnl"] - result["invert_mean_pnl"]
    return result


def evaluate(*, candidate_path: Path, eval_csv: Path, eval_manifest_path: Path,
             authorization_path: Path, cohort_root: Path = DEFAULT_COHORT,
             ledger_root: Path | None = None) -> dict[str, Any]:
    """Consume one precomputed candidate-vs-baselines table, exactly once."""
    candidate_path = candidate_path.resolve()
    eval_csv = eval_csv.resolve()
    eval_manifest_path = eval_manifest_path.resolve()
    authorization_path = authorization_path.resolve()
    cohort_root = cohort_root.resolve()
    for path in (candidate_path, eval_csv, eval_manifest_path, authorization_path, cohort_root):
        _refuse_protected_path(path)
    eval_root = cohort_root / "evaluation"
    if eval_root not in eval_csv.parents or eval_root not in eval_manifest_path.parents:
        raise ValueError("Evaluation inputs must be physically inside the cohort evaluation directory")
    if not candidate_path.is_file() or not eval_csv.is_file() or not eval_manifest_path.is_file() or not authorization_path.is_file():
        raise ValueError("Candidate, evaluation table, evaluation manifest, and authorization are required")

    candidate = _read_json(candidate_path)
    manifest = _read_json(eval_manifest_path)
    authorization = _read_json(authorization_path)
    candidate_hash, table_hash = sha256(candidate_path), sha256(eval_csv)
    candidate_sidecar = candidate_path.with_name(candidate_path.name + ".sha256")
    if (not candidate_sidecar.is_file()
            or candidate_sidecar.read_text(encoding="ascii").split()[0] != candidate_hash):
        raise ValueError("Candidate must have a matching immutable SHA-256 sidecar")
    cohort_manifest_path = cohort_root / "cohort_manifest.json"
    cohort_hash = sha256(cohort_manifest_path)
    if candidate.get("status") != "FROZEN" or not candidate.get("candidate_id"):
        raise ValueError("Only a frozen candidate may be evaluated")
    expected = {
        "candidate_sha256": candidate_hash,
        "evaluation_table_sha256": table_hash,
        "cohort_manifest_sha256": cohort_hash,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"Evaluation manifest hash mismatch: {key}")
    if manifest.get("maturity_status") != "PASS" or manifest.get("causality_status") != "PASS":
        raise ValueError("Cohort maturity and causality must both PASS")
    if (authorization.get("user_authorized") is not True
            or authorization.get("candidate_sha256") != candidate_hash
            or authorization.get("cohort_manifest_sha256") != cohort_hash
            or authorization.get("evaluation_table_sha256") != table_hash):
        raise ValueError("Explicit matching one-time authorization is required")

    with eval_csv.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise ValueError(f"Evaluation table lacks required columns: {sorted(REQUIRED_COLUMNS)}")
        rows = list(reader)
    if not rows or any(row["decision"] not in {"FOLLOW", "INVERT"}
                       or row["side"] not in {"BUY", "SELL"} for row in rows):
        raise ValueError("Unexpected/empty evaluation table")
    if len({row["signal_id"] for row in rows}) != len(rows) or any(not row["signal_id"] for row in rows):
        raise ValueError("Signal IDs must be nonempty and unique")
    # Parse all score columns before consuming the one-time evaluation token.
    for row in rows:
        for key in ("candidate_pnl", "follow_pnl", "invert_pnl"):
            float(row[key])

    ledger_root = (ledger_root or eval_root / "evaluation_ledger").resolve()
    ledger_root.mkdir(parents=True, exist_ok=True)
    ledger_key = hashlib.sha256(f"{candidate_hash}:{cohort_hash}".encode()).hexdigest()
    lock_path = ledger_root / f"{ledger_key}.consumed"
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError("This candidate/cohort pair has already been consumed") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(json.dumps({"candidate_sha256": candidate_hash,
                                 "cohort_manifest_sha256": cohort_hash,
                                 "evaluation_table_sha256": table_hash,
                                 "status": "CONSUMED"}, sort_keys=True))

    result = {
        "status": "EVALUATED_ONCE",
        "candidate_id": candidate["candidate_id"],
        **expected,
        "all": _summary(rows),
        "by_side": {side: _summary([row for row in rows if row["side"] == side])
                    for side in ("BUY", "SELL") if any(row["side"] == side for row in rows)},
        "tuning_allowed": False,
        "final_test_accessed": False,
        "demo_enabled": False,
        "live_trading": False,
    }
    result_path = eval_root / f"evaluation_{ledger_key}.json"
    temp = result_path.with_suffix(".tmp")
    temp.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, result_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--table", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(candidate_path=args.candidate, eval_csv=args.table,
                      eval_manifest_path=args.manifest, authorization_path=args.authorization)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
