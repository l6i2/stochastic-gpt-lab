"""Payload reconciliation, not proof of unique broker event identity."""
from collections import Counter
from .pretrain_contracts import seal
from python.native_m5_rebuild import price_units


def key(r,step):
    if int(r['time'])!=int(r['time_msc'])//1000:raise ValueError('TIME_UNIT_MISMATCH')
    return (int(r['time_msc']),price_units(r['bid'],step),price_units(r['ask'],step),int(r['flags']))


def reconcile(raw,reference,start,end,step):
    for rows in (raw,reference):
        if any(not start<=int(r['time_msc'])<end for r in rows):raise ValueError('OUT_OF_RANGE_NOT_SILENTLY_FILTERED')
    def summarize(rows):
        bid=[r for r in rows if int(r['flags'])&2]
        counts=Counter(key(r,step) for r in bid)
        return bid,counts
    a,ca=summarize(raw);b,cb=summarize(reference)
    missing=cb-ca;extra=ca-cb
    return dict(raw_events=len(raw),reference_events=len(reference),raw_bid=len(a),reference_bid=len(b),
        net_bid_difference=len(b)-len(a),raw_repeated_identical_payloads=sum(n-1 for n in ca.values()),
        reference_repeated_identical_payloads=sum(n-1 for n in cb.values()),
        missing_reference_payload_occurrences=sum(missing.values()),extra_raw_payload_occurrences=sum(extra.values()),
        missing_payload_hashes=[dict(payload_hash=seal(k),native_time_msc=k[0],count=n) for k,n in missing.items()],
        extra_payload_hashes=[dict(payload_hash=seal(k),native_time_msc=k[0],count=n) for k,n in extra.items()],
        ordered_bid_payloads_equal=[key(r,step) for r in a]==[key(r,step) for r in b],
        broker_unique_event_ids_available=False,reference_adopted_as_raw=False,
        disposition='QUARANTINED_NOT_REPAIRED',generation_latency_inferred=False)
