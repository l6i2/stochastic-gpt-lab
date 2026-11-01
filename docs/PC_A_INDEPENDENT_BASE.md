# Base operativa independiente de PC A

**Corte: 1 de noviembre de 2026, 18:47:42 Ecuador.** Se retiran los manifests
antiguos irrecuperables de la ruta **operativa**, sin convertir su ausencia en
un permiso científico. Captura, comparación, preparación y reportes siguen en
PC A; ningún servicio necesita conectarse a la computadora anterior.

Evidencia versionada: `research/studies/pc_a_independent_advance_20261101_v1/`.
No se sustituyen los informes anteriores: se registra la recuperación limitada
y el avance real posterior, incluyendo los primeros ticks de esta captura.

## Recuperación limitada: finalizada

Se enumeraron 536 directorios accesibles bajo Documents/Codex, incluidos los
workspaces anteriores y respaldos del proyecto. Se buscaron nombres de manifests,
índices, checksums e identidad, sin abrir CSV, Parquet ni datasets protegidos.
Hubo cinco candidatos: una plantilla y cuatro manifests diagnósticos propios;
ninguno coincide con los hashes originales buscados. No se encontraron nombres
adicionales de manifests de holdout/reserva ni archivos de proyecto en las
ubicaciones superiores Downloads/Desktop/Documents consultadas.

También se comprobaron las dos ramas remotas, el historial Git completo
alcanzable y los índices públicos GitHub: **cero artifacts, releases y workflow
runs**, sin páginas pendientes. El conector tampoco encontró el split solicitado
ni runs de PR del commit productor. Los respaldos consultados no contienen ZIP
con metadatos recuperables. No se descargaron o abrieron datos protegidos.

| Evidencia buscada | Disposición |
|---|---|
| Split del run `r20261014T070800_6a2dbe02`, hash `be6960e7…` | IRRECOVERABLE_IN_ACCESSIBLE_SEARCHED_SOURCES |
| Identidad original de ese run, hash `65332af3…` | IRRECOVERABLE_IN_ACCESSIBLE_SEARCHED_SOURCES |
| Manifest original del master | Misma disposición; no existe hash original conocido que permita fabricar una recuperación |
| Reserva original del Historical Holdout | Misma disposición; límites y membership siguen desconocidos |
| Manifest original de cohorte 20261019 | Misma disposición; plantilla no equivale a original |
| Envolvente, IDs publicados y referencias conocidas | Derivado identificado, `original=false`, en `derived_legacy_provenance.json` |
| Manifests y frontera de la captura PC A | Retenidos y verificados exactamente contra sus hashes existentes |

**IRRECOVERABLE tiene alcance explícito:** no recuperable desde las fuentes
accesibles examinadas, no una afirmación de inexistencia en toda computadora o
respaldo posible. `work_plan.json` fija `automatic_retry=false`: no repetir la
búsqueda salvo que aparezca una fuente, respaldo o acceso nuevo. El derivado
tiene hash propio y nunca se presenta como manifest original recuperado.

## Captura nueva: identidad, aislamiento y funcionamiento real

ID: `us30cap_15cbddec947f42c98219caa4cec978f2`.
Activación registrada: `2026-10-31T18:33:53.341916+00:00`, equivalente a
13:33:53.341916 Ecuador. Su bracket NTS original es
18:33:52.983025–18:33:53.700806 UTC, condicionado por la incertidumbre declarada
de la referencia. No es certificación del instante físico de generación XM.

Las rutas exclusivas permanecen en
`outputs/new_native_studies/us30cash_m5_native_20261030_01/<capture_id>/` y
`outputs/prospective_derivatives_v1/<capture_id>/`. Manifests, autorización,
frontera, fuente nativa, bytes originales y prefijos crudos/derivados fueron
verificados sin sustituir artefactos anteriores. El manifest de captura conserva
SHA-256 `d6c02812fecf17f6aa3747db50b4cb7fa5a466c8145e98ec37208b80429a571a`.

El prefijo auditado contiene **503 callbacks de quote y 5.961 heartbeats**.
Su membership de fuente comienza en secuencia 139, después del EOF autorizado,
y termina en 6604 en este corte. Las filas de referencia históricas adoptadas
como datos prospectivos son cero; no se heredan warmup, señales ni cohortes.
El número de callbacks de quote no implica igual número de ticks únicos del
broker ni exhaustividad del feed.

Dos muestras reales separadas por 146,49 s mostraron +165 callbacks de quote,
+194 registros crudos y +194 consumidos por el worker. Hay un único worker
propietario, sin duplicados inesperados; la CPU media fue 0,75% de un núcleo.
Working set: 13,64 MB; memoria privada comprometida: 251,89 MB tras cargar la
interfaz MT5. No se confunden ambas medidas ni se afirma un límite de recursos
no medido. Supervisor, watchdog, reportes de madurez y NTS existentes siguen
activos; no se añadió infraestructura, reinicios o servicios nuevos.

