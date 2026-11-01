# Cierre de preparación científica — US30Cash M5

**Corte: 1 de noviembre de 2026, 13:17:55 Ecuador (18:17:55 UTC de recepción local, no certificación UTC del evento XM).**

Se cerraron las tareas técnicas de preparación que podían verificarse con la
evidencia disponible. **No existe todavía un dataset científico admitido ni una
autorización de entrenamiento.** La captura permanece en cuarentena. Esperar
cotizaciones no resuelve por sí solo las lagunas históricas de membership,
la procedencia temporal ni las interrupciones anteriores.

La evidencia de este corte está en
`research/studies/scientific_preparation_closure_20261101_v2/`.
`hashes.json` sella los archivos de este cierre; el manifiesto PC A v37 incorpora
sus hashes y conserva el vínculo con v36. El commit que contiene este informe
identifica el código publicado; `summary.json.code_head` conserva el HEAD base
inspeccionado, no pretende ser el commit que todavía no existía al capturarlo.

## Estado consolidado

| Requisito | Resultado y alcance |
|---|---|
| STUDY_PACKAGE | Hashes del paquete congelado verificados. PRE_TRAIN; evidencia incompleta. |
| EXPOSURE_LEDGER | Índice encadenado de evidencia local reconciliado; conserva las dos ramas originales. Completitud histórica no demostrada. |
| MEMBERSHIP | Prefijos crudos y derivados verificables. Independencia científica todavía no certificada. |
| FEATURE_CAUSALITY | Disponibilidad sintética nativa verificada; semillas y cobertura de captura real pendientes. CAUSAL_AUDIT global sigue FAIL. |
| TEMPORAL_DEPENDENCIES | Seis features de whitelist con dependencias explícitas; doce grupos revisados. |
| STATISTICAL_PROTOCOL | Diseño preregistrado y hashes intactos. Una familia, una configuración, cuatro folds, ocho fits futuros máximos. Cero autorizados. |
| TRAINING_RUNNER_READY | Código futuro y planificación preparados, ejecución bloqueada antes de cualquier lector. No equivale a validación de entrenamiento real. |
| PROSPECTIVE_COLLECTION | ACTIVE_QUARANTINED. |
| M5_PROCESSOR | ACTIVE_QUARANTINED_WAITING_NATIVE_TICKS. |
| DATASET_MATURITY | NOT_READY_QUARANTINED; DATASET_HASH=null. |
| BLOCKERS_REQUIRING_CODE | Ningún defecto demostrado pendiente en la preparación revisada. Integración con datos admitidos y validación estadística futura siguen pendientes antes de autorizar ejecución. |
| TRAINING_READINESS | BLOCKED. |

## Datos e independencia

La captura nueva es `us30cap_15cbddec947f42c98219caa4cec978f2`.
Su inicio autorizado tiene estimación UTC `2026-10-31T18:33:53.341916+00:00`,
13:33:53.341916 de Ecuador, acotada por las mediciones NTS originales
18:33:52.983025–18:33:53.700806 UTC. Es una cota de activación condicionada
por la incertidumbre declarada de la fuente, no la hora certificada de generación
de ticks XM. Se preservaron la manifestación de cierre de la reserva anterior,
los tres registros de decisión y la frontera de inicio real.

`exposure.json` crea una cadena de **referencias** a las diez entradas originales,
las dos extensiones hermanas y los recibos de fuentes. Ambas extensiones tienen
el mismo padre y la misma secuencia original: no se las hizo pasar por una cadena
lineal ni se recalcularon sus hashes. Este índice no convierte evidencia parcial
en una historia de exposición completa.

`membership.json` incorpora los 28 IDs diagnósticos previamente expuestos,
dos IDs censurados publicados como no miembros y su clasificación de cuarentena,
el membership anterior, los recibos de activación y los prefijos actuales.
No se abrieron precios, labels ni resultados de conjuntos protegidos. No se
reclasificaron los dos IDs censurados como una purga confirmada o como datos nuevos.

Los históricos diagnósticos de enero de 2024 son **expuestos**, no independientes.
TRAIN agotado sigue cerrado. Discovery Validation, Historical Holdout y Final
Test conservan sus protecciones. Una redescarga, otro hash o una copia del mismo
evento no crean independencia. Las observaciones postfrontera de la captura
nueva constituyen una reserva prospectiva aislada; **ningún intervalo está
admitido como dataset independiente**. No hay todavía señales o labels propios
que puedan incorporarse a un membership científico sellado.

