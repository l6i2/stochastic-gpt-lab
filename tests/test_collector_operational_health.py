from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from collector_operational_health import operational_health


class OperationalHealthTests(unittest.TestCase):
    def test_runtime_requires_all_environment_gates(self):
        ready = {"SAFE_FOR_RESEARCH": True, "CONNECTED": True,
                 "ACCOUNT_MODE": "DEMO", "US30Cash_AVAILABLE": True}
        for failed in (None, *ready):
            environment = dict(ready)
            if failed is not None:
                environment[failed] = None
            with self.subTest(failed=failed), patch("collector_operational_health.health") as capture:
                capture.return_value = {"collector_status": "HEALTHY"}
                result = operational_health(cohort_root=Path("nonexistent-fixture"),
                                            environment_status=lambda: environment)
                self.assertEqual(result["runtime_ready"], failed is None)
                self.assertEqual(result["capture_data_health"], "HEALTHY")
                self.assertEqual(result["runtime_status"], "READY" if failed is None else "BLOCKED_ENVIRONMENT")

    def test_probe_failure_leaves_runtime_blocked(self):
        with patch("collector_operational_health.health", return_value={"collector_status": "HEALTHY"}):
            result = operational_health(cohort_root=Path("nonexistent-fixture"),
                                        environment_status=lambda: 1 / 0)
        self.assertFalse(result["runtime_ready"])
