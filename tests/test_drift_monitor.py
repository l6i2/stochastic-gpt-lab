from __future__ import annotations

import csv
import tempfile
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from drift_monitor import (compare_drift, compare_health_metadata,
                           summarize_feature_csv, summarize_shadow_latency)  # noqa: E402


class DriftMonitorTests(unittest.TestCase):
    def test_feature_drift_has_no_outcome_fields_or_scoring(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "features.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=["spread", "atr_ratio"])
                writer.writeheader(); writer.writerows([{"spread": 0.5, "atr_ratio": 1.0}, {"spread": 4, "atr_ratio": ""}])
            now = summarize_feature_csv(path, whitelist={"spread", "atr_ratio"},
                                        bins={"spread": [1, 2, 5], "atr_ratio": [0.8, 1.25]})
            baseline = {"feature_only": True, "features": {
                "spread": {"counts": [1, 0, 1, 0], "missing": 0, "missing_rate": 0},
                "atr_ratio": {"counts": [0, 1, 1], "missing": 0, "missing_rate": 0},
            }}
            report = compare_drift(baseline, now)
            self.assertFalse(report["labels_read"])
            self.assertFalse(report["pnl_read"])
            self.assertFalse(report["candidate_scored"])
            self.assertFalse(report["threshold_tuning"])

    def test_outcome_columns_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text("atr,pnl\n1,2\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "whitelist|outcome"):
                summarize_feature_csv(path, whitelist={"atr", "pnl"}, bins={"atr": [1], "pnl": [1]})

    def test_coverage_spread_and_latency_drift_are_metadata_only(self):
        baseline = {"spread_distribution_metadata": {"low": 8, "high": 2},
                    "session_coverage_metadata": {"Asia": 5, "London": 5},
                    "volatility_coverage_metadata": {"low": 4, "high": 6},
                    "latency_distribution_metadata": {"bin_0": 5, "bin_1": 5},
                    "missing_utc_days": [], "invalid_ticks": 0, "invalid_bars": 0}
        current = {"spread_distribution_metadata": {"low": 2, "high": 8},
                   "session_coverage_metadata": {"Asia": 5, "London": 5},
                   "volatility_coverage_metadata": {"low": 4, "high": 6},
                   "latency_distribution_metadata": {"bin_0": 1, "bin_1": 9},
                   "missing_utc_days": ["2026-10-20"], "invalid_ticks": 0, "invalid_bars": 0,
                   "session_calendar_verified": False}
        report = compare_health_metadata(baseline, current)
        self.assertTrue(report["metadata_distributions"]["spread_distribution_metadata"]["alert"])
        self.assertTrue(report["quality_and_gaps"]["missing_utc_days_changed"])
        self.assertFalse(report["labels_read"])
        self.assertFalse(report["candidate_scored"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "shadow.jsonl"
            path.write_text('{"latency_ms":10}\n{"latency_ms":90}\n', encoding="utf-8")
            self.assertEqual(summarize_shadow_latency(path, edges_ms=[50]), {"bin_0": 1, "bin_1": 1})


if __name__ == "__main__":
    unittest.main()
