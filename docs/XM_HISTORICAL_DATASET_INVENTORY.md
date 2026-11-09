# Inventario XM para desarrollo histórico amplio

Se recuperó el día fijo permitido en **276 lotes** de cinco minutos con Python CopyTicksRange. Se guardaron 79.211 ticks, todos con Bid/Ask válido, orden y cotizaciones idénticos al archivo sellado. El guard pausó la extracción a los 140 lotes y reanudó por recibos tras recuperarse la RAM. Se conserva el vintage local, con reloj de extracción y hash por lote. B+C permaneció en ejecución.

| Serie del día autorizado | Filas | Primera etiqueta XM | Última etiqueta XM |
|---|---:|---|---|
| M1 nativas archivadas | 1.376 | 01:00 | 23:59 |
| M5 nativas archivadas | 276 | 01:00 | 23:55 |
| Ticks históricos recuperados | 79.211 | 01:00:00.107 | 23:59:58.386 |

Se cotejaron OHLC y volumen de todas las M1 existentes y todas las M5 directas a partir de ticks. Cuatro minutos carecen de M1 y de ticks en el vintage y el archivo sellado. Las cuatro M5 correspondientes pasan el cotejo directo con ticks. Se mantuvo el último segundo fuera de la consulta para preservar el límite del día. No hay ticks archivados en ese segundo. Las horas son etiquetas nativas de XM.

Los ensayos previos de CopyRates Python rechazaron respuestas fuera del rango del día. CopyRates MQL5 dio error 4401 con 20.000 barras y se usaron las barras selladas del exportador nativo. Los metadatos del servidor anuncian series desde 2011-08-10. La profundidad por tipo sigue sin certificar fuera del intervalo autorizado. El día fijo está expuesto y su recuperación no amplía el permiso de desarrollo.

[Recibos, índice de lotes y hashes](../research/studies/us30cash_xm_historical_ai_development_v1/sha256.json).
