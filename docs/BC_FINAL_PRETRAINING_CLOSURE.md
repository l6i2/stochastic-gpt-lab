# Cierre pre-entrenamiento B+C

El estudio `US30CASH_M5_XM_TRAIN_FUTURE_EVAL_PROPOSED_V1` sigue activo en cuarentena. La infraestructura necesaria está preparada y las tareas existentes ejecutan la adquisición y la revisión automática. No se admitió un dataset ni se entrenó una IA.

## Evidencia operativa

La reconexión real desconectó y reconectó solo el cliente IPC contra el mismo MT5 PID 18064, con servidor XMGlobalSC-MT5 5, US30Cash y trading deshabilitado. Se añadió al conector existente un único reintento acotado de cinco a veinte segundos, con identidad/PID verificados antes y después. No se reinició Windows ni XM. No es una tolerancia de calidad científica ni una promesa de disponibilidad perpetua.

Windows denegó cambiar tareas mediante cmdlets, COM y elevación legítima; el recibo confirma administrator=true y applied=false. Se resolvió mediante la alternativa autorizada de reutilizar el worker y el guardian instalados: las definiciones de tareas permanecen intactas. No se cambiaron ACL ni privilegios globales. Los intentos de tarea adicional y acceso directo tampoco se aplicaron; el watcher temporal se detuvo. No queda ninguna instrucción manual necesaria.

La tarea de adquisición completó ejecuciones reales con salida 0 después de la reparación. El guardian PID 28100 lanzó automáticamente el helper 26640; su cadena de ancestros lo demuestra. A las 2026-11-08T16:02:37.237979-05:00 Ecuador el helper emitió `WAITING_FOR_DATA` en solo lectura. La nueva revisión no arranca otro capturador. Usa lock y marcador de datos/proofs/código para no reevaluar inputs idénticos. Git se resuelve por ruta comprobada aunque el servicio no tenga PATH interactivo.

El último registro NTS examinado, 2026-11-08T15:59:12.166116-05:00 Ecuador, conserva hash/cabecera válidos y una medición autenticada de time.cloudflare.com; ntppool2.time.nl figura UNAVAILABLE. No se ejecutó otro probe NTS. Esta autenticación no certifica la generación del evento XM.

La recuperación conserva el checkpoint y la cadena activos B+C y verifica el cierre C+F sin intentar reactivar su productor antiguo. Sus 47.173 registros y manifests permanecen preservados. No se debilitó su pin científico ni se modificaron contratos anteriores. Las conexiones SQLite ahora se cierran explícitamente. El próximo arranque natural generará un recibo de transición; reinicio físico y recuperación de ticks tras ese arranque siguen sin prueba real. No se provocó un reinicio.

## Dataset y estados reales

Corte de autorización original: 8 de noviembre de 2026, 11:23:07,713 Ecuador; bracket NTS UTC [16:23:07,321083; 16:23:08,105853], condicionado al error remoto anunciado. No certifica generación UTC del broker. Dataset de captura `bc_train_f6b99cbfc59542a38627868015f65792`. El primer límite nativo sigue null hasta observar una cotización estrictamente posterior al ancla y omitir su barra en formación.

Al recibo 2026-11-08T15:59:45.187179-05:00 Ecuador (etiqueta del host; UTC original conservado en JSON): **0 M5**, contexto **0/350**, señales **0/800**, posteriores **0/100**, evaluables **0/200**, BUY **0/80**, SELL **0/80**, folds por lado **0/3**. No existen intervalos adquiridos nuevos; DATASET_HASH admitido=null. Las 88 M5 C+F y 251 M5 B antiguas no se cuentan. El proceso observado consumió 26.4 MiB. La ausencia legítima de cotizaciones se representa WAITING_FOR_MARKET / WAITING_FOR_DATA, no como un fallo de integridad.

HISTORICAL_ACQUISITION=READY_WAITING_FOR_DATA: mecanismos y endpoints probados, pero aún no hay adquisición real posterior al nuevo corte que pueda declararse PASS. Los registros recuperados siempre conservan vintage, tiempo de descarga, hashes y origen retrospectivo. No se presentan como recepción original ni rellenan cohortes prospectivas anteriores.

## Indicadores, causalidad y admisión

MAIN_K, reglas 5/3/3 y niveles 20/80, BUY/SELL, FOLLOW/INVERT, TP240, SL180 y TIME_EXIT100 permanecen congelados. ATR usa la variante aprobada con hash 9bc2efb0e3a2d1af750d4c47ce38fb8ca2b245639856c63ba210a82d23c70dfc. El adapter nuevo comprobó 287 valores ATR contra el export MQL sintético existente, sin ejecutar otro probe sobre datos antiguos. Eso es TECHNICAL_TEST_PASS; la paridad del dataset nuevo espera datos.

