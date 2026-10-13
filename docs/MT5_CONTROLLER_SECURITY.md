# Controller security

There is no DEMO or LIVE order executor. LIVE_TRADING remains false.
Account information is queried only from the already running, verified terminal;
only a masked login and account mode are returned. No password files are read.
The controller never calls login, symbol_select, order_send, or changes accounts.
Cold starts reuse only verified executable/data paths and source hashes, not
account database contents. The native terminal may reconnect its existing saved
account; controller presets contain no login, password, server override, or token.
AllowLiveTrading=0 and AllowDllImport=0 are explicit in launch configurations.
Network log messages that the account permits trading do not enable an executor.
Account IDs in copied logs are redacted, including the terminal's quoted-ID form.
Lines mentioning passwords or authorization material are omitted entirely.

The synthetic causal script uses only generated January 2024 prices. Market-data
calls are adapted before including the exact production source. It never invokes
the EA's initialization handler, never enables an account executor, and never
queries historical broker data for its fixture. Script return code is explicitly
zero on completion, following the official int OnStart contract.

The split manifest is metadata and is permitted to read. Protected FINAL_TEST
datasets must never be opened. Date requests reaching the protected boundary fail
closed with FINAL_TEST_GATE_BLOCKED; no override is provided. Unknown coverage or
missing manifests must block execution.

Existing local modifications belong to the user and are excluded from controller
commits. No resets or branch changes are performed in the original checkout.
