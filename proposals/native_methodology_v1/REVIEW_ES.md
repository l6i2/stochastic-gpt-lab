# Revisión final de gobernanza: propuesta de metodología nativa v1

Estado: **DRAFT_NOT_ACTIVE — ninguna modificación de contrato autorizada**.
Base revisada: `ca7bab3d366d6a95575f54b57a923762fb234f5e`.
Fecha de expediente: 2026-10-30, Ecuador (America/Guayaquil); no certifica el reloj del host.

## 1. Contrato original y jerarquía

El inventario `contracts_inventory.json` identifica rutas, hashes de bytes locales,
seals y objetos Git de los contratos, especificaciones, diccionarios e hipótesis.
Los archivos archivados son antecedentes, no permiso para revertir restricciones.
Una mención histórica a “pendiente” o a TRAIN disponible no renueva su presupuesto.
La instrucción vigente añade expresamente Historical Holdout al bloqueo.

| Documento | Obligación que permanece |
|---|---|
| `docs/STRATEGY_SPEC.md`, diccionarios de entrada e intra-trade | MAIN_K nativo 5/3/3 SMA Low/High; BUY <=20→>20; SELL >=80→<80; barra cerrada shift 1; primera cotización de siguiente barra observada; FOLLOW/INVERT, TP240/SL180/TIME_EXIT100; censura y faltantes conservados |
| `docs/RESEARCH_PROTOCOL.md`, `DATASET_FREEZE.md` | Congelar feed/configuración/calendario y dataset; particiones cronológicas por señal, sin shuffle; purgar por horizonte máximo de etiquetas de ambos lados; hipótesis congeladas; no acceso libre a holdouts |
| `INTRATRADE_RESEARCH_PROTOCOL.md`, R2/R3/R4, hipótesis selladas | Selecciones y presupuestos finitos, cuatro folds TRAIN purgados, soporte BUY/SELL, concentración, drawdown y latencias fijas; fracaso no autoriza retuning. El resultado posterior de agotamiento prevalece sobre el antiguo estado inicial |
| `RESEARCH_PROTOCOL_V2.md` y HV2 sellada | Familia y variantes acotadas, cortes ajustados solo dentro de TRAIN del fold, gates conjuntivos; no sustitución de fuentes, nuevas familias ni ronda automática tras no obtener candidato |
| `configs/timestamp_clock_contract_v1.json` | `decision_authority = independently attested UTC, unavailable on this host`; mapping desconocido BLOCK; tolerancia futura cero; quote age máximo 5000 ms; sin correcciones automáticas. **También** define `replay_domain = frozen native event timestamps and sequence; no current wall-clock conversion` |
| `FUTURE_VALIDATION_PROTOCOL.md`, regla de madurez y `PROSPECTIVE_EVALUATION_PROTOCOL.md` | Cohorte separada, comienzo fijo, no backfill ni uso TRAIN; 16 semanas UTC completas / cuatro meses, soporte y cobertura congelados; calendario XM UTC y excepciones verificadas; candidato y evaluación única autorizados separadamente |
| Drift, whitelist v2, shadow y plantillas | Productor común con UTC normalizado verificado; drift feature-only; shadow deshabilitado, sin órdenes; plantillas DRAFT no son candidatos ni autorizaciones |

Los guards activos, manifiestos originales, seals y archivos científicos de esta
tabla no se modifican. Este directorio no está importado por collector, trainer,
evaluator, shadow ni gates de producción. No se escribe un token de autorización.

El inventario distingue bytes de checkout Windows y contenido Git. En varias
hipótesis antiguas el seal verifica el blob Git LF, mientras el archivo local usa
CRLF: `PARTIAL_LOCAL_CRLF_GIT_SEAL_VERIFIED`. No es una alteración semántica, pero
**no es PASS de hash local**. No se normalizan ni re-sellan esos originales. Una
reproducción futura necesitaría artifacts exactos sellados en una copia derivada
separada antes de admisión; esta revisión no ejecuta esos estudios.

## 2. Cambio propuesto exacto y fundamento

**No eliminar UTC de ejecución, cohorte futura, madurez, calendario o drift.**
Proponer un anexo nuevo para **simulación e investigación en dominio nativo**:

