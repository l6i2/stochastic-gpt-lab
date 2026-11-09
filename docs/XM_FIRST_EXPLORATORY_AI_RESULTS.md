# Resultados y límite del primer entrenamiento exploratorio

El nuevo vintage reprodujo la secuencia de tiempo, BID y ASK utilizada por el replay fijo. Se retienen sus 28 señales, 13 BUY y 15 SELL, y 18 pares de salidas completos. Las métricas describen la simulación virtual del día expuesto.

| Política | Cerradas | Acierto en cerradas | PF | PnL cerrado |
|---|---:|---:|---:|---:|
| FOLLOW | 19 | 52,63 % | 1,386 | +472,12 |
| INVERT | 19 | 31,58 % | 0,455 | −999,06 |

Cada modo tuvo 9 censuras. PnL en unidades de precio. El recibo conserva MFE, MAE, drawdown y desglose BUY/SELL. No se calculó rendimiento por sesión sin mapping certificado.

La purga deja **cero evaluaciones BUY y una SELL**. Los valores finitos de las seis features no certifican las semillas de ATR y Heikin Ashi ni el contexto previo. El día único, expuesto y censurado no permite medir generalización. Dataset de entrenamiento y modelos sin crear, **0/8 fits**, sin métricas de IA. Siete pruebas de diagnóstico nativo pasaron.

[Recibos, índice de lotes y hashes](../research/studies/us30cash_xm_historical_ai_development_v1/sha256.json).

La ampliación descriptiva conserva cero fits. [Contexto multivariable](MULTIVARIATE_MARKET_CONTEXT_RESEARCH.md) · [Causalidad e intratrade](FEATURE_CAUSALITY_AND_LEAKAGE_AUDIT.md).
