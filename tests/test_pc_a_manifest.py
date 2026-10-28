"""Migration manifests must retain baseline coverage and detect source tampering."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from local_finalize import verify_source_manifest


class MigrationManifestTests(unittest.TestCase):
    def test_rejects_omission_parent_change_and_tampered_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.py'
            source.write_bytes(b'original')
            baseline = root / 'outputs/status/CLOUD_SOURCE_HASHES.json'
            baseline.parent.mkdir(parents=True)
            files = {'source.py': hashlib.sha256(source.read_bytes()).hexdigest()}
            baseline.write_text(json.dumps({'files': files}))
            parent = hashlib.sha256(baseline.read_bytes()).hexdigest()
            manifest = root / 'migration.json'
            manifest.write_text(json.dumps({'files': files, 'parent_manifest_sha256': parent}))
            verify_source_manifest(manifest, root)
            source.write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'HASH_MISMATCH'):
                verify_source_manifest(manifest, root)
            manifest.write_text(json.dumps({'files': {}, 'parent_manifest_sha256': parent}))
            with self.assertRaisesRegex(ValueError, 'OMITS_BASELINE'):
                verify_source_manifest(manifest, root)
            manifest.write_text(json.dumps({'files': files, 'parent_manifest_sha256': '0' * 64}))
            with self.assertRaisesRegex(ValueError, 'PARENT_MISMATCH'):
                verify_source_manifest(manifest, root)
