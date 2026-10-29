"""Stream a shared event CSV while retaining only a frozen TRAIN ID set."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


_PROTECTED_SPLIT_NAMES = {
    "validation", "discovery_validation", "discovery-validation",
    "final_test", "final-test", "finaltest",
    "future_validation_cohort", "future-validation-cohort", "futurevalidationcohort",
    "pc_a_raw_archive", "pc_a_raw_backup", "pc_a_data_repair",
    "pc_a_remaining_blockers", "pc_a_evidence_backup", "pc_a_temporal_intake",
}


def assert_train_only_source_path(path: Path) -> Path:
    """Fail before I/O when a TRAIN runner is pointed at a protected split."""
    resolved = Path(path).resolve(strict=False)
    parts = {part.casefold() for part in resolved.parts}
    name = resolved.name.casefold()
    stem = resolved.stem.casefold()
    if (parts & _PROTECTED_SPLIT_NAMES or name in _PROTECTED_SPLIT_NAMES
            or stem in _PROTECTED_SPLIT_NAMES
            or any(token in stem for token in ("validation", "final_test", "final-test"))):
        raise ValueError(f"TRAIN runner refuses protected split path: {resolved}")
    return resolved


def read_events_for_ids(path: Path, columns: list[str], train_ids: set[str], *,
                        chunksize: int = 50_000) -> pd.DataFrame:
    if "signal_id" not in columns or chunksize <= 0 or not train_ids:
        raise ValueError("A nonempty frozen TRAIN ID set and signal_id column are required")
    path = assert_train_only_source_path(path)
    kept = []
    for chunk in pd.read_csv(path, usecols=columns, dtype={"signal_id": str}, chunksize=chunksize):
        selected = chunk[chunk.signal_id.isin(train_ids)]
        if not selected.empty:
            kept.append(selected)
    result = pd.concat(kept, ignore_index=True) if kept else pd.DataFrame(columns=columns)
    actual = set(result.signal_id.astype(str))
    if actual != train_ids or result.signal_id.duplicated().any():
        raise ValueError("Shared event source does not contain exactly one row for each frozen TRAIN ID")
    return result


def read_rows_for_ids(path: Path, signal_ids: set[str], *, columns: list[str] | None = None,
                      chunksize: int = 50_000) -> pd.DataFrame:
    """Stream a shared row table and retain rows belonging only to frozen TRAIN IDs."""
    if not signal_ids or chunksize <= 0:
        raise ValueError("A nonempty frozen TRAIN ID set and positive chunksize are required")
    path = assert_train_only_source_path(path)
    if columns is not None and "signal_id" not in columns:
        raise ValueError("Filtered row columns must include signal_id")
    kept = []
    reader = pd.read_csv(path, usecols=columns, dtype={"signal_id": str}, chunksize=chunksize)
    observed: set[str] = set()
    for chunk in reader:
        if "signal_id" not in chunk:
            raise ValueError("Shared row source is missing signal_id")
        selected = chunk[chunk.signal_id.isin(signal_ids)]
        observed.update(selected.signal_id.astype(str))
        if not selected.empty:
            kept.append(selected)
    if not observed <= signal_ids:
        raise ValueError("Filtered row source contains a signal outside frozen TRAIN membership")
    if kept:
        return pd.concat(kept, ignore_index=True)
    return pd.DataFrame(columns=columns or [])
