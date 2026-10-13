# Project status

## CHECKPOINT_A — baseline audit

**Status:** complete on branch `research/full-pipeline`; no project code was changed before the audit. The public manifest is `outputs/baseline_smoke_test_manifest.json`.

- Repository HEAD at audit: `d8f639578a409acd941ec35b6d5349a66d7007c4`.
- MT5: XM Global SC MT5 6257; the terminal title showed a DEMO account. Active chart was US30Cash H1 at audit time; the completed Strategy Tester run used US30Cash M5.
- EA: all three required source files were together in the active terminal's `MQL5/Experts/StochasticResearch/`. `LIVE_TRADING=false`, the `.ex5` exists, and the latest MetaEditor log records 0 errors and 0 warnings.
- Smoke test: 2026-10-01 through 2026-10-11 server time, 888,125 ticks and 1,932 M5 bars; real-tick attestation true; 200 signals and 200 dataset rows; schema 1.1; no abort or fatal error; 95 BUY and 105 SELL. Each signal has FOLLOW and INVERT virtual outcomes.
- Raw CSV and audit remain on the local MT5 tester agent; only small metadata and hashes are published. No real trading occurred.

## Python environment blocker

- The machine has Python 3.8 x64 and Python 2.7 x86, while this repo requires Python 3.10+. No project `.venv` exists.
- Python 3.8 `compileall` passes as syntax-only validation. `python -m unittest discover -s tests -v` fails during import because NumPy and pandas are missing.
- The official signed Python 3.12.10 x64 installer was downloaded and Authenticode-verified. Two quiet user-scope install attempts hung without creating a runtime and were cancelled. No global Python configuration was changed.
- `g++` is unavailable.

**Gate:** historical expansion, dataset freezing, analysis, validation and ML remain paused until a supported Python runtime/dependencies are available and the existing tests pass. Do not open FINAL_TEST. Do not enable Demo execution. Keep `LIVE_TRADING=false`.
