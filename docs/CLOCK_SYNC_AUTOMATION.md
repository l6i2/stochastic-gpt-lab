# Preparación de captura simultánea Windows + MT5

Expediente del cliente 2026-10-23. Este checkpoint conserva el bloqueo científico y no modifica el reloj, la estrategia ni datos aceptados.

## Estado previo preservado

El probe `ResearchDiagnostics/attest_20261023_a2/ClockAttestationProbeV2` ya produjo 50 frames / 150 registros y CLOCK_ATTESTATION_END. Se verificaron otra vez source y EX5 contra el build aceptado. **No se compiló, reinstaló ni cambió el probe.**

El ejecutable rechaza sobrescribir sus archivos. Para reutilizarlo con sus inputs existentes, los dos archivos diagnósticos anteriores se archivaron mediante rename dentro de `MQL5/Files/clock_audit_archive/a2_first_completed`. Se verificaron SHA-256, tamaño y mtime antes/después. Los campos temporales del contenido no se tocaron. Hay copias íntegramente idénticas en este expediente. No se archivó, renombró ni tocó ningún dataset de investigación.

## Evidencia Windows directa

Se observaron `GetSystemTimePreciseAsFileTime`, `GetSystemTimeAsFileTime`, Python time/datetime, reloj monotónico/QPC y `w32tm`. Precise y estándar Windows indican la misma fecha atrasada; Python coincide con el estándar. No es una diferencia introducida únicamente por un wrapper Python.

`w32tm /query /source` y `/query /status` devolvieron servicio no iniciado (0x80070426). `w32tm /stripchart /computer:time.windows.com /dataonly /samples:3`, sin cambiar configuración, midió aproximadamente **+207999.8 s**. Coincide con el expediente NTP/TLS anterior. El reloj Windows no está atestado/sincronizado. No se inició servicio, ajustó fecha, cambió timezone o forzó resincronización.

## Automatización probada, en orden

| Vía | Resultado |
|---|---|
| Python watcher | ARMED_NO_EXPIRY: activo y esperando archivos nuevos |
| PowerShell watcher | Bloqueado por la política de ejecución de scripts; no se eludió |
| Task Scheduler temporal, token interactivo limitado | La tarea arrancó; el mismo bloqueo impidió ejecutar el watcher PS. LastTaskResult=1. Tarea retirada y ausencia verificada |
| Configuración StartUp de MT5 existente | No se observó ejecución del script; no se reinició el terminal original. Se retiró únicamente el proceso adicional propio si persistía |
| Log tailing | Sólo aparecen BEGIN/END del registro anterior, no una nueva ejecución |
| MCP soportado del terminal | HTTP 401; no se modificó autenticación ni se crearon credenciales |
| Control de Windows | FrameArrived timeout; selección recuperada y segundo intento con window capture timeout. No se enviaron inputs sin una observación válida |

Watchers y Scheduler capturan Windows; por sí solos no aportan una API de ejecución MQL. No se presenta iniciar un proceso o cargar un script como prueba de que se haya ejecutado OnStart. No se intentó habilitar permisos de trading, DLLs, acceso externo o políticas de seguridad para sortear los bloqueos.

## Watcher preparado

`python/simultaneous_clock_capture.py` observa Windows continuamente mientras espera **sin plazo de caducidad**. Sale después de un único registro nativo completo. Depende de que este proceso y Windows sigan activos; ready.json no sustituye comprobar su liveness. No crea una automatización de scoring ni un monitor de trading.

Cada observación incluye:

- UTC preciso Windows en unidades enteras ns derivadas de FILETIME; UTC estándar y Python por separado.
- GetLocalTime, Python local y **Windows TimeZoneKeyName leído fresco**, con sus brackets.
- GetTickCount64 compartido entre procesos y perf_counter/QPC, con inicio/fin de cada lectura.
- Consultas w32tm source/status/offset antes/después, con returncode y tiempos.
- Referencias NTP con corroboración TLS, tomadas asíncronamente para no detener el muestreo Windows, incluidas referencias durante el registro nativo.

El watcher conserva una ventana circular de observaciones anteriores y empareja cada frame del probe con una lectura Windows anterior y otra posterior, por los contadores compartidos. El campo `bracket_width_ms` conserva la separación real. No es una lectura atómica y no se añade un epsilon para aparentar simultaneidad o aceptar quotes.

Se evita el problema anterior: una referencia externa lenta ya no impide armar la captura y esperar al usuario. El muestreo Windows empieza antes de lanzar el trabajo de red. No se emparejan retroactivamente registros viejos con una lectura Windows nueva; si falta bracket previo, no se declara overlap.

