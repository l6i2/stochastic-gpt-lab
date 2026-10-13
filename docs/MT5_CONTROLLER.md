# Local MT5 controller

Run from this worktree with `.venv\Scripts\python.exe -m controller.controller status`.
Dependencies: psutil, MetaTrader5, and the project's research requirements.
The system Python 3.8 does not have the project dependencies; use the worktree venv.

Discovery pairs the active process executable with origin.txt and verifies the exact
Data Folder through the read-only MetaTrader5 terminal API. Multiple terminals,
ambiguous origins, portable launch mode, and unknown account modes fail closed.

Tester CLI reference: https://www.metatrader5.com/en/terminal/help/start_advanced/start
The documented real-tick model is 4. Tester automation remains unverified until a
bounded TRAIN run and split-aware validators pass.

Commands: status, compile --ea StochasticIntratradeResearchEA,
backtest --from YYYY-MM-DD --to YYYY-MM-DD [--timeout SECONDS],
validate --run-id ID, logs --run-id ID, history --mode intratrade, resume.
`resume --run-id ID` checks a previously launched nonce after a manual clean start.
Timeout never kills a process or proves that an in-progress test failed internally.

The runner saves a unique preset with nonce-prefixed output filenames. These differ
from the EA defaults to make stale cross-run collection impossible. Report paths
are relative to the verified Data Folder; forward testing and optimization are off.
No phase beyond C2 is currently accepted: see MT5_CONTROLLER_STATUS.md.
