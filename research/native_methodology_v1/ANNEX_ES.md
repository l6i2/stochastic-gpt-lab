# Anexo metodológico nativo MT5 v1 — incorporado para diagnóstico

**ADOPTED_DIAGNOSTICS_ONLY.** Autorización limitada explícita del usuario posterior
al informe publicado en `5e2973723e307e29479f0419163df54e547a8e94`.
La propuesta aprobada, conservada sin cambios, es
`proposals/native_methodology_v1/REVIEW_ES.md`, SHA-256
`c8ddaac2a6aeac7d25826b59226dde23256e560771eebfda96d5e493d41cb8b5`.
`adoption.json` registra ese alcance; no es token de entrenamiento o de scoring.

## Ámbito y reglas

El dominio XM_NATIVE_ORDER permite demostrar disponibilidad **computacional en
simulación**, separada de certificación UTC externa. No modifica el contrato UTC
v1 ni los contratos científicos congelados, datasets, hashes, offsets, estrategia,
triggers, MAIN_K, FOLLOW/INVERT, TP240/SL180/TIME_EXIT100 o entrada del baseline.

La barra cerrada limita las observaciones utilizables. El primer tick de la barra
siguiente dispara el callback que consulta shift 1, calcula contexto y decide.
El cutoff nominal no prueba que los cálculos terminaron antes de ese callback.
El orden de llegada distingue timestamps repetidos; no se corrige el orden ni se
rellenan barras. La cotización de entrada del baseline continúa siendo una
suposición virtual idealizada; para políticas derivadas se conserva fill posterior
al índice de llegada y latencias fijas. Ningún resultado demuestra fills reales.

## Implementación y evidencia nueva

`controller/native_feature_diagnostic.py` deriva el harness sintético ya existente
sin editar `tests/mql5/SnapshotCausalProbe.mq5` ni el productor congelado. Copia éste
y sus includes a un directorio único del terminal portátil aislado. Usa MetaEditor
de XM, exige log **0 errores/0 warnings**, EX5 nuevo y hashes. MetaEditor devolvió
código de proceso 1 pese al log de compilación correcta: se registra, no se oculta;
la aceptación depende del log, artifact y ejecución real, no solo del exit code.

El script invoca **el OnTick, Capture, SnapshotTrade, Profile, HA y trade-state del
productor real** contra adaptadores sintéticos. No invoca su OnInit de Strategy
Tester ni realiza consultas de datos históricos. El harness anterior aproximaba
Stochastic por media de Fast K: la copia diagnóstica usa ratio-of-sums 5/3/3. ATR
y EMA siguen siendo adaptadores causales sintéticos: esta prueba no sustituye una
prueba numérica de todos los indicadores nativos. MAIN_K nativo ya aprobado se
conserva, sin repetir su probe. El Strategy Tester y controlador nativos existentes
permanecen disponibles para el día técnico autorizado; no se amplían fechas.

Captura válida: **nfeat_41d5994c6b84**. Tres cortes sintéticos (barras 45, 400, 450),
cada uno con base completa, futuro perturbado y prefijo truncado: nueve ejecuciones
del productor en un script. Datos completamente sintéticos; no son nueve backtests
históricos, cohortes o entrenamientos. El prefijo incluye el primer callback de
la barra siguiente, pero no sus ticks posteriores ni sus velas futuras.

| Corte | Entradas comparadas | Snapshots comparados | Targets futuros cambiados |
|---|---:|---:|---:|
| 45 | 1 | 16 | 16 |
| 400 | 36 | 6.272 | 1.072 |
| 450 | 41 | 7.258 | 1.058 |

Las observaciones de los cortes se solapan: **no sumarlas como muestras
independientes**. Los targets futuros actúan solo como control positivo; no se
usan como features ni se calcula rendimiento de datos reales. En cada corte el
comparador confirma que los inputs pasados no cambiaron y que sí cambió el futuro.
Las features anteriores al corte coinciden exactamente bajo las dos variantes.

Registro exhaustivo por columna en `evidence/availability.json`: **225 predictoras
de entrada** del whitelist congelado y **257 campos de snapshot**, 482 registros
tabla/columna. Todos aparecen no vacíos al menos en una situación sintética.
420 reciben `PASS_SYNTHETIC_NATIVE_PREFIX_ONLY`, 54 son metadata de auditoría y
8 registros de hora NY/UTC/weekday/session siguen `QUARANTINED_UTC_SEMANTICS`.
Los otros campos de entrada (targets, ejecución, configuración, IDs) se enumeran
expresamente como no predictoras; no se omiten para hacer pasar la comparación.
El PASS demuestra invariancia en estas fixtures, **no que toda columna tenga
variación/información predictiva ni que todos sus valores sean correctos**.

Casos cubiertos: barra en formación perturbada, llegada siguiente M5, duplicados
de timestamp con secuencia conservada, gap de dos barras sin relleno, HA fría y
ready, ventanas largas faltantes, volumen real cero/no cero, perfiles por ventana
y sesión nativa, estado MFE/MAE previo al tick siguiente y futuro separado.
Los adapters rechazan CopyRates/CopyBuffer shift<1 y CopyTicksRange más allá del
cutoff disponible. No prueban completitud del feed, vintage histórico, sesiones
UTC/NYSE/XM exactas ni instante físico de generación.

