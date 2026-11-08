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
