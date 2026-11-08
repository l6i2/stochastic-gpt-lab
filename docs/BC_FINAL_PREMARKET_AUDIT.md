# Auditoría final antes de reapertura B+C

**TECHNICAL_PRETRAINING_CLOSED.** No quedan defectos técnicos demostrables sin resolver en el alcance auditado. La infraestructura está preparada; el dataset no está admitido ni hay autorización de entrenamiento.

## Evidencia actual

Estudio US30CASH_M5_XM_TRAIN_FUTURE_EVAL_PROPOSED_V1, rama research/full-pipeline. HEAD local/remoto al comenzar: `4d8e6eb89bda8746e18fcd6a543f0bc9b6fb0ead`. La revisión verificó una instancia XM, conexión read-only con XMGlobalSC-MT5 5/US30Cash, cero procesos del productor C+F cerrado y su enabled=false. Reserva, autorización, contratos, semilla ATR y allowlists científicas permanecen intactos. El registro B diagnóstico no se incorpora al nuevo dataset.

Al recibo **2026-11-08T16:59:21.343453-05:00 Ecuador**: 0 M5 propias, contexto 0/350, señales 0/800, posteriores 0/100, evaluables 0/200, BUY 0/80, SELL 0/80 y folds 0/3 por lado. El último tick sigue siendo anterior al corte y native_floor=null. No se hizo ninguna descarga anterior al corte ni se fabricaron datos. El ID de captura es `bc_train_f6b99cbfc59542a38627868015f65792`; DATASET_HASH admitido=null.

La tarea B+C conserva su definición y ejecución periódica de cinco minutos y al logon, IgnoreNew y lock. Su última ejecución observada terminó con código 0. El guardian 28100 lanzó el helper 15412: ancestry y heartbeat confirman revisión automática real. Los códigos históricos no cero de disparos de tareas guardian/NTS no se sustituyen por un PASS genérico: su operación se acredita con el proceso activo, recibos recientes y medición NTS autenticada. La fuente Cloudflare sigue produciendo medidas autenticadas; el segundo origen queda registrado como no disponible cuando corresponde.

La recuperación real de checkpoint/cadena pasó y conserva el head cerrado C+F. Las pruebas sintéticas cubren reinicio y reanudación idempotente; **no se ha demostrado todavía un apagado/reinicio físico**. Esa evidencia se registrará tras el próximo arranque natural, sin provocarlo. No se cambiaron energía, batería, privilegios globales ni tareas de Windows.

## Código y reparaciones efectuadas

**68 tests PASS**, únicamente fixtures, exports nativos sintéticos ya autorizados y estimadores simulados. Imports de 12 módulos requeridos y versiones de numpy, scikit-learn, MetaTrader5 y psutil verificados; compilación Python completa PASS. No se recompiló MQL sin cambios: se conservaron los binarios/recibos aprobados y la especificación fresca de la misión anterior. No se repitieron descargas ni auditorías del histórico protegido.

Cobertura: SQLite y cierre de conexiones, checkpoints, recuperación y orphans, hashes, duplicados, límites inclusivos/semientreabiertos, timestamps, prefijos, Bid/Ask, M1/M5, volumen, ATR/Heikin Ashi/MAIN_K, vintages, rechazo sin grant, purga, ocho fits simulados y conservación fold4. Estas pruebas acreditan software; no certifican nuevas barras reales que todavía no existen.

Se corrigieron dos puntos verificables:

1. El estado técnico completo ahora es **READY_FOR_ADMISSION_REVIEW**, separado de training_authorization_status=WAITING_FOR_AUTHORIZATION. Los cuatro estados solicitados se prueban; para cada uno de los 18 gates se prueba que evidencia pendiente impide readiness y evidencia fallida produce FAIL. READY no admite datos ni habilita fits.
2. Un cache hit compara también el paquete candidato actual y la versión inmutable con su SHA esperado. La prueba modifica el paquete y confirma rechazo, aunque los inputs no hayan cambiado. Se conserva el rechazo previo por alteración del recibo.

No se modificaron estrategia, parámetros, contratos, whitelist, semillas ni umbrales. Las allowlists ADMITTED_PACKAGE_HASHES y AUTHORIZED_GRANT_HASHES continúan vacías.

## Indicadores, admisión y entrenador

INDICATOR_PIPELINE=READY técnico. ATR mantiene su variante aprobada y hash 9bc2efb0e3a2d1af750d4c47ce38fb8ca2b245639856c63ba210a82d23c70dfc; MAIN_K 5/3/3, 20/80 y HA conservan sus definiciones. Los oráculos esperan 15/30/276/350 barras propias y se ejecutan por prefijo/vintage; no se inventa NATIVE_PARITY_PASS ni CAUSAL_CERTIFICATION_PASS a partir de fixtures. La auditoría causal global no se cambia a PASS.

Los 18 gates están implementados. Estado actual WAITING_FOR_DATA, con calendario, excepciones, cobertura y causalidad esperando evidencia. Se mantienen 350/800/100/200/80/80 y tres folds por lado. Los puentes entre sesiones requieren certificados específicos revisados; una especificación semanal genérica no basta. Un label incompleto queda censurado, no se añade una barra para completarlo.

TRAINER_READY=READY_BUT_GATED: logística L2 C1, BUY/SELL separados, FOLLOW/INVERT, TP240/SL180/TIME_EXIT100 y Bid/Ask originales. Cuatro folds cronológicos purgados, escalado solo en TRAIN, ocho fits máximos, cero búsquedas, modelos fold4 prefijados y semilla 20261030. La matriz de entrenamiento tiene como máximo 800 señales y seis features; el bootstrap trabaja por resample, sin crear una matriz gigante de 10.000 muestras. El worker procesa chunks acotados y el consumo observado permanece alrededor de 38.2 MiB.

Grant y admisión confiables se comprueban antes del lector científico o de crear estimadores. El hash del dataset, protocolo, whitelist, entorno, código limpio, posiciones observadas, soporte purgado, clases y presupuesto se verifican antes de fits. Se preparan paquetes por generación inmutable, sin rellenar hashes ausentes ni solicitar entrenamiento prematuramente. No se ejecutó ningún fit científico ni scoring protegido.

## Reapertura y pendientes

La prueba de apertura existente está lista. Al observar una cotización nueva verificará identidad, registrará su primera observación, excluirá la barra en formación y recuperará únicamente intervalos completos autorizados B+C. Validará precios, ticks, OHLC/volumen, M1/M5, hashes y membership y actualizará contadores. El horario nominal domingo 8 a las 18:00 Ecuador es solo una referencia operacional condicionada a la sesión real; no prueba apertura. La vigilancia se basa en ticks, no en asumir esa hora.

No quedan bloqueos técnicos reproducibles. Quedan datos futuros, oráculos sobre prefijos propios, calendario/excepciones y certificados de cobertura/causalidad; después admisión y grant específico. La recuperación física queda pendiente de observación natural. No se necesita acción manual ahora.

DISCOVERY_VALIDATION=BLOCKED; HISTORICAL_HOLDOUT=LOCKED; FINAL_TEST=LOCKED; DEMO=DISABLED; LIVE_TRADING=false; terminal_trade_allowed=false; TRAINING_EXECUTED=false. Cero órdenes, sin modificar el otro proyecto.

Recibos y hashes: [índice](../research/studies/bc_train_future_eval_v1/premarket_audit_20261108/index.json). El HEAD final es el commit contenedor de estos archivos, verificado local/remoto después del push normal. Los recibos locales siguen automáticamente; futuras publicaciones remotas requieren la sesión o credencial GitHub autorizada.
