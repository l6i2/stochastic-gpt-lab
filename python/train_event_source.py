"""Stream a shared event CSV while retaining only a frozen TRAIN ID set."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_events_for_ids(path: Path, columns: list[str], train_ids: set[str], *,
                        chunksize: int = 50_000) -> pd.DataFrame:
    if "signal_id" not in columns or chunksize <= 0 or not train_ids:
        raise ValueError("A nonempty frozen TRAIN ID set and signal_id column are required")
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