> En un estudio nativo expresamente admitido, el orden causal se demuestra con
> fuente congelada, barras cerradas, secuencia de llegada y orden de cálculo.
> La certificación independiente del instante UTC de generación del tick no es
> prerrequisito para ese resultado limitado. Cada afirmación se etiqueta
> XM_NATIVE_ORDER, sin equivalencia UTC, de sesión externa ni de ejecución real.

La frase de `decision_authority` y `unknown_mapping_action=BLOCK` conserva su
vigencia en los consumidores UTC actuales. El cambio sería **de ámbito científico**,
no una corrección del timestamp. La excepción nativa tendría contrato y lector
propios, versionados tras aprobación; no una bandera que relaje el contrato v1.
El replay nativo diagnóstico ya existe en v1: no necesita un nuevo permiso para
las comprobaciones técnicas aquí efectuadas. **Admitir un nuevo estudio o fit sí
requiere metodología y datos/presupuesto autorizados.** Ninguna de estas dos
aprobaciones implica automáticamente la otra.

Fundamento local: `configs/pc_a_native_tester_evidence_20261030/` prueba, para el
único día nativo 2024-01-02, 79.211 cotizaciones ordenadas iguales al archivo
conservado; 1.376 M1 y 276 M5 con OHLC y volumen BID verificados; ocho artifacts
byte-idénticos entre repeticiones y sin interferencia del wrapper. MAIN_K:
268 barras comparadas, 27 señales contrastadas; una señal inicial sin prehistoria
comparable. La tolerancia 1e-10 es la heredada del oracle, no un margen nuevo.
El replay es del **exportador virtual congelado frente a Python**, no del motor
de órdenes/fills MT5. No demuestra rentabilidad, generalización ni UTC físico.

## 3. Cierre M5, disponibilidad y entrada siguiente

En el productor congelado `mt5/StochasticBarDecisionResearchEA.mq5`:

1. Se registra el tick y su índice en la cinta. `iTime(...,0)` detecta cambio de barra.
2. `CopyRates(...,1,...)` y `CopyBuffer(...,1,...)` leen contexto cerrado.
3. Se actualizan HA/perfiles y snapshots con cutoff de la barra cerrada; se procesan
   barreras de posiciones existentes antes de nuevas decisiones discrecionales.
4. La señal se calcula con los buffers cerrados; se verifica la cronología y se
   abren los dos contrafactuales virtuales con Bid/Ask del tick de apertura recibido.

`signal_time_msc=(bar_open+300)*1000-1` es un **límite de datos**, no una medición
de que todos los cálculos finalizaron entonces. La información cerrada se consulta
en el callback siguiente. La simulación coloca feature-ready antes de decisión
dentro de ese callback; no mide duración de CPU ni garantiza ese fill negociable.
Conservar la entrada original como baseline virtual idealizado; no “arreglarla”
moviendo timestamps ni atribuir a una política el precio de antes de calcularla.

Nueva comprobación offline: `python -m proposals.native_methodology_v1.review`.
Reutiliza exclusivamente los artifacts hash-pinned de `diag_fd4e5bf3d468`, sin
ejecutar MT5 ni cargar ningún split. Para **56 entradas** y **3.279 snapshots**
verifica feature_max <= cutoff < callback y que éste corresponde al primer índice
observado de la barra de llegada. Delta etiqueta cutoff→callback **5..49.327 ms**
(49,327 segundos en el extremo superior), no latencia de red ni CPU. Gaps no se
rellenan. Timestamps repetidos conservan índices distintos.

Esto demuestra cronología de llegada y compatibilidad con el orden del código
**en esa simulación**. No demuestra para cada feature su valor bajo todos los
prefijos posibles, la versión del histórico disponible en el pasado, ni el
instante independiente de generación. No convertir el PASS nativo en PASS global.

Para políticas derivadas, mantener ejecución estrictamente posterior al índice de
llegada, más latencia primaria 250 ms y sensibilidades 0/500; aun con latencia cero
un timestamp igual exige índice posterior. Barreras TP/SL/TIME_EXIT prevalecen.
No hay autorización de reversión, modificación de entrada ni optimización.

