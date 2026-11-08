# Viabilidad de un estudio híbrido independiente

La recuperación histórica permite usar PC A con apagados diarios y conservar información útil del broker, siempre que XM siga proporcionando ese historial. Ya facilita validar agregación, indicadores y fallos de adquisición. No elimina retrospectivamente las interrupciones de observación C+F.

## Qué datos existen y qué independencia tienen

El registro A contiene las observaciones originales del estudio US30CASH_M5_NATIVE_OBSERVATIONS_20261105_01. El registro B es una descarga posterior de intervalos que ya pertenecen a esa reserva. Cambiar ruta, ID o fecha de descarga no crea independencia. El nuevo ledger de exposición clasifica B como copia diagnóstica de intervalos reservados a C+F, con ausencia de labels o scoring científico.

Los límites originales de algunas reservas legacy siguen sin reconciliarse. La autorización del corte existente resuelve el ingreso futuro desde PC A para C+F, pero no concede una reserva científica al registro B. Los históricos actuales quedan fuera de un nuevo entrenamiento independiente.

## Protocolo propuesto, inactivo

Se propone un estudio futuro US30CASH_M5_XM_HYBRID_PENDING_AUTHORIZATION. Su objetivo sería evaluar logística L2 frente a FOLLOW e INVERT, por separado para BUY y SELL, sobre un periodo futuro reservado antes de recopilar o inspeccionar sus resultados. Las cuatro hipótesis primarias serían BUY frente a cada baseline y SELL frente a cada baseline. No se activan con esta propuesta.

La estrategia mantendría K=5, D=3, Slowing=3, MAIN_K 20/80, TP=240, SL=180, TIME_EXIT=100 y la semántica Bid/Ask vigente. La whitelist propuesta conserva stoch_k, delta_k_1, ATR, relative_volume_20, ha_direction y range_to_ATR. Se propone logística L2 C=1, semilla fija, escalado solo en TRAIN de cada fold y cuatro folds cronológicos purgados. El presupuesto propuesto sería ocho fits y una ejecución, con cero búsquedas. El presupuesto autorizado actual es cero.

Como punto de partida para aprobación, se conservarían 350 barras de contexto, las primeras 800 señales base, 100 barras posteriores, 200 señales evaluables, 80 por lado y tres folds evaluables por lado. El nuevo protocolo necesitaría definir expresamente continuidad del historial nativo, disponibilidad de features reconstruidas y tratamiento de recuperaciones. Esa definición es distinta de acreditar recepción original en vivo y no se aplica al contrato C+F existente.

La adquisición asignaría cada intervalo una sola vez, con fuente, hora de descarga, ordinal dentro de timestamps iguales, hashes y vintage. Las consultas repetidas conservarían todas sus versiones, identificando discrepancias. Antes de producir labels se congelaría un snapshot del historial y se auditaría su cobertura. Los datos recuperados nunca heredarían un timestamp de recepción prospectiva.

La admisión requeriría paridad exacta M1/M5, datos Bid/Ask válidos y cobertura suficiente de los horizontes de decisión y salida. El orden de ticks simultáneos se preservaría. Las discrepancias y los huecos no explicados quedarían en cuarentena. Las reglas de sesiones y excepciones tendrían evidencia aplicable. Los indicadores recurrentes usarían seeds declarados y un oráculo nativo ligado a esa inicialización.

El ATR candidato necesita una decisión específica sobre su versión y pin. El estudio no asumiría que un PASS sintético o retrospectivo certifica el instante original de generación. Un backtest de historial revisado tampoco acredita latencia, ejecución ni rendimiento prospectivo real.

Las cuatro comparaciones heredarían, previa aprobación, bootstrap pareado de 10.000 resamples con seed 20261030, límite inferior unilateral 98,75% mayor que cero y sensibilidad por bloques de 451 barras observadas. Se exigirían efecto positivo en al menos 70% de los folds, concentración de efecto positivo por fold no mayor de 50% y drawdown proxy no más de 20% peor que cada baseline. IC degenerados o dependencia que impida interpretarlos producirían INCONCLUSIVE. El JSON vincula por hashes el protocolo estadístico y la whitelist propuestos. La purga cubriría los horizontes completos. La recolección no se prolongaría después de ver rendimiento. Una muestra insuficiente produciría NOT_READY. No se abrirían Discovery Validation, Historical Holdout ni Final Test anteriores.

