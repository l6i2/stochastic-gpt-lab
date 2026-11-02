# Diagnóstico de resets de warmup — 2 noviembre 2026

STATUS ejecutado; corte final 14:25:19 Ecuador. La captura es activa y sigue en cuarentena. Desde el último prefijo publicado: +52.505 ticks, +10 M5 aceptadas y +48 rechazadas; acumulados68.655 ticks,16 M5 aceptadas,78 rechazadas. Warmup actual0/350; señales BUY/SELL0. No confundir aumento acumulado con continuidad.

## Causa demostrada y límites

Los resets recientes son la aplicación de la regla congelada: cada M5 incompleta reinicia el contexto de features/warmup. Último descenso positivo a cero: cierre observado13:10 Ecuador (ventana nativa20:05), después de una barra válida. Los rechazos posteriores vuelven a aplicar reset sobre cero; último al cierre14:25. No son reinicios de Windows ni equivalen todos a terminaciones del worker.

Una consulta diagnóstica única de la ventana nueva nativa21:15–21:20, recibida hasta14:20 Ecuador, demuestra793 callbacks BID y793 ticks BID de referencia; seis payloads faltantes y seis extras, todos estos extras duplicados de la captura; referencia sin duplicados. OHLC/volumen iguales no prueban secuencia. No se consultó la antigua259/284 ni se adoptaron referencias como datos crudos. El campo de lectura tiene retraso0ms, limitado por resolución; no demuestra ausencia de carrera o latencia.

El productor usa OnTick→SymbolInfoTick, que lee la última cotización; no recibe un payload inmutable del evento. [MetaQuotes documenta que OnTick puede coalescer nuevos eventos](https://www.mql5.com/en/docs/event_handlers/ontick) y que [SymbolInfoTick devuelve la última actualización](https://www.mql5.com/en/docs/marketinformation/symbolinfotick). Esta arquitectura no garantiza correspondencia uno a uno con CopyTicks. La divergencia concreta está probada; atribuir cada sustitución a una cola, hilo o recurso preciso requeriría trazas que no existen. No se inventa esa causa física. No se eliminan duplicados, rellenan faltantes, sustituyen ticks, modifican el observador aprobado ni relajan contratos. Garantizar350 barras continuas completas sigue sin estar demostrado con este productor.

## Logs y calendario

XM registra retiradas/cierres normales de terminal a08:21 y08:25, carga de observador08:26:35 y sincronización posterior; no nueva desconexión registrada en los últimos resets. Se conservaron hashes y extractos sanitizados; no credenciales ni cuenta/IP. Observador mantiene el mismo segmento, contador y cadena; los payloads repetidos ya están en el origen, no se atribuyen sin prueba al worker. Windows506/507 a14:19 fue un estado de pantalla de1,096s: SleepEntered=false y SleepDuration=0; no se interpreta como suspensión. La pareja antigua08:20 se mantiene separada de resets intradía recientes.

La evidencia de sesiones del servidor observada28/10 permanece PARTIAL y sin extrapolación UTC/DST. Hay cientos de ticks dentro de cada ventana rechazada reciente: no es un cierre normal sin cotizaciones. No se ha demostrado interpretación contractual incorrecta de cierre de mercado; por tanto no se propone ni aplica excepción contractual. La única UNKNOWN_NATIVE_SESSION_GAP histórica no explica estos rechazos nuevos. Un futuro cambio requeriría sesiones certificadas, ausencia de pérdida y aprobación separada; nunca excepción automática.

## Reparación técnica aplicada

last_error del worker a12:19:14 Ecuador documenta PermissionError leyendo checkpoint.json activo. Demuestra terminación por acceso al archivo, no identifica si hubo bloqueo compartido, antivirus o ACL. Se extiende a runtime_state/checkpoint el reintento de lectura ya existente: cinco intentos con20ms entre errores PermissionError. No se reintenta el procesamiento, no se usa snapshot viejo y JSON corrupto/archivo ausente/denegación persistente fallan cerrados. No son tolerancias de datos ni reglas científicas. Pin nuevo versionado, mismo fragmento de features, manifests y checkpoints originales. Se reinició únicamente el worker identificado; XM, observador y colector no se detuvieron. No hizo falta RESUME global: guardian saludable.

## Verificación real después

Dos ejecuciones independientes de lectura verificaron prefijo/cursores persistentes y datos nuevos. Al siguiente cierre M5 la referencia volvió a rechazar la secuencia:16 aceptadas antes y después, warmup0 antes y después. Persistencia y procesamiento demostrados; aumento de M5 válidas posterior a reparación **NO DEMOSTRADO**, no se declara PASS. Una lectura sin permisos futura no se ha reproducido deliberadamente sobre captura real; recuperación transitoria/exhaustión/corrupción comprobadas con tests controlados.

25 tests relevantes PASS; compileall y diff check correctos. Se mantienen cuarentena, CAUSAL_AUDIT globalFAIL, entrenamiento/scoring deshabilitados y todas las puertas protegidas. No accesos a conjuntos protegidos ni modificación del otro proyecto. No intervención manual inmediata. Siguiente paso automático: seguir procesando nuevas ventanas con comparación exacta; no repetir consultas antiguas. Si la continuidad sigue fallando por muestreo latest-quote, no basta esperar ni prometer admisión: requiere estudiar una procedencia prospectiva completa y autorizada, sin backfill ni cambiar este dataset.
