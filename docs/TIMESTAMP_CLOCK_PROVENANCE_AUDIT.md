# Procedencia de la quote y auditoría de relojes

Identificador del expediente: 20261023, fecha del host investigado. **No equivale a una fecha UTC certificada.** Las referencias externas sitúan la captura en 2026-10-25; se conservan ambos valores sin corregir artefactos anteriores.

## Conclusión y límites

**Categoría A: el reloj local usado como referencia está atrasado.** Tres servidores NTP independientes, con nonce de petición verificado, coinciden; tres respuestas HTTPS Date corroboran la referencia. A las `2026-10-23T11:47:51.435922` del host, el intervalo NTP corresponde a `2026-10-25T21:34:31.231509646`–`21:34:31.247509646Z`. El atraso es 207999.795587146–207999.811587146 segundos: unas 57 h 46 min 40 s. Windows Time está detenido y deshabilitado. Esto prueba la discrepancia; no identifica quién configuró el reloj ni demuestra que el estado del servicio sea su causa original.

La quote US30Cash retenida tiene `time=1792799997`, `time_msc=1792799997469`, bid `52271.09`, ask `52277.09`. Es anterior al UTC externo. Parecía futura al compararla con el reloj local atrasado. No hay evidencia de que represente una operación futura del broker. Los precios se capturaron en esta auditoría para la misma marca temporal; no se atribuyen retroactivamente a capturas antiguas que no guardaron precios.

Hay además **B: semántica de relojes/dominio temporal** y **F: último tick retenido**, como factores secundarios. Los ticks activos de EURUSD tienen etiquetas aproximadamente UTC+2 frente al UTC externo, mientras US30Cash conserva una marca de viernes. No se demuestra corrupción de caché ni su capa física. La API devuelve la última actualización, sin garantizar que sea una quote nueva tras adjuntar el proceso. El `TimeCurrent` del script nuevo sigue la última quote de Market Watch, no exclusivamente US30Cash.

La procedencia del aparente futuro está identificada. **El cierre causal operativo sigue bloqueado:** el reloj del host no es fiable y falta una correspondencia UTC del feed certificada y versionada. No se cambió el reloj, no se normalizaron datos aceptados ni se introdujo una resta de dos horas para aceptar quotes.

La fecha externa del 25 de octubre es posterior al cambio DST europeo de ese día; UTC+2 resulta compatible con esa fecha, mientras la fecha local errónea del 23 sugería UTC+3. Esto puede explicar la discrepancia DST anterior; es una inferencia sobre capturas previas, no una razón para reescribir sus fechas ni elevar el calendario histórico a VERIFIED.

| Campo | Resultado |
|---|---|
| FUTURE_QUOTE_ROOT_CAUSE | A: referencia local atrasada; B/F secundarios |
| AUTHORITATIVE_CLOCK | UTC independiente atestado; ninguno habilitado para decisiones en este host |
| TIMESTAMP_NORMALIZATION | FAIL: correspondencia nativo/UTC sin certificar |
| FUTURE_QUOTE_GUARD | PASS: sigue rechazando todo futuro, sin tolerancia nueva |
| TEMPORAL_CAUSALITY | PASS: invariantes/rechazos; no certifica el feed ni el reloj |
| MAIN_K_PARITY | PASS: revalidación de exports existentes; script no repetido |
| CAUSAL_AUDIT | FAIL: reloj operativo y correspondencia temporal pendientes |
| SESSION_CALENDAR | PASS_WITH_RUNTIME_GUARD |
| DISCOVERY_VALIDATION | BLOCKED |
| FINAL_TEST | LOCKED |
| DEMO | DISABLED |
| LIVE_TRADING | false |
| HARD_BLOCKER | HOST_CLOCK_UNTRUSTED_AND_NATIVE_UTC_MAPPING_UNVERIFIED |
| NEXT_STATE | HARD_BLOCKER_CLOCK_ATTESTATION_AND_MAPPING |

## Evidencia reproducible

`python/quote_clock_audit.py` se adjunta sólo al terminal activo verificado DEMO. Captura símbolo, bid/ask, todos los campos de tick, límites exactos de lectura UTC local, latencia monotónica y `copy_ticks_range` de tres segundos. No usa órdenes, no modifica símbolos y no usa el resultado histórico como precio alternativo. La captura principal tiene 15 lecturas: cinco por símbolo US30Cash/EURUSD/USDCHF. Otra captura de nueve lecturas incluye una segunda comprobación independiente de referencias. Ninguna lee outcomes o puntúa la cohorte.

Reproducción desde la raíz del repositorio, con el entorno que tiene MetaTrader5 instalado:

```text
.venv/Scripts/python.exe python/quote_clock_audit.py --output work/clock_new_capture.json --samples 5
```

La salida se niega a sobrescribir evidencia. `python/independent_clock_reference.py` consulta time.windows.com, time.cloudflare.com y time.google.com; verifica modo, stratum, leap y nonce reflejado. Proyecta los intervalos con el RTT completo sobre un mismo reloj monotónico. Si no hay tres fuentes independientes o sus intervalos no intersectan, falla la verificación. NTP aquí no tiene autenticación criptográfica: se corrobora mediante HTTPS con validación TLS normal, Date sin Age positivo y tres dominios distintos. Es diagnóstico, no un servicio de tiempo aprobado para ejecución. Los límites de RTT no se utilizan como tolerancia para quotes futuras.

`ClockProvenanceProbe.mq5`, ejecutado por el usuario en el XM activo, exportó **24 filas completas**, ocho por símbolo. Todas tienen `tester=0`, `connected=1`, `tick_ok=1`; las parejas segundos/milisegundos concuerdan. La compilación produjo 0 errores y 0 advertencias. Registra SymbolInfoTick, CopyTicksRange, TimeCurrent, TimeTradeServer, TimeLocal, TimeGMT, offset, DST y contadores monotónicos antes/después. No se volvió a ejecutar MainKNativeParity ni SessionCalendarProbe por parte del agente.

Ejemplo de la muestra nativa 0:

| Reloj/campo | Entero nativo |
|---|---:|
| TimeGMT antes/después | 1792756178 |
| TimeLocal | 1792738178 |
| TimeTradeServer | 1792763378 |
| TimeCurrent | 1792971376 |
| US30Cash tick.time | 1792799997 |
| US30Cash tick.time_msc | 1792799997469 |
| TimeGMTOffset | 18000 |
| TimeDaylightSavings | -3600 |

TimeTradeServer − TimeGMT es 7200 s en las 24 filas. TimeLocal es cinco horas menos que TimeGMT. Son relaciones internas del host; **no certifican su fecha absoluta**. TimeCurrent ya no coincide con US30Cash: avanza con FX mientras US30Cash permanece retenido. La salida independiente, con intervalos proyectados a cada recepción Python, deja US30Cash unos 164 millones de ms en el pasado; EURUSD ronda +7.2 millones de ms en su etiqueta bruta. Esto respalda un dominio de servidor UTC+2 para las etiquetas actuales, pero no demuestra una regla UTC universal para todos los productos, fechas o DST.

## Clasificación de alternativas

| Categoría | Hallazgo |
|---|---|
| A: reloj local incorrecto | Demostrado por NTP y HTTPS independientes; también afecta TimeGMT/TimeLocal |
| B: semántica de relojes | Demostrado: TimeCurrent es última quote de Market Watch; TimeTradeServer se calcula en cliente |
| C: servidor entrega tick realmente futuro | No demostrado; el tick US30Cash es pasado frente al UTC externo |
| D: doble conversión timezone | No aparece en la ruta de rechazo; la comparación usa enteros brutos |
| E: segundos/milisegundos | No explica el caso: todas las parejas observadas concuerdan |
| F: lectura retenida/cache | Último tick US30Cash persistente; capa interna exacta desconocida, sin evidencia de corrupción |
| G: fixture | Excluido: símbolos reales, API nativa, tester=0; sin inyección sintética |
| H: collector | No produce la quote de SymbolInfoTick; sí hereda un `now` local no fiable |
| I: comportamiento esperado | Retener el último tick y semántica de TimeCurrent son esperables; no legitiman aceptarlo |
| J: otros | UTC de etiquetas actuales requiere conciliación con contrato del broker; no se inventa |

El fenómeno persiste entre capturas previas y actuales, y depende del símbolo. FX avanza; US30Cash permanece fijo. No se reinició el terminal: **dependencia exclusiva del arranque UNKNOWN**. No se observó una transición de sesión controlada: **dependencia de transición UNKNOWN**. US30Cash tiene marca de viernes frente a referencias externas de domingo, compatible con cierre; eso no constituye una atestación independiente de disponibilidad de ejecución. Se conserva `market_open=UNKNOWN`.

## Reloj autoritativo y contrato congelado

Para decisiones live/shadow, la autoridad deberá ser **UTC disciplinado y atestado independientemente del tick**, con vínculo fiable entre recepción, decisión y dominio de timestamps del feed. TimeCurrent nunca es un reloj independiente de recepción: usarlo para aceptar su propia quote sería circular. TimeTradeServer y TimeGMT tampoco corrigen un host mal fechado: ambos dependen de su configuración, según documentación MT5.

