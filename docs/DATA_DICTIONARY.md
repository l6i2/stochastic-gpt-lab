# Diccionario del dataset v1.1

Una fila por señal; CSV separado por coma, UTF-8 y punto decimal. Faltantes se escriben vacíos, se leen como NaN y se conservan en Parquet. No se reemplazan por ceros. Todos los precios, distancias, ATR y PnL están en unidades absolutas del símbolo. Ratios son fracciones salvo nombres que indican percent/percentile (0–100). La lista exhaustiva está al final; `python/research.py:REQUIRED` define el contrato ejecutable.

`t=0` representa la vela de señal ya cerrada; `t=1` la vela anterior. Una ventana que incluye señal nunca incluye la vela de entrada. Media/desviación con ventana insuficiente, denominador cero o indicador EMPTY_VALUE => vacío. Desviación poblacional (ddof=0). Percentil empírico = `100*count(x[j] <= x[0])/n`, incluyendo t=0; los empates cuentan completos.

## Identidad, configuración y auditoría

`signal_id`: símbolo + M5 + cutoff en ms + línea trigger. `symbol`, `schema_version`, `trigger_line`, `simulation_mode`, constantes `stoch_k_period=5`, `stoch_d_period=3`, `stoch_slowing=3`, `tp_distance=240`, `sl_distance=180`, `time_exit_bars=100`. Una corrida usa un símbolo/configuración.

`signal_time_msc`: cutoff inclusivo de features, en la escala de tiempo server de MT5. `feature_max_time_msc`: límite declarado de features. `signal_bar_open`, `entry_bar_open`: segundos de server. `entry_time_msc`: tick de entrada, posterior al cutoff; **ejecución, no predictor**. `history_bars_available`: barras cerradas cargadas, máximo 350. `run_status`: OK o ABORTED; además se exige audit lateral (signals, rows_written, aborted, deinit_reason). El audit registra además bin/tamaño máximo del perfil, fuente, ancla de sesión, reglas horarias del broker, build del terminal y confirmación de ticks reales. Los campos de tiempo MT5 no deben interpretarse como UTC sin la corrección del broker.

## Stochastic

| Campo | Definición |
|---|---|
| stoch_k, stoch_d | Buffers nativos MT5 en t=0 |
| stoch_k_prev, stoch_d_prev | Buffers en t=1 |
| distance_to_20, distance_to_80 | Línea trigger actual menos umbral (con signo) |
| delta_k_1/2/3, delta_d_1/2/3 | Línea actual menos su valor de 1/2/3 barras atrás; no diferencias sucesivas |
| bars_in_oversold, bars_in_overbought | Longitud de la secuencia contigua extrema que termina en t=1; la vela de salida no cuenta |
| zone_run_censored | 1 si la secuencia llega al límite de historia cargada; el conteo entonces es una cota inferior |
| exit_speed_from_zone | Valor absoluto del cambio de la línea trigger entre t=1 y t=0, unidades de oscilador/barra |

## Volumen

`tick_volume` y `real_volume` proceden de MqlRates y se conservan separados. `real_volume_status=broker_reported` si es positivo; `zero_or_unavailable` si es cero. Cero no prueba ausencia de operaciones reales. `volume_feature_source=tick_volume`: todas las siguientes features se basan en **actividad**, nunca se presentan como volumen negociado.

| Familia | Fórmula |
|---|---|
| relative_volume_n, n=5/10/20/50/100 | tick_volume[0] / media(tick_volume[1:n+1]) |
| volume_change_n, n=1/3/5 | tick_volume[0]/tick_volume[n] − 1 |
| volume_percentile_n, n=20/50/100 | Percentil empírico en [0,n) |
| volume_zscore_n, n=20/50 | (v[0] − media(v[1:n+1])) / std(v[1:n+1]) |
| volume_expansion | v[0]/media(v[1:21]); alias explícito de relative_volume_20, no flag optimizado |

## Volume Profile causal

