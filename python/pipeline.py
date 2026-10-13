"""Safe project pipeline. This CLI intentionally has no FINAL_TEST command."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run(args: list[str]) -> int:
    return subprocess.run([PYTHON, *args], cwd=ROOT, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("historical", help="report measured bounded real-tick blocks; does not start MT5")
    sub.add_parser("validate", help="validate all canonical raw blocks")
    sub.add_parser("build-master", help="build master and purged TRAIN/VALIDATION partitions")
    analysis = sub.add_parser("train-analysis", help="TRAIN-only descriptive report and baseline walk-forward")
    analysis.add_argument("--output", type=Path, default=Path("outputs/analysis/current"))
    models = sub.add_parser("ml-train", help="fit fixed models on TRAIN; compare on validation")
    models.add_argument("--output", type=Path, default=Path("outputs/ml/current"))
    models.add_argument("--walk-forward", action="store_true")
    models.add_argument("--round2", action="store_true", help="fixed small feature subset with predefined interactions")
    hypotheses = sub.add_parser("validate-hypotheses", help="evaluate frozen hypothesis files on validation")
    hypotheses.add_argument("hypotheses", nargs="+", type=Path)
    hypotheses.add_argument("--output", required=True, type=Path)
    r2 = sub.add_parser("round2-entry-freeze", help="freeze the fixed ten-hypothesis family using TRAIN only")
    r2.add_argument("--output", type=Path, default=Path("research/hypotheses_round2"))
    r2v = sub.add_parser("round2-entry-validate", help="evaluate frozen round-two entry hypotheses once on validation")
    r2v.add_argument("--hypotheses", type=Path, default=Path("research/hypotheses_round2"))
    r2v.add_argument("--output", type=Path, default=Path("outputs/entry_research_round2/validation"))
    r2i = sub.add_parser("round2-entry-interactions", help="write fixed descriptive interaction tables from TRAIN only")
    r2i.add_argument("--output", type=Path, default=Path("outputs/entry_research_round2/train_report/interactions.csv"))
    sub.add_parser("intratrade-status", help="report whether causal path-state source exists; never fabricates snapshots")
    sub.add_parser("candidate", help="verify promotion gates; creates no candidate if any gate fails")
    args = parser.parse_args()
    if args.command == "historical":
        path = ROOT / "outputs/history_coverage.json"
        coverage = json.loads(path.read_text(encoding="utf-8"))
        blocks = sorted((ROOT / "outputs/history/raw").glob("*/manifest.json"))
        print(json.dumps({"coverage": coverage, "block_manifests": [str(p.relative_to(ROOT)) for p in blocks],
                          "tester_launch_automated": False}, indent=2))
        return 0
    if args.command == "validate":
        manifests = sorted((ROOT / "outputs/history/raw").glob("*/manifest.json"))
        if not manifests:
            print("No canonical historical block manifests found", file=sys.stderr)
            return 1
        for manifest in manifests:
            block = manifest.parent
            if block.name == "2024_precision10_pre_fix":
                continue
            code = run(["python/validate_dataset.py", str(block / "stochastic_events.csv")])
            if code:
                return code
        return 0
    if args.command == "build-master":
        blocks = [str(p.parent) for p in sorted((ROOT / "outputs/history/raw").glob("*/manifest.json"))
                  if p.parent.name in {"2023_12", "2024", "2025", "2026_ytd"}]
        if len(blocks) != 4:
            print("Expected four canonical real-tick blocks; inspect outputs/history/validation_status.csv", file=sys.stderr)
            return 1
        return run(["python/build_master_dataset.py", *blocks])
    if args.command == "train-analysis":
        return run(["python/analyze_dataset.py", "outputs/master/stochastic_master.parquet",
                    "--output", str(args.output), "--evaluate", "TRAIN", "--walk-forward",
                    "--wf-initial", "5000", "--wf-step", "2500"])
    if args.command == "ml-train":
        command = ["python/train_direction_model.py", "outputs/splits/train.parquet",
                   "outputs/splits/validation.parquet", "--output", str(args.output)]
        if args.walk_forward:
            command.append("--walk-forward")
        if args.round2:
            command.append("--round2")
        return run(command)
    if args.command == "validate-hypotheses":
        return run(["python/evaluate_hypotheses.py", "outputs/splits/validation.parquet",
                    *[str(p) for p in args.hypotheses], "--output", str(args.output)])
    if args.command == "round2-entry-freeze":
        return run(["python/round2_entry_research.py", "freeze", "outputs/splits/train.parquet",
                    "--out", str(args.output)])
    if args.command == "round2-entry-validate":
        return run(["python/round2_entry_research.py", "validate", "outputs/splits/validation.parquet",
                    str(args.hypotheses), "--out", str(args.output)])
    if args.command == "round2-entry-interactions":
        return run(["python/round2_entry_research.py", "train-interactions", "outputs/splits/train.parquet",
                    "--out", str(args.output)])
    if args.command == "intratrade-status":
        candidates = [ROOT / "outputs/intratrade/path_states.parquet",
                     ROOT / "outputs/intratrade/path_states.csv"]
        available = [str(path.relative_to(ROOT)) for path in candidates if path.is_file()]
        status = {"status": "PATH_SOURCE_AVAILABLE" if available else "BLOCKED_MISSING_PATH_STATE_SOURCE",
                  "path_sources": available, "snapshots_built": False,
                  "final_test_accessed": False, "reason": None if available else
                  "The frozen event dataset contains signal-time features and terminal outcomes, not the open-trade M5/tick path required to reconstruct causal snapshots."}
        status_path = ROOT / "outputs/intratrade/round2_build_status.json"
        status_path.parent.mkdir(parents=True, exist_ok=True)
        if status_path.exists():
            print(f"Refusing to overwrite existing status artifact: {status_path}", file=sys.stderr)
            return 1
        status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(status, indent=2))
        return 0 if available else 2
    if args.command == "candidate":
        result_path = ROOT / "outputs/validation/20261013_v2/results.json"
        if not result_path.is_file():
            print("Candidate blocked: no frozen-hypothesis validation evidence.", file=sys.stderr)
            return 2
        results = json.loads(result_path.read_text(encoding="utf-8"))
        if not any(item.get("status") == "SURVIVES_VALIDATION" for item in results):
            print("Candidate blocked: no hypothesis survived validation; FINAL_TEST remains locked.", file=sys.stderr)
            return 2
        print("Candidate review required; this command never opens FINAL_TEST or enables trading.")
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
