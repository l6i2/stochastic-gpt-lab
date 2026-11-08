# Propuesta única de primer entrenamiento

STUDY_ID: `US30CASH_M5_XM_TRAIN_FUTURE_EVAL_PROPOSED_V1`. Estado DRAFT_INACTIVE. DATASET_ID=null, DATASET_HASH=null, reserva y corte=null. No se autoriza entrenamiento con este documento.

Objetivo: comparar logística L2 con FOLLOW e INVERT en BUY y SELL, cuatro hipótesis primarias. Mantener Stochastic MAIN_K 5/3/3, niveles 20/80, TP240, SL180, TIME_EXIT100 y Bid/Ask originales. Whitelist: stoch_k, delta_k_1, ATR, relative_volume_20, ha_direction, range_to_ATR. Sin selección de nuevas features.

## Universo, fuentes y roles

No hay intervalo actual elegible. Tras una aprobación futura, establecer corte exclusivo verificable posterior a ella, sin inventar precisión UTC. Cerrar únicamente nuevas incorporaciones C+F posteriores a ese corte; preservar datos, derechos, restricciones y hashes anteriores. Reservar una secuencia nueva con roles TRAIN_CONTEXT y TRAIN_DEV; posteriormente EVAL_CONTEXT y EVAL_PROSPECTIVE separados. No importar B ni legacy. Esta es una propuesta de reserva, no una asignación ejecutada.

TRAIN puede adquirirse de historial nativo XM después de ocurrir los eventos, con vintage, servidor, símbolo, límites, orden de empates, hashes y manifest inmutables. Registrar explícitamente recuperación, no recepción original. Antes de labels, congelar las versiones de datos. Ledger por intervalos y señales, identidad de productor y código; roles sin doble asignación, incluyendo contexto y horizontes de salida. La ausencia de solapamiento requiere evidencias de los límites, no leer contenido protegido.

## Contexto, causalidad y cobertura

El método propuesto exige 350 M5 completas de contexto antes de la primera señal elegible; primera señal posible en barra 351 (base uno). Después, primeras 800 señales base consecutivas y 100 barras posteriores, mínimo 200 evaluables, 80 BUY, 80 SELL y tres folds evaluables por lado. Muestra insuficiente: NOT_READY, sin prolongar tras observar rendimiento. C+F vigente no cambia.

Solo barras cerradas anteriores a decisión y quote disponible antes de decisión. Reconstrucción histórica demuestra disponibilidad en dominio nativo, no latencia real ni tiempo físico UTC de generación. Seeds ATR y HA expresas, prefijos independientes y paridad con oráculo nativo ligado al contexto. ATR candidato sigue sin promoción: su aprobación y pin pertenecen a la decisión metodológica. No usar una recurrencia distinta como reparación silenciosa.

Exigir paridad M1/M5, ticks y volumen según semántica congelada, Bid/Ask válido, identidad estable y horizonte completo de cada salida. Gaps inexplicados, revisiones incompatibles o excepciones no demostradas quedan en cuarentena. Cruces de sesión requieren calendario aplicable y cobertura de transición/excepciones demostrada. No imponer offset XM; Ecuador es la visualización principal y Nueva York usa DST histórico. UTC externo se informa aparte.

## Entrenamiento y evaluación independiente

Cuatro folds cronológicos purgados con dependencias y labels completos fuera de cada evaluación; transformación ajustada solo en TRAIN. Logística L2 C1, lbfgs, max_iter1000, seed20261030. Ocho fits máximos (BUY/SELL × cuatro folds), cero búsquedas y cero refit final. Congelar para evaluación futura los modelos del fold 4 por lado, elegidos de antemano, sin comparar ganadores. Hash de modelos, entorno, código, whitelist y protocolo antes de la primera observación EVAL. El hook está preparado; no hay artefacto científico entrenado.

EVAL empieza después de congelar modelos y cerrar el último label TRAIN y su purga. Contexto EVAL separado adquirido después de congelar modelos; no reutilizarlo para ajustes. Evaluación prospectiva sin backfill, resultados cerrados hasta un permiso específico. El primer entrenamiento puede preceder a la acumulación de EVAL, pero no permite afirmar rendimiento independiente. No se abren Discovery Validation, Historical Holdout ni Final Test anteriores.

## Estadística, rechazo y riesgos

Cuatro contrastes pareados: BUY/SELL frente FOLLOW/INVERT. Bootstrap 10.000, seed20261030; intervalos descriptivos 95%, límite inferior unilateral 98,75% >0 para las cuatro comparaciones; sensibilidad por bloques de 451 barras observadas. Exigir fracción de folds positivos ≥0,70, concentración positiva por fold ≤0,50 y drawdown proxy ≤1,20 de cada baseline. Dependencia no resuelta o bootstrap degenerado: INCONCLUSIVE. Sin retuning, ampliaciones por PnL, ni consumo adicional de hipótesis.

Riesgos: revisiones del historial, retención XM, causalidad de seeds, discontinuidades de sesiones, dependencia serial, insuficiente soporte por lado y discrepancia entre backtest y ejecución. El histórico no prueba ejecución real. Faltan reserva aprobada, datos nuevos, límites y calendario demostrados, seeds aprobadas, membership completo y recibos de admisión. Después se requiere un grant específico por hashes, nunca una autorización implícita.

Definición estructurada: [proposal.json](../research/studies/first_training_five_paths_20261108/proposal.json). Decisión única: [solicitud](../research/studies/first_training_five_paths_20261108/SCIENTIFIC_DECISION_REQUEST.md).
