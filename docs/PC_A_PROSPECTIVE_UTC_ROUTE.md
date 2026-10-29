# Ruta prospectiva temporal PC A

Ecuador sigue como vista principal. Se prepara una ruta nueva; no se repiten auditorías históricas ni se convierte historia redescargada en evidencia prospectiva. La implementación no concede certificación.

## Captura callback nativa

`mt5/ProspectiveUtcObserver.mq5` es un EA dedicado sin órdenes, DLL, WebRequest, CopyTicks, CopyRates ni includes. Se compiló en la instalación XM fijada con cero errores y cero advertencias. Restringe inicio a US30Cash, cuenta DEMO de datos, servidor XMGlobalSC-MT5 5 y data folder del proyecto; rechaza Strategy Tester. DEMO de ejecución continúa deshabilitado.

OnTick registra MqlTick.time/time_msc, bid/ask, flags, símbolo, servidor, identificadores de captura/sesión, secuencia, conexión, contador de uptime al entrar al callback, microsegundos desde inicio del programa, uptime tras leer el quote y TimeGMT del host en segundos. Este último campo se llama receipt_host_gmt_seconds y no es UTC de evento certificado. No se altera el timestamp nativo. Heartbeat cada 5 segundos y registros SESSION_START/END separan reinicios/reinicializaciones. Una nueva sesión también podría proceder de otro gráfico: no se interpreta automáticamente como reinicio de Windows.

