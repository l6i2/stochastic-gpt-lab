# Calibración temporal observacional — PC A

Se amplía únicamente la observación futura y el análisis de evidencias. Ecuador sigue siendo la vista principal. No se modifica el EA aprobado, los timestamps, datasets, estrategia, órdenes ni puertas científicas.

## Por qué NTS no bastaba

El RTT guardado era una duración, no el valor absoluto de un contador que pudiera compararse entre consultas. Los registros antiguos conservan brackets GetTickCount64 y, más adelante, BootId; los seis primeros no tienen identificador de arranque y no se completan retroactivamente. GetMicrosecondCount del EA es relativo al programa y se reinicia al reinicializarlo: no se compara entre sesiones. Compartir un uptime y BootId permite formular comparaciones locales, pero no prueba continuidad de captura ni ausencia de suspensión.

[Microsoft documenta](https://learn.microsoft.com/en-us/windows/win32/sysinfo/windows-time) que GetTickCount64 incluye suspensión/hibernación y tiene la resolución del timer. El rango típico de 10–16 ms no se utiliza como cota garantizada ni como tolerancia de aceptación. Dos lecturas idénticas no representan un intervalo físico de anchura cero. Las proyecciones antiguas quedan identificadas como modelos condicionales con cuantización GTC sin calibrar.

NTS autentica la fuente y los timestamps de una consulta; no autentica continuamente el reloj Windows ni acota por sí solo su deriva entre consultas. El error anunciado por el servidor es una estimación, no una garantía metrológica. La latencia asimétrica tampoco se sustituye por la mitad del RTT. Más mediciones no eliminan esos supuestos.

## Nueva evidencia y partición

Se observa un hueco de unas diez horas entre registros, terminación explícita de la sesión XM previa, nueva sesión tras abrir MT5 y eventos locales de energía/cambios de hora. El registro Kernel-General 207319 declara un cambio de 03:55:54.3611195Z a 14:00:58.5000000Z; el 207355 declara un ajuste posterior hacia atrás de aproximadamente 1,223 segundos. Son declaraciones del sistema local, no una referencia UTC independiente. No se atribuye la diferencia completa a deriva del oscilador ni se rellena el hueco. El estado observado de w32time declara leap=3/stratum=0; no se hereda un PASS anterior de sincronización como prueba actual. NTS y w32time son mecanismos separados; no se cambió su configuración.

La historia se recorre en orden de su cadena de hashes, evitando ordenar mediciones por un reloj host que puede saltar. Se separan cambios de BootId, regresiones de contador/host, periodos completos del monitor perdidos y fuentes NTS no disponibles o inválidas. La cadencia de consulta del monitor es 60000 ms; superar el vencimiento NTS en más de un periodo completo es un criterio operativo de separación, no un error temporal admisible. Se mantienen orígenes NTS separados. Un fallo de TimeNL no se rellena con Cloudflare para aparentar continuidad de esa fuente.

## Observación futura

Cada lectura UTC local asociada a la respuesta NTS queda rodeada por QueryPerformanceCounter y registra QueryPerformanceFrequency y GetTickCount64 antes/después. Se guardan ticks QPC originales y frecuencia; la conversión a nanosegundos redondea hacia fuera usando enteros. Cambiar de frecuencia o época separa el modelo. [QPC sirve para medir intervalos y no implica sincronización UTC](https://learn.microsoft.com/en-us/windows/win32/sysinfo/acquiring-high-resolution-time-stamps). El bracket se refiere a la lectura del reloj local, no al instante de llegada al kernel del paquete ni a generación del tick XM.

Las consultas futuras también registran el RecordId más reciente de Kernel-General/Id=1 mediante una consulta read-only acotada. Un cambio o regresión de ese cursor entre muestras separa el ajuste; un resultado ausente no se inventa ni se atribuye a registros antiguos. Este testigo cubre los cambios observados en el log, no todos los posibles slews ni una atestación independiente del arranque. La consulta tiene timeout de ocho segundos; el timeout del subprocess NTS pasa de 40 a 50 segundos para incluirla. Un fallo no impide persistir la captura nativa. Se conserva la frecuencia nominal NTS de cinco minutos y el polling de un minuto.

Se registra además el bracket de duración de la consulta alrededor de la lectura local. El campo RTT incluye procesamiento local de la consulta; no se interpreta como demora pura de red del broker. Las claves y cookies siguen efímeras y no se publican.

## Estimaciones defendibles y sus límites

Para dos observaciones con contador [aL,aU], [bL,bU] y UTC condicional [AL,AU], [BL,BU], se calcula el intervalo de pendiente media:

`[(BL-AU)/(bU-aL), (BU-AL)/(bL-aU)]`

Se exige orden positivo separable del contador; si falta no se ajusta. Los intervalos UTC incompatibles no se omiten para conseguir un modelo: pueden rechazarlo. Las fracciones son exactas. Los ppm mostrados son `(pendiente-1)*10^6`: UTC transcurrido menos tiempo del contador por unidad de contador. Se informa por separado el cambio medio del offset NTS menos Windows. Esto incluye disciplina/ajustes del host y error de referencia; no es una medición aislada del oscilador.

Se conservan las pendientes adyacentes y de la base completa. La intersección de las restricciones de pares comprueba si un modelo de tasa constante es compatible con las muestras y sus intervalos declarados. Si es vacía, se rechaza el modelo sin ampliar tolerancias ni eliminar muestras. Una intersección no vacía sigue siendo una hipótesis compatible, no una prueba de constancia física. No se extrapola fuera de las muestras. Las proyecciones de recepción con deriva usan exclusivamente ese modelo condicional, manteniendo explícita la cuantización GTC no calibrada. QPC aún no elimina esa limitación del EA, que registra GTC.

No se estima una deriva instantánea máxima ni una incertidumbre UTC absoluta garantizada a partir de secantes. En el tramo previo al hueco, la pendiente media Cloudflare sobre unos 1304 segundos permite aproximadamente −98,22 a +69,39 ppm, condicionada al error NTS y a la lectura GTC. Incluye cero. El informe contiene los nuevos intervalos QPC cuando hay al menos dos muestras reales, sin convertirlos en certificación.

La incertidumbre de los extremos domina la pendiente de bases cortas. Sin un objetivo de precisión aprobado ni cota de variación instantánea, aumentar la frecuencia no justifica una cota física más estrecha; se mantienen cinco minutos y no se realizan ráfagas ni nuevos probes manuales.

## Automatización, integridad y gobierno

El monitor existente integra el análisis y modelos condicionales por callback. El ajuste se cachea por hashes de registros en orden de cadena y hash del código; el cache tiene digest verificable y snapshots inmutables. Si no cambia la evidencia ni el código, se reutiliza. Se agrupan las restricciones por día UTC del servidor NTS, origen y base del contador para limitar el coste del ajuste diario; esa partición de informe no afirma una discontinuidad ni es una tolerancia de aceptación. Se conservan los puntos y lotes anteriores. No se repiten las auditorías históricas aprobadas. Los prefijos nativos se verifican y los tramos con discontinuidades siguen en cuarentena; el modelo no autoriza callbacks rechazados. No se hace backfill.

CERTIFIED_SEGMENTS permanece vacío sin vínculo independiente entre evento XM y su instante de generación, cotas de cola/transporte y mapping revisado. Recepción condicional, plausibilidad de time_msc y certificación de generación son estados diferentes. El calendario histórico XM continúa PARTIAL. Los contadores PARTIAL/QUARANTINED agrupan callbacks observados, no prueban exhaustividad del feed. Todos permanecen en cuarentena científica.

Los tests cubren pendiente sintética conocida, ausencia de época, reinicios, pérdida/invalidación de NTS, saltos de reloj/cursor, regresión, modelo no afín, redondeo QPC, no extrapolación/no mutación y cache/tampering, más las regresiones afectadas. CAUSAL_AUDIT falla cerrado antes de admitir filas con normalización no demostrada. DISCOVERY_VALIDATION=BLOCKED; FINAL_TEST=LOCKED; DEMO=DISABLED; LIVE_TRADING=false; entrenamiento y cohortes no activados.