## 4. Criterios de aceptación propuestos (todos obligatorios)

1. Autorización explícita del anexo, identificada por hash, **y** protocolo del
   estudio con dataset, roles, exclusiones, presupuesto y familia congelados antes
   de ver sus outcomes. Hasta entonces DRAFT_NOT_ACTIVE / TRAINING BLOCKED.
2. Cero solapamiento de signal IDs, intervalos de features/warmup/etiquetas y fuentes
   protegidas con Discovery Validation, Historical Holdout, Final Test o la cohorte
   prospectiva sellada. Manifest de pertenencia completo verificable antes de I/O;
   fecha aparente o nombre TRAIN no bastan. No admitir IDs desconocidos.
3. Identidad exacta de feed/servidor/símbolo/build/modelo, parámetros, prehistoria,
   archivos y hashes reproducibles. El feed actual no se presume equivalente al
   master legacy. No sobreescritura, deduplicación silenciosa ni backfill prospectivo.
4. Todas las filas admitidas pasan dominio/orden, OHLC/quotes válidos, cobertura
   declarada y hashes. Cero features de barra en formación, quote futuro o feature
   disponible después de la decisión. Gaps/errores/censura conservados y auditados;
   ninguna tolerancia temporal. Señales correlacionadas se agrupan para incertidumbre.
5. Prueba del productor real por prefijos y perturbación **solo del futuro**:
   features pasadas byte-idénticas y control positivo de targets futuros alterados.
   Cubrir cierre/apertura, timestamps iguales, gaps, warmup, HA, MFE/MAE, EMA/ATR,
   perfiles y fallos de buffers. La comprobación offline actual no reemplaza esto.
6. Whitelist nueva explícita y grafo de dependencias: excluir UTC_time, NY_time,
   signal_utc_epoch, NY_hour/minute, weekday/session y derivados sin mapping probado.
   Revisar también agrupaciones y métricas por sesión y perfiles anclados. Un perfil
   diario nativo es una convención congelada, no sesión certificada NYSE/XM. Ventanas
   de CopyTicks cerradas no prueban completitud ni vintage histórico.
7. Baseline congelado idéntico y replay independiente; tolerancias numéricas
   heredadas documentadas (MAIN_K 1e-10, replay de precios según validador existente),
   nunca offsets/tolerancias temporales nuevos. Prueba de primer fill admisible,
   precedencia de barreras y latencias fijas sin selección retrospectiva.
8. Diseño estadístico aprobado antes del fit: folds cronológicos purgados por
   horizonte completo de ambas etiquetas, soportes por lado, incertidumbre por
   señal, presupuesto finito, regla de parada, missingness y censura. No inventar
   ahora un mínimo muestral para hacer pasar el día técnico. Los thresholds de
   V2/R2/R3/R4 permanecen ligados a esos estudios y **no se heredan como permiso**.

Fallo de integridad/causalidad → REJECTED o QUARANTINED; falta de evidencia →
NOT_READY/INCONCLUSIVE, nunca PASS por omisión. La aprobación metodológica no
dispensa ninguno de estos requisitos ni abre una evaluación protegida.

## 5. Datos y entrenamientos

**Permitido ahora:** fixtures sintéticos y auditoría/reproducción técnica fija del
día ya autorizado con fuentes selladas. Se pueden revisar código, manifests,
metadatos de gobernanza y hashes sin explorar resultados de conjuntos bloqueados.
No repetir los smokes aprobados: reusar los dos runs publicados, sus logs y hashes.

**Bloqueado:** TRAIN agotado para nuevas familias, modelos, thresholds o búsquedas;
Discovery Validation, Historical Holdout y Final Test incluso como warmup o fuente
de etiquetas; cohorte futura para fitting/tuning/scoring; captura nueva en cuarentena
para entrenamiento. Redescargar TRAIN no crea evidencia independiente.

**Después de aprobaciones y gates:** un fit reproducible de una familia preregistrada
sobre un dataset nuevo realmente no expuesto, asignado exclusivamente al estudio,
con membership sellado, origen/ticks verificables, prehistoria admitida y horizonte
de etiquetas íntegro. Reportar evaluación interna purgada sin tocar holdouts.
Reproducir un fit histórico exacto requeriría recuperar sus artifacts/membership y
permiso de reproducción; no es una nueva búsqueda ni una vía de promoción.

