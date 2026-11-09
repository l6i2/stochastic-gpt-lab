# Baseline histórico Stochastic M5

Se reprodujo el replay Python contra el exportador virtual de MT5 sobre el diagnóstico autorizado del 2 de enero de 2024. Paridad OHLC de 1.376 M1 y 276 M5, 28 señales y 56 caminos. K/D/Slowing 5/3/3, cruce de 20 hacia arriba y de 80 hacia abajo, entrada en la M5 siguiente con Bid/Ask, TP 240, SL 180 y salida temporal a las 100 barras observadas. Se conserva la resolución intrabar del contrato.

| Señal | Modo | Cerradas | Censuradas | Acierto cerrado | PF | PnL cerrado | DD por salida | MFE/MAE media observada |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ALL | FOLLOW | 19 | 9 | 52.63% | 1.386 | +472.12 | -393.20 | 108.07 / 88.52 |
| ALL | INVERT | 19 | 9 | 31.58% | 0.455 | -999.06 | -1052.16 | 90.28 / 104.17 |
| BUY | FOLLOW | 9 | 4 | 44.44% | 1.042 | +31.00 | -742.15 | 96.57 / 92.30 |
| BUY | INVERT | 9 | 4 | 33.33% | 0.684 | -227.54 | -660.34 | 103.69 / 101.41 |
| SELL | FOLLOW | 10 | 5 | 60.00% | 1.915 | +441.12 | -366.19 | 118.04 / 85.25 |
| SELL | INVERT | 10 | 5 | 30.00% | 0.306 | -771.52 | -931.50 | 78.65 / 106.56 |

PnL y excursiones en unidades de precio. El drawdown se calcula por orden de salida de los caminos virtuales cerrados. Se conservaron los censurados y hubo 18 señales con ambos modos completos. Rentabilidad por sesión certificada, frecuencia de recuperaciones/reversiones y sensibilidad independiente a variaciones de spread o ejecución quedan NO DISPONIBLES en este corte. El replay valida la estrategia virtual con el tape permitido y su spread observado. La muestra de un día ya expuesto no permite inferir generalización.

[Replay, distribuciones y hashes](../research/studies/historical_return_20261108/sha256.json).
