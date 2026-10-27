> HISTORICAL SNAPSHOT: preserved evidence, not current operational authority. Current status: [PROJECT_STATUS.md](PROJECT_STATUS.md); Cloud audit: [CLOUD_PREPARATION_AUDIT.md](CLOUD_PREPARATION_AUDIT.md).

# XM `US30Cash` session calendar status

## Authoritative operational checkpoint — 2026-10-23

[Current addendum and evidence](PROSPECTIVE_OPERATIONAL_ADDENDUM_20261023.md): `SESSION_CALENDAR=PASS_WITH_RUNTIME_GUARD` for operational containment; historical UTC calendar remains unverified. Guard READY, DST PARTIAL, holidays UNKNOWN. Causal audit FAIL (frozen metadata/native-trigger non-equivalence), manifest chain PARTIAL, drift NOT_READY. Collector active/HEALTHY, cohort NOT_MATURE, evaluator READY_BUT_GATED. DEMO executor and shadow READY_BUT_DISABLED; no orders. FINAL_TEST LOCKED; DEMO DISABLED; LIVE_TRADING=false. Full suite: 190 tests, 9 native skips. NEXT_STATE=HARD_BLOCKER.

All operational snapshots below are historical and superseded by the linked addendum; sealed scientific protocols remain unchanged.



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
