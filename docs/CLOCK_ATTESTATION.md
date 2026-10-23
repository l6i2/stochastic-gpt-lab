# Clock attestation y mapping temporal

## Preparación posterior: captura simultánea automatizada

El [checkpoint de automatización](CLOCK_SYNC_AUTOMATION.md) reutiliza el probe a2 sin recompilarlo. Sus registros anteriores se archivaron conservando bytes, hashes y mtime. El watcher Python y el finalizador automático están armados sin caducidad; las rutas de lanzamiento automático fallaron de forma documentada. Windows preciso/estándar y w32tm confirman que el reloj sigue sin atestarse. La única acción manual pendiente y todos los estados están en ese checkpoint. Los apartados siguientes conservan la captura anterior como evidencia histórica.

Expediente 20261023, identificado por la fecha del cliente. Las fechas del host, MT5 y referencias externas se guardan como observaciones distintas; ninguna se sustituye silenciosamente.

## Resultado

Se completaron **50 frames consecutivos**, durante unos 50 segundos, con **150 lecturas nativas** de US30Cash, EURUSD y USDCHF. Un sidecar emparejó cada frame con UTC/local de Windows mediante `GetTickCount64`, compartido por ambos procesos. La separación medida entre fin de lectura nativa e inicio de la observación Windows fue **0–125 ms**. Es una captura acotada, no atómica.

La integridad de captura pasa, pero **la atestación del reloj y el mapping nativo/UTC no pasan**. Los dos quórums externos vuelven a situar el reloj del host aproximadamente 207999.8 segundos atrasado. Ningún reloj operativo actual queda aprobado como autoridad causal. Las vistas Ecuador/New York están implementadas y probadas desde un UTC explícito; no se inventan vistas para quotes cuyo mapping es desconocido.

| Campo | Estado |
|---|---|
| CLOCK_ATTESTATION | FAIL |
| AUTHORITATIVE_CLOCK | NONE operativo; quórum UTC independiente sólo para diagnóstico |
| NATIVE_TO_UTC_MAPPING | FAIL — segmentos autorizados vacíos |
| ECUADOR_TIME_MAPPING | PASS — vista de UTC explícito con America/Guayaquil |
| NEW_YORK_TIME_MAPPING | PASS — vista de UTC explícito con America/New_York |
| DST_HANDLING | PASS en vistas IANA y rechazo de ambigüedad; DST nativo no atestado |
| FUTURE_QUOTE_ROOT_CAUSE | A: referencia local incorrecta; B: semántica de relojes; F sólo para el tick retenido anterior |
| FUTURE_QUOTE_GUARD | PASS — tolerancia futura cero |
| TEMPORAL_CAUSALITY | FAIL — relaciones operativas aún no demostradas |
| MAIN_K_PARITY | PASS — exports previos revalidados |
| CAUSAL_AUDIT | FAIL |
| SESSION_CALENDAR | PASS_WITH_RUNTIME_GUARD |
| DISCOVERY_VALIDATION | BLOCKED |
| FINAL_TEST | LOCKED |
| DEMO | DISABLED |
| LIVE_TRADING | false |
| HARD_BLOCKER | HARD_BLOCKER_CLOCK_ATTESTATION_AND_MAPPING |
| NEXT_STATE | HARD_BLOCKER_CLOCK_ATTESTATION_AND_MAPPING |

Los PASS de zonas describen conversiones desde un instante UTC ya conocido. **No certifican UTC de las quotes nativas.** TEMPORAL_CAUSALITY se informa aquí con el alcance estricto pedido: todas las relaciones operativas, no sólo tests del rechazo. Por eso los PASS anteriores limitados a invariantes no cierran esta auditoría.

## Captura y procedencia

`tests/mql5/ClockAttestationProbe.mq5` fue compilado con el MetaEditor del XM activo: 0 errores y 0 advertencias. El usuario ejecutó `ResearchDiagnostics/attest_20261023_a1/ClockAttestationProbe`. No se repitieron MainKNativeParity ni SessionCalendarProbe por parte del agente. El nuevo script sólo observa: sin DLLs, órdenes, custom symbols/ticks, cambio de hora o configuración.