Los oráculos se disparan en prefijos propios 15/30/276/350, ligados a sus hashes y semilla; un resultado de otro epoch o vintage no basta. Un prefijo con una transición cerrada previamente certificada usa el adapter aislado preparado para conservar sus timestamps reales. No se activa ningún puente hoy: el registro de calendarios y la lista de certificados independientemente verificados están vacíos. Falta evidencia específica del servidor y excepciones fechadas. No basta una declaración local o un hash de un documento genérico.

Los 18 gates cubren independencia, exclusividad, membership, procedencia, ticks, OHLC, Bid/Ask, continuidad, calendario, ATR/HA, causalidad, features, horizontes, leakage, folds, hashes y reproducción. Devuelven WAITING_FOR_DATA, WAITING_FOR_EVIDENCE o FAIL según la evidencia; contadores completos solo permitirían preparar revisión, nunca autoadmisión. La auditoría global sigue **FAIL**; la causalidad nativa B+C tiene validadores implementados y espera evidencia real.

Los labels técnicos futuros usan únicamente el nuevo TRAIN permitido y los baselines congelados. Antes de calcularlos se congela una lista de manifests/vintages; snapshot, revisión, membership y paquete se conservan por generación inmutable. La entrada es la primera quote ejecutable de la siguiente barra, con feature_max_time < quote_time = decision_time. TIME_EXIT exige su quote real en entry_index+100; si el límite de 100 barras posteriores no la contiene, el label queda censurado, no se fabrica una barra adicional. Las filas censuradas no cuentan como evaluables. Los soportes se cuentan después de la purga; se comprueban ambas clases para las ocho posiciones. No se extiende la muestra ni se cambia la regla para obtener soporte.

## Entrenador y autorización

TRAINING_PIPELINE_READY=READY_BUT_GATED. Se corrigió el gate que apuntaba al protocolo legacy: B+C ahora vincula su contrato aprobado y su whitelist exacta, sin cambiar el camino legacy. Se preservan cuatro folds cronológicos purgados, logística L2 C1, escalado solo en TRAIN, ocho fits y modelos finales fold4 prefijados. La autoridad se comprueba antes de leer el dataset o crear estimadores; integridad, contexto, presupuesto, orden y soporte se comprueban antes de fits. No se ejecutó ningún fit científico.

El paquete futuro se rellena con hashes reales de código, entorno, protocolo, whitelist, membership, exposición, dataset candidato y plan cuando existan. Los campos de datos faltantes permanecen null. El candidato sigue en pretraining_quarantine; las allowlists ADMITTED_PACKAGE_HASHES y AUTHORIZED_GRANT_HASHES permanecen vacías. No se produce una solicitud de entrenamiento prematura. EVAL_CONTEXT/EVAL_PROSPECTIVE siguen inactivos hasta congelar modelos, cerrar labels/purga y obtener autorización posterior.

**54 pruebas PASS**, con fixtures y estimadores simulados: rechazo sin grant, protocolo B+C correcto, replay Bid/Ask, censura temporal, prefijos sin futuro, presupuesto de ocho fits, modelos fold4, hashes, cache alterada, cierre SQLite, reinicio simulado sin falsa prueba física y reconexión acotada. La operación real se acredita por separado con los recibos de IPC, tarea, checkpoint y guardian.

## Próximas acciones automáticas

La cotización nueva fija el primer intervalo nativo; adquisición versionada, agregación/verificación, prefijos, labels técnicos y revisión avanzan con inputs nuevos. Los oráculos esperan sus hitos. Al completar la evidencia se prepara el expediente; admisión científica y grant específico siguen siendo puertas separadas. No se programó ningún entrenamiento.

Quedan datos nuevos, calendario/continuidad certificados, paridad de las semillas propias, soporte purgado y admisión. No se cambió ningún umbral. No hay código de adquisición pendiente de instalación para la operación vigente. La prueba física de recuperación se observará en el próximo arranque natural.

DISCOVERY_VALIDATION=BLOCKED; HISTORICAL_HOLDOUT=LOCKED; FINAL_TEST=LOCKED; DEMO=DISABLED; LIVE_TRADING=false; terminal_trade_allowed=false; TRAINING_EXECUTED=false; PROTECTED_SCORING=false. Cero órdenes, sin tocar el otro proyecto.

Recibos estructurados y hashes: [índice](../research/studies/bc_train_future_eval_v1/final_pretraining_closure/index.json). La publicación se identifica por su commit contenedor; el índice registra el HEAD padre revisado y evita una referencia circular a su propio commit. Los recibos locales continúan automáticamente; publicar actualizaciones remotas requiere una sesión o credencial GitHub autorizada.
