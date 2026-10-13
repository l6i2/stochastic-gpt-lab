"""Classify and record bounded, fail-safe project remediation events."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = {
    "ENVIRONMENT", "MT5_UI", "MQL5_COMPILE", "DATA_COVERAGE", "DATA_QUALITY",
    "PYTHON_DEPENDENCY", "PERFORMANCE", "MEMORY", "STORAGE", "TEST_FAILURE",
    "LEAKAGE_RISK", "SECURITY_GATE", "FINAL_TEST_GATE",
}
PATTERNS = {
    "MQL5_COMPILE": (r"\bmetaeditor\b", r"\bcompile\b", r"\b0 errors\b"),
    "MT5_UI": (r"strategy tester", r"navigator", r"window capture", r"terminal ui"),
    "DATA_COVERAGE": (r"no (?:real )?ticks", r"history.*(?:missing|unavailable)", r"coverage"),
    "DATA_QUALITY": (r"schema", r"duplicate", r"validator", r"aborted dataset"),
    "PYTHON_DEPENDENCY": (r"module not found", r"no module named", r"dependency"),
    "PERFORMANCE": (r"timeout", r"too long", r"slow"),
    "MEMORY": (r"out of memory", r"memory error", r"memory limit"),
    "STORAGE": (r"disk full", r"no space", r"permission denied.*file"),
    "TEST_FAILURE": (r"test.*fail", r"assertionerror", r"unittest"),
    "LEAKAGE_RISK": (r"lookahead", r"future leakage", r"after snapshot"),
    "FINAL_TEST_GATE": (r"final_test", r"final test"),
    "SECURITY_GATE": (r"live_trading", r"real account", r"demo trading"),
}


def classify(reason: str) -> str:
    value = reason.lower()
    for category, patterns in PATTERNS.items():
        if any(re.search(pattern, value) for pattern in patterns):
            return category
    return "ENVIRONMENT"


def safe_actions(category: str) -> list[str]:
    actions = {
        "MQL5_COMPILE": ["inspect the exact compiler diagnostic", "apply only a minimal source fix", "recompile once"],
        "MT5_UI": ["inspect the current window once", "use a prebuilt tester config if supported", "stop after two failed methods"],
        "PYTHON_DEPENDENCY": ["check the project .venv", "install only into the project .venv"],
        "DATA_COVERAGE": ["record exact available start/end times", "do not extend into FINAL_TEST"],
        "DATA_QUALITY": ["quarantine the failed block", "preserve source files and diagnostics"],
        "LEAKAGE_RISK": ["stop the stage", "remove the unsafe feature or reject the dataset"],
        "FINAL_TEST_GATE": ["stop and request explicit authorization"],
        "SECURITY_GATE": ["stop; keep LIVE_TRADING=false and DEMO disabled"],
    }
    return actions.get(category, ["record evidence", "make only bounded reversible changes"])


def record(category: str, stage: str, reason: str, attempts: int = 0,
           artifacts: list[str] | None = None, git_sha: str | None = None,
           manual_action: str | None = None) -> Path:
    if category not in CATEGORIES:
        raise ValueError(f"Unknown category: {category}")
    if not 0 <= attempts <= 2:
        raise ValueError("Automatic attempts must be between 0 and 2")
    now = datetime.now(timezone.utc).isoformat()
    if git_sha is None:
        git_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                 capture_output=True, text=True, check=False).stdout.strip() or "unknown"
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
    payload = {"run_id": run_id, "start_time_utc": now, "end_time_utc": now,
               "git_sha": git_sha, "dataset_hash": None, "status": "BLOCKED",
               "stage": stage, "blocker": {"category": category, "reason": reason,
                                                "manual_action": manual_action,
                                                "automatic_attempts": attempts,
                                                "safe_actions": safe_actions(category)},
               "tests": [], "artifacts": artifacts or [],
               "LIVE_TRADING": False, "FINAL_TEST_accessed": False,
               "DEMO_execution": False}
    folder = ROOT / "outputs" / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{run_id}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    checkpoint = ROOT / "outputs" / "checkpoints"
    checkpoint.mkdir(parents=True, exist_ok=True)
    (checkpoint / "latest.json").write_text(json.dumps({"run_id": run_id, "stage": stage,
        "status": "BLOCKED", "category": category, "manual_action": manual_action,
        "resume_safe": category not in {"MT5_UI", "LEAKAGE_RISK", "SECURITY_GATE", "FINAL_TEST_GATE"}
        and manual_action is None}, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reason")
    parser.add_argument("--stage", default="unknown")
    parser.add_argument("--category", choices=sorted(CATEGORIES))
    parser.add_argument("--attempts", type=int, default=0)
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--manual-action")
    args = parser.parse_args()
    try:
        category = args.category or classify(args.reason)
        path = record(category, args.stage, args.reason, args.attempts, args.artifact,
                      manual_action=args.manual_action)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps({"category": category, "log": str(path.relative_to(ROOT)),
                      "safe_actions": safe_actions(category), "manual_action": args.manual_action}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