Prefijos: `vp_30m_`, `vp_60m_`, `vp_120m_`, `vp_240m_`, `vp_session_`, `vp_previous_session_`.

Ventanas móviles: `[cutoff+1−minutos*60000, cutoff]`. Sesión: día de server anclado a `SessionStartServerHour`, hasta cutoff. Se utiliza la sesión que contiene el último ms de la vela completada; la señal de medianoche incluye la sesión recién cerrada. Sesión previa: intervalo calendario completo inmediatamente anterior de 24 horas, no «última sesión con actividad» (domingo/festivos pueden no tener datos). Es una convención configurable, no un calendario de futuros CME ni acciones NYSE.

`CopyTicksRange` en fragmentos consecutivos inclusivos de hasta una hora, sin solapamiento; se rechaza cualquier tick fuera de ventana. No se consulta más allá del cutoff. Defaults: bins de 10 unidades, anclados en cero; índice `floor(price/bin_size)`. Límite 20 000 bins ocupados y de amplitud total; excederlo invalida sólo el perfil. No se suaviza ni se reparte volumen por OHLC.

Fuentes:

- `tick_activity_bid`: cada registro de tick devuelto con Bid positivo aporta 1 al bin de Bid, aunque sea una actualización de Ask o trade. Es actividad de ticks del feed, no contratos. No se deduplican ticks idénticos ni timestamps repetidos.
- `real_trade_volume_last`: sólo ticks con flags LAST/VOLUME/BUY/SELL, Last positivo y `volume_real>0`; peso `volume_real` al bin de Last. Los flags se combinan con OR para conservar trades del mismo precio. Se interpreta volumen por tick entregado por el broker, no un contador acumulado. Verificar semántica del feed antes de elegir este modo. Nunca se cambia a tick activity silenciosamente.

POC es centro del bin de máxima masa (empate: precio inferior). Área de valor: comenzar por POC y ampliar hacia el bin adyacente con mayor masa, de uno en uno; empate: inferior. Parar al acumular al menos 70 % de masa total. Se incluyen bins vacíos entre extremos. VAL es borde inferior, VAH borde superior. Puede contener más del 70 % por discretización. No se calcula con precios futuros ni perfiles dibujados.

| Sufijo | Definición |
|---|---|
| status | available_coverage_unverified, no_eligible_ticks, empty_window, copy_error_or_limit o bin_limit |
| source | tick_activity_bid o real_trade_volume_last |
| window_start_msc, window_end_msc | Límites inclusivos consultados |
| copy_error | Código MT5; −1 tick fuera de intervalo, −2 límite de bins |
| ticks_used | Registros elegibles incorporados, no suma de volumen real |
| first_tick_msc, last_tick_msc | Extremos temporales de los ticks elegibles usados |
| POC, VAH, VAL | Precios definidos arriba |
| distance_price_to_POC/VAH/VAL | close[0] menos nivel; signo conservado |
| inside_value_area | 1 si VAL <= close <= VAH, límites incluidos |
| above_value_area, below_value_area | close > VAH; close < VAL |
| POC_position_in_range | (índice POC relativo + 0.5)/número de bins desde mínimo a máximo |
| high_volume_node_nearest | Centro del máximo local de masa más cercano a close, masa >0 y >= ambos vecinos |
| low_volume_node_nearest | Centro del mínimo local <= ambos vecinos y estrictamente menor que al menos uno; admite huecos de masa cero |
| distance_to_HVN, distance_to_LVN | close menos el nodo correspondiente; vacío si no existe |

En bordes, vecino ausente equivale al propio bin. Empates de distancia favorecen precio inferior. Son nodos discretos sin suavizado ni umbrales ajustados. Una meseta positiva puede producir varios HVN. Un perfil de un bin puede no tener LVN.

`available_coverage_unverified` significa que la API no reportó error, **no** que el broker garantice historia completa. Primer/último tick y conteos ayudan a auditar; no se puede distinguir un hueco legítimo de datos omitidos sólo con CopyTicksRange. Perfiles faltantes conservan la fila y metadata; sus valores son NaN.

