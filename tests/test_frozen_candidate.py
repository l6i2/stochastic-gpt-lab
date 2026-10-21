from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from frozen_candidate import freeze_candidate, sha256, validate_candidate  # noqa: E402


class FrozenCandidateTests(unittest.TestCase):
    def _package(self, root: Path):
        evidence = root / "train_walk_forward.json"
        evidence.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
        digest = "a" * 64
        candidate = {
            "schema_version": "prospective-candidate/1.0", "candidate_id": "fixture-v1",
            "status": "DRAFT", "symbol": "US30Cash", "timeframe": "M5", "latency_ms": 250,
            "features_sha256": digest, "code_sha256": digest, "dataset_sha256": digest,
            "model_sha256": None, "policy_sha256": digest,
            "prospective_protocol_sha256": sha256(ROOT / "docs/PROSPECTIVE_EVALUATION_PROTOCOL.md"),
            "policy": "frozen fixture policy", "failure_criteria": ["frozen_protocol"],
            "strategy_contract": {"stochastic": {"K": 5, "D": 3, "slowing": 3, "trigger_line": "MAIN_K"},
                                  "buy": "previous <= 20 and current > 20",
                                  "sell": "previous >= 80 and current < 80",
                                  "tp": 240, "sl": 180, "time_exit_bars": 100},
            "train_walk_forward_report_sha256": sha256(evidence), "thresholds": {"fixed": 1},
            "discovery_validation_used": False, "future_cohort_used": False,
            "final_test_used": False, "demo_enabled": False, "live_trading": False,
        }
        candidate_path = root / "candidate.json"
        candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
        return candidate_path, evidence

    def test_freeze_is_hash_pinned_immutable_and_rejects_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate, evidence = self._package(root)
            path, digest = freeze_candidate(candidate, evidence, root / "frozen")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["status"], "FROZEN")
            self.assertEqual(path.with_name(path.name + ".sha256").read_text().split()[0], digest)
            with self.assertRaises(FileExistsError):
                freeze_candidate(candidate, evidence, root / "frozen")

    def test_protected_evidence_and_nonpassing_train_report_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate, evidence = self._package(root)
            protected = root / "future_validation_cohort" / "evidence.json"
            protected.parent.mkdir()
            protected.write_text('{"status":"PASS"}', encoding="utf-8")
            data = json.loads(candidate.read_text(encoding="utf-8"))
            data["train_walk_forward_report_sha256"] = sha256(protected)
            with self.assertRaisesRegex(ValueError, "protected"):
                validate_candidate(data, protected)
            evidence.write_text('{"status":"REJECTED"}', encoding="utf-8")
            data["train_walk_forward_report_sha256"] = sha256(evidence)
            with self.assertRaisesRegex(ValueError, "passing TRAIN"):
                validate_candidate(data, evidence)


if __name__ == "__main__":
    unittest.main()
