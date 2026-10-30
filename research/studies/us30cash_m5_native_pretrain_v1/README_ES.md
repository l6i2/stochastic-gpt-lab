# Paquete PRE_TRAIN — US30Cash M5 nativo

STUDY_ID: **US30CASH_M5_NATIVE_20261030_01**.
DATASET_ID: **us30cash_m5_native_new_01_reserved** (nombre reservado, sin dataset).
Estado: **PREPARED_INCOMPLETE_EVIDENCE_PRE_TRAIN**. No se solicita autorización
científica porque todavía no existe un dataset independiente verificable.

## Trabajo realizado y límites de la auditoría

Inventario local por nombres y tamaños, sin abrir o hashear payloads protegidos.
Se leyeron contratos/registros científicos publicados y manifiestos raw permitidos,
no filas de TRAIN, Discovery Validation, Historical Holdout o Final Test. Los
únicos IDs de mercado leídos son los **28 del día diagnóstico 2024-01-02** ya
autorizado; su identidad se verifica contra el hash previamente publicado antes
de extraer ID/cutoff. No se calcularon labels, PnL, scoring o features nuevas sobre
datos reales. No se repitieron los probes MT5 ni las pruebas nativas ya aprobadas.

`exposure_ledger.json` encadena diez registros de fuentes/roles/versiones conocidos:
master legacy y derivado quality-v1, reserva Historical Holdout sin límites
recuperados, cohorte protegida 20261019, archivos raw histórico/prospectivo y
cuatro runs nativos del mismo día. Cada versión queda ligada a su evidencia/hash,
intervalo cuando existe y membership conocido. `known_exposed_signal_membership.json`
conserva esos 28 IDs; **no sustituye memberships legacy ausentes**.

El master original declaró 20.422 señales y splits purgados 12.243 TRAIN / 4.077
Discovery Validation. Son cifras de su freeze, no un recuento nuevo ni una lectura
del tail. Las hipótesis registradas y sus versiones se inventariaron por hashes,
sin volver a leer resultados. TRAIN sigue agotado; un prerregistro antiguo
pendiente no se convierte en nuevo permiso. El alcance exacto de Historical Holdout
permanece desconocido: se protege sin afirmar que fue leído.

Los manifiestos raw se leen **una vez por revisión** para una instantánea coherente
mientras el collector continúa escribiendo. Se verifica su hashchain y cursor en
metadatos; `archive_windows.json` contiene intervalos de consulta y conteos
declarados, no datos de ticks. El archivo histórico conserva 79.211 ticks declarados
y M5 originalmente vacío; las 276 M5 reconstruidas/verificadas posteriores son
otra versión del mismo día, nunca datos independientes. Los conteos prospectivos
cambian con la captura: consultar la instantánea hash-bound, no presentar un número
de este texto como estado vivo. Cadena de consultas continua **no prueba** cobertura
del mercado, ausencia de pérdidas, semántica UTC ni integridad de payload revalidada.

No se encontraron master/split/membership originales en las ubicaciones esperadas.
No se repite una búsqueda de recuperación ya agotada ni se fabrica ancestry.
Los nombres de archivos desconocidos y backups quedan en cuarentena; una copia,
reexportación o redescarga del mismo intervalo no crea muestra independiente.
La revisión cubre este repositorio y sus outputs, no asegura inventario completo
de exposiciones externas ni toca el otro proyecto de PC A.

## Archivos del expediente

- `dataset_inventory.json`: existencia de originales, namespaces y tamaños; cero
  filas de conjuntos protegidos abiertas.
- `exposure_ledger.json`, `archive_windows.json`, `research_registry_inventory.json`:
  evidencia por fuente/intervalo/versión y límites explícitos de completitud.
- `dataset_membership.json`: reservado y vacío; su hash no es DATASET_HASH.
- `temporal_dependencies.json`, `feature_causality.json`: seis features cerradas,
  lookbacks y semillas completas, con evidencia sintética heredada separada del
  dataset real inexistente. MAIN_K actual requiere siete barras; delta K una
  adicional; volumen relativo, 21. HA depende de toda su recurrencia desde seed;
  ATR nativo no se declara finito por poner “14”.
