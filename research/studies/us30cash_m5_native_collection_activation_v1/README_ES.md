# Activación autorizada — PC A, 2026-10-31 (Ecuador)

**Captura activa en QUARANTINED.** Reserva anterior cerrada únicamente a nuevas
incorporaciones científicas desde la frontera de activación. No se modificó ningún
contrato congelado ni dato/manifiesto/checkpoint anterior por este colector.
No hay entrenamiento, scoring, órdenes, DEMO executor o trading real.

## Identidad e inicio real

- Capture ID: `us30cap_15cbddec947f42c98219caa4cec978f2`.
- Estudio reservado: `US30CASH_M5_NATIVE_20261030_01`.
- Inicio UTC estimado: **2026-10-31 18:33:53.341916 UTC**.
- Hora Ecuador estimada: **2026-10-31 13:33:53.341916 America/Guayaquil**.
- Intervalo UTC: **18:33:52.983025 .. 18:33:53.700806 UTC**.
- Semiancho: **358.890.332 ns (aproximadamente 0,359 segundos)**.

No se presenta el estimador como una hora metrológica exacta. Se midió NTS fresco
con TLS/hostname/ALPN/exporter/AEAD/UID/origin verificados inmediatamente antes y
después del corte de activación. Por orden causal, éste es posterior al transmit
UTC de la primera respuesta y anterior al receive UTC de la segunda petición.
Se amplía el intervalo por el error anunciado por cada servidor. Esto evita
extrapolar offset/deriva del reloj local; sigue siendo condicional a la corrección
del tiempo/error anunciado por el servidor, no una cota metrológica absoluta.

`activation_utc.json` vincula ambos IDs y el intervalo. Los dos registros NTS
permitidos se publican sin cookies, claves ni credenciales. El host UTC original,
BootId, uptime, QPC/perf_counter y frontera de fuente se conservan por separado.
**La evidencia UTC de activación no certifica UTC de generación de ticks XM.**
No se corrigió Windows ni se aplicó un offset al broker o a datos originales.

## Decisión inmutable y conservación

`authorization.json` registra la autorización explícita limitada del usuario y el
hash de la solicitud aprobada en `3244088ba15946b68ca32e7a29357a022055cfcf`.
El ledger `decisions/` contiene tres eventos exclusivos, encadenados y con fsync:

1. Autorización del usuario, sin derechos de entrenamiento/scoring/admisión.
2. Cierre de nuevas incorporaciones científicas a la reserva
   `us30cash_m5_future_20261019_v1`, ligado a la nueva frontera y evidencia UTC.
3. Reserva de la nueva captura en cuarentena, sin adoptar segmentos antiguos.

Las decisiones y el manifiesto son byte-idénticos a los originales locales.
La semántica es **forward-only**: no se cambian fechas, membresías, resultados ni
umbrales de madurez de la cohorte anterior. Si no satisface sus criterios retenidos,
sigue sin madurar; no se inventa un PASS. Los observadores raw anteriores pueden
seguir añadiendo observaciones en cuarentena, sin nuevas incorporaciones científicas
a aquella reserva. No se detuvo ni modificó su código, EX5, task o identidad.

Se conservaron instantáneas inmutables de versiones previas de metadatos y sus
hashes en el namespace nuevo. El auditor comprueba también los 577 archivos del
seal previo v26 sin cambios, y la identidad publicada del observador instalado.
Esto no afirma que se releyeron datasets protegidos ni que los archivos raw vivos
de los observadores anteriores dejan de avanzar naturalmente.

## Captura y aislamiento

Raíz exclusiva:
`outputs/new_native_studies/us30cash_m5_native_20261030_01/us30cap_15cbddec947f42c98219caa4cec978f2/`.
Allí están manifiesto, ledger, evidencia UTC, segmentos, checkpoints y estado.
Los journals raw permanecen locales y no se publican. `collection_manifest.json`
conserva `dataset_admission=false`, `independence_certified=false`,
`training_authorized=false`, `scoring_authorized=false`, `orders_sent=0`.

