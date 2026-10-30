# Correlación prospectiva NTS y XM, sin autorización científica

America/Guayaquil sigue siendo la vista principal. Este cambio no modifica el módulo horario aprobado, el EA, la estrategia, los históricos, los contratos congelados ni los timestamps originales.

## Criterios antes de clasificar

CERTIFIED exige evidencia independiente del instante de generación del evento, mapping revisado del servidor concreto, continuidad y cotas justificadas del reloj/contador y de la demora de generación a callback. Ninguna salida del correlador concede ese estado. Un cambio futuro de esas condiciones requiere revisión del mecanismo de certificación, no activar un booleano.

PARTIAL describe únicamente callbacks observados con prefijo nativo verificado, enlace NTS a un prefijo real de esa misma sesión, dos mediciones autenticadas que delimitan el uptime observado y un identificador local de arranque coincidente. Además no debe observarse desconexión, regresión del contador, discontinuidad host/contador, desorden nativo, hueco de heartbeat o pérdida total de NTS dentro del bracket. PARTIAL no habilita datasets, scoring, entrenamiento ni una cohorte. Incluso estos registros permanecen en la cuarentena científica.

QUARANTINED indica que falta alguna condición anterior o se observa una discontinuidad. Los registros antiguos sin identificador de arranque no se completan retroactivamente. Las secuencias sin ticks se conservan, pero no se cuentan como segmentos de callbacks con datos. Los segmentos del informe son grupos de callbacks discretos con el mismo diagnóstico, no intervalos de cobertura completa del mercado ni intervalos UTC certificados.

## Medición y límites

Se reutiliza el cliente de [RFC 8915](https://www.rfc-editor.org/info/rfc8915/) y sus dependencias aisladas y fijadas por hash. El correlador verifica la historia NTS y las cadenas nativas antes de analizarlas. Cada enlace NTS debe identificar un hash que exista en el prefijo nativo verificado; se limita la lectura a los bytes verificados para no incorporar un append concurrente sin verificar. No se publican cookies, claves de sesión, credenciales ni el feed de cotizaciones.

Para una muestra con recepción UTC condicional [L,U] y bracket de contador [a,b], la proyección diagnóstica de un callback de uptime x es [L+(x-b)*10^6, U+(x-a)*10^6], en nanosegundos. Se conserva cada proyección por separado: no se intersectan estimaciones incompatibles para fabricar una cota estrecha. El supuesto de deriva cero no está demostrado; las estimaciones anunciadas por el servidor tampoco son una garantía metrológica. **certified_receipt_bounds_ns=null** en todas las salidas. Las mediciones delimitadoras constituyen cobertura observacional, no un intervalo físico de validez continua de NTS ni autorización para interpolar timestamps.

El offset registrado es servidor NTS menos reloj Windows, no offset XM. El RTT es el de la consulta NTS. read_uptime menos callback_uptime mide el tiempo observado entre entrada al callback y lectura local, con la resolución del contador; no es latencia de generación, red del broker ni tiempo total de cola. generation_latency_ns queda null. time_msc original menos la proyección de recepción es una diferencia de coordenadas, no un mapping aceptado ni una prueba de procedencia UTC del evento. No se aplica ningún desplazamiento a XM.

La procedencia documentada de los campos MqlTick y su consistencia de unidades se conserva como evidencia distinta de la plausibilidad observada y de la certificación independiente de generación. Las dos primeras no implican la tercera. El calendario histórico del servidor XM permanece PARTIAL, incluidas las excepciones no demostradas.

## Servicio y continuidad

El monitor existente invoca el cliente NTS automáticamente. Tras un éxito, la siguiente medición vence a los 300000 ms del inicio previo; el monitor consulta cada minuto. Por ello la ejecución real puede ocurrir después del vencimiento, además de la duración variable de red. El informe publica horas y contadores reales; no afirma una cadencia exacta de 300 segundos. Los registros previos a esta mejora no distinguían en su propio payload las invocaciones forzadas de las periódicas y se etiquetan LEGACY_NOT_RECORDED. La primera incorporación del identificador de arranque motivó una revalidación anticipada; su registro conservó PERIODIC_DUE, pero el contador de inicio es menor que prior_due y no se usa como prueba de cadencia de cinco minutos.

Los nuevos registros incluyen inicio/fin monotónicos, vencimiento previo, motivo de ejecución y Windows Prefetch BootId. Este identificador es un separador local de épocas dentro de esta PC, no una atestación criptográfica del arranque, una fuente UTC ni garantía frente a restauraciones del sistema. Si no está disponible o cambia, se mantiene el fallo cerrado. No se reconstruyen identidades de registros antiguos.

Los fallos de consulta o timeout NTS se registran sin impedir guardar el estado de captura. Después de guardar el estado nativo, el monitor ejecuta tools/correlate_nts_xm.py y conserva nts_xm_correlation.json y correlation_monitor_status.json. El correlador puede ejecutarse aparte sobre prefijos existentes sin red, sin CopyTicks y sin backfill. Una carrera transitoria con el commit de un registro NTS puede bloquear esa pasada: no se omite el verificador ni se repara la cadena automáticamente.

Los gaps se detectan con dos periodos nominales del timer existente, no mediante una tolerancia científica escogida para aceptar eventos. La diferencia entre reloj de segundos y contador se compara con el intervalo de cuantización de un segundo; una discrepancia es diagnóstico de reloj/contador, no atribución automática a una causa. El gap de 46469 ms sigue sin causa demostrada. No se infiere pérdida real de eventos ni exhaustividad del feed por continuidad de secuencias: OnTick puede coalescer notificaciones.

## Regresión y gobernanza

Se prueban ausencia y lectura inválida de NTS, pérdida intermedia, desconexión, salto de reloj, cambio de época/reinicio, DST de Nueva York sin reordenar UTC/Ecuador, timestamps fuera de orden y huecos de heartbeat. Se conservan las pruebas existentes de AEAD, integridad, mapping y causalidad; los resultados del snapshot se publican con sus hashes.

La auditoría causal intenta cargar el mapping autorizado y falla cerrado antes de normalizar filas si sigue sin verificarse. No evalúa feature_max_time <= decision_time ni quote_time <= decision_time sobre coordenadas ambiguas. DISCOVERY_VALIDATION=BLOCKED, FINAL_TEST=LOCKED, DEMO=DISABLED, LIVE_TRADING=false. No se activa una nueva cohorte ni se accede al TRAIN agotado.
