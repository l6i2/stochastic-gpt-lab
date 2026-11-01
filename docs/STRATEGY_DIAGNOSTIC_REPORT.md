# Informe diagnóstico de la estrategia Stochastic M5

**Fecha: 1 noviembre 2026, referencia principal America/Guayaquil.** Estado: investigación diagnóstica y PRE_TRAIN; ningún candidato, entrenamiento o scoring nuevo. La conclusión útil es doble: el productor y replay nativos son reproducibles para el día autorizado, pero los estudios anteriores no demostraron una ventaja robusta y no autorizan seguir buscando sobre TRAIN agotado.

## 1. Qué datos podemos usar y qué queda cerrado

| Fuente | Clasificación actual | Uso en este informe |
|---|---|---|
| Diagnóstico nativo 2024-01-02, dos runs sellados | Expresamente permitido para diagnóstico, ya expuesto; no independiente | Revisión de hashes, replay fijo y descripción de 28 señales/56 caminos |
| Histórico original de 79.211 ticks del mismo día | Evidencia técnica conocida; una redescarga no lo vuelve independiente | Se usan los outputs nativos ya sellados, sin descargas nuevas |
| stochastic_master_v1, 20.422 señales declaradas | Fuente mixta con tail protegido; no abrir completo | Solo docs/DATASET_FREEZE.md y metadata publicada |
| TRAIN purgado 12.243 / quality-v1 elegible 11.714 | TRAIN agotado, poblaciones relacionadas no intercambiables | Solo informes publicados; cero búsquedas nuevas |
| Discovery Validation, 4.077 declarados | Bloqueado por posible contaminación y falta de runners íntegros | Únicamente resultados ya publicados, sin releer sus filas |
| Historical Holdout | Bloqueado; membership exacto incompleto | NO DISPONIBLE para análisis |
| Final Test | LOCKED; puede existir como tail del master aunque no haya archivo separado | Ninguna lectura |
| Reserva us30cash_m5_future_20261019_v1 | Cerrada a nuevas incorporaciones científicas; originales retenidos | No se adopta ni se puntúa |
| Nueva captura us30cap_15cbddec947f42c98219caa4cec978f2 | Observacional QUARANTINED, no dataset admitido | Solo conteos/estado, nunca outcomes |

El anexo nativo aprobado autoriza diagnóstico separado, no cambia contratos UTC ni permite cohortes o entrenamiento. La excepción de lectura está limitada al día fijo conocido y a sus hashes; no es permiso para recorrer el resto del TRAIN. No se abrieron conjuntos protegidos ni se cargaron modelos históricos o CSV mixtos para generar esta revisión.

## 2. Estrategia inmutable y reproducción comprobada

US30Cash M5, MAIN_K de iStochastic 5/3/3 SMA Low/High. BUY anterior <=20 y actual >20; SELL anterior >=80 y actual <80. Entrada en el primer tick observado de la siguiente barra, manteniendo ambos caminos virtuales FOLLOW/INVERT. TP=240, SL=180, TIME_EXIT=100 barras observadas. Se conserva precedencia de barreras, Bid/Ask y spread. No son 500 minutos garantizados; no se rellenan sesiones sin barras.

Ahora se revalidó Python contra los outputs nativos permitidos: **79.211 quotes; 56 caminos; 3.279 llegadas; 1.376 M1 y 276 M5 iguales en OHLC; 268 cierres MAIN_K comparables, error máximo 1,421e-14** bajo la cota 1e-10 ya aprobada. Los ocho artifacts de investigación de los dos runs siguen idénticos byte a byte. La señal inicial cuyo K anterior necesita historia previa se conserva; no se cuenta como demostración de seed independiente dentro de ese día.

No se repitió un tester ni se optimizó ningún periodo. Se reejecutó el replay Python sobre el tape fijo y se verificaron los hashes de la pareja MT5 original. La paridad es del **exportador virtual congelado frente a Python**, no del motor de fills de órdenes de MT5 ni de una cuenta real. La certificación UTC externa y el calendario completo siguen pendientes. Plan reproducible y hash-bound: [reproduction_plan.json](../research/studies/strategy_diagnostic_preparation_20261101_v1/reproduction_plan.json).

