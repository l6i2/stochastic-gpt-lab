"""Pure native-order checks, not UTC certification or an authorization gate.

Times here are untouched broker labels. Sequence identifies arrivals sharing
one timestamp. Stages model source execution order, not measured CPU latency.
"""
from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Position:
    quote_index: int
    stage: int  # 0 receive, 1 closed context computed, 2 decision


def check_availability(*, bar_open_ms, feature_max_ms, arrival_ms,
                       quote_ms, feature_ready, decision, domain):
    if domain != "XM_NATIVE_ORDER":
        raise ValueError("DOMAIN_NOT_PROVEN_NATIVE")
    values = (bar_open_ms, feature_max_ms, arrival_ms, quote_ms,
              feature_ready.quote_index, decision.quote_index,
              feature_ready.stage, decision.stage)
    if any(type(v) is not int or v < 0 for v in values):
        raise ValueError("INVALID_INTEGER_POSITION")
    if bar_open_ms % 300000:
        raise ValueError("UNALIGNED_M5")
    cutoff = bar_open_ms + 300000 - 1
    if feature_max_ms > cutoff or arrival_ms <= cutoff:
        raise ValueError("FORMING_BAR_OR_PREMATURE_DECISION")
    if quote_ms > arrival_ms:
        raise ValueError("FUTURE_QUOTE")
    if feature_ready.stage != 1 or decision.stage != 2:
        raise ValueError("INVALID_STAGE")
    if feature_ready > decision:
        raise ValueError("FEATURE_NOT_YET_AVAILABLE")
    return {"native_order": "PASS", "cutoff_is_availability_time": False,
            "physical_availability": "NOT_CERTIFIED",
            "training_authorized": False}


def check_policy_fill(*, decision_index, decision_ms, fill_index,
                      fill_ms, latency_ms):
    """A policy fill must be a later arrival, even at equal native timestamps.

    Frozen baseline entry at the triggering quote is intentionally outside
    this policy check; it remains an idealized virtual baseline unchanged.
    """
    if any(type(v) is not int or v < 0 for v in
           (decision_index, decision_ms, fill_index, fill_ms, latency_ms)):
        raise ValueError("INVALID_FILL_POSITION")
    if latency_ms not in (0, 250, 500):
        raise ValueError("UNREGISTERED_LATENCY")
    if fill_index <= decision_index or fill_ms < decision_ms + latency_ms:
        raise ValueError("FILL_BEFORE_ARRIVAL_OR_LATENCY")


def training_readiness():
    """No input, approval flag, file or environment can activate this draft."""
    return {"proposal_status": "DRAFT_NOT_ACTIVE",
            "training_authorized": False,
            "training_readiness": "BLOCKED_BY_RESEARCH_GOVERNANCE"}
