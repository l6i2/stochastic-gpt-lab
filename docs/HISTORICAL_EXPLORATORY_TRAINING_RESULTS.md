# Resultados del estudio histórico exploratorio

El replay congelado pasó sobre 79.211 ticks, 1.376 M1 y 276 M5. El vintage ya preservado de cinco minutos contiene 96 ticks válidos que coinciden con el archivo sellado. Los 28 casos diagnósticos incluyen 13 BUY y 15 SELL. Hay 18 pares completos, nueve por lado. El plan conservó los censurados para delimitar cronología y aplicó purga por ambos horizontes.

| Fold | TRAIN BUY / SELL antes de filtrar features | Evaluación BUY / SELL tras purga |
|---|---:|---:|
| 1 | 2 / 5 | 0 / 0 |
| 2 | 4 / 7 | 0 / 1 |
| 3 | 6 / 8 | 0 / 0 |
| 4 | 9 / 9 | 0 / 0 |

Quedaron cero evaluaciones BUY y una SELL. Por ello el presupuesto consumido fue cero. Los dos estimadores están especificados sin ajuste, sin artefactos de modelo ni métricas de IA.

| Baseline virtual | Cerradas / censuradas | Acierto | PF | PnL cerrado |
|---|---:|---:|---:|---:|
| FOLLOW | 19 / 9 | 52,63 % | 1,386 | +472,12 |
| INVERT | 19 / 9 | 31,58 % | 0,455 | −999,06 |

PnL en unidades de precio. El replay y el recibo conservan métricas por lado, drawdown, MFE, MAE y motivos de salida. Reversiones y rendimiento por sesión certificada quedan sin estimar. La concentración en un día ya expuesto, la censura y la escasez de folds impiden una inferencia de rendimiento futuro.

[Recibos y hashes](../research/studies/us30cash_historical_exploratory_ai_v1/sha256.json).