## 3. Rendimiento descriptivo del día autorizado

Hay **13 señales BUY y 15 SELL**. La tabla usa el lado original de señal: FOLLOW lo conserva e INVERT lo invierte. PnL, MFE, MAE, TP/SL y drawdown se expresan en **unidades de precio**, no dinero, porcentaje de retorno ni equity real. Spread incluido; sin añadir comisión, swap, lotaje o slippage no modelados. Las posiciones virtuales pueden solaparse.

| Lado original | Modo | Señales | Cerrados | Censurados | PnL medio cerrados | Suma cerrados | PF cerrados | DD proxy por salida |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ALL | FOLLOW | 28 | 19 | 9 | 24.85 | 472.12 | 1.386 | -393.20 |
| ALL | INVERT | 28 | 19 | 9 | -52.58 | -999.06 | 0.455 | -1052.16 |
| BUY | FOLLOW | 13 | 9 | 4 | 3.44 | 31.00 | 1.042 | -742.15 |
| BUY | INVERT | 13 | 9 | 4 | -25.28 | -227.54 | 0.684 | -660.34 |
| SELL | FOLLOW | 15 | 10 | 5 | 44.11 | 441.12 | 1.915 | -366.19 |
| SELL | INVERT | 15 | 10 | 5 | -77.15 | -771.52 | 0.306 | -931.50 |

El drawdown es una curva descriptiva de PnL realizado virtual, ordenada por instante de salida y orden de señal en empates; **no** es mark-to-market ni drawdown de una cuenta con capital, costes y margen. No se suman drawdowns por lado para obtener el agregado.

FOLLOW acumula +472,12 en sus 19 caminos cerrados frente a −999,06 de INVERT, con nueve censurados por modo. No se convierten los censurados en cero ni se ocultan: la rentabilidad final de esos caminos es desconocida. Tampoco se presentan 19/19 como idéntica población: **solo 18 señales tienen ambos caminos completos** (9 BUY y 9 SELL). En esa intersección, la diferencia media FOLLOW−INVERT es +81,74; BUY +28,73 y SELL +134,75. Es descripción de un día, sin prueba de efecto general ni selección de subgrupos.

| Lado | Modo | MFE media observada, todos | MAE media observada, todos | Duración media cerrados, barras | TP | SL | TIME_EXIT | END_OF_DATA |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ALL | FOLLOW | 108.07 | 88.52 | 66.63 | 6 | 6 | 7 | 9 |
| ALL | INVERT | 90.28 | 104.17 | 68.11 | 3 | 9 | 7 | 9 |
| BUY | FOLLOW | 96.57 | 92.30 | 57.56 | 3 | 4 | 2 | 4 |
| BUY | INVERT | 103.69 | 101.41 | 70.67 | 2 | 3 | 4 | 4 |
| SELL | FOLLOW | 118.04 | 85.25 | 74.80 | 3 | 2 | 5 | 5 |
| SELL | INVERT | 78.65 | 106.56 | 65.80 | 1 | 6 | 3 | 5 |

Las excursiones de caminos censurados son solo lo observado hasta el corte, no sus máximos finales. La duración no se transforma a minutos usando una regla fija. La media ATR del día es 17.49 (rango 4.68–42.04); relative_volume_20 medio 1.015 (rango 0.160–3.893). No se eligieron regímenes, bins o reglas basándose en esos valores.

## 4. Qué conocemos de estudios anteriores y estabilidad

Estas cifras se transcriben de informes publicados, no de una reapertura de sus datasets:

