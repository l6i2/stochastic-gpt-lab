# B+C: activación, adquisición y preparación científicaLa autorización adjunta se aplicó. El nuevo estudio está activo exclusivamente para adquisición en cuarentena; no hay dataset admitido, fits científicos, scoring ni órdenes.

> Auditoría premercado vigente: TECHNICAL_PRETRAINING_CLOSED; 68 tests, imports y compilación PASS. 18 gates y cuatro estados verificados; dataset 0 M5, WAITING_FOR_DATA, sin admisión ni grant. Sin acción manual. [Informe definitivo](BC_FINAL_PREMARKET_AUDIT.md). Los apartados previos son históricos.

> Estado vigente — cierre pre-entrenamiento: tarea existente e IPC integrados, guardian verifica admisión automáticamente, 54 tests PASS; 0 M5/0 señales, WAITING_FOR_DATA, sin admisión ni entrenamiento. El bloqueo anterior de edición de tareas se resolvió reutilizando los servicios instalados; no requiere acción manual. [Informe consolidado](BC_FINAL_PRETRAINING_CLOSURE.md). Los apartados anteriores describen estados históricos.

## Corte y exclusividad

Estudio: `US30CASH_M5_XM_TRAIN_FUTURE_EVAL_PROPOSED_V1`. Dataset de captura: `bc_train_f6b99cbfc59542a38627868015f65792`. Productor: `bc_history_43a3fd9587504d7586c04d9f28548a81`. Epoch: `bc_epoch_0482f829cded4fb0957d6e0dc11804c5`.

Corte Ecuador: **2026-11-08T11:23:07.713468-05:00**, estimación UTC **2026-11-08T16:23:07.713468+00:00**. Cota UTC registrada: **[2026-11-08T16:23:07.321083+00:00, 2026-11-08T16:23:08.105853+00:00]**, semiancho 0.392385152 segundos. Son dos mediciones NTS autenticadas que encierran la activación; la cota depende del error anunciado por el servidor. No certifica la generación física de los ticks XM ni extrapola un offset fijo.

El ingreso futuro C+F se cerró ordenadamente mediante su control operativo existente. Se esperó a que el productor liberase su lock después de persistir. Verificados 47.173 registros finales, cabecera y checkpoint, cero registros añadidos después del cierre y manifests originales sin cambios. Contratos y datos anteriores intactos. El registro B anterior no se reasigna.

La última cotización al corte era antigua. Por eso `native_floor=null`: el worker exige una cotización nativa estrictamente más reciente que el ancla posterior al corte y omite también su intervalo en formación. Solo entonces vinculará el siguiente inicio M5 y podrá consultar intervalos completos posteriores. El corte de autorización es real; el primer intervalo nativo adquirible sigue pendiente. No se convierte una etiqueta nativa en UTC certificado.

## Evidencia real actual

Al recibo 2026-11-08T19:09:21.386082+00:00 (etiqueta del host): estado `WAITING_FIRST_NEW_NATIVE_QUOTE`. Intervalos adquiridos=0; M5 verificadas=0; consecutivas=0; rechazadas=0; warmup=0/350; señales=0/800; BUY=0; SELL=0; posteriores=0/100; evaluables=0. DATASET_HASH=null. Nada de las 88 M5 C+F ni de las 251 M5 B se suma al nuevo estudio.

El proceso observado consumió 38.3 MiB. La tarea `StochasticGPTLab_PC_A_BCTrainAcquisition_v1` tiene disparador al inicio de sesión y cada cinco minutos, IgnoreNew, lock de archivo, presupuesto de seis intervalos por ejecución, límite de cuatro minutos y reintentos. Ejecución real completada con resultado 0 el 8 de noviembre a las 13:54:44 Ecuador. También hubo errores transitorios IPC y un rechazo del programador; no se atribuyen a una causa no probada. La conexión se recuperó sin reiniciar Windows ni XM. Los fallos conservan recibos inmutables locales y no modifican el corte.

La tarea requiere sesión del usuario; no se promete ejecución gráfica antes de iniciar sesión. La recuperación tras apagado físico queda configurada, pero no se ha provocado ni certificado un reinicio físico. NTS y guardian existentes siguen siendo reutilizados. La tarea diagnóstica B antigua encuentra el monitor C+F cerrado/stale; el intento de desactivar su sondeo redundante fue denegado por Windows y la tarea quedó sin cambios. Ese índice antiguo no es una dependencia de B+C; sus datos y permisos se conservan.

## Implementación y pruebas

La adquisición reutiliza CopyRates/CopyTicksRange y la corrección de endpoints existente. Guarda cada vintage, fecha de recuperación, identidad, hashes de payloads y manifest, sin afirmar recepción original. Los roles TRAIN_CONTEXT/TRAIN_DEV y el exposure ledger están ligados al nuevo corte. El ledger SQLite append-only y el checkpoint se confirman en una transacción. Un intento incompleto no se sobrescribe; un vintage histórico reparado crea una revisión derivada y replay identificados, sin duplicar contadores ni tocar prospectivos anteriores.