Cada una de las 150 filas conserva frame, símbolo, bid/ask, `tick.time`, `tick.time_msc`, `TimeLocal`, `TimeGMT`, `TimeCurrent`, `TimeTradeServer`, offset, DST, terminal build, conexión y tester. Cada lectura de reloj/tick lleva un contador monotónico; se conservan inicio y fin del frame. Todas las filas tienen `tester=0`, `connected=1`, `tick_ok=1`; las parejas segundos/ms concuerdan y los contadores no retroceden.

`python/clock_attestation_capture.py` captura UTC/local Windows para cada frame, con sus límites monotónicos, y conserva las tres filas MQL originales. El identificador Windows timezone se obtuvo con `tzutil /g` y se repite como metadata **cacheada**, junto con el bracket monotónico de esa consulta original. No se presenta como consulta fresca por frame ni se afirma que el timezone no pudiera cambiar entre consultas. La hora local y su offset sí se observaron en cada frame. Si hace falta atestar cambios del identificador timezone durante la ventana, esa evidencia adicional sigue pendiente.

Los 150 diccionarios nativos emparejados coinciden exactamente, en contenido y orden, con las filas del CSV crudo. El SHA-256 del CSV original se conserva. Los JSON de análisis y vistas son artefactos nuevos, no reemplazos del crudo ni de datasets aceptados.

Los quórums NTP antes/después y la corroboración HTTPS se conservan completos. Sus intervalos incluyen RTT; no aportan permiso de ejecutar ni tolerancia de futuro. NTP es diagnóstico no autenticado, contrastado con TLS Date de dominios independientes. La fuente independiente detecta el reloj incorrecto; no se convierte automáticamente en servicio de tiempo de producción.

## Lo observado

- `TimeTradeServer − TimeGMT` fue **7200 segundos** en todas las lecturas. Es una relación interna entre un estimador y el reloj local incorrecto, no prueba de UTC absoluto.
- Las etiquetas `TimeGMT`/UTC Windows y `TimeLocal`/local Windows coinciden al segundo en las 150 comparaciones; GMT−local y TimeGMTOffset son 18000 s. Compartir el reloj incorrecto no equivale a una atestación independiente.
- `TimeCurrent − TimeTradeServer` osciló entre **207997 y 208000 segundos**. Usar TimeCurrent como reloj independiente de su propia quote sería circular.
- US30Cash produjo 24 timestamps distintos; EURUSD 19; USDCHF 14. En esta captura US30Cash **ya avanza**, a diferencia del tick de viernes retenido en la captura anterior. La anomalía frente al host no está limitada al caso de mercado cerrado.
- El primer/último UTC observado del host fue `2026-10-23T12:16:04.411598+00:00` / `12:16:54.267603+00:00`. Son etiquetas del host no atestado, no fecha UTC certificada.
- Se conservan los deltas de pared, monotónicos, offsets y orden. Los residuos pared−monotónico van de −10 a +12 ms. `GetTickCount64` tiene resolución limitada; esos residuos **no demuestran drift real** ni estabilidad perfecta. No se ocultan con un epsilon: la reconciliación fina queda sin certificar.
- El atraso del host fue aproximadamente 207999.8 s antes y después. Su persistencia no legitima sumar ese valor a decisiones o restarlo a datos.

No se reinició el terminal. Dependencia de startup: UNKNOWN. No hubo captura controlada cruzando una transición DST o una sesión: UNKNOWN. La reanudación de actualizaciones entre expedientes se registra, pero no certifica por sí sola disponibilidad ejecutable o instante exacto de apertura. Mercado ejecutable: UNKNOWN; el guard sigue cerrado.

## Semántica y autoridad