Hasta corregir/atestar el reloj y certificar la correspondencia del feed:

- `clock_verified=false`; no convertir el quórum diagnóstico en permiso de operar.
- `feature_max_time <= decision_time`; quote no posterior a decisión y edad máxima congelada de 5000 ms.
- Igualdad permitida; +1 ms y futuros submilisegundo rechazados; sin tolerancia futura nueva.
- Timestamp nativo desconocido, mapping ambiguo, mercado cerrado, quote stale o tick de arranque no fresco: rechazo.
- `time_msc // 1000 == time`, con enteros no negativos; discrepancias se rechazan antes de construir datetime.
- Nada de restar automáticamente el desfase del host, el offset del broker o DST para hacer pasar una quote. La correspondencia futura requiere un expediente y una versión explícitos antes de auditarla.
- Replay histórico compara eventos y secuencias dentro del dominio histórico congelado. No se le aplica el reloj actual ni un offset inferido hoy.

El contrato se registra y sella antes de la reauditoría en [timestamp_clock_contract_v1.json](../configs/timestamp_clock_contract_v1.json). La tolerancia a futuro sigue siendo exactamente cero. La política v3 sólo registra cambios defensivos de código y el estado bloqueado.

## Auditoría de código e impacto

| Componente | Resultado |
|---|---|
| Collector sellado | `copy_ticks_range` recibe datetime aware; usa time_msc entero para particiones. `_ms` usa float y no valida naive por sí mismo, pero sus llamadores construyen UTC aware. `now` depende del host: afecta selección de días/capturas y metadatos de salud. No es la fuente de SymbolInfoTick. Código y hashes conservados. |
| Runtime adapter | Añadido rechazo explícito de pareja segundos/ms inconsistente; datetime por suma entera de milisegundos, sin float. Expone reloj no atestado y mapping bloqueado. Sigue sin permiso de ejecución. |
| Guard y shadow | Exigen UTC explícito; no usan TimeCurrent para aceptar su propia quote. Rechazos de futuro/stale/mercado cerrado y clock ambiguity permanecen. |
| Normalización | `utc_milliseconds` exige timezone; convierte un instante explícito, no adivina server time. La aritmética pasa tests; la correspondencia real nativo/UTC sigue FAIL. |
| Replay | Compara enteros ms y secuencia; conserva llegada después del cutoff y latencia congelada. Sin cambios. |
| Snapshot MQL | Cutoffs/ticks en dominio de servidor/tester; shift 1 y feature cutoff conservados. No se certifica equivalencia UTC universal con esta auditoría. |
| Controller | Sus límites de tester etiquetan el calendario del servidor mediante enteros; no son atestación de UTC real. No se modificaron splits ni fuentes históricas. |

Se conservan fuentes MQL aceptadas, datasets, manifiestos, metadata sellada y evidencias anteriores. La metadata operativa basada en hora local queda sin autoridad para madurez o autorización hasta reconciliar el reloj. No se regeneró, puntuó ni rehabilitó ninguna cohorte, ni se abrieron splits protegidos. La política v3 registra los hashes nuevos sin sobrescribir v1/v2.

## Fuentes y verificación

[TimeCurrent](https://www.mql5.com/en/docs/dateandtime/timecurrent), [TimeTradeServer](https://www.mql5.com/en/docs/dateandtime/timetradeserver) y [TimeGMT](https://www.mql5.com/en/docs/dateandtime/timegmt) documentan las dependencias citadas. La [documentación Python de ticks](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py) declara UTC, mientras la observación actual de FX respalda etiquetas de servidor. Se registra esta diferencia explícitamente; no se resuelve desplazando datos silenciosamente. [CopyTicks](https://www.mql5.com/en/docs/series/copyticks) explica las fuentes/cache de los ticks; no permite identificar físicamente la capa de caché de esta muestra.

Los tests nuevos cubren igualdad, quote correcta, +1 ms, stale/startup, offset explícito, DST, doble conversión y mismatch segundos/ms. La suite existente cubre mercado cerrado y futuro submilisegundo. Los tests NTP rechazan nonce incorrecto, referencia no sincronizada y quórum incompleto/discrepante. Los exports MAIN_K existentes se revalidaron: PASS, 960 filas, error máximo 1.4210854715202004e-14. No se ejecutó otra vez el script.

Evidencia íntegra y sellada: [expediente](../configs/clock_provenance_evidence_20261023/audit.json). El estado final de pruebas se registra allí. No se publica información de cuenta, credenciales ni paths privados del terminal.