## Velas, volatilidad, tendencia y estructura

OHLC son Bid de MqlRates. `direction` = +1/−1/0 según close frente a open. `body=abs(close-open)`, `range=high-low`, `body_percent=100*body/range`; mecha superior `high-max(open,close)`, inferior `min(open,close)-low`. `range_to_ATR=range/ATR`.

`bullish_ratio_n`/`bearish_ratio_n`, n=5/10/20: fracción de velas alcistas/bajistas en [0,n), dojis en denominador sin sumar a ningún lado.

ATR es **iATR nativo MT5 de periodo 14**, sin reimplementación Python; `ATR_normalized=ATR/close`. `ATR_percentile_20/50/100` usa el percentil causal definido arriba. `rolling_std_20/50`: desviación poblacional de precios close, **no retornos**. `range_expansion=range[0]/media(range[1:21])`; `range_compression` es el cociente inverso, no un flag binario.

EMAs nativas MT5 sobre close: 20/50/100/200. `price_to_emaN=close[0]−EMA_N[0]`; `emaN_slope=EMA_N[0]−EMA_N[1]`. Diferenciales `ema20_minus_50`, `ema50_minus_100`, `ema100_minus_200`. `bull_alignment=EMA20>EMA50>EMA100>EMA200`; bear invierte desigualdades; igualdad => ninguno. La inicialización depende de la prehistoria nativa del terminal; aportar suficiente historia.

HH/HL/LH/LL no son pivotes retrospectivos: cuentan comparaciones de cada vela cerrada con su predecesora. Para ventana n=5/10/20 se hacen n comparaciones (requiere n+1 barras): HH high[j]>high[j+1]; HL low[j]>low[j+1]; LH high[j]<high[j+1]; LL low[j]<low[j+1]. Igualdad no suma. `distance_to_recent_high=close[0]−max(high[0:20])`; low análogo con mínimo. Incluyen la vela señal; no esperan confirmación futura.

## Hora

`server_time`, `UTC_time`, `NY_time`: strings `YYYY.MM.DD HH:MM:SS` del límite de cierre. `signal_utc_epoch`: segundos UTC corregidos. `server_utc_offset_seconds`: corrección aplicada. El offset de invierno y DST del broker son inputs; no usar `TimeGMT()` del Strategy Tester para inferirlos. Soporta NONE, EU (último domingo de marzo/octubre a 01 UTC) y US. NY usa reglas US **desde 2007** (segundo domingo de marzo a 07 UTC; primero de noviembre a 06 UTC). Históricos anteriores o brokers con reglas especiales no están cubiertos.

`NY_hour`, `NY_minute`; `weekday` lunes=0, domingo=6 en NY. `session` son intervalos NY **descriptivos, disjuntos**: Asia 19:00–03:00, London 03:00–08:00, New_York 08:00–17:00, Other 17:00–19:00. No pretenden modelar festivos ni horarios oficiales de cada bolsa. La ambigüedad de una hora repetida al cambiar DST del servidor exige verificar el histórico con el broker.

## Ejecución y resultados (excluidos de features)

`entry_bid`, `entry_ask`, `spread=ask-bid`, `follow_side`, `invert_side`. Para cada prefijo `follow_`/`invert_`: `entry_price`, `exit_time` (milisegundos de server), `exit_price`, `exit_reason` (TP/SL/TIME_EXIT/END_OF_DATA), `PnL`, `MFE`, `MAE`, `bars_in_trade`. Censura mantiene último precio observado como marca, PnL vacío y ventaja vacía si cualquiera de los lados está censurado. MFE/MAE no negativas en unidades de precio, definición y límites en STRATEGY_SPEC.

`excursion_quality=observed_quotes` o `full_exit_bar_bounds`. `directional_advantage=follow_PnL−invert_PnL`. Valores positivos favorecen FOLLOW. No implican rentabilidad monetaria.

