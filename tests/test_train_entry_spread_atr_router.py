from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from train_entry_spread_atr_router import (
    QUOTE_CHUNK_SIZE, _lower_bound, _price_block_extrema, _regime, _replay_entry_latency,
    _prefix_quotes, _select_policy,
)
from validate_bar_path import QUOTE_DTYPE


class TrainEntrySpreadAtrRouterTests(unittest.TestCase):
    def test_low_memory_lower_bound_matches_numpy_for_strided_quote_fields(self):
        tape = np.array([
            (1000, 1.0, 2.0, 0), (1000, 1.1, 2.1, 0),
            (1200, 1.2, 2.2, 1), (1400, 1.3, 2.3, 1),
        ], dtype=QUOTE_DTYPE)
        for field in ("time_msc", "bar_index"):
            values = tape[field]
            for target in (-1, 0, 1000, 1001, 1200, 1400, 1401):
                self.assertEqual(_lower_bound(values, target),
                                 int(np.searchsorted(values, target, side="left")))

    def test_low_memory_prefix_matches_normal_prefix_on_quote_fixture(self):
        tape = np.array([
            (1000, 1.0, 2.0, 0), (1000, 1.1, 2.1, 0),
            (1200, 1.2, 2.2, 1), (1400, 1.3, 2.3, 1),
        ], dtype=QUOTE_DTYPE)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quotes.bin"
            tape.tofile(path)
            for boundary in (1001, 1200, 1300, 1400, 1401):
                low = _prefix_quotes(path, boundary, low_memory=True)
                normal = _prefix_quotes(path, boundary, low_memory=False)
                try:
                    np.testing.assert_array_equal(low, normal)
                finally:
                    low._mmap.close()
                    normal._mmap.close()

    def test_regime_and_missing_feature_policy_are_deterministic(self):
        self.assertEqual(_regime(float("nan"), 1.0, 2.0), "MISSING")
        self.assertEqual(_regime(1.0, 1.0, 2.0), "LOW")
        self.assertEqual(_regime(1.5, 1.0, 2.0), "MID")
        self.assertEqual(_regime(2.1, 1.0, 2.0), "HIGH")

    def test_router_uses_only_training_cell_means_and_minimum_support(self):
        rows = pd.DataFrame({
            "signal_id": [f"s{i}" for i in range(300)],
            "direction": [1] * 300,
            "spread_to_atr": np.linspace(0.0, 3.0, 300),
        })
        outcomes = {
            f"s{i}": {"side": "BUY", "pnl": {250: {
                "FOLLOW": 10.0 if 100 <= i < 200 else 0.0,
                "INVERT": 20.0 if 100 <= i < 200 else 0.0,
            }}}
            for i in range(300)
        }
        policy = _select_policy(rows, outcomes, 1/3, 2/3)
        self.assertEqual(policy["mode"][("BUY", "MID")], "INVERT")
        self.assertEqual(policy["mode"][("BUY", "LOW")], "FOLLOW")
        self.assertEqual(policy["mode"][("SELL", "HIGH")], "FOLLOW")

    def test_latency_fill_is_strictly_after_arrival_and_reprices_entry(self):
        tape = np.array([
            (1000, 99.0, 100.0, 0),
            (1100, 100.0, 101.0, 0),
            (1500, 101.0, 102.0, 0),
            (1600, 342.0, 343.0, 0),
        ], dtype=QUOTE_DTYPE)
        record = {"entry": 0, "entry_time": 1000, "side": "BUY"}
        bar_starts = {0: 0}
        extrema = _price_block_extrema(tape["bid"], tape["ask"], QUOTE_CHUNK_SIZE)
        out0 = _replay_entry_latency(tape, extrema, record, 0, 5000)
        out500 = _replay_entry_latency(tape, extrema, record, 500, 5000)
        self.assertEqual(out0, _replay_entry_latency(
            tape, extrema, record, 0, 5000, low_memory=False))
        self.assertEqual(out500, _replay_entry_latency(
            tape, extrema, record, 500, 5000, low_memory=False))
        self.assertEqual(out0["entry_index"], 1)
        self.assertEqual(out0["entry_time"], 1100)
        self.assertEqual(out500["entry_index"], 2)
        self.assertEqual(out500["entry_time"], 1500)
        self.assertEqual(out0["reason"], "TP")
        self.assertEqual(out500["reason"], "TP")
        self.assertEqual(out0["pnl"], 240.0)
        self.assertEqual(out500["pnl"], 240.0)

    def test_boundary_without_post_arrival_quote_fails_closed(self):
        tape = np.array([(1000, 99.0, 100.0, 0)], dtype=QUOTE_DTYPE)
        record = {"entry": 0, "entry_time": 1000, "side": "BUY"}
        extrema = _price_block_extrema(tape["bid"], tape["ask"], QUOTE_CHUNK_SIZE)
        out = _replay_entry_latency(tape, extrema, record, 0, 1001)
        self.assertFalse(out["complete"])
        self.assertEqual(out["reason"], "TRAIN_BOUNDARY")

    def test_compiled_replay_preserves_sl_tp_and_time_exit_semantics(self):
        record = {"entry": 0, "entry_time": 1000, "side": "BUY"}
        sl_tape = np.array([
            (1000, 100.0, 101.0, 0), (1100, 100.0, 101.0, 0),
            (1200, -80.0, -79.0, 0),
        ], dtype=QUOTE_DTYPE)
        sl = _replay_entry_latency(
            sl_tape, _price_block_extrema(sl_tape["bid"], sl_tape["ask"], QUOTE_CHUNK_SIZE),
            record, 0, 5000)
        self.assertEqual(sl, _replay_entry_latency(
            sl_tape, _price_block_extrema(sl_tape["bid"], sl_tape["ask"], QUOTE_CHUNK_SIZE),
            record, 0, 5000, low_memory=False))
        self.assertEqual((sl["reason"], sl["pnl"]), ("SL", -181.0))

        tp_tape = np.array([
            (1000, 100.0, 101.0, 0), (1100, 100.0, 101.0, 0),
            (1200, 341.0, 342.0, 0),
        ], dtype=QUOTE_DTYPE)
        tp = _replay_entry_latency(
            tp_tape, _price_block_extrema(tp_tape["bid"], tp_tape["ask"], QUOTE_CHUNK_SIZE),
            record, 0, 5000)
        self.assertEqual(tp, _replay_entry_latency(
            tp_tape, _price_block_extrema(tp_tape["bid"], tp_tape["ask"], QUOTE_CHUNK_SIZE),
            record, 0, 5000, low_memory=False))
        self.assertEqual((tp["reason"], tp["pnl"]), ("TP", 240.0))

        timeout_tape = np.array([
            (1000 + i, 100.0, 101.0, i) for i in range(102)
        ], dtype=QUOTE_DTYPE)
        timeout = _replay_entry_latency(
            timeout_tape,
            _price_block_extrema(timeout_tape["bid"], timeout_tape["ask"], QUOTE_CHUNK_SIZE),
            record, 0, 5000)
        self.assertEqual(timeout, _replay_entry_latency(
            timeout_tape,
            _price_block_extrema(timeout_tape["bid"], timeout_tape["ask"], QUOTE_CHUNK_SIZE),
            record, 0, 5000, low_memory=False))
        self.assertEqual(timeout["reason"], "TIME_EXIT")
        self.assertEqual(timeout["exit_time"], 1101)

    def test_index_skips_safe_quote_blocks_and_finds_first_later_barrier(self):
        rows = [(i, 100.0, 101.0, 0) for i in range(9000)]
        rows[8500] = (8500, 341.0, 342.0, 0)
        tape = np.array(rows, dtype=QUOTE_DTYPE)
        extrema = _price_block_extrema(tape["bid"], tape["ask"], QUOTE_CHUNK_SIZE)
        out = _replay_entry_latency(
            tape, extrema, {"entry": 0, "entry_time": 0, "side": "BUY"}, 0, 10000)
        self.assertEqual((out["reason"], out["exit_time"], out["pnl"]), ("TP", 8500, 240.0))


if __name__ == "__main__":
    unittest.main()
