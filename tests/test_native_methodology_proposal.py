import unittest
from proposals.native_methodology_v1.availability import (
    Position, check_availability, check_policy_fill, training_readiness)


class NativeMethodologyProposalTests(unittest.TestCase):
    def args(self):
        return dict(bar_open_ms=0, feature_max_ms=299999,
                    arrival_ms=300100, quote_ms=300100,
                    feature_ready=Position(10, 1), decision=Position(10, 2),
                    domain="XM_NATIVE_ORDER")

    def test_next_bar_callback_is_not_nominal_cutoff(self):
        result = check_availability(**self.args())
        self.assertEqual(result["native_order"], "PASS")
        self.assertFalse(result["cutoff_is_availability_time"])
        self.assertEqual(result["physical_availability"], "NOT_CERTIFIED")

    def test_forming_bar_and_early_arrival_rejected(self):
        for change in ({"feature_max_ms": 300000}, {"arrival_ms": 299999}):
            with self.assertRaises(ValueError):
                check_availability(**(self.args() | change))

    def test_equal_timestamp_does_not_hide_later_feature(self):
        with self.assertRaisesRegex(ValueError, "NOT_YET_AVAILABLE"):
            check_availability(**(self.args() | {"feature_ready": Position(11, 1)}))

    def test_wrong_domain_future_quote_and_stages_rejected(self):
        for change in ({"domain": "UTC"}, {"quote_ms": 300101},
                       {"feature_ready": Position(10, 2)},
                       {"decision": Position(10, 0)}):
            with self.assertRaises(ValueError):
                check_availability(**(self.args() | change))

    def test_negative_fractional_and_unaligned_positions_rejected(self):
        for change in ({"bar_open_ms": 1}, {"feature_max_ms": -1},
                       {"arrival_ms": 300100.5}, {"decision": Position(-1, 2)}):
            with self.assertRaises(ValueError):
                check_availability(**(self.args() | change))

    def test_policy_requires_later_sequence_and_fixed_latency(self):
        args = dict(decision_index=10, decision_ms=300100,
                    fill_index=11, fill_ms=300350, latency_ms=250)
        check_policy_fill(**args)
        for change in ({"fill_index": 10}, {"fill_ms": 300349},
                       {"latency_ms": 249}):
            with self.assertRaises(ValueError):
                check_policy_fill(**(args | change))
        check_policy_fill(**(args | {"latency_ms": 0, "fill_ms": 300100}))

    def test_proposal_cannot_authorize_training(self):
        self.assertFalse(training_readiness()["training_authorized"])
        with self.assertRaises(TypeError):
            training_readiness(approved=True)


if __name__ == "__main__":
    unittest.main()