## HEIKIN_ASHI — familia causal, schema 1.1

HA es exclusivamente contexto. No genera ni cancela señales, no modifica dirección Stochastic, entrada, TP, SL, timeout ni FOLLOW/INVERT. Los precios HA **no son cotizaciones ejecutables**.

### Serie, inicialización y warmup

El EA carga hasta 350 barras M5 **cerradas** en su primer cambio de vela. Recorre esas barras desde la más antigua hasta la de señal. Para la primera barra histórica usada:

```text
HA_Close[0] = (Open[0] + High[0] + Low[0] + Close[0]) / 4
HA_Open[0]  = (Open[0] + Close[0]) / 2
```

Para cada barra cronológicamente posterior t:

```text
HA_Close[t] = (Open[t] + High[t] + Low[t] + Close[t]) / 4
HA_Open[t]  = (HA_Open[t-1] + HA_Close[t-1]) / 2
HA_High[t]  = max(High[t], HA_Open[t], HA_Close[t])
HA_Low[t]   = min(Low[t], HA_Open[t], HA_Close[t])
```

La recurrencia y los contadores persisten toda la corrida. Se actualizan **en cada barra cerrada, también sin señal**; no se reinician por señal ni al deslizar la ventana de CopyRates. Se guardan 21 barras HA recientes para estadísticas y un estado recursivo/streak persistente. Se rechazan barras duplicadas, anteriores o cuyo cierre `(bar_open+300)*1000-1` supere el cutoff. La HA exportada debe corresponder exactamente a `signal_bar_open`; nunca a `entry_bar_open`.

Warmup fijo de **256 barras procesadas**, incluidas en la recurrencia pero excluidas de las ventanas HA exportables. La primera fila `ready` requiere **276 barras**: así su ventana máxima de 20 comienza en la barra 257. Para la misma secuencia de OHLC posterior al seed, un error inicial de HA_Open se divide por 2 por barra: queda multiplicado por 2^-256 al inicio de las ventanas elegibles (salvo redondeo). Esto no garantiza signo estable para dojis numéricamente casi exactos; las fórmulas de dirección son comparaciones estrictas.

Si no hay prehistoria suficiente, se conservan **todas** las señales y trades Stochastic: campos HA vacíos, `ha_status=warming_up`. No se fuerza un filtro operativo ni se completa HA retrospectivamente. Para un run ordinario, aportar las 350 barras previas recomendadas. Cambiar la fecha inicial puede cambiar seed/streak observado; conservar metadata y misma prehistoria al comparar corridas.

### Metadata HA

| Campo | Definición |
|---|---|
| ha_status | ready, warming_up o unavailable (desalineación de contexto); sólo ready publica features |
| ha_seed_bar_open | Timestamp server en segundos de la primera barra usada, no se mueve durante la corrida |
| ha_last_bar_open | Timestamp server de la última barra HA incorporada; igual a signal_bar_open para ready |
| ha_bars_processed | Total acumulado de barras cerradas procesadas desde seed |
| ha_warmup_bars | Constante 256 |
| ha_streak_left_censored | 1 si un streak actual o el previo alcanza la primera barra del seed; su longitud observada es una cota inferior |

Los streaks cuentan desde seed (incluido warmup), no se limitan a 21/350 barras. Un doji termina ambos streaks. Censura izquierda no cancela señales ni invalida los demás campos.

### Fórmulas de features

En la tabla, `x[0]` = HA de la vela señal cerrada, `x[j]` = j barras antes; `B=abs(HA_Close−HA_Open)`, `R=HA_High−HA_Low`. División por cero => vacío, nunca infinito. Medias y ratios sólo usan las barras HA descritas, no las futuras.