`TimeCurrent` representa la última recepción de quote de Market Watch fuera de OnTick; se forma en el servidor. `TimeTradeServer` es estimado por el cliente y depende de su reloj. Las observaciones de divergencia concuerdan con esa distinción documentada. `TimeGMT` y `TimeLocal` tampoco corrigen una fecha errónea del host.

La etiqueta nativa actual es compatible con calendario de servidor alrededor de UTC+2 frente a referencias externas. **Compatibilidad no es atestación.** La edad de un tick, retención de cache y offset de calendario no se pueden separar universalmente sólo por última quote y recepción. Tampoco se demostró una regla del broker a ambos lados de DST. No se autoriza restar 7200 segundos.

AUTHORITATIVE_CLOCK operativo: **NONE**. RATIONALE: el host discrepa con referencias independientes; los relojes derivados no son independientes; la etiqueta del feed no tiene correspondencia UTC certificada. Para uso futuro se requiere UTC independiente atestado y vínculo documentado con el instante de decisión/recepción. El quórum actual sólo prueba la discrepancia.

La quote inicial US30Cash no era una operación futura frente al UTC externo: parecía futura frente al reloj atrasado. Los timestamps posteriores, con ticks ya actualizándose, siguen sin poder usarse como epoch UTC sin mapping. Se conserva la clasificación A principal, B secundaria y F como explicación del último tick retenido anterior. No se encontró doble conversión ni mismatch segundos/ms en la evidencia nativa; no es fixture ni Strategy Tester, y el collector no fabrica SymbolInfoTick.

## Función única de mapping y zonas

`python/native_time_mapping.py::native_to_utc` es la única función nueva que convierte una etiqueta nativa en instante UTC. Consume `NativeTimestamp` inmutable y `ClockMapping` explícito. El loader exige sello de configuración, hash de evidencia, atestaciones PASS, al menos 50 frames completos y segmentos autorizados idénticos a los del expediente. El preparado actual tiene `status=FAIL` y **cero segmentos**: se rechaza antes de cualquier desplazamiento.

Cada segmento futuro deberá definir un intervalo UTC válido y offsets nativo/UTC y servidor/UTC demostrados para esa identidad de servidor/símbolo. No existe fallback a un offset observado, al timezone del host ni a una regla DST teórica. Cero candidatos o varios candidatos producen rechazo. El overlap de otoño y los huecos de primavera no se resuelven por adivinación.

Una conversión aprobada conserva `native_mt5_time`, `raw_sha256`, `normalized_utc`, `ecuador_time`, `new_york_time`, `xm_server_time` e identidad de mapping. Segundos/ms se validan por división entera. No usa float para el instante. Rechaza entradas ya normalizadas, identidad incorrecta, provenance ausente, intervalos desconocidos o ambiguos. La verificación causal compara UTC y conserva igualdad, rechazo +1 ms, stale >5000 ms y rechazo de feature futura. La comprobación de secuencia normalizada detecta regresiones; las vistas horarias nunca se usan como clave de orden.

El hash derivado `utc_event_sha256` usa únicamente hash crudo, milisegundos UTC e identidad de mapping en JSON canónico. Las vistas Ecuador/New York no participan en esa identidad causal. Es un hash nuevo de metadata derivada, sin sustituir hashes crudos o aceptados.

Ecuador usa **America/Guayaquil**, UTC−5 sin DST en el periodo operativo probado. New York usa **America/New_York**, con EST/EDT y fold por IANA. No se fija un offset New York. Se carga explícitamente el paquete congelado **tzdata 2026.5**, sin depender de una tzdb distinta del sistema. UTC es el dominio para orden, validación y serialización del instante; las zonas son vistas humanas. El hash de procedencia del crudo no cambia al producirlas.

El adaptador runtime usa el loader y deja `normalized_utc`, Ecuador, New York y servidor como `null` si no hay mapping verificado. Conserva la etiqueta nativa y el hash del nuevo registro de diagnóstico. Ya no llama UTC a esa etiqueta bruta. `decision_time_utc` también queda `null`: la hora observada del sistema se registra aparte. Incluso un mapping histórico válido no autoriza el reloj de decisión actual. No se abre ningún gate de sesión ni de trading.

