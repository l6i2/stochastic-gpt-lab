# Auditoría de MAIN_K y causalidad temporal — 2026-10-23

## Resultado actual

| Campo | Estado |
|---|---|
| MAIN_K_ROOT_CAUSE | metadata; el fixture auxiliar legado comparte la aproximación incorrecta para certificar semántica nativa |
| MAIN_K_PARITY | FAIL — falta la ejecución nativa de los cinco fixtures, no se observó un mismatch del productor |
| HISTORICAL_DATASET_IMPACT | NONE — productor y datasets aceptados conservados; ninguna reconstrucción |
| TIMESTAMP_ROOT_CAUSE | estado nativo de última cotización futuro/inconsistente frente a UTC y consulta acotada; origen servidor/caché pendiente de captura MQL |
| TEMPORAL_CAUSALITY | PASS — invariantes de entrada y rechazo implementados/probados; no certifica el reloj del broker |
| CAUSAL_AUDIT | FAIL — evidencia nativa incompleta |
| SESSION_CALENDAR | PASS_WITH_RUNTIME_GUARD |
| DISCOVERY_VALIDATION | BLOCKED |
| FINAL_TEST | LOCKED |
| DEMO | DISABLED |
| LIVE_TRADING | false |
| HARD_BLOCKER | ejecutar MainKNativeParity en XM para obtener CSV/resultado y relojes MQL5 |
| NEXT_STATE | HARD_BLOCKER_NATIVE_PARITY_AND_CLOCK_EXPORT_PENDING |

Estos estados sustituyen los checkpoints operativos anteriores. No se declara PASS por compilar un script ni por validar un ejemplo Python. No se abrió Validation, FINAL_TEST ni ningún outcome de la cohorte futura. No se generaron hipótesis ni se calcularon resultados de trading.

## 1. La estrategia congelada y el error auxiliar

README y productor histórico especifican Stochastic 5/3/3, SMA, Low/High, MAIN_K por defecto, BUY anterior <=20 y actual >20, SELL anterior >=80 y actual <80. No se sustituyó esa definición por una fórmula de un ejemplo.

`StochasticBarDecisionResearchEA.mq5` crea directamente el handle nativo:

```mql5
stoch=iStochastic(sym,PERIOD_M5,K_PERIOD,D_PERIOD,SLOWING,MODE_SMA,STO_LOWHIGH);
```

Los parámetros constantes son 5, 3, 3. El helper de producción `Buffer` marca el array como serie y usa `CopyBuffer(handle,buffer,1,n,a)`: MAIN_K sale del buffer 0 de la última barra cerrada, no de una fórmula manual. `ResearchSignal` conserva las igualdades/inequidades congeladas. Los cinco hashes de fuentes registrados en la prueba causal aceptada siguen coincidiendo; no se editó ningún `.mq5/.mqh` del productor.

