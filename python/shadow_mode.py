"""Disabled-by-default, read-only shadow decision pipeline; never sends orders."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
import sqlite3
from pathlib import Path
import re
import time
from typing import Any, Callable

from runtime_session_guard import RuntimeSessionGuard, SessionObservation
from temporal_causality import utc_milliseconds, validate_decision_times


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Shadow timestamps must include UTC offset")
    return parsed.astimezone(timezone.utc)


class ShadowRecorder:
    """Append-only JSONL audit writer for hypothetical decisions only."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def claim(self, signal_id: str) -> bool:
        """Durably reserve before policy execution; a crash cannot replay a signal."""
        if not signal_id:
            raise ValueError("Signal identity required")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.path) + ".sqlite3") as connection:
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("CREATE TABLE IF NOT EXISTS claims (signal_id TEXT PRIMARY KEY)")
            cursor = connection.execute("INSERT OR IGNORE INTO claims VALUES (?)", (signal_id,))
            return cursor.rowcount == 1

    def record(self, event: dict[str, Any]) -> None:
        required = {"timestamp_utc", "signal_id", "candidate_sha256", "decision", "reason",
                    "features", "feature_sha256", "quote_time_utc", "spread", "latency_ms",
                    "feature_max_time_utc", "policy_version", "baseline_decision"}
        if not required.issubset(event):
            raise ValueError(f"Missing shadow event fields: {sorted(required - set(event))}")
        if event["decision"] not in {"FOLLOW", "INVERT", "NO_DECISION"}:
            raise ValueError("Shadow decisions must be hypothetical")
        if not isinstance(event["features"], dict):
            raise ValueError("Shadow features must be a structured object")
        if not event["signal_id"]:
            raise ValueError("Shadow signal ID must be nonempty")
        candidate_hash = event["candidate_sha256"]
        if candidate_hash is None:
            if event["decision"] != "NO_DECISION":
                raise ValueError("A shadow action requires a frozen candidate hash")
        elif not re.fullmatch(r"[0-9a-f]{64}", str(candidate_hash).lower()):
            raise ValueError("Shadow candidate hash must be SHA-256")
        if not re.fullmatch(r"[0-9a-f]{64}", str(event["feature_sha256"]).lower()):
            raise ValueError("Shadow feature hash must be SHA-256")
        actual_feature_hash = sha256_bytes(json.dumps(event["features"], sort_keys=True,
            separators=(",", ":"), allow_nan=False).encode("utf-8"))
        if actual_feature_hash != str(event["feature_sha256"]).lower():
            raise ValueError("Shadow feature hash does not match the feature payload")
        _parse_utc(str(event["timestamp_utc"]))
        _parse_utc(str(event["quote_time_utc"]))
        _parse_utc(str(event["feature_max_time_utc"]))
        if not math.isfinite(float(event["spread"])) or float(event["spread"]) < 0:
            raise ValueError("Shadow spread must be finite and nonnegative")
        if not math.isfinite(float(event["latency_ms"])) or float(event["latency_ms"]) < 0:
            raise ValueError("Shadow latency must be finite and nonnegative")
        payload = dict(event)
        payload.update({"orders_sent": 0, "order_count": 0, "mode": "SHADOW_ONLY"})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())