| Campos | Fórmula exacta |
|---|---|
| ha_open/high/low/close | OHLC sintéticos de la recurrencia anterior |
| ha_direction | +1 si HA_Close>HA_Open, −1 si menor, 0 si iguales |
| ha_body, ha_range | B, R |
| ha_body_percent | 100*B/R |
| ha_upper_wick | HA_High−max(HA_Open,HA_Close) |
| ha_lower_wick | min(HA_Open,HA_Close)−HA_Low |
| ha_upper_wick_to_range, ha_lower_wick_to_range | Mecha correspondiente/R, fracción 0–1 |
| ha_delta_close_1/2/3 | HA_Close[0]−HA_Close[j] |
| ha_delta_body_1/2/3 | B[0]−B[j] |
| ha_body_expansion | B[0]/B[1] (no se resta 1) |
| ha_range_expansion | R[0]/R[1] |
| ha_consecutive_bullish/bearish | Longitud contigua de ese color terminando en señal; 0 si señal de otro color o doji |
| ha_bullish_ratio_n/ha_bearish_ratio_n, n=3/5/10/20 | Fracción de barras de ese color en índices [0,n); incluye señal; dojis sólo en denominador |
| ha_avg_body_n/ha_avg_range_n, n=3/5/10/20 | Media de B/R en [0,n); incluye señal |
| ha_body_vs_avg5/10 | B[0]/media(B[1:n+1]); denominador excluye señal |
| ha_range_vs_avg5/10 | R[0]/media(R[1:n+1]); denominador excluye señal |
| ha_no_lower_wick/ha_no_upper_wick | 1 si mecha correspondiente <=1e-10 unidades de precio, tolerancia numérica fija |
| ha_small_body | 1 si R>0 y B<=0.25*R |
| ha_bullish_strong | 1 si direction=+1, no_lower_wick=1 y B>=0.5*R |
| ha_bearish_strong | 1 si direction=−1, no_upper_wick=1 y B>=0.5*R |
| ha_indecision | 1 si small_body=1 y ambas mechas >1e-10 |
| ha_changed_to_bullish | 1 si direction[0]=+1 y direction[1]!=+1; incluye transición desde doji |
| ha_changed_to_bearish | 1 si direction[0]=−1 y direction[1]!=−1; incluye transición desde doji |
| ha_bullish_after_bearish_run | 1 si dirección actual +1 y streak bearish que termina en la barra anterior >0 |
| ha_bearish_after_bullish_run | 1 si dirección actual −1 y streak bullish que termina en la barra anterior >0 |
| ha_bullish_run_before_signal/ha_bearish_run_before_signal | Longitud contigua de ese color terminando en la barra inmediatamente anterior, excluye señal |

Los umbrales 25 % / 50 % son convenciones descriptivas fijas, no parámetros optimizados con resultados. No activan acciones. En vela de rango cero, direction=0, small_body=0, strong=0, indecision=0; las dos flags sin mecha son 1 y los cocientes de rango son vacíos.

### Compatibilidad

Schema 1.1 incorpora 54 features y 6 campos de metadata HA: **329 columnas, 225 features numéricas causales**. CSV y Parquet conservan las mismas columnas y faltantes. Schema 1.0 sigue siendo legible/validable/analizable sin HA; no se puede reconstruir una serie recursiva completa usando sólo sus filas de señales. No se mezclan versiones dentro de un archivo; columnas HA requieren versión 1.1. Audit y dataset deben coincidir en versión.

## Columnas exhaustivas por clase

### Features causales numéricas