Se verifica Bid/Ask, OHLC, cinco M1 frente M5 y volumen según flags BID. Solo una paridad completa permite derivar contexto en cuarentena. Las primeras 350 barras son exclusivamente contexto; la primera señal elegible puede estar en la barra 351. Se conservan 800 señales base y 100 barras posteriores, 200 evaluables, 80 por lado y tres folds por lado. No hay labels ni resultados científicos producidos en esta misión. Los horizontes completos y el soporte purgado tendrán que demostrarse con los datos futuros antes de preparar la admisión.

ATR usa exactamente el archivo candidato aprobado, hash `9bc2efb0e3a2d1af750d4c47ce38fb8ca2b245639856c63ba210a82d23c70dfc`. Heikin Ashi se inicializa con el primer bar del nuevo contexto. MAIN_K y reglas BUY/SELL permanecen congelados. Los ensayos nativos se intentarán en hitos 15, 30, 276 y 350 de barras propias recuperadas, como máximo un oráculo por ejecución; un PASS sellado no se repite. Falta evidencia real nueva para esas pruebas.

Calendario PARTIAL. Un hueco nativo no demostrado segmenta el contexto; un reinicio de proceso o de Windows por sí solo no elimina el histórico recuperable. No se unen sesiones con excepciones desconocidas. En particular, los 350 M5 requieren demostrar cruces de sesión: la tarea no inventa esa evidencia ni puede garantizar hoy una racha de 350. El origen histórico aprobado permite recuperar intervalos tras desconexiones; no permite fabricar barras ni certificar gaps ambiguos.

**38 tests PASS** (36 principales y dos adicionales de IPC), solo fixtures y estimadores simulados. Incluyen persistencia entre ejecuciones, revisión histórica sin sobrescribir, límites del corte, causalidad de prefijos, contexto 350, gaps y preflight. El entrenador conserva BUY/SELL × cuatro folds, ocho fits máximos, escalado solo en TRAIN y grant obligatorio. Para este estudio se conectó la conservación inmutable de los modelos fold4, con hashes y bracket NTS antes de cualquier EVAL, sin noveno fit ni selección por rendimiento. Las listas de admisión y entrenamiento siguen vacías.

La recurrencia de fallos IPC motivó un wrapper operativo separado y sellado: tras el timeout original de cinco segundos, permite un único reattach de veinte segundos a la misma instancia exacta y vuelve a verificar identidad. No reinicia XM ni cambia tolerancias científicas. El wrapper ejecutó una lectura real correcta y pasó dos tests simulados. Windows denegó Set-ScheduledTask y Register-ScheduledTask para actualizar la tarea, incluso tras intentar UAC: **el wrapper todavía no está desplegado en la tarea periódica**, que conserva la estación original y sus reintentos cada cinco minutos. El helper scripts/Update-BCWorkerTask.ps1 está preparado; aplicar esa mejora requiere una cuenta con permisos sobre la tarea. No se declara aplicada. Los recibos distinguen el último éxito de los fallos transitorios posteriores.

EVAL_CONTEXT y EVAL_PROSPECTIVE están inactivos. Requieren modelos congelados, cierre de labels y purga TRAIN y autorización posterior. Ningún check de orden por sí solo autoriza scoring o certifica procedencia UTC.

## Pendientes y siguientes acciones

1. Esperar una cotización nativa nueva y registrar el primer límite adquirible; adquirir automáticamente solo su futuro reservado.
2. Acumular contexto y señales, verificar vintages, semillas y oráculos en los hitos. Resolver calendario y cobertura con evidencia del nuevo periodo; mantener las incertidumbres en cuarentena.
3. Completar horizontes, folds, membership y causalidad, después generar el dataset sellado y el paquete de admisión. No se solicita un grant incompleto ni se autoadmiten datos.
4. Únicamente después de admisión, presentar la solicitud específica por hashes para ocho fits. No existe autorización de entrenamiento actual.

DISCOVERY_VALIDATION=BLOCKED; HISTORICAL_HOLDOUT=LOCKED; FINAL_TEST=LOCKED; DEMO=DISABLED; LIVE_TRADING=false; terminal_trade_allowed=false; TRAINING_EXECUTED=false; PROTECTED_SCORING=false. No se modificó el otro proyecto.

Recibos, decisión y hashes: [índice](../research/studies/bc_train_future_eval_v1/index.json). El HEAD padre revisado se registra en el índice; el commit contenedor identifica esta publicación sin una referencia circular a su propio hash. Los recibos automáticos futuros se guardan localmente; su publicación remota requiere una sesión o credencial GitHub autorizada.
