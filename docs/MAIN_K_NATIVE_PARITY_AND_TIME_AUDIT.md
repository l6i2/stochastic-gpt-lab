# AuditorÃ­a de MAIN_K y causalidad temporal â€” 2026-10-23

## Actualización posterior de procedencia temporal

La [auditoría de relojes](TIMESTAMP_CLOCK_PROVENANCE_AUDIT.md) identifica la referencia local atrasada frente a tres NTP y tres HTTPS independientes. La hipótesis previa de un tick US30Cash físicamente futuro queda sustituida: su última marca es pasada frente a UTC externo. MAIN_K sigue PASS; reloj operativo y correspondencia nativo/UTC permanecen bloqueados. No se alteran evidencias anteriores.

## ActualizaciÃ³n: ejecuciÃ³n nativa validada

Native execution pk_41a2e93f is now validated: MAIN_K_PARITY PASS, 960 closed-bar rows (930 ready, 30 warmup), five fixtures; maximum independent reference error 1.4210854715202004e-14 at fixed tolerance 1e-10. Historical impact NONE. Native clocks confirm TimeCurrent=quote_time=1792799997, TimeGMT=1792753785, TimeTradeServer=1792760985 (+7200s). The quote is 46,212,469 ms ahead of capture GMT; this is not explained by server/local timezone or units. Feed/cache provenance remains unverified; quote rejection stays fail-closed. TEMPORAL_CAUSALITY PASS; CAUSAL_AUDIT FAIL. SESSION_CALENDAR PASS_WITH_RUNTIME_GUARD; DISCOVERY_VALIDATION BLOCKED; FINAL_TEST LOCKED; DEMO DISABLED; LIVE_TRADING=false. NEXT_STATE HARD_BLOCKER_FUTURE_NATIVE_QUOTE. Evidence: [native validation](../configs/main_k_native_evidence_20261023/validated_audit.json). No dataset, strategy, sealed metadata or earlier evidence was overwritten.

Los apartados siguientes conservan el checkpoint previo como evidencia histÃ³rica; la ausencia de exports ya estÃ¡ resuelta. Sigue pendiente explicar la procedencia del timestamp futuro nativo antes de cerrar CAUSAL_AUDIT. No repetir el script: las llamadas posteriores rechazaron sobrescribir los resultados.

## Checkpoint anterior: previo a la ejecución nativa

| Campo | Estado |
|---|---|
| MAIN_K_ROOT_CAUSE | metadata; el fixture auxiliar legado comparte la aproximaciÃ³n incorrecta para certificar semÃ¡ntica nativa |
| MAIN_K_PARITY | FAIL â€” falta la ejecuciÃ³n nativa de los cinco fixtures, no se observÃ³ un mismatch del productor |
| HISTORICAL_DATASET_IMPACT | NONE â€” productor y datasets aceptados conservados; ninguna reconstrucciÃ³n |
| TIMESTAMP_ROOT_CAUSE | estado nativo de Ãºltima cotizaciÃ³n futuro/inconsistente frente a UTC y consulta acotada; origen servidor/cachÃ© pendiente de captura MQL |
| TEMPORAL_CAUSALITY | PASS â€” invariantes de entrada y rechazo implementados/probados; no certifica el reloj del broker |
| CAUSAL_AUDIT | FAIL â€” evidencia nativa incompleta |
| SESSION_CALENDAR | PASS_WITH_RUNTIME_GUARD |
| DISCOVERY_VALIDATION | BLOCKED |
| FINAL_TEST | LOCKED |
| DEMO | DISABLED |
| LIVE_TRADING | false |
| HARD_BLOCKER | ejecutar MainKNativeParity en XM para obtener CSV/resultado y relojes MQL5 |
| NEXT_STATE | HARD_BLOCKER_NATIVE_PARITY_AND_CLOCK_EXPORT_PENDING |

Estos estados sustituyen los checkpoints operativos anteriores. No se declara PASS por compilar un script ni por validar un ejemplo Python. No se abriÃ³ Validation, FINAL_TEST ni ningÃºn outcome de la cohorte futura. No se generaron hipÃ³tesis ni se calcularon resultados de trading.

## 1. La estrategia congelada y el error auxiliar