```text
stoch_k
stoch_d
stoch_k_prev
stoch_d_prev
distance_to_20
distance_to_80
delta_k_1
delta_k_2
delta_k_3
delta_d_1
delta_d_2
delta_d_3
bars_in_oversold
bars_in_overbought
exit_speed_from_zone
tick_volume
real_volume
relative_volume_5
relative_volume_10
relative_volume_20
relative_volume_50
relative_volume_100
volume_change_1
volume_change_3
volume_change_5
volume_percentile_20
volume_percentile_50
volume_percentile_100
volume_zscore_20
volume_zscore_50
volume_expansion
open
high
low
close
direction
body
range
body_percent
upper_wick
lower_wick
range_to_ATR
bullish_ratio_5
bullish_ratio_10
bullish_ratio_20
bearish_ratio_5
bearish_ratio_10
bearish_ratio_20
ATR
ATR_normalized
ATR_percentile_20
ATR_percentile_50
ATR_percentile_100
rolling_std_20
rolling_std_50
range_expansion
range_compression
price_to_ema20
price_to_ema50
price_to_ema100
price_to_ema200
ema20_slope
ema50_slope
ema100_slope
ema200_slope
ema20_minus_50
ema50_minus_100
ema100_minus_200
bull_alignment
bear_alignment
HH_count_5
HH_count_10
HH_count_20
HL_count_5
HL_count_10
HL_count_20
LH_count_5
LH_count_10
LH_count_20
LL_count_5
LL_count_10
LL_count_20
distance_to_recent_high
distance_to_recent_low
NY_hour
NY_minute
weekday
vp_30m_POC
vp_30m_VAH
vp_30m_VAL
vp_30m_distance_price_to_POC
vp_30m_distance_price_to_VAH
vp_30m_distance_price_to_VAL
vp_30m_inside_value_area
vp_30m_above_value_area
vp_30m_below_value_area
vp_30m_POC_position_in_range
vp_30m_high_volume_node_nearest
vp_30m_low_volume_node_nearest
vp_30m_distance_to_HVN
vp_30m_distance_to_LVN
vp_60m_POC
vp_60m_VAH
vp_60m_VAL
vp_60m_distance_price_to_POC
vp_60m_distance_price_to_VAH
vp_60m_distance_price_to_VAL
vp_60m_inside_value_area
vp_60m_above_value_area
vp_60m_below_value_area
vp_60m_POC_position_in_range
vp_60m_high_volume_node_nearest
vp_60m_low_volume_node_nearest
vp_60m_distance_to_HVN
vp_60m_distance_to_LVN
vp_120m_POC
vp_120m_VAH
vp_120m_VAL
vp_120m_distance_price_to_POC
vp_120m_distance_price_to_VAH
vp_120m_distance_price_to_VAL
vp_120m_inside_value_area
vp_120m_above_value_area
vp_120m_below_value_area
vp_120m_POC_position_in_range
vp_120m_high_volume_node_nearest
vp_120m_low_volume_node_nearest
vp_120m_distance_to_HVN
vp_120m_distance_to_LVN
vp_240m_POC
vp_240m_VAH
vp_240m_VAL
vp_240m_distance_price_to_POC
vp_240m_distance_price_to_VAH
vp_240m_distance_price_to_VAL
vp_240m_inside_value_area
vp_240m_above_value_area
vp_240m_below_value_area
vp_240m_POC_position_in_range
vp_240m_high_volume_node_nearest
vp_240m_low_volume_node_nearest
vp_240m_distance_to_HVN
vp_240m_distance_to_LVN
vp_session_POC
vp_session_VAH
vp_session_VAL
vp_session_distance_price_to_POC
vp_session_distance_price_to_VAH
vp_session_distance_price_to_VAL
vp_session_inside_value_area
vp_session_above_value_area
vp_session_below_value_area
vp_session_POC_position_in_range
vp_session_high_volume_node_nearest
vp_session_low_volume_node_nearest
vp_session_distance_to_HVN
vp_session_distance_to_LVN
vp_previous_session_POC
vp_previous_session_VAH
vp_previous_session_VAL
vp_previous_session_distance_price_to_POC
vp_previous_session_distance_price_to_VAH
vp_previous_session_distance_price_to_VAL
vp_previous_session_inside_value_area
vp_previous_session_above_value_area
vp_previous_session_below_value_area
vp_previous_session_POC_position_in_range
vp_previous_session_high_volume_node_nearest
vp_previous_session_low_volume_node_nearest
vp_previous_session_distance_to_HVN
vp_previous_session_distance_to_LVN
ha_open
ha_high
ha_low
ha_close
ha_direction
ha_body
ha_range
ha_body_percent
ha_upper_wick
ha_lower_wick
ha_upper_wick_to_range
ha_lower_wick_to_range
ha_delta_close_1
ha_delta_close_2
ha_delta_close_3
ha_delta_body_1
ha_delta_body_2
ha_delta_body_3
ha_body_expansion
ha_range_expansion
ha_consecutive_bullish
ha_consecutive_bearish
ha_bullish_ratio_3
ha_bullish_ratio_5
ha_bullish_ratio_10
ha_bullish_ratio_20
ha_bearish_ratio_3
ha_bearish_ratio_5
ha_bearish_ratio_10
ha_bearish_ratio_20
ha_avg_body_3
ha_avg_body_5
ha_avg_body_10
ha_avg_body_20
ha_avg_range_3
ha_avg_range_5
ha_avg_range_10
ha_avg_range_20
ha_body_vs_avg5
ha_body_vs_avg10
ha_range_vs_avg5
ha_range_vs_avg10
ha_no_lower_wick
ha_no_upper_wick
ha_small_body
ha_bullish_strong
ha_bearish_strong
ha_indecision
ha_changed_to_bullish
ha_changed_to_bearish
ha_bullish_after_bearish_run
ha_bearish_after_bullish_run
ha_bullish_run_before_signal
ha_bearish_run_before_signal
```