| Estudio/documento | Resultado documentado | Conclusión conservada |
|---|---|---|
| QUALITY_DIRECTION_MODEL_REPORT, 16 octubre | Validation FOLLOW media −3,81/PF 0,946; INVERT −8,52/PF 0,883. Logística −14,13/PF 0,813; RF −7,86/PF 0,891; HGB −9,90/PF 0,864 | Ningún modelo superó FOLLOW; discriminación próxima a azar; rechazados para promoción |
| Dynamic EXIT TRAIN | Solo 2/4 folds positivos; fold principal 69,7% del efecto positivo | No candidato, pese a mejoras pooled puntuales |
| R2/R3/R4 | 0/8, 0/4 y 0/4 hipótesis supervivientes | Las 16 fallaron el conjunto completo de gates |
| V2 entry spread/ATR router | BUY n=3.641, 3/4 folds positivos, concentración de bloque 79,7% y sesión 70,1%; SELL n=4.036, 2/4 folds, concentración de fold 69,5% | Rechazo final; pasar un gate no rescata el resto |

Los IC por señal documentados de V2 incluyen cero: BUY [−2,85; 7,75], SELL [−0,81; 5,69]. La sensibilidad de latencia pasó, pero no resolvió concentración ni inestabilidad. Su DD proxy −37.092,63 frente a −42.263,14 del baseline pasó su gate; no compensó los otros fallos ni equivale a equity real. No hay un informe separado de estabilidad mensual para esa familia: **NO DISPONIBLE**, sin inferirlo de sesiones/bloques.

**Diferencia BUY/SELL:** en el día fijo SELL FOLLOW aportó más PnL cerrado que BUY FOLLOW; en V2 BUY pasó consistencia de folds pero falló concentración y SELL falló dirección de folds y robustez de umbral. Son preguntas y poblaciones distintas. No justifican operar solo SELL por el día positivo, rescatar BUY de V2, invertir toda señal o combinar resultados de estudios para fabricar un candidato.

El incidente de aislamiento permanece POTENTIAL/CANNOT_CLOSE, no «contaminación demostrada» ni «validación limpia». Sus métricas históricas publicadas no autorizan nuevos accesos. No se crea una hipótesis número 18 ni se reabre TRAIN agotado. Un día positivo tampoco contradice por sí solo los resultados negativos o inestables de muestras más amplias.

## 5. Sesiones: Ecuador primero, sin inventar conversión histórica

Rentabilidad por hora Ecuador/Nueva York o por sesiones XM del histórico: **NO DISPONIBLE CON MAPPING CERTIFICADO**. El productor histórico contiene offsets configurados y etiquetas de sesión; no se convierten aquí en evidencia independiente ni se desplazan timestamps originales para generar nuevos agrupamientos de PnL.

