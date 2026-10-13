from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def function_source(source: str, name: str) -> str:
    match = re.search(rf"(?m)^[^\n]*\b{re.escape(name)}\s*\([^;]*?\)\s*\{{", source)
    if not match:
        raise AssertionError(f"Function not found: {name}")
    start = source.find("{", match.start())
    depth = 0
    for index in range(start, len(source)):
        depth += source[index] == "{"
        depth -= source[index] == "}"
        if depth == 0:
            return source[match.start():index + 1]
    raise AssertionError(f"Unbalanced body: {name}")


class IntratradeInstrumentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = (ROOT / "mt5/StochasticResearchEA.mq5").read_text(encoding="utf-8")
        cls.instrumented = (ROOT / "mt5/StochasticIntratradeResearchEA.mq5").read_text(encoding="utf-8")
        cls.core = (ROOT / "mt5/ResearchCore.mqh").read_text(encoding="utf-8")

    def test_strategy_execution_core_is_byte_identical(self):
        for name in ("TickTrade", "BarTrade", "TradeCSV", "TradeHeader"):
            self.assertEqual(function_source(self.base, name), function_source(self.instrumented, name), name)
        signal = function_source(self.core, "ResearchSignal")
        self.assertIn("if(previous<=20.0&&current>20.0)return 1;", signal)
        self.assertIn("if(previous>=80.0&&current<80.0)return -1;", signal)

    def test_strategy_constants_and_safety_gates_are_preserved(self):
        for token in (
            "input bool LIVE_TRADING=false;", "K_PERIOD=5,D_PERIOD=3,SLOWING=3,TIME_EXIT_BARS=100",
            "OVERSOLD=20.0,OVERBOUGHT=80.0,TP_DISTANCE=240.0,SL_DISTANCE=180.0",
            "int side=ResearchSignal(previous,current);if(side==0)return;",
            "OpenTrade(events[index].follow,side,tick,id,cutoff,\"FOLLOW\")",
            "OpenTrade(events[index].invert,ResearchInvert(side),tick,id,cutoff,\"INVERT\")",
            "MQLInfoInteger(MQL_TESTER)", "MQLInfoInteger(MQL_OPTIMIZATION)",
        ):
            self.assertIn(token, self.instrumented)
        for forbidden in ("OrderSend", "OrderSendAsync", "CTrade", "PositionOpen"):
            self.assertNotIn(forbidden.lower(), self.instrumented.lower())

    def test_snapshot_schedule_and_future_labels_are_separate(self):
        self.assertIn("snapshot_offsets[9]={1,2,3,5,10,15,20,30,50}", self.instrumented)
        self.assertIn('SnapshotOutputFile="intratrade_snapshots.csv"', self.instrumented)
        self.assertIn('TargetOutputFile="intratrade_snapshot_targets.csv"', self.instrumented)
        self.assertIn("feature_max_time_msc", self.instrumented)
        self.assertIn("WriteSnapshotTargets", self.instrumented)
        self.assertIn("snapshot MFE >= 60", self.instrumented)


if __name__ == "__main__":
    unittest.main()