`python/simultaneous_clock_audit.py` verifica 50 frames, 150 filas, membresía, contadores, brackets, seconds/ms, tester=0, conexión y END. Sólo entonces SIMULTANEOUS_OVERLAP puede pasar. La comparación Windows/NTP usa los brackets QPC exteriores de cada adquisición; no asume iguales los orígenes numéricos de diferentes APIs monotónicas. La incertidumbre de red sólo acota el diagnóstico: **no es tolerancia para quotes futuras**.

`python/finalize_clock_capture.py` también queda armado sin caducidad: al aparecer capture.json verifica source/EX5, correspondencia exacta con el CSV, marcas y hashes, copia el crudo intacto y escribe audit.json automáticamente. No autoriza mapping, scoring ni trading. Rechaza ejecutables cambiados y no sobrescribe auditorías completas.

Incluso con overlap PASS, el reloj operativo y el mapping necesitan sus propias pruebas. Este auditor no autoriza segmentos nativo→UTC. La función existente `native_to_utc` sigue rechazando el mapping preparado FAIL; los eventos no reciben horas UTC/Ecuador/New York inventadas. Las vistas IANA desde UTC conocido y tzdata congelada permanecen disponibles.

## Una sola acción pendiente

```text
Navigator -> Scripts -> ResearchDiagnostics -> attest_20261023_a2 -> ClockAttestationProbeV2
```

El source/EX5 es el mismo ya ejecutado. El watcher Python está preparado para el nuevo CSV y las marcas. No hay que cambiar inputs, recompilar ni instalar otro script. Al recibir la ejecución se analizarán los registros; no habrá scoring ni evaluación mientras CLOCK/CAUSAL fallen.

## Estado publicado mientras se espera

| Campo | Estado |
|---|---|
| WINDOWS_CLOCK_SYNC | FAIL |
| CLOCK_PROBE | PASS — ejecución anterior conservada |
| SIMULTANEOUS_OVERLAP | FAIL — nuevo registro pendiente |
| AUTHORITATIVE_CLOCK | NONE operativo; UTC externo sólo diagnóstico |
| BROKER_SERVER_OFFSET | 7200 s observados entre estimador y GMT del host; mapping no certificado |
| BROKER_DST | PARTIAL |
| NATIVE_TO_UTC_MAPPING | FAIL |
| ECUADOR_TIME_MAPPING | PASS — sólo vistas de UTC explícito |
| NEW_YORK_TIME_MAPPING | PASS — sólo vistas de UTC explícito |
| FUTURE_QUOTE_ROOT_CAUSE | A: reloj Windows incorrecto; B: semántica; F del tick retenido anterior |
| TEMPORAL_CAUSALITY | FAIL |
| MAIN_K_PARITY | PASS — exports existentes revalidados |
| CAUSAL_AUDIT | FAIL |
| HISTORICAL_DATASET_IMPACT | NONE |
| DISCOVERY_VALIDATION | BLOCKED |
| FINAL_TEST | LOCKED |
| DEMO | DISABLED |
| LIVE_TRADING | false |
| HARD_BLOCKER | Host no atestado, nueva captura simultánea pendiente, correspondencia nativo/UTC no certificada |
| MANUAL_ACTION_REQUIRED | La única ruta indicada arriba |
| NEXT_STATE | HARD_BLOCKER_CLOCK_ATTESTATION_AND_MAPPING_PENDING_SIMULTANEOUS_RUN |

La suite existente mantiene Ecuador UTC−5, New York EST/EDT, DST marzo/noviembre, exactitud, +1 ms, stale/startup, mercado cerrado, doble conversión, drift y divergencia de relojes. Cinco tests adicionales cubren brackets reales, ausencia de observaciones previas, uso monotónico independiente de etiquetas de pared, CSV incompleto/duplicado y no confundir overlap con atestación. Las cifras finales de suite y hashes quedan en el [estado sellado](../configs/clock_sync_block_evidence_20261023/status.json).

Suite completa: **222 tests en 215.383 s: 213 correctos y 9 omitidos por falta de g++**. Después se ejecutaron siete tests relevantes (incluidos dos nuevos del finalizador), todos correctos. Compileall y git diff --check pasan. Los fixtures sintéticos de tests no cuentan como evidencia de relojes reales.

No se continúa con manifest chain, drift monitor, salud/madurez evaluativa, future evaluator, shadow o executor hasta que los gates requeridos estén resueltos. Los procesos de colección existentes no se convierten en permiso de scoring.

Fuentes: [StartUp soportado](https://www.metatrader5.com/en/terminal/help/start_advanced/start), [capacidades MCP](https://www.metatrader5.com/en/terminal/help/mcp_and_ai/capabilities), [TimeTradeServer](https://www.mql5.com/en/docs/dateandtime/timetradeserver). Las rutas locales y errores observados determinan el estado real, no la disponibilidad teórica de una función.