class ShadowMode:
    """Read-only signal-to-hypothetical-decision runner, disabled by default."""

    def __init__(self, recorder: ShadowRecorder, *, enabled: bool = False,
                 max_quote_age_seconds: float = 5.0,
                 session_guard: RuntimeSessionGuard | None = None):
        self.recorder = recorder
        self.enabled = enabled is True
        self.max_quote_age_seconds = max_quote_age_seconds
        self.order_count = 0
        self.session_guard = session_guard

    def observe(self, *, signal: dict[str, Any], quote: dict[str, Any],
                candidate_sha256: str, policy_version: str,
                decision_fn: Callable[[dict[str, Any]], str],
                now_utc: datetime | None = None,
                session_observation: SessionObservation | None = None) -> dict[str, Any]:
        if not self.enabled:
            return {"status": "DISABLED", "orders_sent": 0, "order_count": self.order_count}
        now = now_utc or datetime.now(timezone.utc)
        utc_milliseconds(now)  # Reject naive clocks before astimezone can infer a local zone.
        now = now.astimezone(timezone.utc)
        signal_time = _parse_utc(signal["signal_time_utc"])
        quote_time = _parse_utc(quote["time_utc"])
        features = dict(signal.get("features", {}))
        feature_time = _parse_utc(signal["feature_max_time_utc"])
        stale_age = (now - quote_time).total_seconds()
        spread = float(quote["ask"]) - float(quote["bid"])
        temporal_ok, temporal_reason = validate_decision_times(
            feature_max_time_msc=utc_milliseconds(feature_time), decision_time_msc=utc_milliseconds(now),
            quote_time_msc=utc_milliseconds(quote_time), max_quote_age_msc=int(self.max_quote_age_seconds * 1000))
        reason = "OK"
        decision = "NO_DECISION"
        if signal_time > now:
            reason = "FUTURE_SIGNAL_TIME"
        elif signal.get("symbol") != "US30Cash" or quote.get("symbol") != "US30Cash":
            reason = "SYMBOL_NOT_ALLOWED"
        elif feature_time > signal_time:
            reason = "FEATURE_LOOKAHEAD"
        elif not (0 < float(quote["bid"]) <= float(quote["ask"])):
            reason = "INVALID_QUOTE"
        elif quote_time > now:
            reason = "FUTURE_QUOTE"
        elif stale_age > self.max_quote_age_seconds:
            reason = "STALE_QUOTE"
        elif not temporal_ok:
            reason = temporal_reason
        elif not candidate_sha256:
            reason = "NO_FROZEN_CANDIDATE"
        elif not re.fullmatch(r"[0-9a-f]{64}", candidate_sha256.lower()):
            reason = "CANDIDATE_HASH_INVALID"
        elif self.session_guard is None:
            reason = "SESSION_GUARD_UNAVAILABLE"
        elif not (session_result := self.session_guard.check(session_observation, now_utc=now)).allowed:
            reason = session_result.reason
        elif not self.recorder.claim(str(signal.get("signal_id", ""))):
            reason = "DUPLICATE_SIGNAL_OR_CRASH_RECOVERY"
        else:
            proposed = decision_fn(features)
            if proposed in {"FOLLOW", "INVERT"}:
                decision, reason = proposed, "HYPOTHETICAL_ONLY"
            else:
                reason = "POLICY_NO_DECISION"
        payload = {
            "timestamp_utc": now.isoformat().replace("+00:00", "Z"),
            "signal_id": str(signal.get("signal_id", "")),
            "candidate_sha256": candidate_sha256.lower() if candidate_sha256 and re.fullmatch(
                r"[0-9a-f]{64}", candidate_sha256.lower()) else None,
            "policy_version": policy_version,
            "decision": decision,
            "baseline_decision": "FOLLOW",
            "reason": reason,
            "signal_time_utc": signal_time.isoformat().replace("+00:00", "Z"),
            "feature_max_time_utc": feature_time.isoformat().replace("+00:00", "Z"),
            "quote_time_utc": quote_time.isoformat().replace("+00:00", "Z"),
            "spread": spread,
            "latency_ms": max(0.0, (now - signal_time).total_seconds() * 1000),
            "features": features,
            "feature_sha256": sha256_bytes(json.dumps(features, sort_keys=True, separators=(",", ":")).encode()),
        }
        self.recorder.record(payload)
        return {"status": reason, "decision": decision, "orders_sent": 0,
                "order_count": self.order_count}


class ReadOnlyMT5Adapter:
    """Thin allowlist adapter exposing data reads and deliberately no trade API."""

    ALLOWED_METHODS = frozenset({"initialize", "shutdown", "terminal_info", "account_info",
                                 "symbol_info", "symbol_info_tick", "copy_rates_from_pos",
                                 "copy_ticks_range", "last_error"})

    def __init__(self, mt5_module: Any):
        self._mt5 = mt5_module

    def __getattr__(self, name: str):
        if name not in self.ALLOWED_METHODS:
            raise AttributeError(f"Read-only MT5 adapter refuses method: {name}")
        return getattr(self._mt5, name)


def prepare_mt5_read_only_adapter() -> ReadOnlyMT5Adapter:
    """Create a read-only adapter without connecting or initializing MT5."""
    import MetaTrader5 as mt5  # type: ignore[import-not-found]
    return ReadOnlyMT5Adapter(mt5)
