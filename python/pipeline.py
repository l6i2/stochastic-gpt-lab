"""Safe project pipeline. This CLI intentionally has no FINAL_TEST command."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import hashlib
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run(args: list[str], stage: str | None = None, *, manual_action: str | None = None,
        resume_safe: bool = False) -> int:
    start = datetime.now(timezone.utc).isoformat()
    proc = subprocess.run([PYTHON, *args], cwd=ROOT, check=False)
    if stage:
        _record_run(stage, start, proc.returncode, args, manual_action, resume_safe)
    return proc.returncode


def _record_run(stage: str, start: str, code: int, command: list[str],
                manual_action: str | None, resume_safe: bool) -> None:
    log_dir, checkpoint_dir = ROOT / "outputs/logs", ROOT / "outputs/checkpoints"
    log_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                         text=True, check=False).stdout.strip()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
    status = "COMPLETED" if code == 0 else "FAILED"
    payload = {"run_id": run_id, "start_time_utc": start,
               "end_time_utc": datetime.now(timezone.utc).isoformat(), "git_sha": sha,
               "dataset_hash": None, "status": status, "stage": stage,
               "blocker": None if code == 0 else {"reason": "stage returned nonzero", "exit_code": code},
               "tests": [], "artifacts": [], "command": command,
               "manual_action": manual_action, "LIVE_TRADING": False,
               "FINAL_TEST_accessed": False, "DEMO_execution": False}
    (log_dir / f"{run_id}.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    state = {"run_id": run_id, "stage": stage, "status":
             "WAITING_MANUAL_MT5" if manual_action else status,
             "resume_safe": bool(resume_safe and not manual_action and code != 0),
             "manual_action": manual_action, "LIVE_TRADING": False,
             "FINAL_TEST_accessed": False, "DEMO_execution": False}
    (checkpoint_dir / "latest.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _status() -> int:
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=ROOT,
                            capture_output=True, text=True, check=False).stdout.strip()
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                         capture_output=True, text=True, check=False).stdout.strip()
    raw = sorted((ROOT / "outputs/intratrade/raw").glob("*/intratrade_snapshots.csv"))
    result = {"repo_branch": branch, "HEAD": sha,
              "intratrade_raw_blocks": [str(p.parent.relative_to(ROOT)) for p in raw],
              "intratrade_master_exists": (ROOT / "outputs/intratrade/master/intratrade_master.parquet").exists(),
              "final_test": "LOCKED", "LIVE_TRADING": False, "demo_execution": "DISABLED"}
    checkpoint = ROOT / "outputs/checkpoints/latest.json"
    result["checkpoint"] = json.loads(checkpoint.read_text(encoding="utf-8")) if checkpoint.exists() else None
    print(json.dumps(result, indent=2))
    return 0


def _resume() -> int:
    checkpoint = ROOT / "outputs/checkpoints/latest.json"
    if not checkpoint.exists():
        print("No checkpoint exists. Run intratrade-export-plan first.", file=sys.stderr)
        return 2
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    if state.get("manual_action"):
        print(json.dumps({"status": "WAITING_MANUAL_ACTION", "stage": state.get("stage"),
                          "manual_action": state["manual_action"], "automatic_retries": 0,
                          "final_test_accessed": False}, indent=2))
        return 2
    if not state.get("resume_safe"):
        print("Checkpoint is not marked safe to replay; inspect status and create the next stage explicitly.",
              file=sys.stderr)
        return 2
    print("Checkpoint is safe to retry, but no resumable stage command is recorded. Use the stage command shown in status.",
          file=sys.stderr)
    return 2


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
    sub.add_parser("intratrade-export-plan", help="write bounded tester configs ending before FINAL_TEST; does not launch MT5")
    sub.add_parser("intratrade-validate", help="validate raw blocks and inherited TRAIN/VALIDATION membership")
    sub.add_parser("intratrade-build", help="build TRAIN and VALIDATION master snapshots only")
    sub.add_parser("intratrade-analysis", help="describe TRAIN snapshots only")
    hfreeze = sub.add_parser("intratrade-hypotheses", help="freeze the predeclared hypothesis set on TRAIN")
    hfreeze.add_argument("--action", choices=("freeze", "validate"), default="freeze")
    sub.add_parser("intratrade-ml", help="fixed intra-trade models: fit TRAIN, score validation")
    sub.add_parser("intratrade-validation", help="evaluate frozen intra-trade hypotheses once")
    sub.add_parser("intratrade-walkforward", help="run bounded intra-trade temporal walk-forward")
    sub.add_parser("status", help="show checkpoints and whether local snapshot blocks exist")
    sub.add_parser("resume", help="resume only a recorded safe stage; never opens FINAL_TEST")
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
        if not status_path.exists():
            status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        else:
            status = json.loads(status_path.read_text(encoding="utf-8"))
        print(json.dumps(status, indent=2))
        return 0 if available else 2
    if args.command == "intratrade-export-plan":
        return run(["python/intratrade_export_plan.py"], args.command,
                   manual_action="In MT5 Strategy Tester, load one generated preset, verify its period and inputs, then press Start once.",
                   resume_safe=False)
    if args.command == "intratrade-validate":
        blocks = sorted((ROOT / "outputs/intratrade/raw").glob("*/intratrade_snapshots.csv"))
        if not blocks:
            print("No raw intra-trade blocks exist; no snapshots are fabricated.", file=sys.stderr)
            return 2
        for snapshot in blocks:
            code = run(["python/validate_intratrade_dataset.py", str(snapshot),
                        "--targets", str(snapshot.parent / "intratrade_snapshot_targets.csv"),
                        "--events", str(snapshot.parent / "stochastic_events.csv"),
                        "--train", "outputs/splits/train.parquet", "--validation", "outputs/splits/validation.parquet"])
            if code:
                return code
        return 0
    if args.command == "intratrade-build":
        blocks = sorted((ROOT / "outputs/intratrade/raw").glob("*/manifest.json"))
        if not blocks:
            print("No manifest-backed raw intra-trade blocks exist.", file=sys.stderr)
            return 2
        return run(["python/build_intratrade_master.py", *[str(p.parent) for p in blocks]],
                   args.command, resume_safe=False)
    if args.command == "intratrade-analysis":
        return run(["python/analyze_intratrade.py"], args.command, resume_safe=False)
    if args.command == "intratrade-hypotheses":
        action = args.action
        command = ["python/intratrade_hypotheses.py", action]
        return run(command, f"intratrade-hypotheses-{action}", resume_safe=False)
    if args.command == "intratrade-ml":
        return run(["python/train_intratrade_models.py"], args.command, resume_safe=False)
    if args.command == "intratrade-validation":
        return run(["python/intratrade_hypotheses.py", "validate"], args.command, resume_safe=False)
    if args.command == "intratrade-walkforward":
        path = ROOT / "python/walk_forward_intratrade.py"
        if not path.exists():
            print("Walk-forward is blocked until the validated TRAIN/VALIDATION snapshot master exists.", file=sys.stderr)
            return 2
        return run(["python/walk_forward_intratrade.py"], args.command, resume_safe=False)
    if args.command == "status":
        return _status()
    if args.command == "resume":
        return _resume()
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
