from __future__ import annotations

import csv
import gzip
import math
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from future_cohort_health import _bar_feature_rows  # noqa: E402
from future_validation_collector import BAR_FIELDS  # noqa: E402


class FutureCohortMetadataCausalityTests(unittest.TestCase):
    def _bars(self, root: Path, *, future_changed: bool) -> list[dict]:
        raw = root / "raw/20261019"
        raw.mkdir(parents=True)
        path = raw / "bars.csv.gz"
        start = 1792368000
        rows = []
        with gzip.open(path, "wt", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=BAR_FIELDS)
            writer.writeheader()
            previous = 40000.0
            for i in range(500):
                phase = i if i < 360 or not future_changed else 3 * i
                amplitude = 150.0 if i < 360 or not future_changed else 650.0
                close = 40000.0 + amplitude * math.sin(2 * math.pi * phase / 20)
                op = previous
                hi = max(op, close) + 2.0
                lo = min(op, close) - 2.0
                row = {"time": start + i * 300, "open": op, "high": hi, "low": lo,
                       "close": close, "tick_volume": 10 + i % 5, "spread": 5,
                       "real_volume": 0}
                writer.writerow(row)
                rows.append(row)
                previous = close
        return [{"day_utc": "20261019", "bars_file": "raw/20261019/bars.csv.gz",
                 "bars_rows": len(rows)}]

    def test_future_bar_perturbation_leaves_prior_metadata_signals_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_root = Path(tmp) / "base"
            changed_root = Path(tmp) / "changed"
            base_segments = self._bars(base_root, future_changed=False)
            changed_segments = self._bars(changed_root, future_changed=True)
            base = list(_bar_feature_rows(base_segments, base_root))
            changed = list(_bar_feature_rows(changed_segments, changed_root))
            cutoff = 1792368000 + 360 * 300
            cutoff_iso = datetime.fromtimestamp(cutoff, timezone.utc).isoformat().replace("+00:00", "Z")
            before = [row for row in base if row.get("time_utc", "") and row["time_utc"] <= cutoff_iso]
            after = [row for row in changed if row.get("time_utc", "") and row["time_utc"] <= cutoff_iso]
            self.assertTrue(before, "fixture must produce pre-perturbation signals")
            self.assertEqual(before, after)
            future_base = [row for row in base if row.get("time_utc", "") and row["time_utc"] > cutoff_iso]
            future_changed = [row for row in changed if row.get("time_utc", "") and row["time_utc"] > cutoff_iso]
            self.assertNotEqual(future_base, future_changed,
                                "future mutation control must change later metadata outputs")


if __name__ == "__main__":
    unittest.main()
