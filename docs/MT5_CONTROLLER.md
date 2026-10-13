# Local MT5 controller

Run from this worktree with `.venv\Scripts\python.exe -m controller.controller status`.
Dependencies: psutil, MetaTrader5, and the project's research requirements.
The system Python 3.8 does not have the project dependencies; use the worktree venv.

Discovery pairs the active process executable with origin.txt and verifies the exact
Data Folder through the read-only MetaTrader5 terminal API. Multiple terminals,
ambiguous origins, custom launch modes, and unknown account modes fail closed.

Tester CLI reference: https://www.metatrader5.com/en/terminal/help/start_advanced/start
The documented real-tick model is 4. Tester automation remains unverified until a
bounded TRAIN run and split-aware validators pass.
