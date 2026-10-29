"""Compare multiplicity-preserving raw quotes without rewriting either source."""
from collections import Counter


def identity(row, include_flags=False):
    keys = ('time', 'time_msc', 'bid', 'ask', 'last', 'volume', 'volume_real')
    values = tuple(str(row[k]) for k in keys)
    # CSV and NumPy scalar spellings differ; canonicalize numeric fields.
    from decimal import Decimal
    values = tuple(Decimal(value).normalize() for value in values)
    return values + ((int(row['flags']),) if include_flags else ())


def compare_quotes(original, later, native_volume):
    old, new = Counter(identity(r) for r in original), Counter(identity(r) for r in later)
    added, removed = new - old, old - new
    bid_old = sum(bool(int(r['flags']) & 2) for r in original)
    bid_new = sum(bool(int(r['flags']) & 2) for r in later)
    if removed:
        classification = 'BROKER_HISTORY_REVISION_OR_SOURCE_DIVERGENCE'
    elif added:
        classification = 'ARCHIVE_UNDERCOVERAGE_RELATIVE_TO_LATER_BROKER_HISTORY'
    elif bid_new != native_volume:
        classification = 'UNRESOLVED_NATIVE_BAR_VERSUS_TICK_VOLUME_INCONSISTENCY'
    else:
        classification = 'CURRENT_REFERENCE_MATCH_OR_ASK_ONLY_ACCOUNTING'
    changed_times = sorted({int(key[1]) for key in list(added) + list(removed)})
    return dict(classification=classification, original_rows=len(original), later_rows=len(later),
                original_bid_updates=bid_old, later_bid_updates=bid_new, native_tick_volume=native_volume,
                remaining_native_bar_tick_difference=native_volume-bid_new,
                native_bar_tick_reference_consistent=bid_new == native_volume,
                added_payload_multiplicity=sum(added.values()), removed_payload_multiplicity=sum(removed.values()),
                flag_sensitive_equal=Counter(identity(r, True) for r in original) == Counter(identity(r, True) for r in later),
                changed_native_time_msc=changed_times,
                coverage_affected=bool(added or removed), quality_affected=True,
                event_causality_proven=False, original_receipt_evidence_recoverable_by_redownload=False,
                repair_action='PRESERVE_BOTH_VERSIONS_QUARANTINE_ORIGINAL_NO_BACKFILL')
