from __future__ import annotations

import csv
import gzip
import json
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from future_cohort_health import build_health_report  # noqa: E402
from future_validation_collector import BAR_FIELDS, TICK_FIELDS, _new_manifest, _save_manifest  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FutureCohortHealthTests(unittest.TestCase):
    def _cohort(self, root: Path):
        cohort = root / "cohort"
        raw = cohort / "raw/20261019"
        raw.mkdir(parents=True)
        ticks = raw / "ticks_20261019.csv.gz"
        with gzip.open(ticks, "wt", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=TICK_FIELDS); writer.writeheader()
            writer.writerow({"time": 1792371600, "time_msc": 1792371600000, "bid": 40000.0,
                             "ask": 40000.5, "last": 0, "volume": 0, "volume_real": 0, "flags": 1})
        bars = raw / "bars_20261019.csv.gz"
        with gzip.open(bars, "wt", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=BAR_FIELDS); writer.writeheader()
            # Synthetic but ordered OHLC fixtures; they cannot create PnL or labels.
            for i in range(48):
                stamp = 1792368000 + i * 300
                close = 40000.0 + (i % 7) - 3
                writer.writerow({"time": stamp, "open": close, "high": close + 2,
                                 "low": close - 2, "close": close, "tick_volume": 5,
                                 "spread": 1, "real_volume": 0})
        manifest = _new_manifest(ROOT / "configs/future_validation_cohort_manifest.template.json")
        manifest["segments"] = [{
            "day_utc": "20261019", "ticks_file": "raw/20261019/ticks_20261019.csv.gz",
            "ticks_sha256": digest(ticks), "ticks_bytes": ticks.stat().st_size, "ticks_rows": 1,
            "bars_file": "raw/20261019/bars_20261019.csv.gz", "bars_sha256": digest(bars),
            "bars_bytes": bars.stat().st_size, "bars_rows": 48,
        }]
        manifest["next_cursor_utc"] = "2026-10-20T00:00:00Z"
        _save_manifest(cohort, manifest, previous_hash=None)
        return cohort

    def test_health_is_metadata_only_and_fails_closed_without_verified_calendar(self):
        with tempfile.TemporaryDirectory() as tmp:
            cohort = self._cohort(Path(tmp))
            report = build_health_report(cohort_root=cohort,
                                         now=datetime(2026, 10, 21, tzinfo=timezone.utc))
            self.assertEqual(report["cohort_rows"], 1)
            self.assertEqual(report["m5_bars"], 48)
            self.assertFalse(report["scoring_performed"])
            self.assertFalse(report["pnl_read"])
            self.assertFalse(report["labels_read"])
            self.assertFalse(report["cohort_mature"])
            self.assertFalse(report["maturity_gates"]["session_calendar_verified"])
            self.assertFalse(report["maturity_gates"]["candidate_frozen"])
            self.assertNotIn("candidate_pnl", json.dumps(report).lower())


if __name__ == "__main__":
    unittest.main()
