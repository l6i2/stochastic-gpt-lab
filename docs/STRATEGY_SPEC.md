# Especificación fija — versión 1.0

## Señal y parámetros

Instrumento único configurable, inicialmente US30/US30Cash. Operación M5. `iStochastic(symbol, PERIOD_M5, 5, 3, 3, MODE_SMA, STO_LOWHIGH)`. Se utilizan los buffers nativos de MT5; no una aproximación Python del indicador. SMA y Low/High son decisiones explícitas porque no se recibió la configuración histórica original.

`trigger_line=MAIN_K` elige buffer 0; `SIGNAL_D` buffer 1. Para la vela cerrada t:

- BUY si `line[t-1] <= 20 && line[t] > 20`.
- SELL si `line[t-1] >= 80 && line[t] < 80`.
- La igualdad en t no activa señal. No importa la posición relativa de K y D. Una salida de zona puede generar una señal nueva aunque haya trades abiertos.

Ningún parámetro de la estrategia se ajusta desde el análisis. TP/SL y timeout son constantes. Si se quiere comparar otra línea trigger, usar un nuevo run y un dataset separado.

## Instantes y causalidad

`signal_bar_open` es el inicio de la vela cerrada. `signal_time_msc=(signal_bar_open+300)*1000-1`: último milisegundo **anterior** a la apertura siguiente. Ningún tick en la nueva vela pertenece a las features. El cierre legible `server_time` es el límite de la vela, un milisegundo después del cutoff. `CopyRates` y todos los buffers empiezan en shift 1; shift 0 sólo identifica la nueva vela para ejecución.

La entrada es el primer tick recibido de la siguiente vela M5 disponible. `entry_time_msc` registra el instante real: puede no ser exactamente `:00.000` y puede haber huecos entre sesiones. No se rellenan velas inexistentes. Tras iniciar el tester, se espera el primer cambio de vela; no se opera retrospectivamente el cierre anterior a la inicialización.

`entry_bid`, `entry_ask`, `spread`, lado, precios y resultados son metadata de ejecución/etiquetas. **No son features disponibles al cierre de señal**. La lista explícita `FEATURE_COLUMNS` impide incluirlos en correlaciones predictoras.

## Contrafactuales

BUY: FOLLOW BUY, INVERT SELL. SELL: FOLLOW SELL, INVERT BUY. Dos trades virtuales totalmente independientes en el mismo tick de apertura, sin cuenta compartida, netting, límites de posiciones ni modificación de lotaje.

| Lado | Entrada | TP | SL | Cotización de salida |
|---|---|---|---|---|
| BUY | Ask | entrada + 240 | entrada − 180 | Bid |
| SELL | Bid | entrada − 240 | entrada + 180 | Ask |

Son **unidades de precio**, no puntos mínimos del broker ni dinero. `PnL=side*(exit-entry)`, side BUY=+1/SELL=−1. `directional_advantage=follow_PnL-invert_PnL`. No hay comisión, swap o slippage aleatorio; el spread sí se refleja en ambas entradas y salidas.

En TICK_QUOTES el SL se llena en la cotización observada que lo cruza (puede perder más de 180 en un gap); TP se llena al nivel de 240 sin mejora de precio. Al tick de frontera se evalúan primero las barreras y luego TIME_EXIT. El vencimiento ocurre en el primer tick tras completar 100 barras observadas desde la vela de entrada, con el Bid/Ask disponible. No equivale necesariamente a 500 minutos de reloj por fines de semana/huecos. Cada tick del mismo timestamp se procesa en el orden del tester.

La primera vela cuenta como 1. TIME_EXIT es 100. Una salida en el tick de apertura siguiente se atribuye al número de barras completadas (mínimo 1). MFE y MAE son máximos no negativos de PnL observado favorable y adverso, incluyendo spread inicial. En TP la excursión de ese tick se limita al precio de llenado, no al sobrepaso del tick.

## Sin ticks de ejecución: BAR_CONSERVATIVE

Se evalúa la barra cerrada por completo. BUY usa OHLC Bid; SELL usa `OHLC Bid + bar.spread*SYMBOL_POINT`. El spread real de entrada sigue siendo el del primer tick recibido. Si el precio de apertura supera una barrera, esa salida tiene orden conocido. En los demás casos, si high/low admiten TP y SL, **SL primero**. SL por gap usa precio de apertura; otros SL usan nivel fijo; TP usa nivel fijo.

TIME_EXIT usa el cierre de la barra número 100. Los tiempos de salida intrabar desconocidos se registran como fin de vela; los gaps conocidos como apertura. MFE/MAE usan todos los extremos de la vela de salida: son cotas, pueden incluir recorrido posterior al cierre virtual y se etiquetan `full_exit_bar_bounds`. No se utilizan como features.

## Fin del histórico y errores

Trades activos al terminar: `END_OF_DATA`, precio/timestamp de última cotización como marca, PnL y ventaja vacíos (censura), MFE/MAE observados conservados. No se fingen TIME_EXIT ni resultados completos. Se exporta una fila por señal, en orden de señal; la cola retrasa escritura hasta resolver ambos resultados. Las filas pendientes se escriben al desinicializar. El audit lateral registra señales, filas y abortos. Un cierre abrupto del proceso puede impedir el último flush: el validador exige audit.

Error de buffers necesarios o cotizaciones inválidas: abortar run; no continuar saltándose señales silenciosamente. Error/falta de ticks de perfil: conservar señal y emitir campos de ese perfil vacíos con status. Un run abortado no sirve para análisis. Ante 0 señales el CSV queda vacío y el audit tiene conteos cero; el análisis lo rechaza de forma explícita.

## Seguridad

`LIVE_TRADING=false`; `true` devuelve INIT_FAILED. Se exige `MQL_TESTER`, y se rechaza `MQL_OPTIMIZATION`. No existen llamadas para enviar, modificar o cerrar órdenes. La simulación no usa capital, lotaje, pending orders, martingala, grid o averaging.
