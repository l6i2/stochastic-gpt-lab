# Pipeline prospectivo incremental — US30Cash M5

## Implementación y funcionamiento real

El colector original y el observador MT5 permanecen intactos. Un worker derivado independiente lee únicamente el journal durable de la nueva captura us30cap_15cbddec947f42c98219caa4cec978f2, conserva sus IDs, secuencias y timestamps, y guarda todo en outputs/prospective_derivatives_v1/<capture_id>. No hay dataset admitido ni ruta de entrenamiento. El worker ya consumió callbacks prospectivos reales conservados desde activación, avanzó después con nuevos heartbeats y pasó recuperación idempotente con el mismo cursor/chain head y cero artefactos duplicados. No se cerró MT5 ni se reinició el colector.

La derivación posterior de raw prospectivo ya registrado no es redescarga histórica; tampoco se presenta como una feature calculada originalmente dentro de OnTick. Cada contexto registra source_receipt, compute_clock real, referencia del callback y etapas ready=1/decision=2. Ningún dato posterior de precio alimenta la feature. Global CAUSAL_AUDIT permanece FAIL; no se certifica vintage real de features en el callback original.

## Buckets, barras y comparación

Ticks BID (flag 2) se acumulan en unidades enteras de la grilla nativa, reutilizando price_units de native_m5_rebuild. Se preparan M1 y M5 sin llenar intervalos vacíos. El primer bucket de cada segmento es parcial y nunca se convierte en barra válida. Una observación del siguiente intervalo cierra el previo; no se usa un reloj UTC supuesto para cerrarlo. Gaps de callback según los dos timers ya fijados, desconexión, regresión temporal, quotes indistinguibles o huecos de sesión no certificados contaminan el bucket y se conservan como incidencias.

Únicamente un bucket sin incidencias, delimitado por intervalos adyacentes y con OHLC + volumen BID exactamente iguales a la referencia nativa puede emitir CLOSED_AGGREGATE_BAR, siempre QUARANTINED. Los demás se guardan como INCOMPLETE_BUCKET/BAR_COMPARISON, no como barras completas, y no alimentan features. No hay tolerancias numéricas nuevas ni valores corregidos.

La referencia CopyRates solicita solamente el timestamp nativo exacto de la barra observada que se acaba de cerrar; registra solicitud, respuesta, tiempos de recepción y hash. No usa CopyTicks, no se consulta el primer bucket parcial, no se incorporan barras descargadas a la serie derivada y no se repara volumen/OHLC. La etiqueta del request no certifica UTC; una respuesta fuera del único bar solicitado se rechaza. La conexión Python comprueba terminal, carpeta, servidor, cuenta de observación demo y chart BID, y no arranca MT5 ausente ni envía órdenes. DEMO executor permanece deshabilitado.

OnTick no entrega necesariamente todos los ticks: https://www.mql5.com/en/docs/event_handlers/ontick y https://www.mql5.com/en/docs/series/copyticks . Por ello la comparación permite afirmar solo paridad del agregado; no certifica el instante de generación ni exhaustividad de eventos. El estado científico permanece bloqueado incluso con agregados coincidentes. En el corte real todavía no hay ticks ni barras: M5_PARITY real está PENDING, nunca PASS por implementar código.

## Features y señales

MAIN_K reutiliza sin modificar python/native_metadata_v3.py: 5/3/3 SMA LowHigh, ratio de sumas, límite plano nativo 100. BUY anterior<=20/actual>20, SELL anterior>=80/actual<80; D=3 permanece en el oracle nativo y no sustituye MAIN_K. No cambian estrategia, FOLLOW/INVERT, TP240/SL180/TIME_EXIT100.

Se implementan stoch_k, delta_k_1, ATR(14), relative_volume_20, ha_direction y range_to_ATR exclusivamente sobre barras derivadas anteriores al callback de decisión. ATR usa el seed y recurrencia del ejemplo MetaQuotes ATR instalado, inicializado con historia propia: 14 true ranges tras la primera barra; no utiliza caché nativa anterior. HA mantiene exactamente open/close recurrentes y Ready a 276 del HeikinAshiCore congelado, con seed propio y sin truncar su memoria al limitar el buffer de barras. Todos los missing permanecen missing, sin imputación. Los hashes de contexto, barra, dependencia y señal permiten seguir el origen.

