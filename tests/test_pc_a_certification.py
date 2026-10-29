import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('certifier', Path(__file__).resolve().parents[1] / 'tools/certify_pc_a_data.py')
certifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(certifier)


class CertificationTests(unittest.TestCase):
    def test_certification_capture_is_rejected_before_train_io(self):
        from train_event_source import assert_train_only_source_path
        with self.assertRaises(ValueError):
            assert_train_only_source_path(Path('outputs/pc_a_certification/event.csv'))

    def test_unverified_reference_has_no_projection(self):
        self.assertIsNone(certifier.project({'comparison': {'status': 'UNVERIFIED'}}, 99))

    def test_projection_preserves_width_and_direction(self):
        reference = {'anchor_monotonic_ns': 100, 'comparison': {
            'status': 'REFERENCE_QUORUM', 'utc_lower_ns': 1000, 'utc_upper_ns': 1030}}
        self.assertEqual(certifier.project(reference, 90), [990, 1020])
        self.assertEqual(certifier.project(reference, 150), [1050, 1080])
