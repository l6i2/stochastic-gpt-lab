import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'python'))
from temporal_evidence_intake import template, inspect_bundle, utc_interval
from train_event_source import assert_train_only_source_path, read_rows_for_ids
spec = importlib.util.spec_from_file_location('prepare_evidence', ROOT / 'tools/prepare_temporal_evidence.py')
prepare = importlib.util.module_from_spec(spec); spec.loader.exec_module(prepare)


class TemporalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'bundle.json'

    def save(self, value):
        self.path.write_text(json.dumps(value))
        return inspect_bundle(self.path)

    def complete(self):
        source = self.root / 'source.txt'; source.write_bytes(b'synthetic test evidence')
        value = template()
        value.update(source_url='https://www.xm.com/example', source_file='source.txt',
                     source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                     independent_authority={'issuer':'synthetic test issuer','authentication_method':'synthetic test method'},
                     event_binding={key:'synthetic' for key in ('native_record_sha256','independent_record_sha256','matching_rule','uniqueness_evidence')},
                     utc_interval={'start':'2026-01-01T00:00:00Z','end_exclusive':'2026-01-01T00:00:01Z'})
        return value

    def test_empty_template_lists_evidence_missing(self):
        result = self.save(template())
        self.assertEqual(result['status'], 'INCOMPLETE')
        self.assertFalse(result['event_mapping_authorized'])

    def test_self_declared_pass_never_authorizes_mapping(self):
        value = self.complete(); value.update(status='PASS', verified=True)
        result = self.save(value)
        self.assertEqual(result['status'], 'STRUCTURALLY_COMPLETE_REVIEW_REQUIRED')
        self.assertFalse(result['semantic_authenticity_verified'])
        self.assertFalse(result['cohort_activation_allowed'])

    def test_wrong_server_hash_and_path_escape_fail(self):
        value = self.complete(); value['server']='OTHER'
        self.assertIn('EXACT_SERVER_SYMBOL_REQUIRED', self.save(value)['missing'])
        value = self.complete(); value['source_sha256']='bad'
        self.assertIn('SOURCE_HASH_MISMATCH_OR_MISSING', self.save(value)['missing'])
        value['source_file']='../outside'
        with self.assertRaisesRegex(ValueError, 'PATH_ESCAPE'): self.save(value)

    def test_bar_and_calendar_evidence_are_distinct(self):
        value = self.complete(); value['evidence_kind']='bar_time'
        self.assertIn('BAR_OPEN_SEMANTICS_REQUIRED_SEPARATE_FROM_TICKS', self.save(value)['missing'])
        value['evidence_kind']='calendar'
        self.assertIn('DATED_SESSIONS_AND_EXCEPTION_COVERAGE_REQUIRED', self.save(value)['missing'])

    def test_naive_reversed_or_non_utc_intervals_rejected(self):
        for value in ({'start':'2026-01-01','end_exclusive':'2026-01-02'},
                      {'start':'2026-01-02T00:00:00Z','end_exclusive':'2026-01-01T00:00:00Z'},
                      {'start':'2026-01-01T00:00:00-05:00','end_exclusive':'2026-01-02T00:00:00-05:00'}):
            with self.assertRaises(ValueError): utc_interval(value)

    def test_quarantine_sources_rejected_before_data_io(self):
        for name in ('pc_a_raw_archive','pc_a_raw_backup','pc_a_data_repair','pc_a_remaining_blockers','pc_a_evidence_backup','pc_a_temporal_intake'):
            with self.subTest(name=name), patch('train_event_source.pd.read_csv') as read:
                with self.assertRaisesRegex(ValueError, 'protected split'):
                    read_rows_for_ids(self.root/name/'ticks.csv', {'frozen-train-id'})
                read.assert_not_called()

    def test_public_fetch_cannot_visit_non_primary_or_credential_url(self):
        for url in ('http://www.xm.com/a','https://localhost/a','https://www.xm.com.evil.test/a','https://user:pass@www.xm.com/a'):
            with self.assertRaises(ValueError): prepare.public_url(url)
        self.assertEqual(prepare.public_url('https://www.mql5.com/en/docs'), 'https://www.mql5.com/en/docs')


if __name__ == '__main__': unittest.main()
