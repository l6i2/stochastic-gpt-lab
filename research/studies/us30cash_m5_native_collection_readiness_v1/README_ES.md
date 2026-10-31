# Readiness final de captura — PC A, 2026-10-31 (Ecuador)

Estado: **preparación técnica verificada; inicio científico bloqueado**.
Estudio: `US30CASH_M5_NATIVE_20261030_01`.
Paquete base inalterado: commit `8901b03813dfc3db65ba54d25d7387ceae4f22bf`.
No se inició una cohorte, dataset admitido, entrenamiento, scoring o trading.

## Permisos: observación y reserva científica son decisiones distintas

La instrucción actual permite captura puramente observacional aislada, sin scoring
ni admisión. Se realizó un diagnóstico acotado permitido de llegada/persistencia.
El anexo aprobado (`research/native_methodology_v1/adoption.json`) conserva
`cohort_activation_authorized=false`. El protocolo de este estudio exige:
“Requiere inicio real posterior a una asignación de rol exclusiva autorizada”.
La reserva protegida `us30cash_m5_future_20261019_v1` sigue abierta; el ledger
actual no demuestra sus límites ni memberships legacy completos.

Por ello **no hace falta permiso adicional para el diagnóstico observacional**,
pero sí una decisión científica explícita para reservar exclusivamente eventos
futuros del nuevo estudio y resolver la reserva anterior. El colector no toma esa
decisión ni convierte autorización en evidencia de independencia. No se cambia
ningún contrato congelado. El archivo `collection_authorization_request.json`
presenta una única solicitud, todavía no concedida, limitada a colección/reserva.

La decisión propuesta tiene una consecuencia científica real: desde una frontera
nueva, la cohorte anterior dejaría de acumular incorporaciones científicas.
Sus datos previos y criterios congelados se conservan; **no se reducen sus umbrales
de madurez ni se inventa un PASS**. Si con lo retenido no cumple duración/soporte,
seguirá sin poder madurar. No se ha cerrado esa reserva durante esta tarea.
La alternativa es mantenerla abierta y esperar a un cierre legítimo demostrado;
no se asume que un cambio de carpeta elimine el conflicto.

## Colector aislado preparado y prueba real de alcance limitado

`controller/isolated_observation.py` recibe **solo bytes nuevos** del JSONL del
observador existente. No llama MT5 Python, CopyTicks/CopyRates, histórico, cuentas
ni órdenes. El EA fuente conserva su hash y EX5 publicados: sus métodos registran
OnTick/heartbeat y no realizan recuperación histórica. Sus guards de identidad
al iniciar se conservan; las constantes en cada fila no son una atestación externa
del instante de generación del broker.

Arranque: leer únicamente una última línea completa como anchor acotado, guardar
offset/chain/session/sequence y tomar una muestra real de reloj **posterior** al
corte. Crear UUID nuevo y directorio exclusivo. Solo callbacks con uptime posterior
al corte son adoptados; registros iguales en resolución o anteriores se excluyen
sin guardar sus quotes. Así no se incorpora el prefijo preexistente ni se reetiqueta
histórico como captura nueva. Un anchor es una frontera observada, no una prueba
de la totalidad del prefijo anterior.

Ruta diagnóstica:
`outputs/pc_a_collection_readiness/observations/<NEW_UUID>/`.
Contiene manifest inmutable, journal append-only encadenado, checkpoint y lock.
La ruta prevista del estudio, **todavía no activada**, permanece separada:
`outputs/new_native_studies/us30cash_m5_native_20261030_01/<FUTURE_CAPTURE_ID>/`.
No se comparte manifest/checkpoint con TRAIN, cohortes o capturas anteriores.

El diagnóstico real recibió **dos heartbeats nuevos, cero ticks** durante la
ventana acotada. Guardó sus bytes originales, hashes, inicio real host/monotónico,
BootId y cursor; cerrar/reabrir el escritor conservó exactamente su estado.
Se preservaron los intentos diagnósticos previos en directorios distintos. El
recibo de la ejecución final vincula los hashes del escritor y herramienta que
efectivamente se ejecutaron. **No prueba captura viva de quotes**, exhaustividad
de ticks, feature values reales, independencia, calendario ni UTC de generación.
No se instaló un task ni se dejó una nueva colección continua ejecutándose.
Los observadores y tasks anteriores no se modificaron ni reiniciaron.