## Decisiones y fuentes pendientes

Se requiere autorización para una reserva futura sin solapamiento. Como C+F mantiene la reserva exclusiva, no basta declarar independiente otra descarga del mismo símbolo. Una nueva asignación exigiría una decisión expresa sobre el alcance futuro, con corte real registrado después de autorizarla. Esta ejecución no cambia esa reserva.

También se requiere aprobar el método retrospectivo/híbrido y sus seeds, después admitir un dataset sellado y finalmente conceder un grant de entrenamiento ligado a hashes. STUDY_ID es provisional; DATASET_ID y DATASET_HASH siguen null. El paquete de entrenamiento no está listo para autorizar.

El historial recuperado actual acelera la preparación técnica. El primer entrenamiento independiente aún necesita el periodo futuro reservado, el dataset admitido y la autorización correspondiente. El [protocolo estructurado](../research/studies/xm_historical_recovery_20261108/hybrid_proposal.json) y el [ledger diagnóstico](../research/studies/xm_historical_recovery_20261108/exposure_ledger.json) permiten revisar esa diferencia sin activar nada.


## Cierre cinco rutas — 2026-11-08

STATUS observado 2026-11-08T15:58:07.130622+00:00 (etiqueta de host, no generación UTC certificada): epoch 39_398136265, 88 M5 acumuladas, 0 consecutivas, 0 warmup científico; BUY=0, SELL=0. B conserva 246.397 ticks, 1.295 M1 y 251 M5 en 302 intervalos únicos; 320 intentos preservados. No hubo nuevas consultas históricas en esta misión. Ningún intervalo actual está demostrado elegible para nuevo TRAIN. Se recomienda ruta B con adquisición C y soporte D/E, condicionada a reserva futura y método aprobado; no se activa ni reasigna C+F.

25 pruebas sintéticas y simuladas PASS; corregidos árbol local sin revisar, límites observados ausentes y soporte purgado insuficiente antes del fit. Cero fits científicos, admisiones y grants vacíos. CAUSAL_AUDIT=FAIL, TRAINING_READINESS=BLOCKED. DEMO=DISABLED, LIVE_TRADING=false. Guardian en ejecución y UTC periódico observado Running/Ready, recuperador diagnóstico programado; C+F sigue ACTIVE_QUARANTINED.

Expediente único: [cinco rutas](XM_FIVE_PATHS_TO_TRAINING.md), [propuesta](PROPOSED_FIRST_TRAINING_STUDY.md), [plan de admisión](TRAINING_ADMISSION_ACTION_PLAN.md). Faltan decisión metodológica/reserva, datos nuevos, cobertura/calendario/seeds demostrados y admisión por hashes; después autorización específica de entrenamiento. No se solicitan reparaciones manuales.


## B+C autorizado y activado — 2026-11-08

La decisión metodológica y la reserva futura ya fueron autorizadas; el corte exclusivo se aplicó a las 2026-11-08T11:23:07.713468-05:00 (Ecuador, con bracket NTS condicionado). C+F anterior conserva 47.173 registros y sus derechos; su ingreso futuro está cerrado. Nuevo dataset de captura `bc_train_f6b99cbfc59542a38627868015f65792`, en cuarentena, sin admisión ni grant de entrenamiento. El primer intervalo nativo sigue pendiente de cotización nueva: 0 M5, 0/350 contexto y 0/800 señales. No se importó A, B ni legacy.

38 pruebas PASS con fixtures y estimadores simulados. Adquisición B+C programada al inicio de sesión y cada cinco minutos; ejecución real comprobada con salida 0, con fallos IPC transitorios documentados. El wrapper de reattach está probado pero Windows denegó actualizar la tarea: mejora pendiente de permisos administrativos, tarea original conservada. Calendario/puentes y paridad de semillas del nuevo contexto siguen pendientes; auditoría global no promocionada. No se ejecutaron fits científicos, scoring ni órdenes. Informe único vigente: [activación B+C y readiness](BC_STUDY_ACTIVATION_AND_READINESS.md). Los apartados previos describen estados históricos.
