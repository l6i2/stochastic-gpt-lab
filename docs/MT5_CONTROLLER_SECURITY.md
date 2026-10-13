# Controller security

There is no DEMO or LIVE order executor. LIVE_TRADING remains false.
Account information is queried only from the already running, verified terminal;
only a masked login and account mode are returned. No password files are read.
The controller never calls login, symbol_select, order_send, or changes accounts.

The split manifest is metadata and is permitted to read. Protected FINAL_TEST
datasets must never be opened. Date requests reaching the protected boundary fail
closed with FINAL_TEST_GATE_BLOCKED; no override is provided. Unknown coverage or
missing manifests must block execution.

Existing local modifications belong to the user and are excluded from controller
commits. No resets or branch changes are performed in the original checkout.