## Flujo y fallos probados

- Escritura: append, flush/fsync, después checkpoint temporal exclusivo y replace
  atómico. Lock de un escritor; sin delete/truncate de capturas.
- Reinicio del proceso: verificar manifest/journal/prefijo del checkpoint; recuperar
  filas completas persistidas antes del checkpoint una sola vez, sin duplicados.
- Línea parcial de la fuente: esperar, sin avanzar cursor. Journal parcial o
  alterado: conservar evidencia y bloquear; no repararlo inventando bytes.
- Error de almacenamiento: parar el escritor; exigir reapertura/verificación.
  fsync no demuestra backup ni dominio físico de fallo independiente.
- Reinicio de Windows/cambio de sesión/regresión monotónica: bloquear la continuación
  del segmento. La transición preparada crea otro UUID desde EOF actual y enlaza
  manifest/hashchain anterior; el gap se declara no verificado, **sin backfill**.
- Duplicados de secuencia, saltos, truncación, servidor/símbolo incorrectos y tipos
  de consulta histórica: rechazo. Timestamps nativos repetidos no se deduplican;
  regresiones nativas/desconexiones se conservan en cuarentena, sin offsets.
- Intervalos entre callbacks se registran sin convertirlos en pérdida demostrada
  ni latencia de red. OnTick puede coalescer: estos son callbacks observados.

## Features, reloj y admisión

El E2E sintético recorre captura nativa simulada, disponibilidad declarada de las
seis features, whitelist, persistencia, hashchain y recuperación; no contiene
targets, PnL ni fitting. Los valores de ese fixture son sintéticos, **no una nueva
validación numérica de indicadores nativos**. Se reutiliza la evidencia MQL5 ya
aprobada sin repetir su ejecución. En modo observacional real el escritor rechaza
la generación sintética de features. La captura/procedencia de features reales y
semillas ATR/HA post-inicio continúa pendiente y bloquea la admisión.

UTC del host y TimeGMT son etiquetas de recepción no atestadas. BootId,
GetTickCount64 y perf_counter se registran sin confundir sus dominios ni equiparar
recepción y generación. El label de recepción se muestra también en Ecuador,
marcado como host-derived. No se impone offset XM ni se ejecutan probes UTC nuevos.
La certificación UTC externa del evento sigue sin demostrarse; el anexo nativo
no la transforma en PASS ni cambia la auditoría causal global.

`readiness.json`, `authority_review.json`, `source_and_storage_audit.json`,
`observational_smoke.json`, `validation.json` y `hashes.json` dejan evidencia
verificable y separan los alcances de PASS. Fuente raw/quotes/journals reales
permanecen locales; se publican hashes y resúmenes permitidos.

## Siguiente decisión única y límites

Se presenta la autorización exacta de `collection_authorization_request.json`:
colección read-only nueva en cuarentena y reserva provisional exclusiva, cerrando
solo nuevas incorporaciones de la reserva anterior desde una frontera posterior
a aprobación. **No solicita** admitir datos, certificar independencia, entrenar,
hacer scoring, abrir holdouts, habilitar DEMO ni enviar órdenes.
Los observadores anteriores seguirían sin cambios como archivos observacionales;
sus segmentos/semillas previos nunca se adoptan. La aprobación no resolvería por
sí sola los memberships históricos ausentes: esos blockers seguirían impidiendo
admisión. No se implementó un bypass ni un activador científico en este escritor.

Mantener DATASET_HASH=null, DATASET_ADMISSION=BLOCKED,
TRAINING_READINESS=BLOCKED, CAUSAL_AUDIT=FAIL_GLOBAL_UNCHANGED,
DISCOVERY_VALIDATION/HISTORICAL_HOLDOUT=BLOCKED, FINAL_TEST=LOCKED,
DEMO=DISABLED y LIVE_TRADING=false.