Siguen faltando los manifests originales de splits y señales del master,
la reserva exacta del Historical Holdout, la reconciliación de roles abiertos y
dominios temporales y la completitud del historial de exposición externo a los
metadatos locales. El cierre autorizado de una reserva concreta no autoriza
cerrar retrospectivamente todos los roles desconocidos del ledger.

## Features y disponibilidad causal

Se reutilizó `nfeat_41d5994c6b84`: tres casos sintéticos de prefijo completo,
prefijo truncado y futuro perturbado, con hashes originales comprobados.
Sus 482 campos se clasifican en 420 con igualdad de prefijos sintéticos,
54 de auditoría ajenos al modelo y ocho temporales UTC en cuarentena.
No se repitió el probe nativo ni se ejecutó otro terminal. El oracle previamente
aprobado de MAIN_K/ATR/HA también se conservó como evidencia de implementación.

| Feature/grupo | Dependencia y límite de la demostración |
|---|---|
| stoch_k / delta_k_1 | MAIN_K 5/3/3 SMA LowHigh, siete/ocho barras cerradas respectivamente. Cruces originales 20/80 intactos. |
| relative_volume_20 | Volumen cerrado actual frente a las veinte barras anteriores: 21 barras. No confundir actividad de ticks de profile con volumen BID nativo. |
| ATR / range_to_ATR | ATR14 nativo y toda su inicialización desde origen propio. Un buffer de 350 barras no prueba aislamiento del seed. |
| ha_direction | Recurrencia HA completa desde semilla propia; Ready a 276 barras. No truncar artificialmente memoria recursiva. |
| Volume Profile / POC / VAH / VAL / HVN / LVN | Ventanas de ticks terminadas en cutoff; las reglas congeladas de bins, desempate y área del 70% se conservan. Prefijo causal no prueba completitud de ticks. No están en la whitelist actual. |
| EMA / tendencia | Barras cerradas y procedencia del seed recursivo; no pivotes futuros. Fuera de whitelist. |
| Estructura / flags de ruptura | El productor congelado incluye la barra actual en max/min: las rupturas estrictas resultan falsas con entradas válidas. Se prueba y documenta, no se redefine. Fuera de whitelist. |
| Horas / sesiones | Ecuador prioritario como display; las features de sesión requieren mapping nativo→UTC demostrado. Fuera de whitelist. |

La decisión exige `source_max <= cutoff < decision`, contexto listo antes de la
decisión y orden de llegada/etapas cuando coinciden timestamps. Se prueban rechazo
de fuentes futuras, semilla previa, contexto corto y disponibilidad tardía.
Las pruebas por grupo son validaciones de sobres de dependencia declarados,
no una certificación de valores reales, cobertura o vintage histórico.

No se detectó un cambio técnico de feature que pudiera aplicarse sin alterar
definiciones congeladas. Redefinir flags de ruptura, agregar VP o cambiar modelos
requeriría una propuesta científica separada; este cierre no lo hace.

## Ejecución futura preparada y bloqueada

`controller/scientific_preparation.py` prepara un plan con seis columnas exactas,
modelo logístico congelado y ocho slots BUY/SELL separados en cuatro folds.
Reutiliza el plan cronológico existente: ambos exits deben preceder estrictamente
la frontera; igualdad se purga y censura no se rellena.

`controller/native_study_runner.py` contiene el cuerpo futuro de ejecución y
verificación de aceptación. La lista de hashes de autorizaciones está **vacía**:
toda llamada actual falla antes del lector de datos y del registro de intento.
No hay CLI de entrenamiento, autoactivación ni acceso a rutas históricas.
Los booleanos enviados por un llamador no constituyen permiso.

El cuerpo preparado conserva StandardScaler entrenado solo en cada fold,
desviación poblacional, escala cero a uno, logística L2 C=1 y seed 20261030.
Sin imputación: no finitos no ajustan y en evaluación reciben FOLLOW fijo;
p>0,5 implica FOLLOW, el resto INVERT. Una clase ausente o falta de convergencia
detiene el intento sin cambiar parámetros. No hay fit global final ni búsquedas.

Se preparó el bootstrap pareado de 10.000 resamples y sensibilidad de bloques
451 anclados al primer índice admitido, conservando bloques vacíos y el bloque
final incompleto. Remuestreos vacíos o distribuciones degeneradas no producen
PASS. El verificador exige los cuatro contrastes BUY/SELL × FOLLOW/INVERT,
límites inferiores unilaterales 98,75% >0, soporte 200/80/80, tres folds por lado,
70% de folds positivos, concentración máxima 50% y drawdown máximo 1,2×baseline.

