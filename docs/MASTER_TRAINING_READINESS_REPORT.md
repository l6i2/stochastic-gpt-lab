# Resolución integral y preparación del primer entrenamiento

**Corte operativo: 1 de noviembre de 2026, 20:47 Ecuador**
(2 de noviembre, 01:47 UTC de recepción local). Evidencia en
`research/studies/master_training_readiness_20261101_v1/`.

El mercado está enviando quotes reales a la instancia XM DEMO correcta. La
captura y el procesamiento avanzan, pero **el dataset no está admitido y no se
ejecutó entrenamiento**. Se completaron la investigación de los 25 BID faltantes,
el gate único, su bloqueo previo a lectura de datos, el dashboard persistente y
la supervisión del mismo. No se cambió la estrategia, el capturador científico,
los timestamps originales ni los contratos congelados.

## Estado observado, no inferido de procesos instalados

| Campo | Corte verificable |
|---|---|
| BROKER_CONNECTION | XMGlobalSC-MT5 5, DEMO, US30Cash y carpeta activa fijada; conectado |
| MARKET_STATE | Quotes nuevos observados; no se deduce un calendario histórico de esta observación |
| REAL_TICKS_RECEIVED | 4.739 callbacks de quote procesados; no implica 4.739 eventos únicos/exhaustivos del broker |
| M5_COMPLETED | 2 intervalos derivados con igualdad agregada y de secuencia BID; siguen en cuarentena |
| M1_COMPLETED | 33 intervalos derivados en cuarentena |
| MAIN_K_SIGNALS | BUY=0, SELL=0 |
| BUY_SUPPORT / SELL_SUPPORT | 0 / 0 evaluables |
| FEATURE_CAUSALITY | Dos prefijos reales con cutoff/etapas válidos; ninguno tiene las seis features completas |
| NATIVE_BACKTEST_PARITY | PASS retenido para el día diagnóstico autorizado y el oracle sintético; no extrapolado a todo el dataset |
| MEMBERSHIP | Prefijo propio y hashes verificados; independencia/admisión científica pendientes |
| TEMPORAL_PROVENANCE | Orden nativo y NTS de recepción separados; generación XM→UTC sin certificar |
| DATASET_MATURITY | NOT_READY_QUARANTINED |
| TRAINING_ADMISSION_GATE | BLOCKED; cero paquetes admitidos y cero grants reconocidos |
| TRAINING_READINESS | BLOCKED |
| TRAINING_EXECUTED / TRAINING_RESULTS | false / no existen resultados nuevos |
| CAUSAL_AUDIT | FAIL global, sin override |
| COLLECTOR_HEALTH | ACTIVE_DERIVED_QUARANTINED; un worker propietario |
| MEMORY_USAGE | Worker: 15,43 MB residentes y 252,87 MB privados comprometidos; launcher separado, no segundo worker |

Entre muestras separadas por 386,65 segundos aumentaron 365 callbacks de quote,
442 registros crudos y 442 registros consumidos. Cambió el quote cacheado y ambas
muestras estaban conectadas. CPU media del worker: 1,83% de un núcleo. Se verificó
la cadena cruda/derivada, el checkpoint y la retención de versiones/prefijos
anteriores. Esto demuestra procesamiento real hasta los artefactos observados;
**no demuestra todavía crecimiento de señales o madurez científica**.

El historial de barras rechazadas no se borra. Los intervalos válidos continúan
procesándose aunque otros fallen. Los dos M5 aceptados son aislados: cada uno
inicia un contexto de una barra y los rechazos posteriores lo reinician. No son
un warmup continuo de dos barras ni un conjunto de features completo.

## Qué ocurrió con los 25 ticks

Intervalo exacto en **coordenadas nativas originales**, sin mapping UTC:
`[1793583600000, 1793583900000)`.