Se recibe exclusivamente la cola nueva del observador nativo instalado. No se
llama CopyTicks/CopyRates, API de órdenes o recuperación histórica. Se guarda
la línea nativa byte a byte, con sus timestamps originales y hashchain. El prefijo
anterior al corte no se incorpora. Los callbacks iguales en resolución o previos
al corte no se adoptan como nuevos quotes. Reanudar un proceso lee callbacks que
el observador ya registró **después** de la activación: es ingestión diferida con
su recepción original preservada, no redescarga/backfill ni timestamp nuevo fingido.

`integrity_and_no_backfill.json` verifica un prefijo consistente del journal vivo
contra un checkpoint instantáneo: hashes, secuencias, source offsets y frontera
post-activación. Las cifras de `status.json` son una instantánea, no una afirmación
de estado permanente. Hasta esa auditoría solo se observaron **heartbeats**, sin
ticks; no se declara cobertura de mercado ni captura de quotes en vivo demostrada.
OnTick puede coalescer, por lo que tampoco se presupone un feed exhaustivo.

## Supervisión y reinicios

Windows denegó registrar una nueva tarea programada (0x80070005). No se pidió
elevación ni credenciales ni se modificó una tarea anterior. Se instaló solo el
valor propio `StochasticGPTLab_PC_A_NewNativeCapture_v1` en HKCU Run.
Inicia al logon un watchdog oculto, protegido por mutex, que supervisa cada cinco
segundos el proceso Pythonw exclusivo del nuevo colector. Su pin de código y
autorización se verifica al arrancar; cambios no revisados bloquean el servicio.

La recuperación real del proceso fue verificada: se terminó solo el PID propio
validado por ejecutable y command line; el watchdog relanzó el colector. Capture ID,
segmento, manifiesto, ledger y cursor se conservaron; aumentaron registros sin
duplicados. El terminal XM y procesos anteriores siguieron activos. Ver
`process_restart_verification.json`. **No se reinició Windows**, para no interrumpir
el otro proyecto; transiciones de BootId/sesión se probaron con fixtures sintéticos.

Tras reboot/sesión nueva se espera una fuente nativa nueva, se crea segmento con
UUID distinto y vínculo al anterior. Se declara el gap no verificado y no se hace
backfill. La captura requiere PC encendida/despierta, sesión de usuario iniciada
y el observador XM disponible; el watchdog no altera energía, login, trading ni
otras aplicaciones para fingir disponibilidad. Falta de fuente, heartbeat atrasado,
hash/clock/IO inválido produce espera/reintento en cuarentena, nunca admisión.

## Incidente previo conservado

El primer intento `us30cap_7dfc7985cf494cce979dc509b5175445` falló antes del cierre
de reserva o ingestión: una ruta temporal de checkpoint alcanzó 265 caracteres
y Windows la rechazó. Su manifest, frontera, NTS previo y journal vacío permanecen
intactos. Se corrigió el I/O mediante rutas extendidas Windows, sin mover/borrar
datos ni cambiar el escritor aprobado. La prueba de regresión reproduce ese caso.
El intento definitivo usa otro ID, NTS y frontera nuevos; cero registros reutilizados.

## Validación y límites científicos

45 pruebas afectadas PASS, cero errores/fallos/skips: autorización acotada, bracket
NTS, atomicidad, larga ruta Windows, reinicio durante activación, recuperación de
proceso y BootId, duplicados, hashchains, buffers parciales, IO, semillas/causalidad
sintética, aislamiento y splits purgados. No se repitieron pruebas nativas aprobadas
ni se consultaron datos protegidos. La única intervención real de reinicio fue
el proceso nuevo identificado, no PC/MT5 ni otra aplicación.

La admisión exige aún integridad/continuidad/cobertura de quotes y M5, fuente y
membership independientes, features reales con warmup/semillas admitidos y
procedencia temporal demostrada. La autorización no sustituye esas pruebas.
DATASET_HASH sigue null; CAUSAL_AUDIT global FAIL; TRAINING_READINESS BLOCKED.
Discovery Validation/Historical Holdout BLOCKED; Final Test LOCKED;
DEMO DISABLED; LIVE_TRADING=false. Intervención manual requerida actualmente: ninguna.
