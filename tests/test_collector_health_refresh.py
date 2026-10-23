from __future__ import annotations

import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_future_validation_collector import _health_report_matches  # noqa: E402


class CollectorHealthRefreshTests(unittest.TestCase):
    def test_calendar_hash_change_invalidates_health_report(self):
        inputs = {
            "manifest_hash": "m" * 64,
            "metadata_hash": "s" * 64,
            "health_code_hash": "c" * 64,
            "calendar_hash": "a" * 64,
            "candidate_hash": None,
            "causality_audit_hash": None,
            "manifest_chain_status": "FULL_CHAIN_VERIFIED",
        }
        report = {
            "cohort_manifest_sha256": inputs["manifest_hash"],
            "metadata_spec_sha256": inputs["metadata_hash"],
            "health_code_sha256": inputs["health_code_hash"],
            "session_calendar_config_sha256": inputs["calendar_hash"],
            "candidate_sha256": None,
            "causality_audit_sha256": None,
            "manifest_chain_status": inputs["manifest_chain_status"],
        }
        self.assertTrue(_health_report_matches(report, **inputs))
        self.assertFalse(_health_report_matches(report, **{**inputs, "calendar_hash": "b" * 64}))


if __name__ == "__main__":
    unittest.main()
