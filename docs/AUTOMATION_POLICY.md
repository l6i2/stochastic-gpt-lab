# Automation and remediation policy

Every run records a run ID, UTC start/end, git SHA, stage, status, blocker, checks, and artifact paths under `outputs/logs/`. Checkpoint state is written under `outputs/checkpoints/`. Logs must not contain account credentials, personal paths, or broker account identifiers.

Limitations are classified as `ENVIRONMENT`, `MT5_UI`, `MQL5_COMPILE`, `DATA_COVERAGE`, `DATA_QUALITY`, `PYTHON_DEPENDENCY`, `PERFORMANCE`, `MEMORY`, `STORAGE`, `TEST_FAILURE`, `LEAKAGE_RISK`, `SECURITY_GATE`, or `FINAL_TEST_GATE`. A remediation may be automated only when it is bounded, reversible, and preserves all gates. Retry the same method at most twice; record each attempt.

The remediation helper records issues and provides safe diagnostics. It does not delete data, modify account configuration, turn on LIVE/DEMO execution, relax causal checks, change the Stochastic strategy, or unlock FINAL_TEST. Unknown split IDs and incomplete or unsafe exports fail closed. MT5 UI actions are not retried indefinitely; after two failed methods the pipeline records the exact manual action needed.

`python/pipeline.py resume` resumes only a previously recorded, safe, non-FINAL_TEST stage with its required inputs still present. It never launches FINAL_TEST, demo execution, or live execution. An operator must explicitly start a separate approved operation for any future gated stage.