## Evidencia negativa y protección de historial corto

El intento **nfeat_dbf52a1354b5**, con inicio de 15 barras, abortó por acceso fuera
de array en el productor congelado, línea 152, dentro del snapshot que recorre 20
barras. Se conserva el artifact y se publica su hash y error en
`evidence/short_history_failure.json`. No se presenta como PASS ni se repite para
ocultar el fallo. El intento previo de compilación nfeat_696afe781bc1 tuvo 0/0 en
el log pero el launcher inicial interpretó incorrectamente el código 1 como fallo;
no ejecutó el productor. Esa distinción queda registrada.

No se parchea el productor ni se instala un guard en la estrategia activa.
`history_preflight` es una **precondición diagnóstica nueva**, con rechazo si hay
menos de 20 barras cerradas. Veinte es el suelo de acceso directo, no warmup
suficiente para todas las features. Las fixtures válidas empiezan con 30 barras,
permitiendo observar missingness y HA fría; el contexto completo exportado puede
requerir 350 barras y la semántica nativa de indicadores exige pruebas separadas.
Nuevos datasets no se admiten por el simple PASS de esta precondición.

## Independencia y diseño de estudio preparados

`controller/native_independence.py` comprueba en memoria manifiestos sintéticos:
roles y namespace nuevos, IDs completos, hashes de fuente/ledger, reutilización
de fuente, intervalo íntegro de warmup/features/decisiones/etiquetas y no solapamiento
con TRAIN agotado, Discovery Validation, Historical Holdout, Final Test y prospectivo
en cuarentena. Dominios de servidor no comparables se rechazan; no se supone UTC.
No abre filas de datasets y **no autentica por sí mismo la integridad/completitud
del ledger de exposición**. Incluso PASS estructural conserva independencia
UNVERIFIED y training/scoring false. Es preparación, no un guard que abra datos.

`STATISTICAL_PROTOCOL_ES.md` fija un diseño de una familia, BUY/SELL separados,
ambos caminos, cuatro folds cronológicos expansivos, purga por ambos exits,
features cerradas, baselines, missingness/censura, incertidumbre, límites de
exposición y parada. `controller/native_study_design.py` construye únicamente
planes sobre metadata sintética, sin PnL/modelos/scoring. El diseño es previo a
outcomes, pero **no es un estudio preregistrado completo** hasta vincular datos,
membership, ledger y aprobación. No renueva presupuestos V2/R2/R3/R4 agotados.

## Automatización y reproducción

Una ejecución de `tools/native_methodology_review.py` valida los seals previos,
reutiliza y verifica los hashes de la captura sintética completa, vuelve a analizar
sus CSV y ejecuta regresiones sintéticas. Publica solo reportes sanitizados,
source harness, manifests/hashes y tests. Raw CSV/bin/logs de terminal permanecen
locales; ningún dato de cuenta o credencial se publica.

`python -m controller.native_feature_diagnostic` reutiliza la captura existente;
no vuelve a abrir MT5. `--run-new` es explícito y solo permite la fixture sintética
fija, sin parámetro de fecha/dataset/modelo. Nunca cierra la instancia XM activa;
el terminal portátil se cierra al concluir el script. Un timeout deja el PID en
checkpoint y no mata procesos ajenos. La instancia original PID 22044 permaneció
activa durante la ejecución válida. No se tocó el otro proyecto de PC A.

## Pendiente y siguiente autorización

Faltan datos realmente independientes no expuestos con membership y ledger
revisables, comparabilidad de feed/dominio y coverage, prehistoria y horizontes
completos admitidos. El split manifest legacy sigue ausente; recuperarlo no haría
nuevo el TRAIN agotado. Ninguna captura actual en cuarentena cambia de rol.
Si no existe histórico no expuesto demostrable, hará falta un stream futuro nuevo
con inicio real y separación autorizados; no renombrar la cohorte sellada ni hacer
backfill prospectivo. Campos UTC/sesiones externas seguirán bloqueados mientras
no se pruebe su mapping; la nueva metodología no certifica UTC por inferencia.

La próxima decisión científica sería autorizar **un estudio nuevo concreto**:
dataset/hash/membership independientes, dominio, protocolo estadístico y whitelist
sellados, presupuesto y outputs. Esta autorización limitada del anexo **no concede
ese permiso**. Antes de solicitarlo se deberá presentar ese paquete verificable.

Estado: `NATIVE_DIAGNOSTIC_METHOD=ADOPTED`; `CAUSAL_AUDIT=FAIL_GLOBAL_UNCHANGED`;
`TRAINING_READINESS=BLOCKED`; `SCORING=NOT_AUTHORIZED`;
`DISCOVERY_VALIDATION=BLOCKED`; `HISTORICAL_HOLDOUT=BLOCKED`;
`FINAL_TEST=LOCKED`; `COHORT_ACTIVATION=NOT_AUTHORIZED`;
`DEMO=DISABLED`; `LIVE_TRADING=false`.