La [documentación de iStochastic](https://www.mql5.com/en/docs/indicators/istochastic) distingue K, D, slowing, método de medias y campo de precios; MAIN_LINE es el buffer 0. El nombre `MODE_SMA` no justifica reemplazar arbitrariamente el MAIN_K nativo por una media de Fast %K.

El contrato auxiliar sellado `future_cohort_metadata_spec.json` y `future_cohort_health.py` sí describen/calculan una media aritmética de tres Fast %K. El ejemplo estándar instalado de MT5, por el contrario, suma primero los términos close-minus-low y high-minus-low de las tres ventanas y calcula su cociente. Esas operaciones no conmutan cuando cambian los rangos.

Contraejemplo ya preservado: numeradores 9, 1, 1 y rangos 10, 100, 100. Media de porcentajes: 30.6666667; cociente de sumas por 100: 5.2380952. En ventana plana, el ejemplo devuelve 100 frente al 50 del metadata auxiliar. Esto identifica un error de metadata/documentación respecto de la estrategia nativa congelada, no un mandato de cambiar el productor para coincidir con un ejemplo.

El adaptador sintético legado `tests/mql5/SnapshotCausalProbe.mq5` también implementa `ProbeK` como media de Fast %K. Su prueba aceptada es una comprobación finita de invariancia ante perturbaciones futuras con indicadores sustituidos; no demuestra paridad de la fórmula nativa. No se reescribió ese fixture histórico ni se reinterpretó silenciosamente su alcance.

### Contraste con señales aceptadas

Se seleccionaron las primeras 64 filas de features/trigger del run TRAIN 2024 aceptado `r20261016T155802_b5bf64eb`, sin ordenar por resultados ni inspeccionar PnL. MAIN_K, parámetros 5/3/3, lados BUY/SELL y cruces congelados concuerdan. `feature_max_time_msc <= signal_time_msc` pasa en las 64 filas.

Se solicitaron únicamente barras OHLC de contexto permitido, entre 2023-12-28 y 2024-01-04, incluyendo la prehistoria necesaria para el primer K anterior después de Año Nuevo. No se usaron las advertencias de calidad de 2023 para investigación ni se rehabilitó ese bloque. Son 1,104 barras de diagnóstico para reconstruir ventanas del indicador, no un dataset nuevo.

Los **128 valores** MAIN_K actual/anterior registrados por producción nativa histórica coinciden con la referencia de cociente de sumas: error absoluto máximo **2.842170943040401e-14**, dentro de la tolerancia técnica fija **1e-10**. La aproximación antigua del metadata difiere hasta **13.77381051482606** puntos. El auditor del run aceptado registra terminal build **6257**, igual al build observado en la instancia diagnóstica.

La comparación usa OHLC consultado actualmente al broker y valores nativos ya archivados: es evidencia histórica fuerte de semántica, pero no sustituye los fixtures nativos controlados ni afirma que se haya rehecho toda la historia. La proyección CSV seleccionó sólo campos de feature/trigger; el SHA-256 del archivo completo se leyó únicamente para integridad. No se calcularon outcomes.

**Impacto: NONE.** No hay evidencia de implementación histórica errónea que justifique reconstruir datasets. Los archivos aceptados, sus hashes y la estrategia se preservan. Una corrección documental versionada y una especificación v2 **preparada, no activa** explicitan la semántica nativa; la especificación sellada original no fue editada, re-firmada ni activamente sustituida.

## 2. Prueba nativa reproducible preparada

`python/main_k_native_parity.py` extrae del productor real la expresión del constructor y el helper `Buffer`, y copia el core de señales sin modificarlo. La plantilla `tests/mql5/MainKNativeParity.mq5` aplica el mismo OHLC a:

1. La ruta de handle/lectura extraída de producción.
2. Un handle nativo separado creado con `IndicatorCreate(...,IND_STOCHASTIC,5,pars)` y parámetros explícitos 5/3/3, MODE_SMA, STO_LOWHIGH.
3. Un oráculo independiente Python de cociente de sumas que valida la exportación posterior.

El bloque se inyecta exclusivamente en símbolos custom `LABPK_<nonce>_<caso>`, separados de US30Cash y de todos los datasets. Cada fixture contiene 193 barras M5, construidas mediante 965 barras M1 sintéticas; el script comprueba que la agregación OHLC recibida coincide con la entrada. Se comparan las 192 barras cerradas, MAIN_K y D, orientación/shift, y cruces del core. Las primeras seis filas se identifican como warmup, sin forzar una paridad de oráculo donde aún falta lookback.

Las cinco familias son tendencia, rango, extremos/rangos variables, igualdad de niveles 20/80 y warmup/ventanas planas. Se perturba sólo la última barra excluida por shift 1 para comprobar que las lecturas cerradas no cambian. La tolerancia absoluta fija es 1e-10; el validador rechaza cambiarla, resultados ausentes, entradas modificadas, fuentes distintas, filas duplicadas/faltantes y dos cálculos que coincidan entre sí pero difieran del oráculo.

El script además exporta `TimeCurrent`, `TimeTradeServer`, `TimeLocal`, `TimeGMT`, `TimeGMTOffset`, `TimeDaylightSavings` y `MqlTick.time/time_msc` de US30Cash antes de los cálculos sintéticos. No tiene API de órdenes, no requiere credenciales, no modifica horarios ni cierra el XM activo.

Despliegue final preparado: **Scripts → ResearchDiagnostics → pk_41a2e93f → MainKNativeParity**. Compilación del MetaEditor de XM: **0 errores, 0 warnings**. Hash del harness: `5d8e5b06d8eaae90e6e7a9ba6e7a931f07a540b8e9b10a3cccd47ba934ae2075`; EX5: `a4e7a00d4dd0ad617a566a04a65eeb6c21a1cb8a0e1f06645ca95f0356bac0d2`.

Todavía no existen `pk_41a2e93f_native.csv`, `pk_41a2e93f_result.json` ni `pk_41a2e93f_clock.json` en los Files de XM. Por tanto **MAIN_K_PARITY no puede marcarse PASS**. Los tests del parser fabrican datos explícitamente dentro de directorios temporales y no cuentan como ejecución MT5.

### Por qué hace falta iniciar el script manualmente

El helper de Windows devolvió `FrameArrived timed out` y, tras recuperar la ventana, `window capture timed out`. La accesibilidad no devolvió controles utilizables. Los MCP oficiales de terminal y MetaEditor devolvieron HTTP 401 con la configuración existente; no se alteró autenticación ni se eludió esa frontera.

También se intentó una copia portátil aislada, sin cuentas/credenciales. El journal confirmó carga del script, pero nunca produjo archivos de ejecución. Una carga no equivale a ejecutar OnStart. Las dos instancias portátiles propias se terminaron comprobando antes que PID/executable pertenecían al directorio de diagnóstico; no se detuvo el XM del collector. No se volvió a ejecutar SessionCalendarProbe.

El paso pendiente es iniciar el script ya instalado. Los resultados se leerán localmente; no hace falta copiar información de cuenta ni subir capturas.

Reproducción: usar `build_harness(folder, run_id, terminal_root=verified_data_folder)`, compilar el source generado con el MetaEditor emparejado, iniciar ese script y validar mediante `validate_native_result(folder, run_id, data_root=verified_data_folder/'MQL5/Files', terminal_root=verified_data_folder)`. La CLI ofrece los subcomandos `build` y `validate` con esos paths. Cada ejecución exige un nonce nuevo para no sobrescribir resultados anteriores.

## 3. Timestamp futuro: hechos y límites de la causa

El diagnóstico se hizo contra la API nativa instalada MetaTrader5 5.0.5572, conectada al XM verificado DEMO. `symbol_info_tick` es una función nativa builtin, no el fixture de un test. Se compararon enteros Unix en milisegundos antes de cualquier formato de pantalla.

En tres consultas posteriores, la última cotización de US30Cash siguió siendo:

- `time = 1792799997` segundos.
- `time_msc = 1792799997469` milisegundos.
- Instante UTC interpretado explícitamente: `2026-10-23T23:59:57.469Z`.
- Consulta UTC alrededor de `2026-10-23T10:24:34Z`; diferencia máxima medida **48,923,330 ms**.
- Latencia de las tres lecturas: 2, 0 y 0 ms.

Segundos y milisegundos concuerdan exactamente por truncamiento. No es un error de multiplicar/dividir por 1000. La diferencia existe en los enteros antes de usar `datetime`, de modo que no es una mera conversión de presentación local/UTC. El reloj Windows usa Central con offset de presentación -05:00 en la observación; la referencia UTC del orquestador fue `10:24:28Z`, coherente con la consulta posterior. El servicio Windows Time no estaba iniciado; no se cambió el reloj ni se afirmó una atestación NTP.

Una consulta separada de `copy_ticks_range` entre `10:01:00.813Z` y `10:01:05.813Z` devolvió nueve ticks de US30Cash; su máximo fue `10:01:04.541Z`. El accessor de última cotización permaneció en `23:59:57.469Z` antes y después. El mínimo de la consulta estuvo 657 ms antes del límite inferior pedido, compatible con granularidad a segundos: cualquier uso futuro de esos datos necesitaría filtrar el intervalo exacto en milisegundos. Esta consulta fue sólo diagnóstica y no reemplazó la fuente de decisiones.

La [API documenta los timestamps de ticks/barras como UTC](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py). No se aplicó ningún ajuste horario para hacer pasar el dato. La persistencia del mismo valor y latencias de milisegundos descartan que la diferencia de horas se deba simplemente a tomar el reloj antes de terminar una lectura asíncrona. Sí se corrigió por separado ese detalle técnico: el diagnóstico de runtime fija su instante de decisión **después** de las lecturas/IPC, evitando falsos positivos pequeños por latencia normal.

Clasificación actual: **C, cotización future-dated en el estado de última cotización expuesto por la API nativa**, inconsistente con el reloj de consulta y con su historial acotado. Se pone en cuarentena. Esto no afirma conocer aún el origen físico del valor en el servidor/caché ni que el mercado haya negociado en el futuro: faltan los relojes MQL de la ejecución preparada. [TimeCurrent](https://www.mql5.com/en/docs/dateandtime/timecurrent) representa tiempo de la última cotización; [TimeTradeServer](https://www.mql5.com/en/docs/dateandtime/timetradeserver) es calculado en el cliente; [TimeGMT](https://www.mql5.com/en/docs/dateandtime/timegmt) depende del reloj/configuración local. No son intercambiables como prueba independiente de UTC.

## 4. Invariante temporal implementado

`python/temporal_causality.py` define dos contratos separados:

- Inputs al decidir: `feature_max_time_msc <= decision_time_msc`, `quote_time_msc <= decision_time_msc`, edad de quote entre 0 y 5,000 ms. Igualdad está permitida; +1 ms futuro se rechaza. Se exige timezone explícito para convertir datetime y se conserva aritmética entera de milisegundos.
- Fills de replay: llegada estrictamente después del cutoff; fill en secuencia posterior a la llegada; timestamp del fill >= timestamp de llegada + latencia. Con latencia cero se permite el mismo milisegundo si la secuencia es posterior, como exige el replay congelado.

Shadow y session guard usan el contrato de inputs. Mantienen además comparaciones datetime exactas para impedir que truncar a milisegundos oculte un futuro submilisegundo; el test integrado rechaza también +1 microsegundo. El gate de features del shadow conserva su restricción previa de entrada `feature_max_time <= signal_time`. No se modificó el replay histórico ni su selección de fills.

Los tests cubren igualdad, +1 ms futuro, +1 microsegundo futuro en shadow, stale quote y borde de cinco segundos, naive timestamps rechazados, offsets explícitos servidor/local y transiciones DST sin reordenar UTC. La cotización futura real sigue rechazada; no se hizo fallback automático a otro precio ni se desplazó su timestamp.

`TEMPORAL_CAUSALITY=PASS` significa que estos invariantes y el fail-closed están implementados y probados. No certifica la corrección del feed o del reloj del servidor. `CAUSAL_AUDIT=FAIL` permanece hasta completar y revisar la evidencia nativa requerida.

## 5. Preservación y verificación

Se conservan sin cambios la estrategia MQL5, los cinco hashes de fuentes aceptados, datasets históricos y sus hashes, el collector sellado, el metadata v1 y ambos protocolos sellados. La corrección de metadata está documentada aparte; `future_cohort_metadata_spec_v2.prepared.json` está preparada pero **no activa**, y no hubo recount de señales de la cohorte ni cambio de gates científicos. La política operativa v2 registra los nuevos hashes de controles temporales; la política v1 permanece intacta.

Collector: activo, XM conectado en DEMO, runtime READY y datos HEALTHY. Las copias diagnósticas aisladas ya no están activas. No hubo scoring de FUTURE_VALIDATION_COHORT, Validation o FINAL_TEST, no se generaron candidatos ni nuevas hipótesis, y no se habilitaron órdenes.

Suite final: **198 tests en 103.318 s, OK; 189 ejecutados correctamente y 9 omitidos por falta de g++**. Compilación del harness nativo: 0 errores/0 warnings. Compileall y revisión de whitespace pasan. Los nueve skips y la falta de exports MT5 no se convierten en PASS por inferencia.

Evidencia machine-readable: [auditoría](../configs/main_k_timestamp_audit_20261023.json), [erratum](../configs/main_k_documentation_erratum_20261023.json), [metadata v2 preparada](../configs/future_cohort_metadata_spec_v2.prepared.json), [política operativa v2](../configs/xm_runtime_session_policy_v2.json), con SHA-256. Paths privados, identificadores de cuenta, credenciales y logs no relacionados no se publican.