| Fuente/conteo | Resultado |
|---|---:|
| Snapshots de quote en callbacks | 269 |
| Snapshots con flag BID | 259 |
| Otros snapshots sin flag BID | 10 |
| BID en las dos consultas posteriores de referencia | 284 en ambas |
| Payloads BID de referencia ausentes en callbacks | 25 |
| Payloads BID sobrantes en callbacks | 0 |
| Payloads idénticos repetidos, en cualquiera de las dos fuentes | 0 |

La sesión es única, el orden de secuencia incluyendo heartbeats es continuo y
ningún callback de quote del intervalo declara desconexión. Se identificaron los
25 payloads mediante hashes y coordenadas nativas. Las consultas repetidas son
reproducibles y coinciden con los 284 BID de la referencia original almacenada.
Son consultas posteriores **solo de contraste**, no nuevos eventos prospectivos.
No se rellenó ni modificó la ventana original.

El observador usa `SymbolInfoTick` al atender OnTick: captura el último snapshot,
no una cola exhaustiva de eventos de mercado. MQL5 documenta que no encola otro
NewTick si ya existe uno pendiente o en procesamiento. El handler escribe y
ejecuta FileFlush de forma serial, lo que puede aumentar esa exposición. Esto
demuestra una limitación arquitectónica y un mecanismo compatible con las
omisiones; **no identifica el scheduler/espera exacta de cada payload ausente**.
[Documentación oficial OnTick](https://www.mql5.com/en/docs/event_handlers/ontick).

CopyTicksRange contrasta otra fuente: historial de ticks, con límites inclusivos
en milisegundos. Aquí se consulta hasta `end-1 ms` y se conservan los flags; no
se equiparan cambios ASK con BID ni snapshots con IDs únicos del broker.
[Documentación oficial CopyTicksRange](https://www.mql5.com/en/docs/series/copyticksrange).

No se encontró un defecto del agregador que permita recuperar estos 25 eventos
sin inventarlos o hacer backfill. Tampoco sería defendible prometer exhaustividad
solo por optimizar el FileFlush: la coalescencia de OnTick seguiría existiendo.
Se conserva el observador aprobado y la ventana en cuarentena. No se introduce
una tolerancia de 25 ticks, una redescarga reparadora ni una nueva cohorte.

## Gate único, runner y automatización persistente

`controller/training_admission_gate.py` centraliza la admisión. Tanto el runner
futuro como el dispatcher pasan por él; no hay un permiso alternativo por booleanos.
Las listas de autoridad están vacías. Sin un hash de autorización reconocido se
rechaza **antes de cualquier lectura de dataset**.

Para un grant futuro, verifica namespace admitido, ausencia de symlinks/junctions
que escapen de él, manifest/archivos/hash canónico, identidad del estudio, proofs
de membership/exposure/admisión, cobertura y causalidad del contrato aplicable,
whitelist/protocolo congelados, madurez exacta, presupuesto, código y versiones
Python/NumPy/scikit-learn. REAL o UNKNOWN produce hard fail. El dispatcher vuelve
a comprobar la cuenta DEMO directamente antes del fit y registra un intento
durable exclusivo; no permite retries adaptativos ni exceder el presupuesto.

Admisión de un paquete y autorización de entrenamiento son autoridades distintas.
Un paquete completo reconocido puede producir **una solicitud identificada por
hash**, sin conceder fit/scoring. Hoy no existe ese paquete: no se generó solicitud
ni se pidió autorización prematura. El código no abre Discovery Validation,
Historical Holdout o Final Test ni cambia el CAUSAL_AUDIT global.

El runner preparado mantiene logística L2 C=1, seed 20261030, BUY/SELL separados,
seis features exactas, StandardScaler de TRAIN del fold, missing sin imputación,
FOLLOW/INVERT y p>0,5. Cuatro folds cronológicos purgados por **ambos** exits,
máximo ocho fits, cero fit final global o búsquedas. Conserva baselines FOLLOW e
INVERT y los criterios conjuntivos/bootstrap preregistrados. Árboles, boosting y
secuenciales siguen fuera de este protocolo; no se activaron otros modelos.

Comando preparado para un futuro grant realmente autorizado, **no para ejecutar ahora**:

```powershell
.venv\Scripts\python.exe tools/admitted_training.py --grant configs/scientific_training_grant.json
```

El dashboard local está en `outputs/research_readiness/index.html`, con JSON en
`status.json`; se actualiza cada minuto y refleja los reportes existentes del
worker. Su mutex impide dobles escritores. Un error publica estado bloqueado y
retira cualquier página previa de apariencia aprobada. No necesita otra instancia
de la DLL MT5 ni carga modelos mientras está bloqueado.

El guardian existente ahora supervisa también ese reporter. Se reinició únicamente
el guardian propio para cargar esa integración; MT5, collector y worker siguieron
activos. Una prueba controlada detuvo solo el reporter: el guardian lo recuperó
de PID 17824 a 13020, conservando el worker 7848 y la captura. No se reinició Windows,
no se alteró energía/red/batería ni se tocó el otro proyecto. La recuperación tras
reinicio físico sigue pendiente de un reinicio natural, sin solicitar uno ahora.
Las tareas existentes, watchdog y NTS continúan; se verificaron 183 registros NTS
encadenados. Medición autenticada no equivale a certificación del evento XM.

## Madurez, contrato y evidencia que falta

| Requisito congelado | Progreso válido al corte |
|---|---:|
| Warmup propio continuo | 0/350 — 0% |
| Primeras señales base consecutivas posteriores al warmup | 0/800 — 0% |
| Barras observadas posteriores a la última entrada | 0/100 — 0% |
| Soporte evaluable | 0/200; BUY 0/80; SELL 0/80 |
| Datos científicamente admitidos | 0% |

No existe un porcentaje global ponderado contractual para cobertura, membership,
semillas y causalidad. No se inventa uno: dos barras aisladas no permiten declarar
que el 0,57% del dataset científico esté listo.

La autoridad es `research/studies/us30cash_m5_native_pretrain_v1/PROTOCOL_ES.md`:
primero 350 barras propias y semillas, primeras 800 señales sin selección, 100
barras posteriores y soporte 200/80/80 con tres folds por lado. Cobertura o
continuidad no verificable implica NOT_READY; no se extiende ni selecciona un
periodo por resultados. La captura conserva `protocol_stream_unbroken=false`.
El anexo nativo permite diagnóstico, no convierte la captura en cohorte admitida.

`controller/pretrain_contracts.py::interval_disposition` conserva el rechazo de
roles abiertos/no comparables. Los manifests originales agotaron su recuperación
accesible en la ejecución anterior; no se repitió esa búsqueda ni se reabrió TRAIN.
Su ausencia no detiene captura, agregación diagnóstica o preparación. Si se
necesita una regla prospectiva independiente diferente para un nuevo estudio,
requiere decisión explícita separada; no se cambian contratos congelados aquí.

Orden nativo, disponibilidad declarada, recepción local, NTS y generación física
son afirmaciones distintas. Los dos prefijos reales cumplen cutoff<decisión y
etapa lista antes de decidir, pero carecen de contexto/semillas/features completas
y son derivados del prefijo recibido, no snapshots nativos de features al llegar.
No se exige generación UTC independiente para producir ese diagnóstico; tampoco
se elimina la exigencia de procedencia de un contrato que sí la requiera.
Faltan el vínculo específico XM→UTC, cotas completas de recepción y calendario
histórico exacto. Sesiones XM no se sustituyen por NYSE. Ecuador y New York usan
IANA con DST; la hora XM se muestra como etiqueta nativa, sin offset impuesto.

## Rendimiento histórico conocido, sin nuevas búsquedas

Se reutilizaron exclusivamente los resultados ya autorizados del **2/1/2024**:
28 señales (13 BUY, 15 SELL), ambos caminos virtuales y censura conservada.
La reproducción existente verificó 79.211 quotes, 1.376 M1 y 276 M5. No se abrió
TRAIN agotado, validación o holdouts ni se calculó PnL sobre la captura nueva.

| Diagnóstico | Caminos cerrados | Censurados | PnL virtual cerrado | PF | Win rate | Drawdown proxy |
|---|---:|---:|---:|---:|---:|---:|
| FOLLOW total | 19 | 9 | +472,12 | 1,386 | 52,63% | −393,20 |
| INVERT total | 19 | 9 | −999,06 | 0,455 | 31,58% | −1.052,16 |
| BUY FOLLOW | 9 | 4 | +31,00 | 1,042 | 44,44% | −742,15 |
| SELL FOLLOW | 10 | 5 | +441,12 | 1,915 | 60,00% | −366,19 |

Son unidades virtuales de la estrategia, no rentabilidad monetaria de cuenta.
Drawdown ordena salidas cerradas, no equity mark-to-market. El mismo expediente
conserva MFE/MAE, duración, ATR, volumen y HA descriptivos. MFE/MAE de caminos
censurados son límites observados, no resultados finales. No se usaron para
seleccionar parámetros, modelos o lados. El mejor SELL FOLLOW de ese día **no**
demuestra ventaja robusta, generalización ni autoriza eliminar BUY/INVERT.
Volume Profile/POC/VAH/VAL/HVN/LVN y estructura conservan su revisión causal,
pero no entran a la whitelist actual. Rendimiento por sesión Ecuador/NY del día
nativo es NO DISPONIBLE sin mapping demostrado; no se asignan horarios ficticios.

## Respuestas ejecutivas y siguiente estado

1. **Porcentaje real:** 0% admitido; todos los requisitos de madurez anteriores
   están en 0% válido. Hay dos M5 diagnósticos aislados, no madurez acumulable.
2. **Señales nuevas:** cero BUY y cero SELL, con soporte evaluable cero.
3. **Falta para entrenar:** cobertura/continuidad, contexto y semillas propios,
   madurez, membership, causalidad del contrato, dataset sellado y grant explícito.
4. **Resuelto aquí:** diferencia de contadores y 25 payloads identificados,
   reproducción del contraste, gate único, rechazo previo a I/O, presupuesto antes
   del fit, solicitud condicionada a admisión y dashboard persistente supervisado.
5. **Continúa automáticamente:** captura sin backfill, comparación de intervalos,
   features/señales diagnósticas cuando haya contexto, NTS, guardian y dashboard.
6. **Decisión humana:** ninguna intervención técnica inmediata. Un entrenamiento
   necesitará autorización específica tras completar el paquete; cambiar la regla
   de estudio o la fuente/vintage requerirá otra decisión científica explícita.
   No se solicita ninguna prematuramente.
7. **Conclusión legítima:** existe reproducción diagnóstica de la estrategia
   congelada; el pequeño estudio conocido favoreció FOLLOW ese día. No demuestra
   rentabilidad robusta ni valida un modelo nuevo.

Validación: **498 tests ejecutados, 489 PASS y 9 SKIPPED**; compileall y diff-check
PASS. El ResourceWarning de fastparquet corresponde a un archivo sintético
temporal de test. No se repitieron probes nativos aprobados ni se ejecutaron fits
científicos. Invariantes Stochastic 5/3/3 20/80, entrada siguiente M5,
TP240/SL180/TIME_EXIT100, Bid/Ask y resolución conservadora permanecen intactos.

DISCOVERY_VALIDATION=BLOCKED; HISTORICAL_HOLDOUT=LOCKED; FINAL_TEST=LOCKED;
DEMO=DISABLED; LIVE_TRADING=false; CAUSAL_AUDIT=FAIL; TRAINING_READINESS=BLOCKED.
