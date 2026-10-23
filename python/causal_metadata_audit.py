"""Independent synthetic audit of frozen health-metadata Stochastic semantics; no cohort I/O."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main_values(bars: list[dict], *, native_reference: bool) -> list[float | None]:
    values = []
    for i in range(len(bars)):
        if i < 6:
            values.append(None)
            continue
        numerators, ranges = [], []
        for k in range(i - 2, i + 1):
            window = bars[k - 4:k + 1]
            low, high = min(b["low"] for b in window), max(b["high"] for b in window)
            numerators.append(bars[k]["close"] - low)
            ranges.append(high - low)
        if native_reference:
            value = 100.0 if sum(ranges) == 0 else 100.0 * sum(numerators) / sum(ranges)
        else:
            value = sum(50.0 if width == 0 else 100.0 * num / width
                        for num, width in zip(numerators, ranges)) / 3
        values.append(value)
    return values


def audit_metadata_contract(reference_path: Path | None = None) -> dict:
    # Valid seven-bar OHLC counterexample; no market or cohort observations.
    bars = [{"low": 40000.0, "high": 40010.0, "close": 40009.0} for _ in range(5)]
    bars += [{"low": 40000.0, "high": 40100.0, "close": 40001.0} for _ in range(2)]
    declared = main_values(bars, native_reference=False)[-1]
    native = main_values(bars, native_reference=True)[-1]
    flat = [{"low": 40000.0, "high": 40000.0, "close": 40000.0} for _ in range(7)]
    spec_path = ROOT / "configs/future_cohort_metadata_spec.json"
    health_path = ROOT / "python/future_cohort_health.py"
    source = health_path.read_text(encoding="utf-8")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    frozen_definition_found = (spec["signal_contract"]["stochastic"]["main_line"] == "3-period SMA of fast %K"
                               and "main_k = sum(fastks) / 3.0" in source)
    reference_hash, reference_recognized = None, False
    if reference_path is not None:
        raw = Path(reference_path).read_bytes()
        reference_hash = hashlib.sha256(raw).hexdigest()
        body = raw.decode("utf-16" if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else "utf-8-sig", errors="replace")
        reference_recognized = all(token in body for token in (
            "sum_low +=(close[k]-ExtLowesBuffer[k]);", "sum_high+=(ExtHighesBuffer[k]-ExtLowesBuffer[k]);",
            "ExtMainBuffer[i]=sum_low/sum_high*100;", "ExtMainBuffer[i]=100.0;"))
    return {"status": "FAIL", "reason": "FROZEN_METADATA_NATIVE_TRIGGER_PARITY_NOT_ESTABLISHED",
            "frozen_definition_found": frozen_definition_found,
            "reference_example_recognized": reference_recognized,
            "native_indicator_binary_parity_verified": False,
            "reference_example_sha256": reference_hash,
            "metadata_spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
            "health_code_sha256": hashlib.sha256(health_path.read_bytes()).hexdigest(),
            "synthetic_counterexample": {"frozen_main_k": declared, "native_example_main_k": native,
                "frozen_flat_main_k": main_values(flat, native_reference=False)[-1],
                "native_example_flat_main_k": main_values(flat, native_reference=True)[-1]},
            "existing_support_counts_usable_for_native_trigger_maturity": False,
            "sealed_spec_modified": False, "cohort_read": False,
            "pnl_read": False, "labels_read": False, "threshold_tuning": False}
