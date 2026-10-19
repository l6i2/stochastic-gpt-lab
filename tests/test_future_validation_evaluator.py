from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from future_validation_evaluator import evaluate, sha256


class FutureValidationEvaluatorTests(unittest.TestCase):
    def _fixture(self, root: Path):
        cohort = root / "cohort"
        evaluation = cohort / "evaluation"
        evaluation.mkdir(parents=True)
        (cohort / "cohort_manifest.json").write_text('{"evaluation_authorized":false}\n', encoding="utf-8")
        candidate = root / "candidate.json"
        candidate.write_text('{"candidate_id":"fixture-v1","status":"FROZEN"}\n', encoding="utf-8")
        candidate.with_name(candidate.name + ".sha256").write_text(sha256(candidate) + "  candidate.json\n", encoding="ascii")
        table = evaluation / "evaluation.csv"
        with table.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=["signal_id", "side", "decision", "candidate_pnl", "follow_pnl", "invert_pnl"])
            writer.writeheader()
            writer.writerows([
                {"signal_id": "s1", "side": "BUY", "decision": "FOLLOW", "candidate_pnl": 2, "follow_pnl": 1, "invert_pnl": -1},
                {"signal_id": "s2", "side": "SELL", "decision": "INVERT", "candidate_pnl": -1, "follow_pnl": -2, "invert_pnl": 1},
            ])
        manifest = evaluation / "evaluation_manifest.json"
        manifest.write_text(json.dumps({
            "candidate_sha256": sha256(candidate),
            "evaluation_table_sha256": sha256(table),
            "cohort_manifest_sha256": sha256(cohort / "cohort_manifest.json"),
            "maturity_status": "PASS", "causality_status": "PASS",
        }), encoding="utf-8")
        authorization = evaluation / "authorization.json"
        authorization.write_text(json.dumps({
            "user_authorized": True,
            "candidate_sha256": sha256(candidate),
            "evaluation_table_sha256": sha256(table),
            "cohort_manifest_sha256": sha256(cohort / "cohort_manifest.json"),
        }), encoding="utf-8")
        return cohort, candidate, table, manifest, authorization

    def test_evaluation_is_one_time_hash_bound_and_never_tunes(self):
        with tempfile.TemporaryDirectory() as tmp:
            cohort, candidate, table, manifest, authorization = self._fixture(Path(tmp))
            result = evaluate(candidate_path=candidate, eval_csv=table,
                              eval_manifest_path=manifest, authorization_path=authorization,
                              cohort_root=cohort, ledger_root=cohort / "ledger")
            self.assertEqual(result["status"], "EVALUATED_ONCE")
            self.assertEqual(result["all"]["n"], 2)
            self.assertEqual(set(result["by_side"]), {"BUY", "SELL"})
            self.assertFalse(result["tuning_allowed"])
            self.assertFalse(result["final_test_accessed"])
            self.assertFalse(result["demo_enabled"])
            self.assertFalse(result["live_trading"])
            with self.assertRaisesRegex(ValueError, "already been consumed"):
                evaluate(candidate_path=candidate, eval_csv=table,
                         eval_manifest_path=manifest, authorization_path=authorization,
                         cohort_root=cohort, ledger_root=cohort / "ledger")

    def test_immature_or_unauthorized_inputs_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            cohort, candidate, table, manifest, authorization = self._fixture(Path(tmp))
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["maturity_status"] = "NOT_MATURE"
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "maturity"):
                evaluate(candidate_path=candidate, eval_csv=table,
                         eval_manifest_path=manifest, authorization_path=authorization,
                         cohort_root=cohort, ledger_root=cohort / "ledger")


if __name__ == "__main__":
    unittest.main()
