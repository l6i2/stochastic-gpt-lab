from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
sys.path.insert(0,str(ROOT/'scripts'))
from manifest_chain_audit import audit_manifest_chain, digest
from future_validation_collector import _new_manifest, _save_manifest
from run_future_validation_collector import _archive_current_manifest


class ManifestChainAuditTests(unittest.TestCase):
    def test_full_and_anchored_chains_and_past_segment_rewrite(self):
        for anchor in (None, 'a'*64):
            with self.subTest(anchor=anchor), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                m=_new_manifest(ROOT/'configs/future_validation_cohort_manifest.template.json')
                m['segments']=[{'day_utc':'20261019','ticks_sha256':'test-fixture'}]
                _save_manifest(root,m,previous_hash=anchor)
                _archive_current_manifest(root)
                first=digest(root/'cohort_manifest.json')
                m['segments'].append({'day_utc':'20261020','ticks_sha256':'fixture2'})
                _save_manifest(root,m,previous_hash=first)
                _archive_current_manifest(root)
                report=audit_manifest_chain(root)
                self.assertEqual(report['status'],'PASS' if anchor is None else 'PARTIAL')
                self.assertTrue(report['verified_from_anchor'])
                parent=digest(root/'cohort_manifest.json')
                m['segments'][0]['ticks_sha256']='rewritten'
                _save_manifest(root,m,previous_hash=parent)
                _archive_current_manifest(root)
                self.assertEqual(audit_manifest_chain(root)['reason'],'ARCHIVED_SEGMENTS_REWRITTEN_OR_REMOVED')

    def test_ledger_path_escape_is_rejected_without_reading_outside(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            _save_manifest(root,_new_manifest(ROOT/'configs/future_validation_cohort_manifest.template.json'),previous_hash=None)
            history=root/'manifest_history';history.mkdir()
            (history/'chain.jsonl').write_text('{"sha256":"'+'a'*64+'","snapshot":"../../outside.json"}\n')
            self.assertEqual(audit_manifest_chain(root)['reason'],'NON_CANONICAL_SNAPSHOT_PATH')

    def test_immutable_identity_change_fails_even_with_valid_hash_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            m=_new_manifest(ROOT/'configs/future_validation_cohort_manifest.template.json')
            _save_manifest(root,m,previous_hash=None);_archive_current_manifest(root)
            parent=digest(root/'cohort_manifest.json')
            m['symbol']='OTHER'
            _save_manifest(root,m,previous_hash=parent);_archive_current_manifest(root)
            self.assertEqual(audit_manifest_chain(root)['reason'],'IMMUTABLE_IDENTITY_CHANGED:symbol')
