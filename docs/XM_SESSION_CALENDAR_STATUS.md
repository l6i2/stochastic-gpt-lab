# XM `US30Cash` session calendar status

**Calendar status: UNVERIFIED; maturity fails closed.**

XM's official help page says MT4/MT5 server clocks are GMT+2 in winter and
GMT+3 in summer, and that the terminal displays EU time. XM's index page says
instrument hours are available after logging in. This verifies the broker's
stated seasonal offsets, but does not specify the active account server's
exact DST switch dates, `US30Cash` weekly quote sessions, or holiday and
early-close exceptions.

The public XM holiday PDFs found during review are dated historical schedules,
so they are not used to validate the 2026 capture. The local weekly schedule
must come from the active terminal's `SymbolInfoSessionQuote` (for expected
bars) and `SymbolInfoSessionTrade` (for execution-session cross-check), then be
converted to UTC using confirmed server offsets. Holiday overrides need a
current authoritative XM schedule. Observed cohort bars must never be used to
infer when the market was expected to be open.

`controller/mql5/SessionCalendarProbe.mq5` is a read-only one-shot script. It
prints only the account server name, current server/UTC clock difference, and
weekly quote/trade session times for `US30Cash`; it does not write files or
invoke any trading interface. Compile it into the active terminal's `MQL5\Scripts`
tree, then double-click `Scripts > ResearchDiagnostics > SessionCalendarProbe`
in Navigator. The terminal should print records prefixed
`XM_SESSION_PROBE|START`, `|CLOCK`, `|QUOTE`, `|TRADE`, and `|END` in Experts or
Journal. This confirms weekly schedule data only. It does not supply holidays.

Sources (checked 2026-10-22):

- [XM terminal time zone FAQ](https://www.xm.com/help-center/trading-platforms/faq-can-i-change-the-time-zone-on-my-trading-terminal)
- [XM equity indices trading hours](https://www.xm.com/equity-indices)
- [MQL5 `SymbolInfoSessionQuote`](https://www.mql5.com/en/docs/marketinformation/symbolinfosessionquote)
- [MQL5 `SymbolInfoSessionTrade`](https://www.mql5.com/en/docs/marketinformation/symbolinfosessiontrade)
- [MQL5 `TimeTradeServer`](https://www.mql5.com/en/docs/dateandtime/timetradeserver)

`configs/xm_us30cash_sessions_utc.json` records the evidence and stays
`verified=false` until both weekly sessions and holiday exceptions are
authoritatively established and hash-pinned.
