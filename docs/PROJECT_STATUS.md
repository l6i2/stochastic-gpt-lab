# Estado actual — preparación Cloud 2026-10-27

Este documento sustituye los checkpoints operativos anteriores. La evidencia
histórica se conserva en [el archivo](archive/pre_cloud_20261027/PROJECT_STATUS.md).
El estado machine-readable está en [CLOUD_HANDOFF.json](../outputs/status/CLOUD_HANDOFF.json).
Auditoría y límites: [CLOUD_PREPARATION_AUDIT.md](CLOUD_PREPARATION_AUDIT.md).

- Rama: `research/full-pipeline`.
- `HYPOTHESES_TESTED_TOTAL=17`, `HYPOTHESES_SURVIVED=0`, `BEST_CANDIDATE=NONE`.
- `DISCOVERY_VALIDATION=BLOCKED`, `FINAL_TEST=LOCKED`, `DEMO=DISABLED`, `LIVE_TRADING=false`.
- `CLOCK_ATTESTATION=READY_FOR_LOCAL_ATTESTATION`, `NATIVE_TO_UTC_MAPPING=READY_FOR_LOCAL_ATTESTATION`.
- `CAUSAL_AUDIT=READY_FOR_LOCAL_FINALIZATION`: herramientas listas; aceptación real pendiente.
- `MAIN_K_PARITY=PASS`: evidencia nativa publicada previa, sin recompilar estrategia ni regenerar datos.
- `SESSION_CALENDAR=PASS_WITH_RUNTIME_GUARD`: vacaciones desconocidas y snapshot expirado bloquean.
- `FUTURE_EVALUATOR=READY_BUT_GATED`, `DRIFT_MONITOR=READY` (tooling; baseline real no ajustado).
- `SHADOW_MODE=READY_BUT_DISABLED`, `SHADOW_ORDER_COUNT=0`.
- `DEMO_EXECUTOR=READY_BUT_DISABLED_FULL`: mocks persistentes, sin adaptador de órdenes.
- `FUTURE_COLLECTION_ACTIVE=YES` es el último estado local conocido, no una observación de Task Scheduler desde Cloud.

Comando local: `powershell -ExecutionPolicy Bypass -File tools/local_finalize.ps1`.
Acciones humanas: [LOCAL_PC_FINAL_STEPS.md](LOCAL_PC_FINAL_STEPS.md).
`READY` describe preparación de herramientas; no equivale a PASS operativo ni a
maturity, autorización, corrección del reloj o certificación del broker.

Historial específico: [snapshot anterior](archive/pre_cloud_20261027/PROJECT_STATUS.md).
