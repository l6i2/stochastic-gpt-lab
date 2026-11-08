# Preparación científica C+F — cierre técnico del 5 de noviembre de 2026

El estudio sigue en cuarentena y no está admitido. Se cerraron tareas técnicas
de calendario, verificación de features, control incremental y ensayo de admisión;
las garantías que aún requieren observaciones o evidencia externa se conservan
pendientes. Las cifras de este corte están en
`research/studies/us30cash_m5_native_observations/readiness_20261105/`.

## Corte, pertenencia y conservación

Se conserva el corte exclusivo autorizado de las 09:22:39 Ecuador, el dataset 02,
productor `cfprod_5c64f0781dc148e5896391b1492ba144` y contrato F original.
La auditoría verifica su cadena, manifest, ledger y límites nativos por timeframe.
No se adoptó ninguna barra del dataset 01 ni de los históricos diagnósticos.
La independencia de roles futuros deriva de la decisión expresa, no de inventar
los manifests ni los límites desconocidos de reservas históricas. Los 53
artefactos anteriores de la comprobación conservan sus hashes.

## Calendario y reparación de continuidad

El probe nativo recuperado identifica US30Cash / XMGlobalSC-MT5 5 y sesiones
QUOTE lunes–viernes 01:00–00:00 nativo; TRADE lunes–jueves 01:05–23:55 y viernes
01:05–23:50. Estas dos clases de sesiones permanecen separadas. No se sustituyen
por NYSE, CME, otro broker ni por un offset fijo. La línea de relojes del probe
no certifica UTC independiente.

Se corrigieron dos defectos demostrados de la ruta de continuidad: un recibo
futuro ya no puede adelantar el cursor actual, y el contador C+F de barras
observadas conserva su significado separado del contador de adyacencia numérica
del productor original. El guard completo rechaza pruebas con booleans sin
soporte. Exige intervalo exacto, reapertura, calendarios de sesiones adyacentes,
excepción fechada aplicable y hash-bound, identidad, cadena de supervisión,
conexión explícita, sleep ID estable, boot y monotonía sin huecos ni interrupciones.

La versión nueva registra conexión y sleep ID en cada observación futura.
Su instalación tiene pin propio y conserva las fuentes anteriores en Git y los
manifests originales. No se certificó ninguna transición real: la allowlist de
recibos de transición sigue vacía. La preparación del verificador no equivale
a una continuidad observada ni garantiza que se alcancen 350 M5 entre sesiones.

