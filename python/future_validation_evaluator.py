"""Single-use, read-only evaluator for an explicitly authorized future cohort.

No CLI run is part of preparation. Inputs must be frozen and the evaluator
will refuse absent authorization, immature data, hash mismatches, and reuse.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
from statistics import mean, median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COHORT = ROOT / "outputs/future_validation_cohort/cohort_20261019"
REQUIRED_COLUMNS = {"signal_id", "signal_time_utc", "side", "decision",
                    "candidate_pnl", "follow_pnl", "invert_pnl"}
PROTOCOL_PATH = ROOT / "docs/PROSPECTIVE_EVALUATION_PROTOCOL.md"
BOOTSTRAP_REPS = 10_000
BOOTSTRAP_SEED = 20261019


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


def _paired_ci(rows: list[dict[str, str]], baseline: str, *, seed: int) -> dict[str, float]:
    differences = [float(row["candidate_pnl"]) - float(row[baseline]) for row in rows]
    if not differences:
        raise ValueError("Cannot calculate paired confidence interval without rows")
    rng = random.Random(seed)
    n = len(differences)
    means = []
    for _ in range(BOOTSTRAP_REPS):
        means.append(sum(differences[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return {"mean_delta": mean(differences),
            "ci95_low": means[int(0.025 * BOOTSTRAP_REPS)],
            "ci95_high": means[int(0.975 * BOOTSTRAP_REPS) - 1],
            "bootstrap_replicates": BOOTSTRAP_REPS,
            "bootstrap_seed": seed}


def _max_drawdown(values: list[float]) -> float:
    equity = peak = 0.0
    drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = min(drawdown, equity - peak)
    return abs(drawdown)


def _evaluation_metrics(rows: list[dict[str, str]]) -> dict[str, Any]:
    result: dict[str, Any] = {"n": len(rows)}
    for baseline in ("follow_pnl", "invert_pnl"):
        result[f"candidate_minus_{baseline.replace('_pnl', '')}"] = _paired_ci(
            rows, baseline, seed=BOOTSTRAP_SEED + (baseline == "invert_pnl"))
    for label, key in (("candidate", "candidate_pnl"), ("follow", "follow_pnl"), ("invert", "invert_pnl")):
        vals = [float(row[key]) for row in rows]
        gains = sum(v for v in vals if v > 0)
        losses = abs(sum(v for v in vals if v < 0))
        result[f"{label}_mean_pnl"] = mean(vals)
        result[f"{label}_median_pnl"] = median(vals)
        result[f"{label}_win_rate"] = sum(v > 0 for v in vals) / len(vals)
        result[f"{label}_profit_factor"] = gains / losses if losses else (None if gains else 0.0)
        result[f"{label}_max_drawdown"] = _max_drawdown(vals)
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
    cohort_sidecar_path = cohort_root / "cohort_manifest.sha256"
    if (not cohort_sidecar_path.is_file()
            or cohort_sidecar_path.read_text(encoding="ascii").strip() != sha256(cohort_manifest_path)):
        raise ValueError("Cohort manifest SHA-256 sidecar is missing or invalid")
    cohort_hash = sha256(cohort_manifest_path)
    health_path = cohort_root / "cohort_health_report.json"
    health_sidecar = health_path.with_name(health_path.name + ".sha256")
    if (not health_path.is_file() or not health_sidecar.is_file()
            or health_sidecar.read_text(encoding="ascii").strip() != sha256(health_path)):
        raise ValueError("A hash-verified cohort health/maturity report is required")
    health = _read_json(health_path)
    if (health.get("cohort_mature") is not True
            or health.get("cohort_manifest_sha256") != cohort_hash
            or health.get("scoring_performed") is not False):
        raise ValueError("Hash-bound cohort health report is not mature and score-free")
    audit_path = eval_root / "causality_audit.json"
    audit_sidecar = audit_path.with_name(audit_path.name + ".sha256")
    if (not audit_path.is_file() or not audit_sidecar.is_file()
            or audit_sidecar.read_text(encoding="ascii").split()[0] != sha256(audit_path)):
        raise ValueError("Independent hash-verified causality audit is required")
    audit_hash = sha256(audit_path)
    audit = _read_json(audit_path)
    if (health.get("causality_audit_pass") is not True
            or health.get("causality_audit_sha256") != audit_hash
            or audit.get("status") != "PASS"
            or audit.get("cohort_manifest_sha256") != cohort_hash
            or audit.get("evaluation_table_sha256") != table_hash
            or audit.get("candidate_sha256") != candidate_hash
            or audit.get("metadata_spec_sha256") != sha256(ROOT / "configs/future_cohort_metadata_spec.json")
            or audit.get("pnl_read") is not False or audit.get("labels_read") is not False
            or any(audit.get(key) is not True for key in (
                "base_trigger_parity_pass", "feature_timestamps_pass", "target_feature_separation_pass",
                "independent_replay_parity_pass"))):
        raise ValueError("Causality audit does not prove this candidate/table and native-trigger parity")
    health_hash = sha256(health_path)
    protocol_hash = sha256(PROTOCOL_PATH)
    protocol_sidecar = PROTOCOL_PATH.with_name(PROTOCOL_PATH.name + ".sha256")
    if (not protocol_sidecar.is_file()
            or protocol_sidecar.read_text(encoding="ascii").split()[0] != protocol_hash):
        raise ValueError("Frozen prospective evaluation protocol sidecar is missing or invalid")
    evaluator_hash = sha256(Path(__file__).resolve())
    if candidate.get("status") != "FROZEN" or candidate.get("candidate_frozen") is not True or not candidate.get("candidate_id"):
        raise ValueError("Only a frozen candidate may be evaluated")
    expected = {
        "candidate_sha256": candidate_hash,
        "evaluation_table_sha256": table_hash,
        "cohort_manifest_sha256": cohort_hash,
    }
    expected["protocol_sha256"] = protocol_hash
    expected["evaluator_sha256"] = evaluator_hash
    expected["health_report_sha256"] = health_hash
    expected["causality_audit_sha256"] = audit_hash
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"Evaluation manifest hash mismatch: {key}")
    if manifest.get("maturity_status") != "PASS" or manifest.get("causality_status") != "PASS":
        raise ValueError("Cohort maturity and causality must both PASS")
    if (authorization.get("user_authorized") is not True
            or not authorization.get("authorization_id")
            or len(str(authorization.get("single_use_nonce", ""))) != 64
            or any(c not in "0123456789abcdef" for c in str(authorization.get("single_use_nonce", "")).lower())
            or authorization.get("candidate_sha256") != candidate_hash
            or authorization.get("cohort_manifest_sha256") != cohort_hash
            or authorization.get("evaluation_table_sha256") != table_hash
            or authorization.get("protocol_sha256") != protocol_hash
            or authorization.get("evaluator_sha256") != evaluator_hash
            or authorization.get("health_report_sha256") != health_hash
            or authorization.get("causality_audit_sha256") != audit_hash):
        raise ValueError("Explicit matching one-time authorization is required")

    ledger_root = (ledger_root or eval_root / "evaluation_ledger").resolve()
    canonical_ledger = eval_root / "evaluation_ledger"
    canonical_ledger.mkdir(parents=True, exist_ok=True)
    ledger_root.mkdir(parents=True, exist_ok=True)
    ledger_key = hashlib.sha256(f"{candidate_hash}:{cohort_hash}".encode()).hexdigest()
    lock_path = ledger_root / f"{ledger_key}.consumed"
    nonce_hash = hashlib.sha256(authorization["single_use_nonce"].encode("ascii")).hexdigest()
    nonce_path = canonical_ledger / f"{nonce_hash}.token-consumed"
    audit_path = ledger_root / "evaluation_audit.jsonl"
    consume_record = {
        "status": "AUTHORIZATION_CONSUMED_BEFORE_OUTCOME_READ",
        "authorization_id": authorization["authorization_id"],
        "single_use_nonce_sha256": nonce_hash,
        **expected,
    }
    result_path = eval_root / f"evaluation_{ledger_key}.json"
    canonical_pair = canonical_ledger / f"{ledger_key}.consumed"
    if canonical_pair.exists() or result_path.exists():
        raise ValueError("This candidate/cohort pair has already been consumed")
    # Reserve the pair first: even a crash before nonce/audit persistence cannot
    # authorize this pair under a fresh token or an alternate audit directory.
    for claim_path, reason in ((canonical_pair, "candidate/cohort pair"),
                               (nonce_path, "one-use authorization token")):
        try:
            claim_fd = os.open(claim_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise ValueError(f"This {reason} has already been consumed") from exc
        with os.fdopen(claim_fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(consume_record, sort_keys=True))
            stream.flush()
            os.fsync(stream.fileno())
    if canonical_pair != lock_path:
        with lock_path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(consume_record, sort_keys=True))
            stream.flush()
            os.fsync(stream.fileno())
    with audit_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(consume_record, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())

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
    times = []
    for row in rows:
        stamp = row["signal_time_utc"]
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Evaluation timestamps must be timezone-aware")
        times.append(parsed.astimezone(timezone.utc))
    if times != sorted(times) or len(times) != len(set(times)):
        raise ValueError("Evaluation rows must have unique, strictly increasing UTC signal times")
    # The authorization was consumed before this outcome table was opened.
    for row in rows:
        for key in ("candidate_pnl", "follow_pnl", "invert_pnl"):
            float(row[key])

    metrics = {"all": _evaluation_metrics(rows)}
    for side in ("BUY", "SELL"):
        side_rows = [row for row in rows if row["side"] == side]
        if side_rows:
            metrics[side] = _evaluation_metrics(side_rows)
    primary_keys = [f"candidate_minus_{baseline}" for baseline in ("follow", "invert")]
    groups = [metrics["all"], metrics.get("BUY", {}), metrics.get("SELL", {})]
    primary = [group[key] for group in groups if group for key in primary_keys]
    follow_dd = metrics["all"]["follow_max_drawdown"]
    candidate_dd = metrics["all"]["candidate_max_drawdown"]
    drawdown_pass = candidate_dd <= follow_dd * 1.2 if follow_dd else candidate_dd == 0
    if not drawdown_pass or any(item["ci95_high"] <= 0 for item in primary):
        evaluation_status = "FAIL"
    elif groups[1] and groups[2] and all(item["ci95_low"] > 0 for item in primary):
        evaluation_status = "PASS"
    else:
        evaluation_status = "INCONCLUSIVE"
    result = {
        "status": "EVALUATED_ONCE",
        "evaluation_status": evaluation_status,
        "candidate_id": candidate["candidate_id"],
        **expected,
        "metrics": metrics,
        "drawdown_pass": drawdown_pass,
        "bootstrap_replicates": BOOTSTRAP_REPS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "tuning_allowed": False,
        "final_test_accessed": False,
        "demo_enabled": False,
        "live_trading": False,
    }
    result_path = eval_root / f"evaluation_{ledger_key}.json"
    with result_path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    with audit_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"status": "EVALUATION_COMPLETE", "evaluation_status": evaluation_status,
                                 "result_sha256": sha256(result_path), **expected}, sort_keys=True) + "\n")
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