**Preparado no significa autorizado ni validado con datos admitidos.** Antes
de cualquier grant futuro faltan la integración verificable del adaptador de
datos admitidos y del claim durable de intento único, vincular código/entorno y
revisar la validez de inferencia bootstrap bajo la dependencia observada. El
diagnóstico sintético de bloques no demuestra cobertura estadística real.
Nada publica una autorización ni activa un presupuesto al tener código disponible.

## Captura, procesamiento y reportes automáticos existentes

Al muestrear el worker había 5.252 registros procesados; la verificación durable
posterior alcanzó 5.253, todos heartbeats y **cero ticks**. Son cortes sucesivos
de una captura activa, no una discrepancia que deba corregirse. Hay cero M1,
cero M5, cero buckets rechazados, warmup 0/350, BUY=0, SELL=0, señales 0/800 y
barras posteriores 0/100. Admitidos: cero. La secuencia científica no está
demostrada continua: se conservan 99 registros de incidentes; su conteo no es
equivalente a 99 pérdidas independientes de mercado.

Un único worker propietario, PID 13028, consumía unos 9,07 MB de working set y
16,50 MB privados; el pequeño proceso padre es el launcher de venv, no otro
procesador. Los prefijos crudos/derivados, hashes, cursores, versiones anteriores
y checkpoints se verificaron sin detener el collector ni efectuar backfill.
No se afirma recuperación por reinicio físico a partir de esta lectura.

El worker existente ya actualiza `maturity.json` automáticamente con barras,
señales, soporte, incidencias, coverage y membership. Se conserva ese productor;
no se añadieron servicios, tareas de energía, probes manuales ni otro monitor.
El nuevo consumidor de cierre genera un snapshot reproducible de esos reportes:

```powershell
.venv\Scripts\python.exe tools/close_scientific_preparation.py --out outputs/scientific_preparation_<identificador_nuevo>
```

Debe usarse una carpeta nueva. Rechaza sobrescribir informes y cualquier cambio
de umbrales 350/800/100/200/80. Los valores derivados no se sustituyen por barras
históricas de MT5. Mientras no lleguen ticks y barras verificables no se afirma
funcionamiento científico extremo a extremo. No se certifica cierre de mercado
ni ausencia de pérdidas solo por observar heartbeats durante el fin de semana.

## Qué falta y siguiente estado

**Depende de datos nuevos:** ticks propios; M5 completos con paridad y cobertura;
350 barras y semillas propias; 800 señales consecutivas; 100 barras posteriores;
200 evaluables, 80 de cada lado y tres folds evaluables por lado. No se pronostica
una fecha ni se modifican los umbrales.

**No se resuelve esperando datos:** membership histórico incompleto, roles
abiertos/no comparables, procedencia temporal y calendario XM parcial,
adjudicación de gaps existentes y futura validación de ejecución admitida.
Si los gaps impiden cumplir el protocolo, el tiempo adicional no borra ese
hecho ni autoriza mover el inicio. No se reinicia una cohorte automáticamente.

**Validación:** 71 pruebas afectadas PASS, incluidos fixtures sintéticos, reglas
de temporalidad, forks del ledger, rechazo antes de I/O, umbrales de aceptación,
procesador y lectura operativa. Cero fits y cero scoring científicos. No se
repitieron pruebas de instalación, energía ni probes MT5 aprobados. Un primer
intento de invocar la suite del procesador sin `PYTHONPATH=tests` falló al importar
su helper; la ejecución conjunta con esa ruta terminó correctamente, sin cambiar
el código del procesador.

No se crea ni se solicita un paquete nuevo de autorización científica: faltan
requisitos materiales y DATASET_HASH sigue null. Se preserva la plantilla antigua
como PRE_TRAIN no lista. El próximo estado es continuar la captura y los informes
en cuarentena, conservar incidentes y completar procedencia antes de admisión.

DISCOVERY_VALIDATION=BLOCKED; HISTORICAL_HOLDOUT=BLOCKED; FINAL_TEST=LOCKED;
DEMO=DISABLED; LIVE_TRADING=false; CAUSAL_AUDIT=FAIL; TRAINING_READINESS=BLOCKED.
Estrategia, contratos, datasets originales, timestamps y otro proyecto intactos.
