"""Persistent mock/shadow adapter; it can record decisions but cannot send orders."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any

from demo_safety import DemoLimits, RuntimeState, authorize_demo_decision


class MockShadowExecutor:
    """Fail-closed local recorder with durable deduplication and audit events.

    `enabled` defaults to False. Even when enabled, the only side effect is an
    SQLite row marked `MOCK_ONLY_ACCEPTED`; this class has no broker adapter.
    """

    def __init__(self, database_path: Path, *, enabled: bool = False):
        self.database_path = Path(database_path)
        self.enabled = enabled is True

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path, timeout=10.0)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("""CREATE TABLE IF NOT EXISTS processed_signals (
            signal_key TEXT PRIMARY KEY, recorded_utc TEXT NOT NULL)""")
        connection.execute("""CREATE TABLE IF NOT EXISTS audit_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp_utc TEXT NOT NULL, signal_key TEXT NOT NULL,
            account_mode TEXT NOT NULL, decision TEXT NOT NULL,
            status TEXT NOT NULL, reason TEXT NOT NULL,
            candidate_sha256 TEXT NOT NULL, payload_json TEXT NOT NULL)""")
        return connection

    def record(self, state: RuntimeState, limits: DemoLimits, *, decision: str,
               candidate_sha256: str, seen_signal_keys: set[str] | None = None) -> dict[str, Any]:
        if decision not in {"FOLLOW", "INVERT", "NO_DECISION"}:
            raise ValueError("Mock adapter accepts only hypothetical decisions")
        if len(candidate_sha256) != 64 or any(c not in "0123456789abcdef" for c in candidate_sha256.lower()):
            raise ValueError("candidate_sha256 must be a 64-character SHA-256 hex digest")
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        if state.account_mode != "DEMO":
            status, reason = "BLOCKED", "ACCOUNT_MODE_NOT_DEMO"
        elif not self.enabled:
            status, reason = "DISABLED", "MOCK_EXECUTOR_DISABLED"
        else:
            seen = set(seen_signal_keys or ())
            allowed, reason = authorize_demo_decision(state, limits, seen)
            status = "MOCK_ONLY_ACCEPTED" if allowed else "BLOCKED"

        payload = {
            "timestamp_utc": timestamp,
            "signal_key": state.signal_key,
            "account_mode": state.account_mode,
            "symbol": state.symbol,
            "decision": decision,
            "status": status,
            "reason": reason,
            "candidate_sha256": candidate_sha256.lower(),
            "mock_only": True,
            "orders_sent": 0,
        }
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            exists = connection.execute(
                "SELECT 1 FROM processed_signals WHERE signal_key=?", (state.signal_key,)
            ).fetchone()
            if exists and status == "MOCK_ONLY_ACCEPTED":
                status, reason = "BLOCKED", "DUPLICATE_OR_EMPTY_SIGNAL"
                payload.update(status=status, reason=reason)
            connection.execute(
                "INSERT INTO audit_events(timestamp_utc,signal_key,account_mode,decision,status,reason,candidate_sha256,payload_json) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (timestamp, state.signal_key, state.account_mode, decision, status, reason,
                 candidate_sha256.lower(), json.dumps(payload, sort_keys=True, separators=(",", ":"))),
            )
            if status == "MOCK_ONLY_ACCEPTED":
                connection.execute("INSERT INTO processed_signals VALUES(?,?)", (state.signal_key, timestamp))
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return payload

