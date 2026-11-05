# Corte prospectivo exclusivo C+F aplicado

La autorización expresa posterior a `fa681f1404ca3b1bae0b66c0f3f3655132405ba3`
aplica íntegramente la decisión publicada. El recibo inmutable está en
`research/studies/us30cash_m5_native_observations/exclusive_cut_v1/authorization.json`.
La solicitud original se conserva sin cambios porque su hash identifica el
alcance aprobado; su estado histórico «no aprobada» queda superado por este recibo.

## Corte y roles

El corte se observó el **5 de noviembre de 2026 a las 09:22:39.247737 Ecuador**.
La referencia NTS acota condicionalmente UTC a
**14:22:38.810252–14:22:39.688892**, estimación 14:22:39.249572.
El orden autorización → corte → primera observación se conserva con boot y
contador monotónico. Estas cotas no certifican la generación física del tick XM.

El ledger inmutable cierra nuevas incorporaciones de US30Cash de PC A a
**todas las reservas anteriores**, incluidas las de extremo desconocido,
y asigna exclusivamente los nuevos intervalos al estudio
`US30CASH_M5_NATIVE_OBSERVATIONS_20261105_01`.
Se mantiene el productor `cfprod_5c64f0781dc148e5896391b1492ba144`.
La captura nueva es `dbsnap_0fd175bd0cb94a5fa26e7404819c2228`, dataset
`us30cash_m5_native_observations_20261105_01_dataset_02`.

La independencia de **roles futuros** se fundamenta en esta decisión expresa y
en el cierre operativo de escritores. No equivale a recuperar los límites de los
datasets antiguos ni a certificar su mapping UTC histórico. No se abrieron los
conjuntos protegidos. La pertenencia de los nuevos intervalos se verifica desde
el manifest, el ledger, las consultas y el checkpoint propios.

## Conservación y cierre efectivo

Los datos previos y sus manifests no se alteraron ni se adoptaron. La captura
C+F anterior terminó con 39 M1 y 6 M5 técnicas; todas quedan en cuarentena,
con cero barras incorporadas al warmup nuevo. Un recibo de 53 artefactos
registra hashes de manifests y estados, incluido el SQLite anterior. La
verificación posterior comprueba que los hashes siguen iguales.

Se deshabilitó la tarea de captura de la reserva anterior y se retiraron sus
dos arranques de watchdog del registro de usuario, conservando sus valores en
un recibo. Se cerraron los escritores antiguos y el worker derivado anterior.
Sus controles enabled quedaron desactivados. El guardian existente respeta el
cierre y mantiene el productor C+F, NTS, XM y el monitor. El observador MQL5
anterior sigue siendo diagnóstico: sus registros no se asignan a otra reserva.
No se cambió su código ni se reinició XM o Windows.

## Epoch, límites y recuperación

La primera observación posterior al corte quedó registrada a las
**09:22:53.988363 Ecuador**. Un ajuste técnico anterior a la primera barra
distinguió los límites de M1 y M5 completas: cada timeframe debe comenzar
después del corte; una M1 posterior al corte puede preceder a la primera M5
completa. Se registró un pin de implementación nuevo, conservando el manifest
de origen. La recuperación abrió epoch 2 con corte fresco, sin backfill.

El contador, historia y semillas del dataset 02 nacen vacíos. Ninguna de las
6 M5 del dataset anterior entra en el nuevo contexto. La recuperación conserva
la primera observación y el prefijo ya comprometido, pero no conserva continuidad
de features a través de una interrupción sin prueba. El aplicador es idempotente:
una nueva ejecución verifica las identidades y no crea otro corte o dataset.

Las cifras reales y la evidencia de avance están en `operational_receipt.json`
y `runtime_status.json` del subdirectorio `exclusive_cut_v1`. Las auditorías de
lectura comprueban toda la cadena, pares de consultas, M1/M5 y prefijo persistente.
No exportan las filas masivas de los snapshots. Las pruebas sintéticas no se
cuentan como datos reales.

## Calendario y requisitos pendientes

El log recuperado del probe ejecutado a las 08:51:22 Ecuador contiene 13 registros
completos. Para XMGlobalSC-MT5 5 / US30Cash observa cotización de lunes a viernes
01:00–00:00 nativo, negociación lunes-jueves 01:05–23:55 y viernes 01:05–23:50.
No se convierte ese horario en certificación UTC ni en calendario de feriados.
La línea TimeTradeServer/TimeGMT del probe no es referencia UTC independiente.

Calendario PARTIAL: faltan excepciones aplicables y una transición entre sesiones
con observación conectada y cobertura verificadas. No se sumará continuidad
entre sesiones con evidencia desconocida. Se mantienen 350/800/100/200/80/80,
tres folds evaluables por lado, MAIN_K 5/3/3 y toda la estrategia congelada.

La nueva asignación cierra el bloqueo de decisión de roles; no cierra cobertura,
semillas, disponibilidad causal completa, paridad iATR ni madurez. El gate sigue
WAITING_FOR_EVIDENCE y el dataset hash sigue null. El entrenamiento necesita
dataset admitido y una autorización específica que **no existe**. El protocolo
preregistrado y el runner conservan cero ajustes autorizados y rechazo sin grant.

CAUSAL_AUDIT global permanece FAIL. Discovery Validation, Historical Holdout y
Final Test siguen cerrados. DEMO=DISABLED, LIVE_TRADING=false,
terminal_trade_allowed=false, TRAINING_EXECUTED=false, PROTECTED_SCORING=false.
No se enviaron órdenes ni se modificó el otro proyecto.
