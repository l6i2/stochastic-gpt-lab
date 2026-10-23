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
        (cohort / "cohort_manifest.sha256").write_text(sha256(cohort / "cohort_manifest.json") + "\n", encoding="ascii")
        health = cohort / "cohort_health_report.json"
        health.write_text(json.dumps({"cohort_mature": True,
                                      "cohort_manifest_sha256": sha256(cohort / "cohort_manifest.json"),
                                      "scoring_performed": False}), encoding="utf-8")
        health.with_name(health.name + ".sha256").write_text(sha256(health) + "\n", encoding="ascii")
        candidate = root / "candidate.json"
        candidate.write_text('{"candidate_id":"fixture-v1","status":"FROZEN"}\n', encoding="utf-8")
        candidate.with_name(candidate.name + ".sha256").write_text(sha256(candidate) + "  candidate.json\n", encoding="ascii")
        table = evaluation / "evaluation.csv"
        with table.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=["signal_id", "signal_time_utc", "side", "decision", "candidate_pnl", "follow_pnl", "invert_pnl"])
            writer.writeheader()
            writer.writerows([
                {"signal_id": "s1", "signal_time_utc": "2026-10-19T00:00:00Z", "side": "BUY", "decision": "FOLLOW", "candidate_pnl": 2, "follow_pnl": 1, "invert_pnl": -1},
                {"signal_id": "s2", "signal_time_utc": "2026-10-19T00:05:00Z", "side": "SELL", "decision": "INVERT", "candidate_pnl": -1, "follow_pnl": -2, "invert_pnl": 1},
            ])
        manifest = evaluation / "evaluation_manifest.json"
        manifest.write_text(json.dumps({
            "candidate_sha256": sha256(candidate),
            "evaluation_table_sha256": sha256(table),
            "cohort_manifest_sha256": sha256(cohort / "cohort_manifest.json"),
            "protocol_sha256": sha256(Path(__file__).resolve().parents[1] / "docs/PROSPECTIVE_EVALUATION_PROTOCOL.md"),
            "evaluator_sha256": sha256(Path(__file__).resolve().parents[1] / "python/future_validation_evaluator.py"),
            "health_report_sha256": sha256(health),
            "maturity_status": "PASS", "causality_status": "PASS",
        }), encoding="utf-8")
        authorization = evaluation / "authorization.json"
        authorization.write_text(json.dumps({
            "user_authorized": True,
            "authorization_id": "fixture-authorization-1",
            "single_use_nonce": "b" * 64,
            "candidate_sha256": sha256(candidate),
            "evaluation_table_sha256": sha256(table),
            "cohort_manifest_sha256": sha256(cohort / "cohort_manifest.json"),
            "protocol_sha256": sha256(Path(__file__).resolve().parents[1] / "docs/PROSPECTIVE_EVALUATION_PROTOCOL.md"),
            "evaluator_sha256": sha256(Path(__file__).resolve().parents[1] / "python/future_validation_evaluator.py"),
            "health_report_sha256": sha256(health),
        }), encoding="utf-8")
        self._bind_causal_fixture(cohort, candidate, table, manifest, authorization)
        return cohort, candidate, table, manifest, authorization

    def _bind_causal_fixture(self, cohort, candidate, table, manifest, authorization):
        # Synthetic fixture only: no real causal PASS artifact is generated.
        audit = cohort / "evaluation/causality_audit.json"
        audit.write_text(json.dumps({
            "status": "PASS", "cohort_manifest_sha256": sha256(cohort / "cohort_manifest.json"),
            "evaluation_table_sha256": sha256(table), "candidate_sha256": sha256(candidate),
            "metadata_spec_sha256": sha256(Path(__file__).resolve().parents[1] / "configs/future_cohort_metadata_spec.json"),
            "pnl_read": False, "labels_read": False, "base_trigger_parity_pass": True,
            "feature_timestamps_pass": True, "target_feature_separation_pass": True,
            "independent_replay_parity_pass": True}), encoding="utf-8")
        audit.with_name(audit.name + ".sha256").write_text(sha256(audit))
        health = cohort / "cohort_health_report.json"
        data = json.loads(health.read_text())
        data.update(causality_audit_pass=True, causality_audit_sha256=sha256(audit))
        health.write_text(json.dumps(data)); health.with_name(health.name + ".sha256").write_text(sha256(health))
        for path in (manifest, authorization):
            data = json.loads(path.read_text())
            data.update(causality_audit_sha256=sha256(audit), health_report_sha256=sha256(health))
            path.write_text(json.dumps(data))

    def test_evaluation_is_one_time_hash_bound_and_never_tunes(self):
        with tempfile.TemporaryDirectory() as tmp:
            cohort, candidate, table, manifest, authorization = self._fixture(Path(tmp))
            result = evaluate(candidate_path=candidate, eval_csv=table,
                              eval_manifest_path=manifest, authorization_path=authorization,
                              cohort_root=cohort, ledger_root=cohort / "ledger")
            self.assertEqual(result["status"], "EVALUATED_ONCE")
            self.assertEqual(result["metrics"]["all"]["n"], 2)
            self.assertEqual(set(result["metrics"]) - {"all"}, {"BUY", "SELL"})
            self.assertFalse(result["tuning_allowed"])
            self.assertFalse(result["final_test_accessed"])
            self.assertFalse(result["demo_enabled"])
            self.assertFalse(result["live_trading"])
            ledger = cohort / "ledger"
            self.assertEqual(len(list(ledger.glob("*.consumed"))), 1)
            self.assertEqual(len((ledger / "evaluation_audit.jsonl").read_text(encoding="utf-8").splitlines()), 2)
            with self.assertRaisesRegex(ValueError, "already been consumed"):
                evaluate(candidate_path=candidate, eval_csv=table,
                         eval_manifest_path=manifest, authorization_path=authorization,
                         cohort_root=cohort, ledger_root=cohort / "ledger")

    def test_one_time_authorization_is_consumed_before_malformed_table_is_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            cohort, candidate, table, manifest, authorization = self._fixture(Path(tmp))
            table.write_text("malformed\n", encoding="utf-8")
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["evaluation_table_sha256"] = sha256(table)
            manifest.write_text(json.dumps(data), encoding="utf-8")
            auth = json.loads(authorization.read_text(encoding="utf-8"))
            auth["evaluation_table_sha256"] = sha256(table)
            authorization.write_text(json.dumps(auth), encoding="utf-8")
            self._bind_causal_fixture(cohort, candidate, table, manifest, authorization)
            with self.assertRaisesRegex(ValueError, "lacks required columns"):
                evaluate(candidate_path=candidate, eval_csv=table,
                         eval_manifest_path=manifest, authorization_path=authorization,
                         cohort_root=cohort, ledger_root=cohort / "ledger")
            with self.assertRaisesRegex(ValueError, "already been consumed"):
                evaluate(candidate_path=candidate, eval_csv=table,
                         eval_manifest_path=manifest, authorization_path=authorization,
                         cohort_root=cohort, ledger_root=cohort / "ledger")

    def test_self_reported_causal_pass_cannot_bypass_missing_or_failed_audit(self):
        for kind in ("missing", "failed", "wrong_table", "native_trigger_failure"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                cohort, candidate, table, manifest, authorization = self._fixture(Path(tmp))
                audit = cohort / "evaluation/causality_audit.json"
                if kind == "missing":
                    audit.unlink()
                else:
                    data = json.loads(audit.read_text())
                    if kind == "failed":
                        data["status"] = "FAIL"
                    elif kind == "wrong_table":
                        data["evaluation_table_sha256"] = "0" * 64
                    else:
                        data["base_trigger_parity_pass"] = False
                    audit.write_text(json.dumps(data))
                    audit.with_name(audit.name + ".sha256").write_text(sha256(audit))
                    # Even a resealed health claim must not rescue a failed audit.
                    health = cohort / "cohort_health_report.json"
                    data = json.loads(health.read_text()); data["causality_audit_sha256"] = sha256(audit)
                    health.write_text(json.dumps(data)); health.with_name(health.name + ".sha256").write_text(sha256(health))
                with self.assertRaisesRegex(ValueError, "[Cc]ausality audit"):
                    evaluate(candidate_path=candidate, eval_csv=table, eval_manifest_path=manifest,
                             authorization_path=authorization, cohort_root=cohort, ledger_root=cohort / "ledger")
                self.assertFalse((cohort / "ledger").exists())

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