[XM](https://www.xm.com/equity-indices) remite los horarios completos a la cuenta
autenticada; la búsqueda oficial acotada no produjo una excepción aplicable.
Una ausencia de ticks por sí sola no certifica cierre normal. Se necesitan
evidencia nativa vigente a ambos lados, supervisión del cierre completo y una
excepción/confirmación fechada aplicable antes de admitir esa continuidad.
Si falta, el nuevo segmento continúa aislado y el anterior queda en cuarentena.

## Features y semillas

Se reutilizó el ensayo nativo retenido de 499 barras, verificando hashes de la
exportación, código de features, MAIN_K y núcleo HA. No se repitió el probe
aprobado. Paridad algorítmica: **ATR exacta, HA exacta, MAIN_K con el límite ya
aprobado**. No se introdujeron nuevas tolerancias.

La prueba de semillas propias verifica el primer hash de barra del contexto,
counts HA/ATR, 14 TR propios y ausencia de herencia entre epochs. ATR se inicializa
en la barra propia 15; HA dispone de su valor autorizado en la 276; el warmup
sigue siendo 350. El oráculo de prefijo propio, compilado con cero errores y
cero advertencias, espera esos datos. Al llegar a 15, 276 y 350 barras se programa
una única comprobación por milestone, epoch y versión del código. Usa el terminal
diagnóstico aislado ya existente y un símbolo personalizado con las M1/M5 propias;
no consulta históricos ni añade una barra sintética. Tiene guard de RAM y timeout
limitado a su proceso aislado. La paridad nativa del dataset propio no es PASS
hasta que ese ensayo termine con evidencia real.

La whitelist de seis features no cambia. Se verifican hashes, cutoff nativo,
orden de cálculo y disponibilidad física anterior al uso offline. Eso no prueba
la disponibilidad en la entrada original en vivo ni la generación UTC física.
Los valores incompletos siguen excluidos de admisión; no se imputan.

## Cobertura, persistencia y suspensión real

El monitor incremental recomputa pares nativos y sus hashes, OHLC/volumen,
BID/ASK, grid, cinco M1 por M5 mediante los recibos de la capa C+F, límites
posteriores al corte, features y checkpoints. Solo recorre el sufijo nuevo y
verifica el ancla del prefijo; un error no convierte datos en admitidos. Consultas
huérfanas de una interrupción explícita quedan excluidas y no bloquean segmentos
posteriores válidos. La auditoría completa independiente complementa el monitor.

Windows registró Modern Standby a las 09:57:45 y 09:58:54 por Idle Timeout y
Austerity Battery Drain Budget Exceeded, con salida a las 10:12:53. El productor
registró fallo de attach y sleep verificado; no fue un cierre de mercado. Se
preservó el hueco. La instalación posterior del guard abrió otro epoch conforme
al contrato, sin conservar su warmup ni hacer backfill. Las seis M5 previas al ajuste de software se
conservan como observaciones técnicas del dataset, sin sumarlas al contexto nuevo.
La estación volvió a corriente; no se cambió la política de batería. El reinicio
físico de Windows continúa sin prueba nueva, y no se provocó uno.

## Madurez y automatización

Se conservan 350 M5 / 800 señales / 100 barras posteriores / 200 evaluables /
80 BUY / 80 SELL / tres folds por lado. El monitor diferencia acumulado, contexto
consecutivo técnico, cuarentena y científico admitido. Sus tasas son descriptivas,
calculadas por barras observadas de un único contexto. No hay muestra suficiente
para una fecha de madurez o para identificar estadísticamente el requisito más
lento. Cinco minutos por barra describen tiempo observado de mercado, no tiempo
calendario ni una promesa de continuidad.

El reporter y guardian existentes ejecutan la verificación sin depender del chat.
No se añadió un servicio permanente. Hay bloqueo exclusivo para el monitor y
un único escritor de captura. Los checkpoints son persistentes y los milestones
se guardan una sola vez; no se repiten oráculos sobre el mismo input. Un fallo
del ensayo conserva logs y no activa entrenamiento. La captura sigue independiente
de los trabajos diagnósticos y del terminal aislado.

## Admisión y entrenamiento

El dry-run sobre metadatos sintéticos y recibos reales rechaza hashes alterados,
importaciones retrospectivas no elegibles, membership incorrecto, overlaps,
continuidad no probada, seeds incompletas, leakage e inmadurez. Incluso el fixture
sintético completo devuelve CHECKS_SATISFIED_DRY_RUN_ONLY, nunca admisión real.
El ensayo real queda NOT_READY con requisitos explícitos, sin ejecutar fit o scoring.
La ausencia de grant se verifica contra la autoridad existente antes de acceder
a archivos de entrenamiento.

Se preservan logística L2, BUY/SELL separados, FOLLOW/INVERT, cuatro folds
cronológicos purgados, whitelist y presupuesto de ocho ajustes planificados:
**cero ajustes autorizados**. Protocolo y código quedan ligados por hashes. El
runner conserva su allowlist y rechazo sin dataset sellado y grant específico;
la preparación no amplía esa autoridad.

Pendientes materiales: continuidad real con calendario/excepción aplicable,
semillas y paridad del prefijo propio, madurez íntegra, cobertura y membership
sellados del dataset final, y posteriormente autorización específica de
entrenamiento. DATASET_HASH sigue null. CAUSAL_AUDIT global no cambia a PASS.
Discovery Validation, Historical Holdout y Final Test siguen cerrados.
DEMO=DISABLED, LIVE_TRADING=false, terminal_trade_allowed=false,
TRAINING_EXECUTED=false y PROTECTED_SCORING=false.


Corte final auditado: **72 M1, 12 M5 verificadas**, cero exclusiones de paridad
M1/M5; **0 M5 consecutivas en el contexto actual**, cero científicamente admitidas.
La cadena conservó el prefijo y avanzó con cinco M5 adicionales desde la primera
prueba posterior a la reparación. Hubo más suspensiones en el transcurso de la
misión; todos los eventos recuperados figuran en `windows_incidents.json`.
No se suman los contextos separados. BUY=0, SELL=0, señales consecutivas=0/800,
barras posteriores=0/100; evaluables=0/200 y 0/80 por lado. 92 regresiones PASS.

Acción física necesaria para recolección sostenida: **conectar PC A a corriente
 y mantenerla encendida**. La medición final indica batería; no se amplió la
 antigua autorización temporal de inhibición ni se cambió el perfil de batería.
El collector se reanuda automáticamente al despertar, pero ninguna automatización
puede producir observaciones mientras Windows está suspendido. No hace falta
otra autorización científica para continuar esta adquisición en cuarentena.


## Continuación en corriente — corte auditado de las 13:35 Ecuador

La PC se comprobó conectada a corriente. El acumulado auditado avanzó a **91 M1
 y 16 M5**, todas las M5 con paridad M1/M5 registrada. El contexto actual es
**1/350**; el científico sigue en cero. Las tres M5 del contexto previo no se
sumaron: a las 13:28:34 apareció un gap nativo tras **173,5372149 segundos**
transcurridos en la fase de identidad/quote del poll. El recibo separa esa fase
larga de la lectura final del tick, que fue breve. No está demostrada la causa
subyacente ni que haya sido un cierre normal. El sleep ID registrado no cambió
entre esas observaciones; no se inventó una desconexión ni se atribuyó todo el
intervalo a la suspensión anterior. La ventana quedó excluida y el segmento
posterior produjo una M5 nueva. No se reiniciaron el capturador ni XM para este
avance. No hubo backfill ni cambios en los contratos o datasets anteriores.

Se reparó el seguimiento automático del oráculo de prefijo: ya distingue proceso
activo, salida incompleta/fallida y resultado válido. Un PASS debe pertenecer al
mismo capture/epoch y cumplir su milestone; desde 276 exige también HA exacta.
Un aplazamiento por recursos puede reintentarse con observaciones nuevas, sin
repetir el input inmóvil. Un resultado exitoso se reutiliza; un fallo de paridad
no se convierte en PASS ni se oculta mediante un reintento. **18 pruebas
focalizadas PASS**, incluida recuperación por recursos sin duplicar trabajo.
No se repitió el ensayo nativo retenido de 499 barras.

La paridad nativa del prefijo actual espera 15 barras propias, HA espera276 y el
warmup350. No se usan barras de epochs previos. El calendario semanal sigue
verificado; falta prueba de transición real y excepción aplicable. Se revisó una
alternativa nativa MCP documentada por MetaQuotes, pero no hay endpoint autenticado
configurado en este entorno. No se modificaron credenciales ni permisos. Esa
alternativa tampoco aporta por sí sola la excepción faltante:
[configuración oficial](https://www.metatrader5.com/de/terminal/help/mcp_and_ai/configuration),
[capacidades oficiales](https://www.metatrader5.com/en/terminal/help/mcp_and_ai/capabilities).
No se repitieron las búsquedas agotadas de la misma excepción.

Los recibos actuales están en
`research/studies/us30cash_m5_native_observations/ac_followup_20261105/`.
Continúan pendientes 349 M5 del contexto para warmup, 800 señales, 100 barras
posteriores, 200 evaluables, 80 por lado y tres folds por lado; además del
calendario/transición, semillas, sellado del dataset final y grant específico.
La cifra349 pertenece al corte de este informe y cambiará con datos nuevos.
No hay ETA de calendario justificable. El monitor y la captura siguen activos
sin depender del chat, con DATASET_ADMISSION=WAITING_FOR_EVIDENCE y ningún fit.


Verificación posterior del mismo avance en corriente: **96 M1 / 17 M5** acumuladas,
**2/350** en el contexto actual, sin nuevas mezclas. El prefijo previo permanece
intacto. Además, el oráculo solo reutiliza un resultado si coincide el hash de
la primera barra propia, evitando heredar una paridad de otro contexto dentro
del mismo epoch. La comprobación HA desde276 exige PASS_EXACT. La batería de
pruebas focalizadas final es **21 PASS**; no se repitieron pruebas nativas aprobadas.
Recibos más recientes: `ac_followup_20261105/interval_progress/`.


## Continuación prioritaria de C+F del 5 de noviembre

El corte auditado de las 15:15 en Ecuador contiene 128 M1 y 20 M5 verificadas.
El contexto actual conserva 1 M5 consecutiva y 0 M5 científicamente elegibles.
La M5 nueva posterior al hueco se verificó con cinco M1 propias. Las 20
observaciones offline conservaron el orden nativo y el orden monotónico entre
la lectura, su verificación, el cálculo y el uso. El auditor reproduce la
paridad M1/M5, enlaza la referencia de decisión a su observación y comprueba el
hash del snapshot. La causalidad física de entrada y la generación UTC siguen
pendientes. Los epochs previos quedan fuera del paquete de admisión vigente.

El hueco de las 15:08 duró 14,287 s entre observaciones. El registro identifica
la regla de discontinuidad de polling. El commit anterior duró 1,467 s, el
identificador de suspensión se mantuvo y la causa subyacente queda desconocida.
Se conserva el corte observado y el productor continúa con su epoch nuevo.

La revisión real del contexto vigente devuelve `NOT_READY`. Faltan evidencia
de calendario aplicable, features completas, semillas y paridad ATR propias,
madurez y sellado del dataset. Los roles prospectivos exclusivos se verificaron.
Faltan 14 M5 propias para la primera comprobación iATR, 275 para HA y 349 para
warmup. El soporte sigue en cero para las 800 señales consecutivas, 100 barras
posteriores, 200 evaluables, 80 BUY, 80 SELL y tres folds evaluables por lado.
La transición de sesión necesita observación continua y excepción aplicable
verificadas. El monitor conserva los hitos 15, 276 y 350.

El entrenador valida todos los folds y el presupuesto antes del primer fit.
El ensayo aislado comprobó el rechazo de un fold tardío inválido y de un
presupuesto insuficiente antes de crear estimadores. El recorrido completo
usó estimadores simulados para las ocho posiciones. Pasaron 50 pruebas
focalizadas. El presupuesto científico consumido sigue en cero.

El boot sigue en 112 y el próximo arranque natural todavía queda por observar.
La recuperación existente y la adquisición siguen activas. Los recibos de este
corte están en `research/studies/us30cash_m5_native_observations/priority_readiness_20261105/`.

## Estabilidad C+F verificada el 5 de noviembre de 2026

El ensayo confirmó 35 M5 verificadas y una racha de 16. Después, una desconexión XM observada abrió un epoch nuevo con 0 M5 consecutivas y conservó las 35 acumuladas. El productor se recuperó en el mismo proceso. El monitor existente publica telemetría pasiva.

La paridad exacta de iATR de producción falló por una unidad de redondeo en dos valores. La variante de semilla y recurrencia reprodujo los tres valores comparables del prefijo ensayado. Sigue aislada como diagnóstico. Pasaron 14 pruebas focalizadas. La admisión permanece en `WAITING_FOR_EVIDENCE` y el entrenamiento sigue bloqueado. [Comparación y recibos](CF_CAPTURE_STABILITY_SIX_SOLUTIONS.md).

## Seguimiento C+F del 6 de noviembre de 2026

El corte comprobó **88 M5 con paridad M1/M5**, 0 consecutivas y 0 elegibles. El terminal XM volvió a autorizar la cuenta demo y a sincronizar US30Cash después de la pérdida de conexión registrada entre las 21:28:09 y las 21:28:40 (Ecuador). IPC confirmó conexión y trading algorítmico deshabilitado. Windows registró una suspensión previa entre las 21:24:58 y las 21:25:00. La causa subyacente de la caída de XM sigue sin determinar. El cambio automático de punto de acceso de MT5 a las 09:40:46 es un incidente separado. Se abrió un epoch nuevo sin incorporar intervalos perdidos.

El replay de los exports nativos propios reprodujo los dos desacuerdos exactos de ATR del epoch 13. El cálculo de producción excluye el rango de la primera barra de la semilla y usa una recurrencia sobre su ventana. La variante diagnóstica incluye el primer rango y conserva el orden de operaciones binary64. Coincidió en los tres valores del prefijo mayor del epoch 13 y en dos del epoch 26, sin contar dos veces el prefijo superpuesto de 15 barras del epoch 13. Un valor de producción también coincidió en el epoch 26. Esta evidencia es diagnóstica. La implementación de producción y el contrato quedan intactos.

El reporter programa un ensayo ampliado en 30 barras propias, además de los de 15, 276 y 350, ligado a la semilla del epoch. El calendario semanal observado sigue parcial, a falta de evidencia exacta de transición y excepciones del broker. La causalidad nativa del prefijo sigue separada de la certificación global y de la procedencia UTC. Pasaron 28 pruebas. La admisión y el entrenamiento siguen bloqueados. [Recibo con hashes y discrepancias](../research/studies/us30cash_m5_native_observations/readiness_followup_20261106.json).

## Seguimiento del 7 de noviembre de 2026

XM y el guardian estaban detenidos al comenzar la sesión. La tarea conservaba el resultado 3221225786, correspondiente a terminación del proceso; el origen de esa terminación sigue desconocido. Se inició la tarea existente. Recuperó una única instancia XM y el productor C+F, que reabrió su checkpoint en el epoch 31. IPC confirmó cuenta demo, servidor XMGlobalSC-MT5 5 y trading algorítmico deshabilitado. El monitor pasó de estado obsoleto durante el arranque a verificar nuevamente la cadena. El corte contiene 500 M1, 88 M5 con paridad, 0 consecutivas y 0 elegibles. La última cotización nativa permanece en el cierre anterior; el retorno de conexión constituye evidencia de recuperación del servicio. La continuidad de barras nuevas espera observaciones futuras.

Se reprodujeron los exports propios de los epochs 13 y 26. En el mayor prefijo del epoch 13, la variante diagnóstica coincide en tres valores binary64 y el cálculo original discrepa en dos por una unidad de redondeo. El epoch 26 añade dos valores comparables de la variante y un valor del cálculo original, todos coincidentes. El prefijo menor del epoch 13 está solapado y no añade independencia. La suma directa de la ventana difiere en dos valores del prefijo mayor, mientras la recurrencia ordenada coincide. El diagnóstico ahora registra el primer rango, la semilla hexadecimal y ambas comparaciones exactas.

Formalmente, el cálculo original inicia con los primeros 14 True Range que disponen de cierre previo, en la barra de índice 14. La variante inicia en el índice 13 con high-low de la primera barra y luego suma (TR_actual-TR_saliente)/14 al valor anterior. Ambos usan solo barras cerradas del prefijo. Aunque las ventanas posteriores representen la misma media en aritmética real, el estado y orden de operaciones binary64 producen redondeos distintos. No hay evidencia suficiente para promover una variante con solo cinco valores únicos de dos epochs. El fragmento de producción está ligado al pin y al certificado retenido. Una futura reparación deberá llevar identidad y recibo nuevos, validar prefijos propios mayores y resolver formalmente su compatibilidad con esa definición. La variante sigue diagnóstica.

Pasaron 67 pruebas autorizadas de recuperación, integridad, causalidad, semillas, MAIN_K, madurez, admisión y calendario. HA espera 276 M5 propias. Los hitos automáticos 15/30/276/350 siguen habilitados. La continuidad entre sesiones exige calendarios nativos anteriores y posteriores, una fuente del broker sobre la excepción exacta y salud continua. Ninguna transición nueva cumple todavía el expediente. El calendario continúa parcial y la auditoría causal global permanece FAIL.

Faltan 350 M5 propias consecutivas, 800 señales, 100 M5 posteriores, 200 evaluables, 80 BUY y 80 SELL y tres folds por lado. La admisión sigue WAITING_FOR_EVIDENCE y el entrenamiento BLOCKED. [Recibo estructurado con hashes, exports y diario filtrado](../research/studies/us30cash_m5_native_observations/readiness_20261107/receipt.json). Guardian, productor, NTS y reporter operan con los servicios existentes. Se preservan las interrupciones reales. Conjuntos protegidos cerrados, DEMO deshabilitado, LIVE_TRADING=false, terminal_trade_allowed=false, cero órdenes, cero scoring y cero entrenamiento.

## Preparación de fin de semana del 7 de noviembre

Se completó el ensayo nativo sintético de 300 barras. La variante iATR coincide en 287 valores y HA coincide en los cuatro precios de las 300 barras, con 25 direcciones desde el hito 276. Pasaron 66 pruebas. El monitor de reapertura quedó integrado en el reporter existente con recibo idempotente y revisión de transición que conserva la cuarentena. Se mantienen 88 M5 propias acumuladas, 0 consecutivas y 0 elegibles. iATR propio, HA propio, calendario y admisión conservan sus pendientes. [Informe único y recibos](CF_WEEKEND_PREPARATION_20261107.md).

## Cierre técnico del 8 de noviembre de 2026

Se preparó el candidato ATR con estado versionado y restauración exacta, se incluyó su hash en los jobs futuros y se incorporó la factibilidad por sesión al monitor. Pasaron 95 pruebas. El máximo observado de 276 M5 por sesión es menor que 350; la adquisición requiere bridges certificados para superar el warmup. La cota optimista del estudio completo es 1249 M5, al menos cinco sesiones y cuatro bridges, sin pronóstico de señales. Continúan 88 M5 acumuladas, 0 consecutivas y 0 elegibles. [Matriz, evidencias y ruta de entrenamiento](CF_FINAL_TECHNICAL_CLOSURE_AND_TRAINING_PATH.md).
