# Pipeline prospectivo — cierre de cobertura nativa, 1 noviembre 2026

## Cambio concreto

Se conserva el pipeline y se corrige una insuficiencia demostrada: un agregado con OHLC y volumen idénticos puede contener otra secuencia de cotizaciones. El test usa [100,105,95,100] frente a [100,95,105,100]: mismos OHLC y número de actualizaciones, recorrido distinto. El criterio anterior era solo paridad de agregado y nunca certificó admisión; ahora tampoco puede emitir una barra derivada válida sin concordancia de secuencia BID.

El worker calcula incrementalmente un SHA256 encadenado por cada actualización BID recibida, conservando su orden, time_msc, bid/ask en grilla exacta y flags. Después de cerrar un intervalo completo observado se contrastan sus OHLC/volumen con CopyRates y el digest/count BID con CopyTicksRange de ese mismo intervalo nativo. Un faltante, cotización adicional, orden diferente, valor alterado o referencia no disponible mantiene el bucket INCOMPLETE y fuera de features y warmup. No se ordenan/corrigen filas ni se introducen tolerancias. El primer bucket parcial no provoca consultas nativas.

La referencia CopyTicksRange es una **reconsulta histórica de comparación**, no captura prospectiva ni entrada de las features. Solo se conserva su resumen/hash y tiempos de consulta. Ninguna fila de referencia se añade al raw, rellena un hueco, repara una barra, cambia timestamps o se cuenta como observación independiente. Las features siguen calculándose exclusivamente con las cotizaciones raw originales. Un guard operacional de 16 MiB rechaza íntegramente una respuesta demasiado grande; no recorta filas ni relaja cobertura.

Documentación oficial: https://www.mql5.com/en/docs/series/copyticks distingue notificaciones OnTick de todos los ticks. https://www.mql5.com/es/docs/python_metatrader5/mt5copyticksrange_py describe la reconsulta por intervalo. Sus afirmaciones genéricas sobre UTC no se convierten en prueba específica de XM: las etiquetas originales permanecen en dominio nativo. La coincidencia de secuencia contra el archivo del mismo broker verifica únicamente correspondencia con esa versión de referencia; no es fuente independiente del instante de generación ni certificación de UTC, sesiones completas o historial inmutable del broker.

## Actualización sin reemplazar el capturador

El raw collector y el observador MT5 no cambiaron. El worker derivado salió voluntariamente entre transacciones mediante su flag; el colector siguió registrando raw. Se conservan SQLite, todos los artefactos, source cursors, hash chain, manifiesto original y deployment_pin.json original byte a byte. Un pin nuevo versionado se selecciona por un puntero hasheado; CODE_VERSION registra la transición en el ledger append-only antes de nuevos inputs. Se verificó que el prefijo anterior sigue íntegro y que la recuperación no reinicia cursores ni duplica artefactos. No había barras ni buckets de mercado previos que reclasificar.

El supervisor existente lo relanzó automáticamente y el nuevo worker volvió a avanzar con callbacks reales. La pausa de derivación no se representa como ticks perdidos ni como backfill: procesa raw prospectivo ya conservado, con source_receipt original y compute_clock efectivo separados. El estado de madurez refleja ahora si el raw deja de estar reciente, en lugar de afirmar ACTIVE solo porque vive el proceso.

## Cálculos y ciencia preservados

El método Processor.features permanece idéntico, verificado por SHA256 de su fragmento exacto frente al source aprobado del commit dbd43f362c69ed710d45ada67b5a9194622c6cc2. Se reutiliza su evidencia nativa de 499 barras sintéticas: MAIN_K, ATR y HA concordaron; no se repitió ese probe aprobado. Los módulos MAIN_K 5/3/3, HeikinAshiCore, ResearchCore, protocolo y umbrales congelados no cambian. La igualdad de fragmento verifica esta implementación; no eleva la causalidad global de datos vivos a PASS.

La versión inicial publicada sigue intacta como evidencia histórica. Sus afirmaciones de paridad eran scoped al agregado. Esta actualización exige además secuencia nativa, sin reinterpretar retrospectivamente aquella evidencia ni fabricar un certificado real donde no hay datos.

Se mantienen 350 M5 propios, primeras 800 señales consecutivas, 100 barras posteriores, total evaluable mínimo 200 y 80 por lado. Las señales siguen evaluable=false hasta todas las condiciones y autorización aplicables. Los gaps anteriores mantienen protocol_stream_unbroken=false: no se elige silenciosamente un periodo limpio, no se reinicia el estudio ni se extiende la selección por resultados. Un contexto local puede calentarse por segmento, pero no equivale a nueva cohorte admitida.

El ledger enlaza membresía raw, derivados y versión de código; su prefijo fue verificado mediante transacción de solo lectura. No inventa los memberships/splits desconocidos del TRAIN agotado, Discovery Validation, Historical Holdout o Final Test. La exposición registra acceso y derivación sin labels ni scoring. Continúa pendiente demostrar no solapamiento y procedencia temporal bajo los contratos vigentes.

## Resultado y límites

64 tests afectados PASS: comparación de recorridos con agregado idéntico; pérdidas/adiciones/alteraciones; orden y empates; BID frente a ASK-only; referencia ausente; grilla/intervalos; guard de recursos; ejecución incremental completa con fixture; punteros de deployment y cambio de código; causalidad y recuperación anteriores. Ninguna prueba abrió conjuntos protegidos, ejecutó entrenamiento o scoring ni envió órdenes.

El corte real sigue mostrando cero ticks, barras M1/M5, features o señales de mercado. M5_PARITY de mercado continúa PENDING. El worker sí procesa nuevos heartbeats reales; esto prueba liveness y avance de cursores, no funcionamiento en condiciones de mercado activo. Las consultas de ticks de referencia aún no se han ejecutado sobre datos vivos porque no existe ningún bucket real cerrado. Los tests de referencia usan fixtures/adaptadores, sin presentarlos como certificación de servidor.

Todos los artefactos siguen QUARANTINED, DATASET_HASH=null, CAUSAL_AUDIT=FAIL y TRAINING_READINESS=BLOCKED. Discovery Validation e Historical Holdout bloqueados, Final Test LOCKED, DEMO DISABLED, LIVE_TRADING=false. No se modificó el otro proyecto ni se repitieron pruebas de energía/instalación o reinicio físico. No hay intervención manual pendiente ahora. Próximo estado: procesar ticks reales cuando lleguen, verificar barras y su secuencia de referencia y publicar progreso sin fabricar fechas de madurez.
