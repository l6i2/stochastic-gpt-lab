"""Metadata-only audit of immutable manifest ancestry and append-only segment membership."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def audit_manifest_chain(cohort_root: Path) -> dict:
    root = Path(cohort_root).resolve()
    report = {"status": "FAIL", "verified_from_anchor": False, "prefix_verified": False,
              "snapshots_verified": 0, "pnl_read": False, "labels_read": False}
    try:
        current = root / "cohort_manifest.json"
        current_hash = digest(current)
        if (root / "cohort_manifest.sha256").read_text(encoding="ascii").strip() != current_hash:
            raise ValueError("CURRENT_MANIFEST_HASH_MISMATCH")
        history = root / "manifest_history"
        entries = [json.loads(line) for line in (history / "chain.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        if not entries:
            raise ValueError("EMPTY_LEDGER")
        previous_hash = previous = None
        for i, entry in enumerate(entries):
            sha = entry.get("sha256", "")
            if not re.fullmatch("[0-9a-f]{64}", sha) or entry.get("snapshot") != sha + ".json":
                raise ValueError("NON_CANONICAL_SNAPSHOT_PATH")
            snapshot = history / entry["snapshot"]
            if digest(snapshot) != sha:
                raise ValueError("SNAPSHOT_HASH_MISMATCH")
            obj = json.loads(snapshot.read_text(encoding="utf-8"))
            parent = obj.get("previous_manifest_sha256")
            if parent != entry.get("previous_manifest_sha256"):
                raise ValueError("LEDGER_PARENT_MISMATCH")
            if i == 0:
                report["prefix_verified"] = parent is None
                report["missing_pre_anchor_sha256"] = parent
            elif parent != previous_hash:
                raise ValueError("CHAIN_LINK_MISMATCH")
            if previous is not None:
                for key in ("cohort_id", "cohort_start_utc", "symbol", "timeframe", "collector_code_sha256",
                            "cohort_template_sha256", "evaluation_authorized", "live_trading", "train_access_allowed"):
                    if obj.get(key) != previous.get(key):
                        raise ValueError("IMMUTABLE_IDENTITY_CHANGED:" + key)
                old_segments, segments = previous.get("segments", []), obj.get("segments", [])
                if segments[:len(old_segments)] != old_segments:
                    raise ValueError("ARCHIVED_SEGMENTS_REWRITTEN_OR_REMOVED")
                if obj.get("next_cursor_utc", "") < previous.get("next_cursor_utc", ""):
                    raise ValueError("CURSOR_ROLLBACK")
            previous_hash, previous = sha, obj
            report["snapshots_verified"] += 1
        if previous_hash != current_hash:
            raise ValueError("CURRENT_MANIFEST_NOT_LATEST")
        report.update(status="PASS" if report["prefix_verified"] else "PARTIAL",
                      verified_from_anchor=True, current_manifest_sha256=current_hash,
                      reason="FULL_CHAIN" if report["prefix_verified"] else "PRE_ANCHOR_BYTES_UNAVAILABLE")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        report["reason"] = str(exc)
    return report