**Siempre prohibido bajo esta propuesta:** búsqueda en TRAIN agotado o holdouts,
selección adaptativa de latencia/periodo/feed/reglas, cambio MAIN_K/FOLLOW/INVERT,
TP/SL, autorización automática de cohorte/candidato, DEMO o trading real.

## 6. Ruta más directa y evidencia todavía necesaria

Primero aprobar o rechazar el anexo limitado; preparar un protocolo nuevo sin
consumir outcomes. Después identificar datos independientes **por trazabilidad de
exposición y rol**, no por fecha elegida tras ver rendimiento. Si ningún histórico
no expuesto es demostrable, hace falta un stream futuro nuevo, con inicio real,
propiedad y separación aprobados; no renombrar la cohorte protegida ni convertir
redescargas en observaciones prospectivas. La captura actual continúa en cuarentena.

Antes de admitir un fit faltan: membership/split manifest recuperado o nuevo
legítimamente sellado; comprobación de no solapamiento ni contaminación de warmup
y etiquetas; proveedor/feed compatible; pruebas por prefijo de todas las features
admitidas y exclusión de dependencias UTC; protocolo estadístico y presupuesto
aprobados; suficiente soporte y cobertura bajo sus criterios preregistrados.
Si el estudio necesita sesiones UTC/NY, mantener bloqueo hasta demostrar mapping
y calendario exactos. Un estudio estrictamente nativo no haría esa afirmación.

Los smokes MT5 ya preparados en `controller/native_diagnostic.py` están limitados
al día técnico 2024-01-02, model real ticks, un agente local, sin cloud/optimización
ni órdenes. Este expediente no amplía fechas del launcher. Nuevos periodos solo
tras membership autorizado y nueva allowlist revisada; no se prepara una entrada
arbitraria de fechas que eluda el guard.

## 7. Beneficios, riesgos y límites

Beneficio: separar reproducibilidad/causalidad computacional nativa de UTC físico
evita bloquear comprobaciones válidas por una capacidad distinta. Proporciona
una ruta auditable hacia un estudio nuevo sin fingir disponibilidad operativa.
Riesgos: sobreajuste por exposición previa; timestamps declarados sin prueba de
disponibilidad; revisiones del feed histórico; equivalencia incorrecta entre
servidores; perfiles incompletos; precio idealizado sin compute/fill real;
comisiones/swaps/slippage ausentes; correlación entre caminos y señales;
generalización no demostrada por un solo día; dependencias horarias ocultas.
Controles: separación de roles y dominios, evidencia por prefijo, manifiestos,
presupuesto/stop-rule previo y bloqueo persistente. UTC externo, excepciones XM
y capacidad negociable siguen siendo afirmaciones separadas no certificadas.

## 8. Decisión exacta pendiente

Texto propuesto para una aprobación posterior, **no emitida por este documento**:

> Apruebo únicamente el anexo de metodología nativa v1 identificado por su hash:
> admitir pruebas de causalidad computacional en XM_NATIVE_ORDER sin exigir UTC
> independiente como prerrequisito de esa afirmación limitada. Mantengo intactos
> el contrato UTC v1, la estrategia y todos los conjuntos/gates protegidos.
> Esta aprobación no autoriza entrenamiento, nuevo presupuesto adaptativo,
> activación de cohortes ni scoring. Un estudio nuevo requerirá dataset y protocolo
> identificados y aprobados con sus criterios antes de cualquier fit.

No se solicita aprobar un dataset inexistente ni un entrenamiento indefinido.
El siguiente estado es **WAITING_METHODOLOGY_REVIEW_AND_NEW_STUDY_SPECIFICATION**.
`CAUSAL_AUDIT=FAIL` global; `TRAINING_READINESS=BLOCKED`;
`DISCOVERY_VALIDATION=BLOCKED`; `HISTORICAL_HOLDOUT=BLOCKED`;
`FINAL_TEST=LOCKED`; `DEMO=DISABLED`; `LIVE_TRADING=false`.