El módulo IANA aprobado se reutiliza únicamente para referencias de visualización. La sesión regular nominal NYSE es 09:30–16:00 Nueva York ([fuente oficial](https://www.nyse.com/trade/hours-calendars)). En Ecuador: **09:30–16:00 en EST** y **08:30–15:00 en EDT**; los ejemplos de enero/julio se guardan con tzdata y cuatro vistas, XM=null sin mapping. No son horarios operativos certificados de US30Cash ni ajustan festivos o cierres anticipados del broker. No se rediseñó el módulo horario.

## 6. Revisión causal de features

| Grupo | Disponibilidad exigida | Límite/evidencia actual |
|---|---|---|
| Stochastic | Buffer nativo shift 1, cierre anterior; anterior/actual y orden de llegada | Paridad nativa retenida y revalidada; MAIN_K ratio de sumas, no media de Fast K |
| Tick volume / relativo | Barra cerrada; relativo con 20 barras anteriores y denominador válido | BID updates para volumen de barra; no es volumen real negociado |
| Volume Profile | Todos los ticks de ventana hasta cutoff; sin ticks futuros ni relleno | `available_coverage_unverified` no certifica completitud |
| POC | Centro de bin de máxima masa; empate a precio inferior | Regla fija, no nivel elegido por rendimiento |
| VAH/VAL | Área contigua desde POC hasta al menos 70% de masa, ties congelados | Ventana cerrada y origen de bins deben demostrarse |
| HVN/LVN | Vecinos discretos dentro de la misma ventana; sin suavizado añadido | Faltantes preservados; no niveles «óptimos» seleccionados |
| Heikin Ashi | Recurrencia completa desde seed propio, ready a 276 | Tener 350 barras no autoriza truncar la memoria recurrente |
| ATR | iATR(14)/semántica nativa, historia y seed vinculados | Paridad sintética aprobada; seed vivo independiente aún pendiente |
| EMA 20/50/100/200 | Barra cerrada, buffer shift 1 y seed inicial trazable | Un buffer de 350 barras no demuestra independencia del seed |
| Tendencia | Pendientes/alineación de EMAs cerradas | No es una hipótesis permitida automáticamente en el estudio nuevo |
| Estructura | HH/HL/LH/LL solo con barras cerradas; sin pivotes futuros | Los flags de ruptura tienen degeneración documentada abajo |
| Horarios/sesiones | Evento UTC verificado + IANA; calendario propio del símbolo | No disponibles como predictores certificados con mapping ambiguo |

**Hallazgo concreto sin modificar estrategia:** el exportador calcula `high20=max(high[0:20])` e inmediatamente `recent_high_break=high[0]>high20`; el mínimo es análogo. Para inputs finitos válidos ambos flags resultan falsos por construcción. Es coherente con el cero soporte documentado de la hipótesis de ruptura R4. No se cambió la ventana para «arreglar» el resultado ni se propuso otra regla con TRAIN agotado; cualquier redefinición necesitaría metodología distinta y autorización.

Otro matiz: `tick_activity_bid` del perfil cuenta cada registro elegible con Bid positivo, incluidos updates ASK-only; el volumen de barra reconstruido cuenta flags BID. No se unifican ambas cantidades ni se sustituyen por real_trade_volume_last. El perfil de sesión usa su convención de anclaje server; no prueba calendario NYSE/CME.

Se añadieron pruebas de metadata de disponibilidad para todos los grupos: source_max<=cutoff<decision, ready antes de decision, seed propio cuando es recurrente y mapping demostrado cuando es horario. Un PASS de esa preflight valida solo declaraciones, no bytes reales, cobertura o admisión. Las seis features del estudio actual siguen siendo exactamente stoch_k, delta_k_1, ATR, relative_volume_20, ha_direction y range_to_ATR. Volume Profile, EMA, tendencia, estructura y horario **no entran en el whitelist** por aparecer en esta revisión.

## 7. Código de modelos preparado, ningún entrenamiento

`controller/pretrain_model_preparation.py` prepara objetos **sin fit ni predict**:

- Logística L2 BUY y SELL separados, C=1, lbfgs, max_iter=1000, class_weight=None, seed=20261030; StandardScaler sin ajustar. Sus metadatos de versión, orden de las seis features y parámetros tienen hash. El escalado futuro es solo del TRAIN del fold; cero desviación pasa a 1. No hay imputación; el tratamiento missing fijo permanece en protocolo.
- Random forest y histogram gradient boosting tienen constructores técnicos de propuesta, bloqueados por defecto para el estudio actual. Requieren una especificación explícita y otro prerregistro/presupuesto; no se escogieron hiperparámetros científicos. Los valores pequeños de los tests son fixtures de constructor, no propuestas evaluadas. RF limita n_jobs a 1; boosting impide split aleatorio/early-stopping automático en ese adaptador.
- Secuenciales: interfaz de planificación bloqueada, sin instalar un framework ni crear entrenador. Requieren justificar dependencia secuencial frente a baselines simples, ventanas causales, purga y presupuesto de datos/cómputo en protocolo separado.

Esto no amplía la familia autorizada: **el próximo diseño congelado contiene solo logística**, una configuración, cuatro folds, dos lados y máximo ocho fits planificados. Hoy son cero fits y cero scoring autorizados. Los entrenadores históricos no se invocaron ni importaron para cargar datos. No se reutiliza el presupuesto de familias anteriores.

## 8. Próximo estudio y datos faltantes

Se conserva el plan US30CASH_M5_NATIVE_20261030_01: captura nueva exclusiva; 350 M5 propios con seeds; primeras 800 señales consecutivas sin seleccionar por outcomes; 100 barras observadas posteriores. Soporte mínimo evaluable 200 total, 80 BUY y 80 SELL, tres folds por lado. La captura permanece en cuarentena: **4696 callbacks, 0 ticks y 0 barras M5** en este corte; cero datos admitidos y DATASET_HASH=null. Los gaps ya ocurridos no se borran ni se reinicia silenciosamente la selección para buscar una racha limpia.

El worker y maturity monitor existentes quedan activos; una nueva cotización será procesada sin pedir lanzar otro componente. No se declaró demostrada la ruta de mercado mientras solo hay heartbeats. Se verificó su recuperación automática reciente ante un PermissionError de lectura de collector_status.json; se añadió un reintento limitado exclusivamente a ese estado derivado (hasta cuatro pausas de 20 ms). No usa estado antiguo para pasar un gate ni reintenta hashes rotos; un error persistente, JSON inválido o archivo ausente sigue fallando. El pin nuevo conserva fuentes raw, manifiesto original, artefactos, IDs y cursores; no hubo backfill ni cambio científico.

Faltan membership/splits originales completos, reserva exacta de Historical Holdout, reconciliación de dominios, prueba de no solapamiento de todas las dependencias y cobertura/causalidad/procedencia temporal del nuevo stream. El cierre forward-only de la reserva anterior ya se documentó; no repara retrospectivamente sus memberships. No se infiere independencia de nuevos hashes de una redescarga.

Metodología siguiente: dataset sellado y admitido; separación cronológica; purged walk-forward expandido con ambos horizontes FOLLOW/INVERT unidos por señal; ninguna etiqueta futura cruza la frontera de un fold; escalado aprendido solo del prefijo TRAIN. Cuatro contrastes por lado/baseline con bootstrap por señal y sensibilidad obligatoria por bloques de 451 barras observadas. Permanecen las reglas de rechazo, censura, soporte, concentración y parada preregistradas; no se adaptan tras ver resultados.

## 9. Autorización exacta que faltará

Solo cuando exista un dataset independiente admisible se presentará un paquete con STUDY_ID, DATASET_ID, DATASET_HASH, EXPOSURE_LEDGER_HASH, FEATURE_WHITELIST_HASH, PROTOCOL_HASH, CODE_HEAD, TRAINING_BUDGET y ACCEPTANCE_CRITERIA. La autorización será para **ese dataset y la única ejecución logística preregistrada**, con BUY/SELL separados y hasta ocho fits de folds, sin buscar hiperparámetros ni fit final sobre todos los datos. No se solicita ahora con hashes null.

Árboles, boosting, secuenciales, cambios de whitelist o redefinición de flags requerirían propuesta y autorización científicas separadas antes de cualquier entrenamiento, con datos independientes y presupuesto fijado. Ningún permiso abre automáticamente Discovery Validation, Historical Holdout, Final Test, DEMO o trading. Continúan CAUSAL_AUDIT=FAIL, TRAINING_READINESS=BLOCKED, DEMO=DISABLED y LIVE_TRADING=false.

Evidencias y hashes: [paquete diagnóstico](../research/studies/strategy_diagnostic_preparation_20261101_v1/), [resumen numérico](../research/studies/strategy_diagnostic_preparation_20261101_v1/fixed_day_diagnostic.json), [fuentes revisadas](../research/studies/strategy_diagnostic_preparation_20261101_v1/reviewed_sources.json). Los resultados históricos adicionales citados están en QUALITY_DIRECTION_MODEL_REPORT, INTRATRADE_TRAIN_ROUNDS_REPORT, DYNAMIC_EXIT_TRAIN_REPORT, TRAIN_V2_LOW_MEMORY_BENCHMARK, V2_FAILURE_ANALYSIS e ISOLATION_INCIDENT_AUDIT. Este informe no sustituye ni altera ninguno de esos contratos o resultados congelados.
