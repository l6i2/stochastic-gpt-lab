from datetime import datetime, timezone
import unittest

from python.tick_quality_gate import (
    BLOCK_RUNS,
    event_server_time_msc,
    expanded_server_day_windows,
    overlaps,
)


class TickQualityGateTests(unittest.TestCase):
    def test_two_day_halo_covers_whole_server_day_and_neighbors(self):
        windows = expanded_server_day_windows(("2024-01-02",))
        start, end = windows[0]
        self.assertEqual(datetime.fromtimestamp(start / 1000, timezone.utc).isoformat(),
                         "2023-12-31T00:00:00+00:00")
        self.assertEqual(datetime.fromtimestamp(end / 1000, timezone.utc).isoformat(),
                         "2024-01-05T00:00:00+00:00")
        self.assertTrue(overlaps(start, start, windows))
        self.assertFalse(overlaps(end, end, windows))

    def test_warning_day_windows_merge(self):
        windows = expanded_server_day_windows(("2024-01-02", "2024-01-03", "2024-01-08", "2024-07-19"))
        self.assertEqual(len(windows), 2)
        self.assertTrue(overlaps(windows[0][0], windows[0][0], windows))

    def test_server_wall_time_is_used_for_warning_date_comparison(self):
        value = event_server_time_msc({
            "server_time": "2024.01.02 01:35:00", "signal_time_msc": "1704159299999"
        })
        self.assertEqual(datetime.fromtimestamp(value / 1000, timezone.utc).isoformat(),
                         "2024-01-02T01:35:00+00:00")

    def test_quality_decision_is_outcome_blind_and_pinned_to_accepted_runs(self):
        self.assertEqual(BLOCK_RUNS["2023"][0], "r20261016T155454_92027a5b")
        self.assertTrue(BLOCK_RUNS["2023"][1])
        self.assertFalse(BLOCK_RUNS["2024"][1])
        self.assertEqual(BLOCK_RUNS["2024"][2],
                         ("2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05",
                          "2024-01-08", "2024-07-19"))


if __name__ == "__main__":
    unittest.main()