README y productor histÃ³rico especifican Stochastic 5/3/3, SMA, Low/High, MAIN_K por defecto, BUY anterior <=20 y actual >20, SELL anterior >=80 y actual <80. No se sustituyÃ³ esa definiciÃ³n por una fÃ³rmula de un ejemplo.

`StochasticBarDecisionResearchEA.mq5` crea directamente el handle nativo:

```mql5
stoch=iStochastic(sym,PERIOD_M5,K_PERIOD,D_PERIOD,SLOWING,MODE_SMA,STO_LOWHIGH);
```

Los parÃ¡metros constantes son 5, 3, 3. El helper de producciÃ³n `Buffer` marca el array como serie y usa `CopyBuffer(handle,buffer,1,n,a)`: MAIN_K sale del buffer 0 de la Ãºltima barra cerrada, no de una fÃ³rmula manual. `ResearchSignal` conserva las igualdades/inequidades congeladas. Los cinco hashes de fuentes registrados en la prueba causal aceptada siguen coincidiendo; no se editÃ³ ningÃºn `.mq5/.mqh` del productor.

La [documentaciÃ³n de iStochastic](https://www.mql5.com/en/docs/indicators/istochastic) distingue K, D, slowing, mÃ©todo de medias y campo de precios; MAIN_LINE es el buffer 0. El nombre `MODE_SMA` no justifica reemplazar arbitrariamente el MAIN_K nativo por una media de Fast %K.

El contrato auxiliar sellado `future_cohort_metadata_spec.json` y `future_cohort_health.py` sÃ­ describen/calculan una media aritmÃ©tica de tres Fast %K. El ejemplo estÃ¡ndar instalado de MT5, por el contrario, suma primero los tÃ©rminos close-minus-low y high-minus-low de las tres ventanas y calcula su cociente. Esas operaciones no conmutan cuando cambian los rangos.

Contraejemplo ya preservado: numeradores 9, 1, 1 y rangos 10, 100, 100. Media de porcentajes: 30.6666667; cociente de sumas por 100: 5.2380952. En ventana plana, el ejemplo devuelve 100 frente al 50 del metadata auxiliar. Esto identifica un error de metadata/documentaciÃ³n respecto de la estrategia nativa congelada, no un mandato de cambiar el productor para coincidir con un ejemplo.

El adaptador sintÃ©tico legado `tests/mql5/SnapshotCausalProbe.mq5` tambiÃ©n implementa `ProbeK` como media de Fast %K. Su prueba aceptada es una comprobaciÃ³n finita de invariancia ante perturbaciones futuras con indicadores sustituidos; no demuestra paridad de la fÃ³rmula nativa. No se reescribiÃ³ ese fixture histÃ³rico ni se reinterpretÃ³ silenciosamente su alcance.

### Contraste con seÃ±ales aceptadas

Se seleccionaron las primeras 64 filas de features/trigger del run TRAIN 2024 aceptado `r20261016T155802_b5bf64eb`, sin ordenar por resultados ni inspeccionar PnL. MAIN_K, parÃ¡metros 5/3/3, lados BUY/SELL y cruces congelados concuerdan. `feature_max_time_msc <= signal_time_msc` pasa en las 64 filas.

Se solicitaron Ãºnicamente barras OHLC de contexto permitido, entre 2023-12-28 y 2024-01-04, incluyendo la prehistoria necesaria para el primer K anterior despuÃ©s de AÃ±o Nuevo. No se usaron las advertencias de calidad de 2023 para investigaciÃ³n ni se rehabilitÃ³ ese bloque. Son 1,104 barras de diagnÃ³stico para reconstruir ventanas del indicador, no un dataset nuevo.

Los **128 valores** MAIN_K actual/anterior registrados por producciÃ³n nativa histÃ³rica coinciden con la referencia de cociente de sumas: error absoluto mÃ¡ximo **2.842170943040401e-14**, dentro de la tolerancia tÃ©cnica fija **1e-10**. La aproximaciÃ³n antigua del metadata difiere hasta **13.77381051482606** puntos. El auditor del run aceptado registra terminal build **6257**, igual al build observado en la instancia diagnÃ³stica.

La comparaciÃ³n usa OHLC consultado actualmente al broker y valores nativos ya archivados: es evidencia histÃ³rica fuerte de semÃ¡ntica, pero no sustituye los fixtures nativos controlados ni afirma que se haya rehecho toda la historia. La proyecciÃ³n CSV seleccionÃ³ sÃ³lo campos de feature/trigger; el SHA-256 del archivo completo se leyÃ³ Ãºnicamente para integridad. No se calcularon outcomes.

**Impacto: NONE.** No hay evidencia de implementaciÃ³n histÃ³rica errÃ³nea que justifique reconstruir datasets. Los archivos aceptados, sus hashes y la estrategia se preservan. Una correcciÃ³n documental versionada y una especificaciÃ³n v2 **preparada, no activa** explicitan la semÃ¡ntica nativa; la especificaciÃ³n sellada original no fue editada, re-firmada ni activamente sustituida.

## 2. Prueba nativa reproducible preparada

`python/main_k_native_parity.py` extrae del productor real la expresiÃ³n del constructor y el helper `Buffer`, y copia el core de seÃ±ales sin modificarlo. La plantilla `tests/mql5/MainKNativeParity.mq5` aplica el mismo OHLC a:

1. La ruta de handle/lectura extraÃ­da de producciÃ³n.
2. Un handle nativo separado creado con `IndicatorCreate(...,IND_STOCHASTIC,5,pars)` y parÃ¡metros explÃ­citos 5/3/3, MODE_SMA, STO_LOWHIGH.
3. Un orÃ¡culo independiente Python de cociente de sumas que valida la exportaciÃ³n posterior.

El bloque se inyecta exclusivamente en sÃ­mbolos custom `LABPK_<nonce>_<caso>`, separados de US30Cash y de todos los datasets. Cada fixture contiene 193 barras M5, construidas mediante 965 barras M1 sintÃ©ticas; el script comprueba que la agregaciÃ³n OHLC recibida coincide con la entrada. Se comparan las 192 barras cerradas, MAIN_K y D, orientaciÃ³n/shift, y cruces del core. Las primeras seis filas se identifican como warmup, sin forzar una paridad de orÃ¡culo donde aÃºn falta lookback.

Las cinco familias son tendencia, rango, extremos/rangos variables, igualdad de niveles 20/80 y warmup/ventanas planas. Se perturba sÃ³lo la Ãºltima barra excluida por shift 1 para comprobar que las lecturas cerradas no cambian. La tolerancia absoluta fija es 1e-10; el validador rechaza cambiarla, resultados ausentes, entradas modificadas, fuentes distintas, filas duplicadas/faltantes y dos cÃ¡lculos que coincidan entre sÃ­ pero difieran del orÃ¡culo.

El script ademÃ¡s exporta `TimeCurrent`, `TimeTradeServer`, `TimeLocal`, `TimeGMT`, `TimeGMTOffset`, `TimeDaylightSavings` y `MqlTick.time/time_msc` de US30Cash antes de los cÃ¡lculos sintÃ©ticos. No tiene API de Ã³rdenes, no requiere credenciales, no modifica horarios ni cierra el XM activo.

Despliegue final preparado: **Scripts â†’ ResearchDiagnostics â†’ pk_41a2e93f â†’ MainKNativeParity**. CompilaciÃ³n del MetaEditor de XM: **0 errores, 0 warnings**. Hash del harness: `5d8e5b06d8eaae90e6e7a9ba6e7a931f07a540b8e9b10a3cccd47ba934ae2075`; EX5: `a4e7a00d4dd0ad617a566a04a65eeb6c21a1cb8a0e1f06645ca95f0356bac0d2`.

TodavÃ­a no existen `pk_41a2e93f_native.csv`, `pk_41a2e93f_result.json` ni `pk_41a2e93f_clock.json` en los Files de XM. Por tanto **MAIN_K_PARITY no puede marcarse PASS**. Los tests del parser fabrican datos explÃ­citamente dentro de directorios temporales y no cuentan como ejecuciÃ³n MT5.

### Por quÃ© hace falta iniciar el script manualmente

El helper de Windows devolviÃ³ `FrameArrived timed out` y, tras recuperar la ventana, `window capture timed out`. La accesibilidad no devolviÃ³ controles utilizables. Los MCP oficiales de terminal y MetaEditor devolvieron HTTP 401 con la configuraciÃ³n existente; no se alterÃ³ autenticaciÃ³n ni se eludiÃ³ esa frontera.

TambiÃ©n se intentÃ³ una copia portÃ¡til aislada, sin cuentas/credenciales. El journal confirmÃ³ carga del script, pero nunca produjo archivos de ejecuciÃ³n. Una carga no equivale a ejecutar OnStart. Las dos instancias portÃ¡tiles propias se terminaron comprobando antes que PID/executable pertenecÃ­an al directorio de diagnÃ³stico; no se detuvo el XM del collector. No se volviÃ³ a ejecutar SessionCalendarProbe.

El paso pendiente es iniciar el script ya instalado. Los resultados se leerÃ¡n localmente; no hace falta copiar informaciÃ³n de cuenta ni subir capturas.

ReproducciÃ³n: usar `build_harness(folder, run_id, terminal_root=verified_data_folder)`, compilar el source generado con el MetaEditor emparejado, iniciar ese script y validar mediante `validate_native_result(folder, run_id, data_root=verified_data_folder/'MQL5/Files', terminal_root=verified_data_folder)`. La CLI ofrece los subcomandos `build` y `validate` con esos paths. Cada ejecuciÃ³n exige un nonce nuevo para no sobrescribir resultados anteriores.

## 3. Timestamp futuro: hechos y lÃ­mites de la causa

El diagnÃ³stico se hizo contra la API nativa instalada MetaTrader5 5.0.5572, conectada al XM verificado DEMO. `symbol_info_tick` es una funciÃ³n nativa builtin, no el fixture de un test. Se compararon enteros Unix en milisegundos antes de cualquier formato de pantalla.

En tres consultas posteriores, la Ãºltima cotizaciÃ³n de US30Cash siguiÃ³ siendo:

- `time = 1792799997` segundos.
- `time_msc = 1792799997469` milisegundos.
- Instante UTC interpretado explÃ­citamente: `2026-10-23T23:59:57.469Z`.
- Consulta UTC alrededor de `2026-10-23T10:24:34Z`; diferencia mÃ¡xima medida **48,923,330 ms**.
- Latencia de las tres lecturas: 2, 0 y 0 ms.

Segundos y milisegundos concuerdan exactamente por truncamiento. No es un error de multiplicar/dividir por 1000. La diferencia existe en los enteros antes de usar `datetime`, de modo que no es una mera conversiÃ³n de presentaciÃ³n local/UTC. El reloj Windows usa Central con offset de presentaciÃ³n -05:00 en la observaciÃ³n; la referencia UTC del orquestador fue `10:24:28Z`, coherente con la consulta posterior. El servicio Windows Time no estaba iniciado; no se cambiÃ³ el reloj ni se afirmÃ³ una atestaciÃ³n NTP.

Una consulta separada de `copy_ticks_range` entre `10:01:00.813Z` y `10:01:05.813Z` devolviÃ³ nueve ticks de US30Cash; su mÃ¡ximo fue `10:01:04.541Z`. El accessor de Ãºltima cotizaciÃ³n permaneciÃ³ en `23:59:57.469Z` antes y despuÃ©s. El mÃ­nimo de la consulta estuvo 657 ms antes del lÃ­mite inferior pedido, compatible con granularidad a segundos: cualquier uso futuro de esos datos necesitarÃ­a filtrar el intervalo exacto en milisegundos. Esta consulta fue sÃ³lo diagnÃ³stica y no reemplazÃ³ la fuente de decisiones.

La [API documenta los timestamps de ticks/barras como UTC](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py). No se aplicÃ³ ningÃºn ajuste horario para hacer pasar el dato. La persistencia del mismo valor y latencias de milisegundos descartan que la diferencia de horas se deba simplemente a tomar el reloj antes de terminar una lectura asÃ­ncrona. SÃ­ se corrigiÃ³ por separado ese detalle tÃ©cnico: el diagnÃ³stico de runtime fija su instante de decisiÃ³n **despuÃ©s** de las lecturas/IPC, evitando falsos positivos pequeÃ±os por latencia normal.

ClasificaciÃ³n actual: **C, cotizaciÃ³n future-dated en el estado de Ãºltima cotizaciÃ³n expuesto por la API nativa**, inconsistente con el reloj de consulta y con su historial acotado. Se pone en cuarentena. Esto no afirma conocer aÃºn el origen fÃ­sico del valor en el servidor/cachÃ© ni que el mercado haya negociado en el futuro: faltan los relojes MQL de la ejecuciÃ³n preparada. [TimeCurrent](https://www.mql5.com/en/docs/dateandtime/timecurrent) representa tiempo de la Ãºltima cotizaciÃ³n; [TimeTradeServer](https://www.mql5.com/en/docs/dateandtime/timetradeserver) es calculado en el cliente; [TimeGMT](https://www.mql5.com/en/docs/dateandtime/timegmt) depende del reloj/configuraciÃ³n local. No son intercambiables como prueba independiente de UTC.

## 4. Invariante temporal implementado

`python/temporal_causality.py` define dos contratos separados:

- Inputs al decidir: `feature_max_time_msc <= decision_time_msc`, `quote_time_msc <= decision_time_msc`, edad de quote entre 0 y 5,000 ms. Igualdad estÃ¡ permitida; +1 ms futuro se rechaza. Se exige timezone explÃ­cito para convertir datetime y se conserva aritmÃ©tica entera de milisegundos.
- Fills de replay: llegada estrictamente despuÃ©s del cutoff; fill en secuencia posterior a la llegada; timestamp del fill >= timestamp de llegada + latencia. Con latencia cero se permite el mismo milisegundo si la secuencia es posterior, como exige el replay congelado.

Shadow y session guard usan el contrato de inputs. Mantienen ademÃ¡s comparaciones datetime exactas para impedir que truncar a milisegundos oculte un futuro submilisegundo; el test integrado rechaza tambiÃ©n +1 microsegundo. El gate de features del shadow conserva su restricciÃ³n previa de entrada `feature_max_time <= signal_time`. No se modificÃ³ el replay histÃ³rico ni su selecciÃ³n de fills.

Los tests cubren igualdad, +1 ms futuro, +1 microsegundo futuro en shadow, stale quote y borde de cinco segundos, naive timestamps rechazados, offsets explÃ­citos servidor/local y transiciones DST sin reordenar UTC. La cotizaciÃ³n futura real sigue rechazada; no se hizo fallback automÃ¡tico a otro precio ni se desplazÃ³ su timestamp.

`TEMPORAL_CAUSALITY=PASS` significa que estos invariantes y el fail-closed estÃ¡n implementados y probados. No certifica la correcciÃ³n del feed o del reloj del servidor. `CAUSAL_AUDIT=FAIL` permanece hasta completar y revisar la evidencia nativa requerida.

## 5. PreservaciÃ³n y verificaciÃ³n

Se conservan sin cambios la estrategia MQL5, los cinco hashes de fuentes aceptados, datasets histÃ³ricos y sus hashes, el collector sellado, el metadata v1 y ambos protocolos sellados. La correcciÃ³n de metadata estÃ¡ documentada aparte; `future_cohort_metadata_spec_v2.prepared.json` estÃ¡ preparada pero **no activa**, y no hubo recount de seÃ±ales de la cohorte ni cambio de gates cientÃ­ficos. La polÃ­tica operativa v2 registra los nuevos hashes de controles temporales; la polÃ­tica v1 permanece intacta.

Collector: activo, XM conectado en DEMO, runtime READY y datos HEALTHY. Las copias diagnÃ³sticas aisladas ya no estÃ¡n activas. No hubo scoring de FUTURE_VALIDATION_COHORT, Validation o FINAL_TEST, no se generaron candidatos ni nuevas hipÃ³tesis, y no se habilitaron Ã³rdenes.

Suite final: **198 tests en 103.318 s, OK; 189 ejecutados correctamente y 9 omitidos por falta de g++**. CompilaciÃ³n del harness nativo: 0 errores/0 warnings. Compileall y revisiÃ³n de whitespace pasan. Los nueve skips y la falta de exports MT5 no se convierten en PASS por inferencia.

Evidencia machine-readable: [auditorÃ­a](../configs/main_k_timestamp_audit_20261023.json), [erratum](../configs/main_k_documentation_erratum_20261023.json), [metadata v2 preparada](../configs/future_cohort_metadata_spec_v2.prepared.json), [polÃ­tica operativa v2](../configs/xm_runtime_session_policy_v2.json), con SHA-256. Paths privados, identificadores de cuenta, credenciales y logs no relacionados no se publican.
