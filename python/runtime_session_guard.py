"""Fail-closed session checks; read-only observations never authorize orders or maturity."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "configs/xm_session_probe_evidence_20261023.json"
DAYS = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")


def eu_expected_offset_seconds(now: datetime) -> int:
    """Diagnostic EU expectation only; never attest the XM server clock with this."""
    now = _utc(now)
    def boundary(month):
        day = datetime(now.year, month + 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
        return day.replace(hour=1) - timedelta(days=(day.weekday() - 6) % 7)
    return 10800 if boundary(3) <= now < boundary(10) else 7200


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("Session timestamps require explicit UTC")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class SessionObservation:
    checked_at_utc: datetime
    quote_time_utc: datetime
    connected: bool = False
    account_mode: str = "UNKNOWN"
    server: str = ""
    symbol: str = ""
    bid: float = 0.0
    ask: float = 0.0
    offset_seconds: int | None = None
    clock_verified: bool = False
    calendar_reconciled: bool = False
    holiday_status: str = "UNKNOWN"  # NORMAL must be independently attested for this server date.
    broker_market_state: str = "UNKNOWN"  # Fresh ticks alone cannot prove executable availability.


@dataclass(frozen=True)
class SessionDecision:
    allowed: bool
    reason: str
    checked_at_utc: datetime
    evidence_sha256: str
    orders_sent: int = 0


class RuntimeSessionGuard:
    """Validated broker-session snapshot plus independent, fresh runtime evidence.

    Missing clock reconciliation, holiday attestation, broker-open evidence or
    fresh quotes always blocks. This guard has no broker connection or order API.
    """
    def __init__(self, path: Path = EVIDENCE):
        path = Path(path)
        raw = path.read_bytes()
        self.evidence_sha256 = hashlib.sha256(raw).hexdigest()
        if path.with_name(path.name + ".sha256").read_text(encoding="ascii").split()[0] != self.evidence_sha256:
            raise ValueError("Session evidence hash mismatch")
        data = json.loads(raw)
        if data.get("symbol") != "US30Cash" or not data.get("server"):
            raise ValueError("Session evidence identity invalid")
        self.server = data["server"]
        rows = data["records"]
        if (not rows[0].startswith("XM_SESSION_PROBE|START|symbol=US30Cash|symbol_selected=YES|")
                or rows[-1] != "XM_SESSION_PROBE|END"
                or not rows[1].startswith("XM_SESSION_PROBE|CLOCK|")):
            raise ValueError("Session evidence is incomplete")
        start = dict(part.split("=", 1) for part in rows[0].split("|")[2:])
        if start["server"] != self.server:
            raise ValueError("Probe server mismatch")
        clock = dict(part.split("=", 1) for part in rows[1].split("|")[2:])
        self.captured_at = datetime.strptime(clock["utc_time"], "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)
        server_clock = datetime.strptime(clock["server_time"], "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)
        self.offset_seconds = int(clock["offset_seconds"])
        if self.offset_seconds not in (7200, 10800) or (server_clock - self.captured_at).total_seconds() != self.offset_seconds:
            raise ValueError("Probe clock mismatch")
        self.sessions = {kind: {day: [] for day in DAYS} for kind in ("QUOTE", "TRADE")}
        for row in rows[2:-1]:
            parts = row.split("|")
            kind = parts[1]
            if kind not in self.sessions:
                raise ValueError("Unknown probe record")
            fields = dict(part.split("=", 1) for part in parts[2:])
            day = fields["day"]
            sessions = self.sessions[kind][day]
            if int(fields["index"]) != len(sessions):
                raise ValueError("Non-contiguous session indexes")
            a, b = self._seconds(fields["from"]), self._seconds(fields["to"])
            # MQL5 ignores the date of returned times. Midnight end means day end;
            # unsupported non-midnight overnight intervals remain ambiguous.
            if b == 0 and a > 0:
                b = 86400
            if b <= a or (sessions and a < sessions[-1][1]):
                raise ValueError("Ambiguous or overlapping session")
            sessions.append((a, b))
        for day in DAYS:
            for a, b in self.sessions["TRADE"][day]:
                if not any(q0 <= a < b <= q1 for q0, q1 in self.sessions["QUOTE"][day]):
                    raise ValueError("Trade session outside quote session")
        if not any(self.sessions["TRADE"].values()):
            raise ValueError("No trade sessions in evidence")

    @staticmethod
    def _seconds(value: str) -> int:
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
            raise ValueError("Invalid session time")
        h, m = map(int, value.split(":"))
        return h * 3600 + m * 60

    def check(self, observation: SessionObservation | None, *, now_utc: datetime) -> SessionDecision:
        now = _utc(now_utc)
        def result(reason):
            return SessionDecision(reason == "SESSION_RUNTIME_PASS", reason, now, self.evidence_sha256)
        if not isinstance(observation, SessionObservation):
            return result("SESSION_RUNTIME_MISSING")
        try:
            checked, quote_time = _utc(observation.checked_at_utc), _utc(observation.quote_time_utc)
        except ValueError:
            return result("INVALID_RUNTIME_TIME")
        if observation.connected is not True or observation.account_mode != "DEMO":
            return result("ENVIRONMENT_NOT_VERIFIED_DEMO")
        if observation.server != self.server or observation.symbol != "US30Cash":
            return result("SESSION_IDENTITY_MISMATCH")
        if not 0 <= (now - checked).total_seconds() <= 5:
            return result("STALE_SESSION_OBSERVATION")
        if observation.broker_market_state == "CLOSED":
            return result("BROKER_MARKET_CLOSED")
        if observation.clock_verified is not True or observation.calendar_reconciled is not True:
            return result("CLOCK_OR_CALENDAR_AMBIGUOUS")
        if observation.offset_seconds != self.offset_seconds:
            return result("OFFSET_CHANGED_REFRESH_REQUIRED")
        if not 0 <= (now - self.captured_at).total_seconds() <= 7 * 86400:
            return result("SESSION_SNAPSHOT_EXPIRED")
        if eu_expected_offset_seconds(now) != eu_expected_offset_seconds(self.captured_at):
            return result("DST_TRANSITION_REFRESH_REQUIRED")
        wall = now + timedelta(seconds=self.offset_seconds)
        day = DAYS[wall.weekday()]
        second = wall.hour * 3600 + wall.minute * 60 + wall.second + wall.microsecond / 1e6
        if not any(a <= second < b for a, b in self.sessions["TRADE"][day]):
            return result("OUTSIDE_OBSERVED_TRADE_SESSION")
        if observation.holiday_status == "CLOSED":
            return result("HOLIDAY_CLOSED")
        if observation.holiday_status != "NORMAL":
            return result("HOLIDAY_UNKNOWN_REQUIRE_RUNTIME_GUARD")
        if observation.broker_market_state != "OPEN":
            return result("BROKER_MARKET_STATE_UNKNOWN")
        if not 0 <= (now - quote_time).total_seconds() <= 5:
            return result("NO_FRESH_QUOTE")
        if not (all(type(v) in (int, float) and math.isfinite(v) for v in (observation.bid, observation.ask))
                and 0 < observation.bid <= observation.ask):
            return result("INVALID_RUNTIME_QUOTE")
        return result("SESSION_RUNTIME_PASS")
