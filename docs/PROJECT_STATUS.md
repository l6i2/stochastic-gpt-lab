# Actualización local — 2026-10-30 (Ecuador)

El diagnóstico nativo automatizado del 2024-01-02 (calendario del servidor XM)
pasó reproducibilidad, quotes/OHLC/volumen y replay virtual MQL5/Python. También
pasaron los cutoffs causales del dominio nativo; esto no certifica UTC ni admite
datos científicos. Collector y NTS siguen activos en cuarentena. 39 pruebas
afectadas PASS. No se cambió estrategia, contratos, entrenamiento ni holdouts.

La [revisión de capacidades y propuesta pendiente](PC_A_NATIVE_TESTER_CAPABILITIES.md)
separa diagnóstico histórico, admisión científica y ejecución UTC. La propuesta
no está aplicada; TRAIN agotado, DISCOVERY_VALIDATION=BLOCKED, FINAL_TEST=LOCKED,
DEMO=DISABLED y LIVE_TRADING=false se conservan.

## Snapshot del handoff Cloud conservado — 2026-10-29

Actualizado sobre `e35b05d461baeee1ee9ab65c4bf1b6f484744f6c`, preservando los
17 commits publicados después del handoff Cloud original. Fuente operativa:
[handoff actual](../outputs/status/CLOUD_HANDOFF.json) y
[pasos locales](LOCAL_PC_FINAL_STEPS.md). Los informes PC A anteriores son snapshots,
no observaciones en vivo desde Cloud.

| Componente | Estado y alcance |
|---|---|
| Clock attestation | PASS_CAPTURE_INTERVAL_ONLY: captura local sellada anterior; no prueba el reloj actual. |
| MAIN_K | PASS nativo retenido; estrategia y datasets intactos. |
| Native/UTC | BLOCKED_EXTERNAL_EVIDENCE_REQUIRED; ningún offset autorizado por observación. |
| Causal audit | FAIL: procedencia temporal/calendario y completitud pendientes. |
| Session calendar | PASS_WITH_RUNTIME_GUARD; observación semanal nativa parcial, UTC/feriados no certificados. |
| Captura prospectiva | Último snapshot STALLED_START_ONLY, cero callbacks tick; no se declara activa. |
| Lanzador | Instalación/compilación y visibilidad Navigator verificadas localmente; script no ejecutado en ese snapshot. |
| Raw quarantine | Último estado local de colección independiente retenido; no verificado en vivo desde Cloud. |
| Future evaluator | READY_BUT_GATED; no candidato, no autorización ni scoring. |
| Drift | READY tooling; sin baseline real ajustado ni comparación de cohorte. |
| Shadow | READY_BUT_DISABLED; SHADOW_ORDER_COUNT=0. |
| DEMO executor | READY_BUT_DISABLED_FULL; mocks, sin órdenes reales. |

17 hipótesis probadas, cero supervivientes, BEST_CANDIDATE=NONE.
DISCOVERY_VALIDATION=BLOCKED; FINAL_TEST=LOCKED; DEMO=DISABLED; LIVE_TRADING=false.

La captura de reloj completada no se repite para continuar. La corrección del
escritor CRLF ya está publicada y compilada localmente; falta recargar únicamente
el observador mediante `Scripts -> ResearchDiagnostics -> PC_A -> StartProspectiveUtcObserver`.
Instalación PASS no equivale a callbacks PASS ni a UTC certificado.

Esta continuación corrige el import Windows del monitor para que sus funciones
puras sean testeables en Cloud, sin habilitar captura Windows en Linux. También
hace que el preflight use el manifest versionado señalado por el handoff; el
manifest Cloud original y los manifests PC A se conservan sin reescribir.

Evidencia: [reloj local](../configs/pc_a_clock_attestation_20261028.json),
[corrección del escritor](PC_A_CALLBACK_WRITE_FIX.md),
[Navigator verificado](PC_A_NAVIGATOR_INSTALL_VERIFIED.md),
[procedencia temporal pendiente](PC_A_TIME_PROVENANCE_REQUIREMENTS.md).
No se leyó raw de cohorte, labels, PnL ni outcomes. No se ejecutó MT5 desde Cloud.
