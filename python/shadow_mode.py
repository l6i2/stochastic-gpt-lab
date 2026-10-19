"""Append-only hypothetical-decision recorder with no trading interface."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ShadowRecorder:
    def __init__(self, path: Path):
        self.path = Path(path)

    def record(self, event: dict[str, Any]) -> None:
        required = {"timestamp_utc", "signal_id", "candidate_sha256", "decision", "reason"}
        if not required.issubset(event):
            raise ValueError(f"Missing shadow event fields: {sorted(required - set(event))}")
        if event["decision"] not in {"FOLLOW", "INVERT", "NO_DECISION"}:
            raise ValueError("Shadow decisions must be hypothetical")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
