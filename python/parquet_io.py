"""Parquet I/O with a safe backend choice for the current CPU."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path


def parquet_engine() -> str:
    """Choose a working pandas engine without invoking unsupported Arrow SIMD."""
    requested = os.environ.get("STOCHASTIC_PARQUET_ENGINE")
    if requested:
        if requested not in {"pyarrow", "fastparquet"}:
            raise ValueError("STOCHASTIC_PARQUET_ENGINE must be pyarrow or fastparquet")
        if importlib.util.find_spec(requested) is None:
            raise ImportError(f"Requested Parquet engine is not installed: {requested}")
        return requested

    has_pyarrow = importlib.util.find_spec("pyarrow") is not None
    has_fastparquet = importlib.util.find_spec("fastparquet") is not None
    if not has_pyarrow and not has_fastparquet:
        raise ImportError("Parquet I/O requires pyarrow or fastparquet")

    # PyArrow's Windows wheels can contain SSE4.2 instructions. NumPy exposes
    # its detected CPU flags; prefer fastparquet on older x86 hosts to avoid a
    # hard process crash (STATUS_ILLEGAL_INSTRUCTION) inside Arrow.
    try:
        import numpy as np

        features = np.core._multiarray_umath.__cpu_features__
        has_sse42 = bool(features.get("SSE42", False))
    except (AttributeError, ImportError):
        has_sse42 = True

    if has_pyarrow and has_sse42:
        return "pyarrow"
    if has_fastparquet:
        return "fastparquet"
    if has_pyarrow:
        raise RuntimeError(
            "This CPU lacks SSE4.2 and no fastparquet fallback is installed; "
            "rebuild PyArrow with SIMD disabled or install fastparquet."
        )
    raise ImportError("Parquet I/O requires pyarrow or fastparquet")


def read_parquet(path: str | Path, **kwargs):
    import pandas as pd
    return pd.read_parquet(path, engine=parquet_engine(), **kwargs)


def write_parquet(frame, path: str | Path, **kwargs) -> None:
    frame.to_parquet(path, engine=parquet_engine(), **kwargs)
