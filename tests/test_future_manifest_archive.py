from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "python"))
from run_future_validation_collector import _archive_current_manifest  # noqa: E402
from future_cohort_health import _manifest_chain_status  # noqa: E402
from future_validation_collector import _new_manifest, _save_manifest  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FutureManifestArchiveTests(unittest.TestCase):
    def test_snapshots_are_immutable_and_future_links_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            cohort = Path(tmp)
            manifest = _new_manifest(ROOT / "configs/future_validation_cohort_manifest.template.json")
            _save_manifest(cohort, manifest, previous_hash=None)
            _archive_current_manifest(cohort)
            first_hash = digest(cohort / "cohort_manifest.json")
            status, passed = _manifest_chain_status(cohort, first_hash)
            self.assertEqual(status, "FULL_CHAIN_VERIFIED")
            self.assertTrue(passed)
            manifest["status"] = "TEST_UPDATED"
            _save_manifest(cohort, manifest, previous_hash=first_hash)
            _archive_current_manifest(cohort)
            second_hash = digest(cohort / "cohort_manifest.json")
            status, passed = _manifest_chain_status(cohort, second_hash)
            self.assertEqual(status, "FULL_CHAIN_VERIFIED")
            self.assertTrue(passed)
            ledger = cohort / "manifest_history/chain.jsonl"
            rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[1]["previous_manifest_sha256"], first_hash)

    def test_restart_recovers_snapshot_written_before_ledger_append(self):
        for initial in (True, False):
            with self.subTest(initial=initial), tempfile.TemporaryDirectory() as tmp:
                cohort = Path(tmp)
                manifest = _new_manifest(ROOT / "configs/future_validation_cohort_manifest.template.json")
                _save_manifest(cohort, manifest, previous_hash=None)
                parent = None
                if not initial:
                    _archive_current_manifest(cohort)
                    parent = digest(cohort / "cohort_manifest.json")
                    manifest["status"] = "TEST_UPDATED"
                    _save_manifest(cohort, manifest, previous_hash=parent)
                current = digest(cohort / "cohort_manifest.json")
                history = cohort / "manifest_history"
                history.mkdir(exist_ok=True)
                snapshot = history / f"{current}.json"
                snapshot.write_bytes((cohort / "cohort_manifest.json").read_bytes())
                _archive_current_manifest(cohort)
                _archive_current_manifest(cohort)
                self.assertEqual(_manifest_chain_status(cohort, current), ("FULL_CHAIN_VERIFIED", True))
                records = (history / "chain.jsonl").read_text().splitlines()
                self.assertEqual(len(records), 1 if initial else 2)

    def test_orphan_snapshot_with_wrong_parent_is_not_recovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            cohort = Path(tmp)
            manifest = _new_manifest(ROOT / "configs/future_validation_cohort_manifest.template.json")
            _save_manifest(cohort, manifest, previous_hash=None)
            _archive_current_manifest(cohort)
            _save_manifest(cohort, manifest, previous_hash="0" * 64)
            current = digest(cohort / "cohort_manifest.json")
            history = cohort / "manifest_history"
            (history / f"{current}.json").write_bytes((cohort / "cohort_manifest.json").read_bytes())
            before = (history / "chain.jsonl").read_bytes()
            with self.assertRaisesRegex(ValueError, "does not link"):
                _archive_current_manifest(cohort)
            self.assertEqual((history / "chain.jsonl").read_bytes(), before)

    def test_altered_snapshot_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            cohort = Path(tmp)
            _save_manifest(cohort, _new_manifest(ROOT / "configs/future_validation_cohort_manifest.template.json"), previous_hash=None)
            _archive_current_manifest(cohort)
            manifest_hash = digest(cohort / "cohort_manifest.json")
            snapshot = next((cohort / "manifest_history").glob("*.json"))
            snapshot.write_text("{}", encoding="utf-8")
            status, passed = _manifest_chain_status(cohort, manifest_hash)
            self.assertEqual(status, "SNAPSHOT_HASH_MISMATCH")
            self.assertFalse(passed)


if __name__ == "__main__":
    unittest.main()
