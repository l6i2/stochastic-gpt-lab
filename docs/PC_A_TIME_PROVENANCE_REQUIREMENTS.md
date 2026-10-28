# Independent event-time evidence still required

No files from the old PC are required for this investigation. The current
XMGlobalSC-MT5 5 / US30Cash feed is being preserved in a separate native archive.

The sealed independent Windows clock evidence has 50 paired frames / 150 rows.
All observed TimeTradeServer minus TimeGMT values are +7200 seconds. All 150 raw
quote timestamps exceed their paired receipt upper bound when interpreted as UTC.
Subtracting 7200 seconds as a diagnostic candidate removes those violations in
this captured interval. This is an observation, not authorization to install a
mapping or alter original data. It does not establish unique event-time UTC,
replay/cache age, January 2024 offsets or DST transition rules.

MetaQuotes Python documentation says received bar/tick times are UTC. That generic
statement conflicts with the observed feed labels. An independent authoritative
source must resolve this exact server/symbol case. General broker GMT+2/GMT+3
advertising, chart appearance, another broker's quotes and local receipt UTC do
not establish exact event timestamps or historical transitions.

The minimal useful broker evidence would specify, for this exact server and
symbol: (1) the encoding/semantics of tick.time, tick.time_msc and M5 opening time;
(2) an independently UTC-stamped event or server log that identifies the same
tick as a preserved native record; (3) the applicable offset interval and exact
historical/DST boundaries; (4) cache/replay and late-tick behavior. Preserve the
original source, date, scope and SHA-256. No credentials or account identifiers
are necessary. No message has been sent to the broker on the user's behalf.

Until this exists, authorized mapping segments remain empty and causal acceptance
fails closed. A mapping valid for a demonstrated short interval must not be
extrapolated to historical days or future DST transitions.

References: [MetaQuotes copy_rates_range](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py),
[MetaQuotes CopyTicks](https://www.mql5.com/en/docs/series/copyticks).
