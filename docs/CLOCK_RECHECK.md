> HISTORICAL SNAPSHOT: preserved evidence, not current operational authority. Current status: [PROJECT_STATUS.md](PROJECT_STATUS.md); Cloud audit: [CLOUD_PREPARATION_AUDIT.md](CLOUD_PREPARATION_AUDIT.md).

# Revisión adicional del bloqueo de reloj

Se reutilizaron los 150 registros originales y se verificaron todos sus hashes. No se repitió, reinstaló ni recompiló el probe. Las rutas automáticas previas permanecen documentadas en CLOCK_SYNC_AUTOMATION.md; repetirlas no resolvería el reloj del host.

Nueva lectura Win32 y referencia externa: Windows atrasado entre 207999.928610259 y 207999.944610259 segundos. w32tm source/status: 0x80070426 (servicio no iniciado); stripchart: éxito. No se modificó el reloj ni el servicio.

Reauditoría de captura existente: FAIL; faltan límites estrictamente externos en 26 frames. La selección corregida y ahora el auditor independiente rechazan igualdad de límites coarse. Sin tolerancias ni reconstrucción de timestamps.

TimeCurrent representa último evento de Market Watch, no reloj UTC corriente; TimeTradeServer se calcula en el cliente y depende del reloj del PC; TimeGMT también deriva del PC. Fuentes oficiales: https://www.mql5.com/en/docs/dateandtime/timecurrent ; https://www.mql5.com/en/docs/dateandtime/timetradeserver ; https://www.mql5.com/en/docs/dateandtime/timegmt . Los +7200 s entre dos relojes derivados no certifican offset UTC del broker. DST broker PARTIAL: no hay transición nativa certificada. El último tick puede ser retenido por símbolo/mercado cerrado; no convierte el reloj local en autoridad.

Los registros nativos ya contienen la discrepancia; no la genera el collector ni replay. Se conserva evidencia previa de SymbolInfoTick live, tester=0, conexión y tick_ok, coherencia seconds/milliseconds. No se demuestra causalidad por cercanía al reloj externo; NTP/TLS se mantienen diagnósticos y no autorizan ejecución. No se atribuye a DST un desfase de ~57 h 46 min 40 s. No hay evidencia que justifique double conversion o bug del wrapper como causa del reloj Windows preciso observado.

Tests relevantes: 35 PASS (17 reloj, 11 mapping, 4 causalidad temporal, 3 paridad). compileall y git diff --check PASS. MAIN_K conserva PASS de evidencia nativa existente; no se ejecutó script de paridad. Ecuador/Nueva York PASS desde UTC explícito; mapping nativo FAIL.

HARD_BLOCKER: UTC Windows no atestiguado y límites inválidos de captura. Requisito para cierre: referencia UTC operacional atestiguada y nueva captura con límites válidos; luego certificar segmentos broker/UTC, sin tocar histórico. No ejecutar otra captura mientras el reloj permanezca inválido. MANUAL_ACTION_REQUIRED=NONE ahora. No se continúa evaluación ni scoring.

WINDOWS_CLOCK_SYNC=FAIL; CLOCK_PROBE=PASS; SIMULTANEOUS_OVERLAP=FAIL; AUTHORITATIVE_CLOCK=NONE_OPERATIONALLY_ATTESTED; BROKER_SERVER_OFFSET=OBSERVED_7200_SECONDS_NOT_CERTIFIED; BROKER_DST=PARTIAL; NATIVE_TO_UTC_MAPPING=FAIL; TEMPORAL_CAUSALITY=FAIL; CAUSAL_AUDIT=FAIL; MAIN_K_PARITY=PASS; HISTORICAL_DATASET_IMPACT=NONE.

DISCOVERY_VALIDATION=BLOCKED; FINAL_TEST=LOCKED; DEMO=DISABLED; LIVE_TRADING=false. Future quote => REJECT, tolerancia cero. NEXT_STATE=HARD_BLOCKER_CLOCK_ATTESTATION_AND_MAPPING.
