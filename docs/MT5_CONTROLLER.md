# Local MT5 controller

Run from this worktree with `.venv\Scripts\python.exe -m controller.controller status`.
Dependencies: psutil, MetaTrader5, and the project's research requirements.
The system Python 3.8 does not have the project dependencies; use the worktree venv.

Discovery pairs the active process executable with origin.txt and verifies the exact
Data Folder through the read-only MetaTrader5 terminal API. Multiple terminals,
ambiguous origins, portable launch mode, and unknown account modes fail closed.

Tester CLI reference: https://www.metatrader5.com/en/terminal/help/start_advanced/start
The documented real-tick model is 4. Cold-start CLI testing is verified by the
full January 2024 TRAIN smoke run, tester/agent completion logs, automatic shutdown,
fresh nonce artifacts and both split-aware validators. No GUI interaction is needed.

Commands: status, compile --ea StochasticIntratradeResearchEA,
backtest --from YYYY-MM-DD --to YYYY-MM-DD [--timeout SECONDS],
validate --run-id ID, logs --run-id ID, history --mode intratrade, resume.
`resume --run-id ID` reattaches observation of a previously launched cold-start run.
Timeout never kills a process or proves that an in-progress test failed internally.

The runner saves a unique preset with nonce-prefixed output filenames. These differ
from the EA defaults to make stale cross-run collection impossible. Report paths
are relative to the verified Data Folder; forward testing and optimization are off.
Calendar ranges are inclusive. MT5 ToDate is exclusive midnight; e.g. January 31
maps to ToDate=2024.02.01. The safety gate checks the entire requested inclusive
range before generating this configuration. The final allowed historical date is
2026-03-19 and the exclusive tester end is 2026.03.20 00:00.

The terminal must be closed before backtest/history. Cold launch uses the last
verified active environment and compiler record, verifies origin.txt, source,
include and binary hashes, then checks the actual Data Folder and DEMO account
evidence in new terminal logs. It never logs in or copies credential files.
ShutdownTerminal=1 permits sequential runs without terminating processes.
Preexisting warm-instance launches that silently exited were rejected.

Install controller dependencies with `.venv\Scripts\python.exe -m pip install -r
configs/controller_requirements.txt`. Use the existing worktree venv; do not replace
the user's Python installation.

Snapshot causal proof: `controller.causal_probe.run_probe()` compiles a separate
script including the unchanged, exact deployed EA. Only market-data API adapters
and event entry names are substituted. Production OnTick, snapshot, profile,
Heikin-Ashi, virtual execution, and target code execute in MT5. Two synthetic
streams differ only after the cutoff. Inputs, all emitted feature columns, targets,
compiler logs and hashes are retained. The regression covers one deterministic
fixture; it is not a mathematical proof for every possible market path. Platform
indicator inputs are supplied by a deterministic causal adapter.

The current proof compares 156 snapshots across 257 columns, with 436 future
ticks and 109 future bars changed; every compared snapshot is identical and all
156 corresponding future target rows change. Validation binds this proof to the
exact producer/include hashes and rejects stale proof artifacts.

Model 4 can still fall back to generated ticks when broker ticks conflict with
minute bars. Preserve the tick-quality diagnostics; a controller PASS establishes
execution and dataset contracts, not perfect raw tick coverage or profitability.
The complete January smoke reports 183 discarded minutes out of 30,095 minute bars.
Historical acceptance remains pending until every checkpoint block validates.
