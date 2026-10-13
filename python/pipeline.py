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
    hypotheses = sub.add_parser("validate-hypotheses", help="evaluate frozen hypothesis files on validation")
    hypotheses.add_argument("hypotheses", nargs="+", type=Path)
    hypotheses.add_argument("--output", required=True, type=Path)
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
        return run(command)
    if args.command == "validate-hypotheses":
        return run(["python/evaluate_hypotheses.py", "outputs/splits/validation.parquet",
                    *[str(p) for p in args.hypotheses], "--output", str(args.output)])
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