Los eventos nativos de este expediente tienen vistas normalizadas explícitamente desconocidas en `native_event_views_blocked.json`. `zone_examples.json` muestra conversiones de instantes UTC sintéticos claramente rotulados; no constituye evidencia de conversión del feed. Ningún replay nuevo de tiempo nativo queda autorizado sin mapping. El replay histórico aceptado y sus hashes se conservan en su dominio original, sin reinterpretarlos silenciosamente como UTC ni ejecutarlos para nuevo scoring.

## Reproducción y pruebas

Para una captura nueva se exige un nonce nuevo. Con el sidecar esperando, ejecutar manualmente el script MQL correspondiente. La ejecución ya realizada es suficiente para este expediente y no se repite:

```text
.venv/Scripts/python.exe -u python/clock_attestation_capture.py --native-file <MQL5/Files/NUEVO_NONCE_native.csv> --output work/NUEVO_NONCE.json
.venv/Scripts/python.exe python/clock_attestation_audit.py --capture work/NUEVO_NONCE.json --output work/NUEVO_NONCE_audit.json
```

Las pruebas cubren UTC/local, offset explícito, exactitud, +1 ms, stale/startup, mercado cerrado, rollover ms, doble conversión, regresión monotónica, discrepancia pared/monotónico, TimeCurrent/estimador divergentes, sellos y provenance. Incluyen Ecuador durante los doce meses, NY EST/EDT, salto de marzo y fold de noviembre, comparación con Ecuador y ambigüedades de segmentos del servidor. Los segmentos de tests son sintéticos; no se convierten en atestación del broker.

Se revalidaron los exports MAIN_K previos: 960 filas, PASS, error máximo 1.4210854715202004e-14. No se repitió el script ni se regeneró un dataset. El estado final de suite, compileall, whitespace y hashes se registra en [audit.json](../configs/clock_attestation_evidence_20261023/audit.json).

Suite completa: **217 tests en 113.564 s, 208 correctos y 9 omitidos por falta de g++**. Tras fijar la carga explícita de tzdata y el hash UTC derivado se repitieron 17 tests relevantes, todos correctos. Compileall y git diff --check pasan. No se convierten los skips ni las relaciones operativas pendientes en PASS.

## Evidencia que falta para cerrar

1. Un reloj operativo UTC corregido/atestado y ligado a recepción/decisión, con precisión y drift reconciliados. No se modificó Windows ni se habilitó su servicio de hora.
2. Correspondencia broker/nativo→UTC independiente, certificada para intervalos/identidades concretos; luego segmentos sellados. No basta que +2 h haga parecer fresca la quote.
3. Evidencia del comportamiento al arranque, mercado ejecutable, cambios de sesión y DST si se pretende cubrir esas condiciones. Fuera de los intervalos certificados se seguirá rechazando.
4. Si se exige atestar el identificador Windows timezone por frame, hace falta captura fresca de ese dato; el identificador de este expediente está cacheado y rotulado como tal.

Mientras falte lo anterior se mantiene HARD_BLOCKER_CLOCK_ATTESTATION_AND_MAPPING. Los guards siguen fail-closed, sin quotes futuras, tolerancias nuevas, DEMO o trading real. La cohorte sólo se trató como integridad/procedencia; no hubo scoring, labels, outcomes, nuevas hipótesis TRAIN ni acceso a splits protegidos.

Fuentes: [ZoneInfo](https://docs.python.org/3/library/zoneinfo.html), [GetTickCount64](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-gettickcount64), [TimeCurrent](https://www.mql5.com/en/docs/dateandtime/timecurrent), [TimeTradeServer](https://www.mql5.com/en/docs/dateandtime/timetradeserver). La evidencia local decide los estados; la documentación no sustituye la atestación.
