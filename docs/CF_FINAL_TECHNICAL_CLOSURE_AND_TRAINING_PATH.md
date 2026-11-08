# Cierre técnico y ruta al primer entrenamiento C+F

El corte actual conserva 500 M1 y 88 M5 verificadas, 0 M5 consecutivas y 0 elegibles, con el productor activo en cuarentena. Se comprobó la permanencia del prefijo publicado. Se preparó un candidato ATR versionado con restauración de checkpoint y se añadió al monitor la factibilidad matemática por sesión. Pasaron 95 pruebas autorizadas. La admisión permanece WAITING_FOR_EVIDENCE y los fits científicos son cero.

## Matriz de bloqueos

| Ruta | Completado en esta ejecución | Pendiente concreto |
|---|---|---|
| ATR | Candidato independiente con esquema propio, exactitud de 287 valores sintéticos y restauración antes de cada barra. Replays de los exports propios preservados. Hash del candidato incluido en el job futuro. | Prefijo real de 30 M5 propias y revisión de integración/pin. |
| HA y features | Pruebas de persistencia, disponibilidad, mutación futura y límites de readiness. Se conserva el oráculo sintético anterior de 300 OHLC y 25 direcciones exactas. | HA propio a 276 barras y contexto completo. |
| Estabilidad | Conexión demo e identidad verificadas, proceso y tareas existentes, NTS con una fuente autenticada. Checkpoint y prefijo anterior intactos. | Causa de interrupciones desconocidas y continuidad futura. |
| Calendario | Cota condicional de 276 M5 por intervalo QUOTE incorporada al reporte automático. Monitor de primera cotización armado. | Transición real, calendarios antes/después y excepción fechada exacta. |
| Madurez | Contadores separados, roles exclusivos en cuarentena y controles de admisión conservados. | 350/800/100/200/80/80 y tres folds evaluables por lado. |
| Entrenador | Logística L2, cuatro folds purgados, BUY/SELL, FOLLOW/INVERT, whitelist y presupuesto verificados por pruebas sintéticas. | Dataset admitido y sellado, adaptación final de datos admitidos y grant específico. |

La [matriz estructurada](../research/studies/us30cash_m5_native_observations/technical_closure_20261108/blocker_matrix.json) distingue los pendientes de datos, fuentes externas y autorización.

## Causa numérica de ATR

La producción calcula TR desde la segunda barra y su primera media usa catorce rangos con cierre previo. La variante nativa observada usa high-low de la primera barra, semilla ordenada de catorce rangos y la recurrencia value += (TR_actual-TR_saliente)/14. Al eliminar el primer rango mediante esa recurrencia se obtiene la misma ventana matemática que una suma directa posterior, pero cambia el redondeo de cada operación binary64.

El candidato controller/cf_atr_candidate.py conserva estado, versión, semilla y cadena de dependencias. Las pruebas compararon todos los 287 valores del export sintético contra MT5 con igualdad exacta, restaurando el checkpoint antes de cada barra. Rechazaron un checkpoint alterado, barras abiertas, duplicadas y fuera de orden. La mutación de datos futuros conserva el prefijo. El replay de los epochs 13 y 26 vuelve a dar cinco valores propios únicos exactos. Los prefijos superpuestos del epoch 13 no aumentan esa cuenta independiente.

La implementación de producción sigue mostrando las discrepancias documentadas. El candidato está separado de su fragmento congelado. El valor diagnóstico se inicializa en la barra 14, mientras el control de semillas vigente exige ATR inicializado desde la barra 15. Una promoción necesita resolver esa frontera, versionar la implementación y revisar el certificado/pin. No basta con cambiar sus hashes. La [propuesta específica](../research/studies/us30cash_m5_native_observations/technical_closure_20261108/ATR_CANDIDATE_DECISION_REQUEST.md) queda preparada e inactiva, a falta del ensayo real de 30 barras.

## Factibilidad del contrato

La metadata nativa semanal recuperada declara QUOTE 01:00–24:00 de lunes a viernes y ningún intervalo durante sábado o domingo, en etiquetas del servidor. Una corrida continua puede contener como máximo:

276 M5 = 23 horas × 60 minutos / 5 minutos.

Por tanto, 276 < 350. Sin un bridge certificado entre sesiones, el warmup no puede completarse bajo ese calendario, incluso con captura perfecta. Un inicio parcial o una pérdida de cobertura reduce la capacidad. Esto demuestra un impedimento condicional de sesión, sin certificar excepciones futuras.

Los primeros 800 cruces base consecutivos posteriores al warmup no son 800 barras ni 800 señales evaluables. La estrategia emite como máximo una señal por barra. El código permite una señal al alcanzar la barra 350. Su cota optimista es 349 + 800 + 100 = 1249 M5. La lectura más estricta de “posteriores” podría requerir 1250. Ambas cotas exigen al menos cinco sesiones completas y cuatro bridges, porque cuatro sesiones solo sumarían 1104 barras. Esta cota no garantiza frecuencia de cruces, equilibrio BUY/SELL, evaluabilidad ni folds, y no cambia la frontera aprobada.

