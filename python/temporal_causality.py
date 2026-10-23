"""Integer-millisecond causal contracts for decision inputs and ordered replay fills."""
from __future__ import annotations
from datetime import datetime,timezone

EPOCH=datetime(1970,1,1,tzinfo=timezone.utc)


def utc_milliseconds(value:datetime)->int:
    if not isinstance(value,datetime) or value.tzinfo is None:
        raise ValueError('Explicit timezone is required; server/local wall time is not UTC evidence')
    delta=value.astimezone(timezone.utc)-EPOCH
    return delta.days*86400000+delta.seconds*1000+delta.microseconds//1000


def validate_decision_times(*,feature_max_time_msc:int,decision_time_msc:int,quote_time_msc:int,
                            max_quote_age_msc:int=5000)->tuple[bool,str]:
    values=(feature_max_time_msc,decision_time_msc,quote_time_msc,max_quote_age_msc)
    if any(type(v) is not int or v<0 for v in values):return False,'INVALID_TEMPORAL_INPUT'
    if feature_max_time_msc>decision_time_msc:return False,'FEATURE_LOOKAHEAD'
    if quote_time_msc>decision_time_msc:return False,'FUTURE_QUOTE'
    if decision_time_msc-quote_time_msc>max_quote_age_msc:return False,'STALE_QUOTE'
    return True,'TEMPORAL_CAUSALITY_PASS'


def validate_execution_times(*,decision_cutoff_msc:int,arrival_time_msc:int,arrival_sequence:int,
                             fill_time_msc:int,fill_sequence:int,latency_msc:int)->tuple[bool,str]:
    """Frozen replay: arrival strictly after cutoff, fill later in sequence and >= latency."""
    values=(decision_cutoff_msc,arrival_time_msc,arrival_sequence,fill_time_msc,fill_sequence,latency_msc)
    if any(type(v) is not int or v<0 for v in values):return False,'INVALID_TEMPORAL_INPUT'
    if arrival_time_msc<=decision_cutoff_msc:return False,'ARRIVAL_NOT_AFTER_CUTOFF'
    if fill_sequence<=arrival_sequence:return False,'FILL_NOT_AFTER_ARRIVAL_SEQUENCE'
    if fill_time_msc<arrival_time_msc+latency_msc:return False,'FILL_BEFORE_LATENCY'
    return True,'EXECUTION_TEMPORAL_PASS'
