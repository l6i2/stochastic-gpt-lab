from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "controller/mql5/SessionCalendarProbe.mq5"


class SessionCalendarProbeTests(unittest.TestCase):
    def test_probe_is_read_only_and_reports_both_session_types(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('const string symbol = "US30Cash";', source)
        self.assertIn("SymbolInfoSessionQuote", source)
        self.assertIn("SymbolInfoSessionTrade", source)
        self.assertIn("TimeTradeServer()", source)
        self.assertIn("TimeGMT()", source)
        self.assertNotRegex(source, re.compile(r"\b(OrderSend|OrderSendAsync|CTrade|PositionOpen)\b", re.I))
        self.assertNotRegex(source, re.compile(r"\b(FileOpen|FileWrite|WebRequest|SocketCreate)\b", re.I))
        self.assertIn('"XM_SESSION_PROBE|END"', source)


if __name__ == "__main__":
    unittest.main()