La [documentación OnTick](https://www.mql5.com/en/docs/event_handlers/ontick) permite callbacks con Algo Trading desactivado y advierte coalescencia de notificaciones. SymbolInfoTick dentro del handler lee el último quote disponible: no garantiza que coincida de forma única con la notificación original ni aporta hora de llegada de red. GetMicrosecondCount es relativo al inicio del programa; GetTickCount64 es uptime. Ninguno se identifica arbitrariamente con UTC. La escritura/flush y el procesamiento pueden demorar el handler. Por eso no se afirma cobertura exhaustiva ni latencia cero.

Cada línea JSON contiene el payload textual, SHA256(previous + LF + payload) y el hash anterior. La secuencia comienza en cero con SESSION_START. El EA crea un archivo nuevo por sesión y rechaza sobrescribir un nombre existente. Flush por registro; una caída puede dejar cola parcial, que no se admite como registro completo. No es almacenamiento WORM ni prueba contra modificación coordinada de todos los archivos/checkpoints; los hashes publicados sirven como anclas de los snapshots observados.

## Testigo externo y límites

`tools/prospective_utc_station.py` registra referencias NTP de Windows/Cloudflare/Google con intervalos de red y corroboración TLS Date, estado w32tm, brackets de uptime Windows, perf_counter y reloj host. No modifica ningún reloj ni considera TimeTradeServer una referencia. Las referencias quedan en JSONL append-only con SHA encadenado y checkpoint de prefijo. Los brackets relacionan observaciones de relojes, no prueban origen del evento XM. Falta una cota calibrada de oscilador, cola y origen; la incertidumbre sigue NO CERTIFICADA.

Se investigó [NTS de Cloudflare](https://developers.cloudflare.com/time-services/nts/) y [RFC 8915](https://www.rfc-editor.org/info/rfc8915/): NTS usa TLS para intercambio de claves y autenticación de paquetes NTP. En PC A la ruta TLS 1.3 al puerto 4460 de Cloudflare falló validación de certificado y Netnod agotó timeout. No se desactiva TLS ni se instala un servicio horario alternativo. No se obtuvieron claves ni se verificaron paquetes NTP autenticados. El runtime Python actual tampoco expone exporter TLS en su stdlib; no se improvisó criptografía propia. NTP sin autenticación y cabeceras HTTP Date no se presentan como NTS ni como prueba UTC del mismo evento.

## Verificador, gaps y recuperación

`python/prospective_utc.py` verifica hashes, secuencias exactas, identidad, prefijo previamente observado, unidades segundos/ms, contador monotónico y límites de lectura. Conserva y cuenta duplicados adyacentes y regresiones; no deduplica. Reporta conexión, último callback, intervalos entre heartbeats y diferencias host/uptime como diagnósticos. Los futuros timestamps de evento son NO EVALUABLES sin mapping; no se impone un offset para conseguir PASS. Los gaps de secuencia y archivos faltantes se rechazan. La ausencia de ticks entre heartbeats no permite saber si hubo pérdida, inactividad o cierre; OnTick puede coalescer sin dejar un hueco de secuencia.

El monitor añade solo líneas completas a `outputs/pc_a_prospective_utc/native_mirror`, conservando originales y verificando prefijos. Es copia del mismo disco, no backup independiente. Un fallo de integridad genera last_failure.json y detiene admisión; no repara ni borra datos. El siguiente proceso puede reanudar lectura desde checkpoints si los prefijos siguen íntegros. Un fragmento irrecuperable o una corrupción quedan en cuarentena; no se inventa continuidad.

El evaluador de segmentos es deliberadamente no autorizante: exige prueba independiente del mismo evento, mapping acotado, cobertura/cota de cola y calendario específico, y hoy devuelve exclusivamente QUARANTINED. Las plantillas de evidencia y los guards ya existentes permanecen disponibles para una revisión posterior; ni un booleano de autenticación ni haber escrito el capturador autorizan un segmento. No se ha observado una ruta CERTIFIED en producción y no se anuncia como validada.

Las sesiones US30Cash observadas previamente se reutilizan con alcance semanal nativo. Las excepciones fechadas continúan desconocidas. No se confunden con NYSE ni se derivan feriados de ausencia de cotizaciones.

## Operación y único paso humano

1. `python tools/install_prospective_utc.py`: despliega/compila solo el observador en Experts/ResearchDiagnostics del terminal fijado. Conserva fuente/binario previo en un bundle de despliegue y sus hashes. No adjunta un EA a gráficos ni modifica perfiles.
2. Adjuntar una sola vez Navigator → Expert Advisors → ResearchDiagnostics → ProspectiveUtcObserver a un gráfico US30Cash. Mantener CaptureId predeterminado y Algo Trading/DLL desactivados. Esta acción no puede realizarse con las interfaces de ejecución disponibles. Aún está pendiente en el snapshot publicado.
3. `powershell -File tools/prospective_utc_schedule.ps1`: tarea separada cada minuto y al iniciar sesión del usuario, Pythonw oculto, IgnoreNew. Ya registrada. `python tools/prospective_utc_station.py --offline` verifica sin consultas externas. Sin --offline añade un testigo.

El monitor programado ya terminó con resultado 0 y existen testigos encadenados reales. El EA solo está COMPILADO/DESPLEGADO: cero callbacks nativos observados. No se declara REALTIME_CAPTURE=PASS. El task no adjunta ni reinicia MT5; si el EA permanece en un perfil guardado por MT5 puede reinicializarse con nueva sesión, pero esa recuperación tras reinicio del terminal/Windows no se ha probado. El monitor la señalará si falta heartbeat; no se modifica ni reinicia el otro proyecto. A partir del adjunto inicial se pueden verificar callback, integridad y recuperación sin backfill.

## Validación y puertas

31 tests afectados PASS; compilación nativa 0 errores/0 advertencias y ausencia estática de llamadas de órdenes PASS. Los tests cubren hash/prefijo, truncamiento, secuencias, timestamps/regresiones, duplicados y rechazo de entradas de captura a TRAIN antes de I/O. No validan recepción nativa inexistente ni NTS fallido. Los módulos horarios y estrategia permanecen idénticos; la única modificación de código anterior protege la nueva carpeta frente a TRAIN.

REALTIME_CAPTURE=PREPARED_NOT_OBSERVED. EXTERNAL_UTC_SOURCE=DIAGNOSTIC_ONLY. CLOCK_UNCERTAINTY=UNVERIFIED. SEGMENT_CERTIFICATION=QUARANTINED. XM_TIMESTAMP_MAPPING=UNVERIFIED. BROKER_CALENDAR=PARTIAL. CAUSAL_AUDIT=FAIL. TRAINING_READINESS=BLOCKED_BY_RESEARCH_GOVERNANCE. DISCOVERY_VALIDATION=BLOCKED; FINAL_TEST=LOCKED; DEMO=DISABLED; LIVE_TRADING=false. Collector histórico/prospectivo anterior sigue activo en cuarentena y conserva su identidad/cursor.