El contrato ya contempla bridges certificados. Su permiso requiere calendarios nativos antes y después, una fuente exacta de excepción del broker, identidad, mismo boot, ausencia de suspensión, observaciones conectadas sin gaps y cadena íntegra. La implementación no puede sustituir esa evidencia por la deducción del horario. El contrato completo es alcanzable solo condicionalmente a obtener esos bridges y suficiente muestra. La operación sin bridges tiene el impedimento aritmético demostrado.

Si la fuente de excepción no puede recuperarse, acumular cotizaciones por sí solo no cierra ese requisito. Cambiar qué evidencia acredita un cierre normal exigiría una enmienda científica explícita. No se aplica una alternativa basada en reducir warmup o unir segmentos incompletos.

## Estado operativo y causalidad

La comprobación IPC confirmó US30Cash, XMGlobalSC-MT5 5, cuenta demo y terminal_trade_allowed=false. El productor conserva el contexto en cuarentena y el monitor verifica la cadena. El diario reciente muestra una pérdida de conexión y un cambio de access point. Esos conteos no establecen la causa de todas las interrupciones. Los eventos por latencia, identidad no verificada o reinicio permanecen UNKNOWN cuando no existe prueba adicional.

Se hizo un inventario acotado de los buzones y noticias locales. No se recuperó una excepción fechada exacta. El inventario por palabras clave no es un parser completo ni prueba de ausencia de mensajes. Los mensajes y las identidades de cuenta no se publican.

NTS produjo una medición autenticada; otra fuente devolvió timeout. La correlación de recepción y la procedencia física de generación XM siguen siendo afirmaciones distintas. El contrato C+F usa orden nativo para diagnóstico y mantiene explícita la falta de certificación UTC del instante de generación. La auditoría causal global permanece FAIL. La disponibilidad del prefijo offline aprobado no admite automáticamente el dataset.

La metadata no atribuye al domingo ecuatoriano los horarios del domingo nativo. Ecuador y Nueva York conservan sus conversiones mediante zonas IANA y el mapping XM no recibe offsets supuestos. El estado operativo es conectado a la espera de una cotización nativa nueva; la ausencia de ticks por sí sola no acredita MARKET_CLOSED_VERIFIED.

## Preparación científica y autorización

El contrato conserva K=5, D=3, Slowing=3, niveles 20/80, TP=240, SL=180 y TIME_EXIT=100. La logística L2 usa instancias distintas por lado y cuatro folds cronológicos purgados, con escalado ajustado solo en TRAIN de cada fold. El presupuesto permanece en ocho fits, una ejecución y cero búsquedas. Las pruebas usan datos sintéticos y estimadores simulados. El grant vacío se rechaza antes de leer datasets.

Los contadores actuales son warmup 0/350, señales 0/800, posteriores 0/100, evaluables 0/200, BUY 0/80, SELL 0/80 y folds evaluables 0/3 por lado. Membership y exclusividad están verificados dentro del alcance prospectivo autorizado, con datos en cuarentena. El dataset hash sigue pendiente.

La futura solicitud de entrenamiento se preparará únicamente después de contar con el dataset admitido y sellado, membership y exposure completos, cobertura, causalidad, semillas, protocolo, whitelist y presupuesto vinculados a hashes. El candidato ATR necesita su propia decisión de versión antes de integrarse. Ninguna de esas decisiones se activa en esta ejecución.

## Automatización y publicación

El reporter existente incorpora el nuevo bound de sesión y el hash del candidato en los ensayos de 15/30/276/350. El monitor de reapertura preserva el baseline y registrará la primera cotización nueva encontrada en el ledger verificado. Su verificador conserva bridge_allowed=false cuando faltan pruebas. Guardian, NTS y adquisición siguen mediante servicios locales mientras la PC esté disponible y haya sesión de usuario.

Los servicios guardan recibos locales sin depender del chat. La publicación remota futura requiere una sesión autorizada o credencial local de GitHub. No se configura un publicador externo ni se extraen credenciales del conector. Esta ejecución publica los cambios actuales por actualización normal de la rama.

El [recibo consolidado](../research/studies/us30cash_m5_native_observations/technical_closure_20261108/receipt.json) incluye hashes, anclaje del prefijo, estado real, incidencias, NTS y requisitos pendientes. El replay del candidato identifica cada export y evita contar prefijos solapados como evidencia nueva.

DISCOVERY_VALIDATION=BLOCKED, HISTORICAL_HOLDOUT=LOCKED, FINAL_TEST=LOCKED, DEMO=DISABLED, LIVE_TRADING=false, terminal_trade_allowed=false, TRAINING_EXECUTED=false y PROTECTED_SCORING=false. Cero órdenes. Los datos y contratos congelados conservan sus hashes.