La cadena NTS auditada tiene 165 registros. Las dos últimas mediciones periódicas
contienen resultados autenticados; se conserva también la medición previa fallida
y el hueco de supervisión durante suspensión. No se afirma continuidad UTC a
través de ese hueco. La recuperación por reinicio de proceso ya documentada se
conserva; **reinicio físico de Windows sigue sin demostración**, no se provocó uno.

## Cobertura: el bloqueo actual es propio de la nueva captura

Se verificaron diez comparaciones nativas: tres coinciden exactamente en OHLC
y volumen, pero ninguna pasa la igualdad de secuencia BID. Hay ocho M1 y dos M5
rechazados, incluidos los primeros intervalos parciales; cero barras aceptadas,
warmup 0/350 y cero señales admitidas. Las comparaciones conservan las cifras:

| Intervalo nativo | Callbacks BID | Volumen de barra nativa | BID de referencia CopyTicks |
|---|---:|---:|---:|
| M1 1793583600000 | 45 | 45 | 43 |
| M1 1793583660000 | 58 | 58 | 57 |
| M5 1793583600000 | 259 | 284 | 284 |

En M5 falta correspondencia completa de callbacks con la referencia. En algunos
M1, coincidir con volumen/OHLC tampoco resuelve la discrepancia con CopyTicks.
No se atribuye toda diferencia a una sola causa sin evidencia; coalescencia,
snapshots y diferencias de consulta siguen siendo limitaciones relevantes.
**Esperar más tiempo o recuperar manifests antiguos no repara estos intervalos.**
No se rellenaron, no se aceptaron tolerancias ni se sustituyeron callbacks por
ticks redescargados. El worker continúa comparando intervalos futuros y conserva
sus fallos. Los datos crudos, derivados en cuarentena y admitidos siguen separados;
el último conjunto continúa vacío y DATASET_HASH=null.

El monitor contiene 50 hechos: 32 gaps, nueve inicios observados de desconexión
y nueve reconexiones. Se reutilizaron 41 adjudicaciones y solo se analizaron nueve
hechos nuevos o afectados por evidencia OS nueva. Resultado: cinco causas
contribuyentes verificadas, once probables y 34 desconocidas. Todos los gaps
mantienen impacto de cobertura desconocido; conocer una causa no recupera eventos.

## Qué avanza y qué sigue requiriendo decisión científica

`work_plan.json` separa tareas sin dependencia de manifests antiguos: captura
actual, hashes e identidad, comparaciones de barras, preparación causal,
correlación de recepción NTS, incidentes e informes automáticos. Su ejecución
autorizada continúa aunque la recuperación legacy haya terminado sin originales.
No se activa una nueva cohorte ni se cambia la frontera de esta captura.

MAIN_K, whitelist, protocolo, presupuesto y runner futuro permanecen congelados.
Se reutiliza la evidencia causal nativa aprobada, sin repetir probes ni ejecutar
entrenamiento o scoring. Tampoco se afirma que UTC de recepción sea UTC de
generación. Los requisitos 350/800/100 y 200/80/80 no se reducen.

Para admitir un estudio futuro **sin depender del ledger antiguo irrecuperable**
haría falta una decisión explícita sobre una regla de procedencia prospectiva
separada: origen propio verificable, reserva de rol exclusiva hacia adelante,
ningún input legacy/protegido, semillas propias, cobertura demostrada y protocolo
predefinido. Debe dejar intactos los contratos y datos antiguos; no puede cerrar
retroactivamente roles desconocidos. Esta ruta queda preparada como propuesta,
**no activada ni solicitada como autorización de entrenamiento**.

También hay que resolver la completitud de captura necesaria para ambos caminos
TP/SL. Si se propone otra fuente o metodología, su tipo y vintage deberán quedar
separados: una consulta histórica posterior nunca se renombra captura prospectiva
directa ni se usa silenciosamente para backfill. La metodología diagnóstica nativa
aprobada no concede por sí sola admisión científica o certificación UTC externa.

**Resultado:** la operación de PC A ya no espera archivos de la computadora
anterior. La admisión continúa bloqueada por cobertura, madurez, procedencia
temporal y la regla científica vigente. No se modifica esa regla para producir PASS.
20 tests relevantes PASS; hashes y originales preservados.

DISCOVERY_VALIDATION=BLOCKED; HISTORICAL_HOLDOUT=BLOCKED; FINAL_TEST=LOCKED;
DEMO=DISABLED; LIVE_TRADING=false; CAUSAL_AUDIT=FAIL; TRAINING_READINESS=BLOCKED.