La implementación se contrastó con iStochastic e iATR reales y el HeikinAshiCore inalterado en un custom symbol exclusivamente sintético, en el terminal portátil aislado ya existente. 499 barras: MAIN_K error máximo 0 (bound aprobado 1e-10), ATR error máximo 0 (tolerancia 0), HA sin discrepancias de dirección/readiness. Compilación 0 errores/0 warnings. No se abrieron datasets protegidos ni se ejecutó Strategy Tester sobre periodos reales. La paridad sintética no demuestra semillas/coverage/vintage del dataset vivo ni procede a activarlo.

## Madurez, soporte y gobernanza

El worker lee los requisitos del paquete congelado, protegido por hashes: 350 M5 propios de warmup; primeras 800 señales consecutivas; exactamente 100 barras observadas posteriores; soporte mínimo total 200, BUY 80, SELL 80. Maturity.json se actualiza automáticamente cada dos segundos con progreso diagnóstico y científico separados, incluidos bars, warmup, BUY/SELL, selección, post-barras, incidentes, membership y causalidad.

Todas las señales siguen siendo diagnósticas, evaluable=false. No se leen ni calculan labels, PnL o resultados para elegibilidad/selección; el contador evaluable no puede crecer por falta de labels autorizados, cobertura, independencia o admisión. Los 800/100 se prueban como contadores de adquisición, no como scoring. Una discontinuidad no reinicia ni extiende silenciosamente esa selección para buscar otro periodo más limpio. La reserva actual ya tiene gaps: protocol_stream_unbroken=false, conservado, sin declarar madurez mediante esperar una nueva racha. El contador de contexto local puede reiniciar seeds por segmento, pero eso no reinicia el estudio ni autoriza otra cohorte.

Los cursores raw→derivados y referencias de cada barra/feature/señal están en un ledger SQLite append-only hasheado. MEMBER/EXPOSURE_PREFIX registra cada prefijo realmente procesado, sin labels. La pertenencia de este prefijo es trazable; no se inventan los IDs/splits ausentes del ledger legado ni se declara completada su independencia. TRAIN agotado, Discovery Validation, Historical Holdout y Final Test siguen cerrados.

## Recuperación y recursos

SQLite WAL+synchronous FULL realiza una transacción que incluye artifacts, hash chain y estado/cursor. Triggers impiden UPDATE/DELETE sobre artifacts. El estado bounded y su hash deben coincidir con el último CHECKPOINT del ledger. Al reiniciar se verifica la cadena completa derivada y el prefijo raw ya procesado; ningún reset destructivo está permitido. Un lock de archivo impide dos workers. Los tests simulan fallo de transacción y alteración de estado: se conserva el último cursor committed.

Memoria de barras limitada a 351, HA/ATR de estado constante; máximo 1000 inputs por transacción. Cuando no llegan datos no se añaden artefactos; no se consulta MT5 por cada heartbeat. El supervisor ya instalado inicia únicamente el worker faltante, con comprobación de 30 s y relanzamiento mínimo de 60 s; arranca también después del siguiente login Windows. El main worker es un hijo runtime Python más su pequeño launcher .venv, no dos capturadores. No se modificaron energía, scripts nativos, tareas anteriores ni el otro proyecto.

Parar solo los derivados, conservando raw y datos:

    powershell -NoProfile -File .\tools\stop_prospective_pipeline.ps1

El flag deshabilita relanzamiento y el worker sale entre transacciones, sin terminar productores. No hay solicitud de intervención manual ahora. El próximo estado es procesamiento y monitorización automáticos en cuarentena, a la espera de datos reales y evidencia científica suficiente; ninguna fecha de madurez se inventa.

Las dos copias textuales de ejecución nativa se publican con LF. artifact_normalization.json vincula sus bytes originales CRLF locales a los hashes publicados; los checksums de compilación/certificado conservan la referencia a los originales. No se modificaron datos de mercado ni los artefactos locales de ejecución.