- `feature_model_whitelist.json`, `PROTOCOL_ES.md` y su seal: una familia L2 por
  BUY/SELL, FOLLOW/INVERT preservados, adquisición outcome-blind, purged walk-forward,
  incertidumbre/multiplicidad, criterios y parada, sin activación.
- `prospective_collection_plan.json`: preparación inactiva basada en el sistema
  instalado, sin nuevos tasks/probes ni cambios de collector.
- `coverage_audit.json`, `pre_train_gates.json`: resultados y blockers.
- `scientific_authorization_package.json`: identificadores, hashes, presupuesto
  y criterios. DATASET_HASH y CODE_HEAD no se rellenan con valores ficticios.
- `code_source_hashes.json`, `environment_versions.json`, `validation.json`,
  `package_hashes.json`: código, entorno, pruebas y seal del paquete.

El CODE_HEAD de la implementación se resuelve por el commit Git que contiene
estos archivos y por el recibo de publicación posterior. REVIEWED_BASE_HEAD es
solo el commit previo; no se hace pasar por el código nuevo ni se intenta un hash
autorreferente dentro de su propio commit. El recibo final vincula CODE_HEAD real
y root hash de este expediente. Antes de pedir autorización de un futuro estudio
deberán sellarse un request nuevo y todos sus inputs reales, sin nulls requeridos.

## Reserva prospectiva preparada, sin activar una cohorte

La captura instalada permanece read-only en cuarentena. **No se adoptan sus
segmentos anteriores**. Para un dataset nuevo se necesita una asignación de rol
exclusiva sin solapamientos, comienzo real con session/sequence y primer M5
completo posterior, warmup propio, cadena de recibos y continuidad verificable.
Una reserva protegida abierta no termina porque el nuevo estudio lo necesite:
hace falta una decisión científica documentada antes de tocar sus límites.
Dominios de servidor/UTC no comparables fallan cerrados; no se impone un offset.

El preview sintético de frontera rechaza reconsultas históricas, secuencias repetidas,
desconexiones y reinicios sin nuevo segmento. No escribe ni activa captura.
La preparación no autoriza un handoff, cierre de cohorte antigua o reasignación
de sus datos. La siguiente adquisición propuesta cuenta 350 barras de warmup propio,
las primeras 800 señales base consecutivas y 100 barras observadas adicionales
para horizontes; su arranque efectivo sigue siendo null. Nunca se extiende tras
mirar rendimiento. La coalescencia OnTick no se confunde con un feed exhaustivo.

## Automatización y siguiente estado

`python tools/pretrain_study_review.py` verifica el seal anterior, reconstruye
metadatos del expediente, ejecuta solo tests sintéticos afectados y verifica
hashes. No contiene lector de splits protegidos, trainer, scorer ni activador.
El inventario no importa librerías para entrenar; solo registra versiones de
distribuciones ya instaladas. El script puede refrescar una instantánea nueva de
metadatos vivos: debe conservarse cada versión publicada y revisar sus cambios,
no reinterpretar un hash antiguo como si describiese el stream actual.
Cada nueva instantánea del ledger enlaza el hash de la última versión publicada;
esa versión completa permanece en el historial Git, además de la cadena interna
de registros de la instantánea. Un hashchain no autentica exposiciones desconocidas.

Faltan datos independientes, ledger/membership completos, identidad y cobertura
reales y aislamiento de semillas. Una vez demostrado todo ello, la autorización
necesaria será **un estudio concreto ligado a esos hashes y presupuesto**, no
permiso para reabrir TRAIN o holdouts. No se pide autorización ahora ni se marca
ready por el simple hecho de haber escrito el paquete.

PRE_TRAIN_GATES=BLOCKED; CAUSAL_AUDIT=FAIL_GLOBAL_UNCHANGED;
TRAINING=BLOCKED; SCORING=NOT_AUTHORIZED; DISCOVERY_VALIDATION=BLOCKED;
HISTORICAL_HOLDOUT=BLOCKED; FINAL_TEST=LOCKED; DEMO=DISABLED;
LIVE_TRADING=false. Intervención manual: ninguna en esta preparación.