### Metadata de evento, ejecución y configuración

```text
signal_id
symbol
schema_version
trigger_line
simulation_mode
signal_time_msc
feature_max_time_msc
signal_bar_open
entry_bar_open
entry_time_msc
stoch_k_period
stoch_d_period
stoch_slowing
tp_distance
sl_distance
time_exit_bars
zone_run_censored
history_bars_available
volume_feature_source
real_volume_status
server_time
UTC_time
NY_time
signal_utc_epoch
session
server_utc_offset_seconds
entry_bid
entry_ask
spread
follow_side
invert_side
excursion_quality
run_status
ha_status
ha_seed_bar_open
ha_last_bar_open
ha_bars_processed
ha_warmup_bars
ha_streak_left_censored
```

### Metadata de perfiles

```text
vp_30m_status
vp_30m_source
vp_30m_window_start_msc
vp_30m_window_end_msc
vp_30m_copy_error
vp_30m_ticks_used
vp_30m_first_tick_msc
vp_30m_last_tick_msc
vp_60m_status
vp_60m_source
vp_60m_window_start_msc
vp_60m_window_end_msc
vp_60m_copy_error
vp_60m_ticks_used
vp_60m_first_tick_msc
vp_60m_last_tick_msc
vp_120m_status
vp_120m_source
vp_120m_window_start_msc
vp_120m_window_end_msc
vp_120m_copy_error
vp_120m_ticks_used
vp_120m_first_tick_msc
vp_120m_last_tick_msc
vp_240m_status
vp_240m_source
vp_240m_window_start_msc
vp_240m_window_end_msc
vp_240m_copy_error
vp_240m_ticks_used
vp_240m_first_tick_msc
vp_240m_last_tick_msc
vp_session_status
vp_session_source
vp_session_window_start_msc
vp_session_window_end_msc
vp_session_copy_error
vp_session_ticks_used
vp_session_first_tick_msc
vp_session_last_tick_msc
vp_previous_session_status
vp_previous_session_source
vp_previous_session_window_start_msc
vp_previous_session_window_end_msc
vp_previous_session_copy_error
vp_previous_session_ticks_used
vp_previous_session_first_tick_msc
vp_previous_session_last_tick_msc
```

### Resultados

```text
follow_entry_price
follow_exit_time
follow_exit_price
follow_exit_reason
follow_PnL
follow_MFE
follow_MAE
follow_bars_in_trade
invert_entry_price
invert_exit_time
invert_exit_price
invert_exit_reason
invert_PnL
invert_MFE
invert_MAE
invert_bars_in_trade
directional_advantage
```
