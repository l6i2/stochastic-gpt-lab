# Inventario histórico XM de US30Cash

La evidencia de series anuncia **2011-08-10** en el servidor y **2022-06-03** en la base local del terminal aislado. El límite de gráfico actual es **20.000**. El ensayo anterior registró 20.000 M1 y 20.316 M5 como contadores de series, con primeras etiquetas de gráfico 2026-10-13 y 2026-07-22. El congelado legado documenta ticks desde 2023-12-20, con advertencias de ticks generados en el Tester. Los totales y la primera fecha real del servidor por tipo siguen indeterminados. [Recibo de contadores](../research/studies/maxbars_history_20261102_v1/summary.json).

El intervalo completo verificado para diagnóstico es **2024-01-02 en el dominio nativo**, con **1.376 M1, 276 M5 y 79.211 ticks**. El primer tick en el archivo es 01:00:00.107 nativo. Los siete archivos del run archivado del Tester coinciden con el manifiesto publicado. La consulta Python nueva en el mismo día devolvió **96 ticks** en cinco minutos. Las consultas de barras M1/M5 devolvieron filas fuera del rango solicitado y el guard descartó la respuesta antes de persistir filas. La consulta pequeña no se suma al total sellado. El ensayo nativo CopyRates anterior devolvió error 4401 con el límite 20.000 para el mismo día.

La descarga acotada Python y el archivo nativo del Tester son rutas verificadas dentro del alcance permitido. El exportador MQL5 con CopyRates/CopyTicksRange se conserva para ventanas con autorización verificable. Los metadatos de series, el límite del gráfico y el resultado de CopyTicksRange se registran por separado. [SeriesInfoInteger](https://www.mql5.com/en/docs/series/seriesinfointeger) · [CopyRates](https://www.mql5.com/en/docs/series/copyrates) · [CopyTicksRange](https://www.mql5.com/en/docs/series/copyticksrange).

## Matriz de reservas

| Periodo | Rol | Uso |
|---|---|---|
| 2024-01-02 XM nativo | DIAGNOSTIC_ONLY_PREVIOUSLY_EXPOSED | Replay fijo autorizado |
| 2023-12-20 a 2026-10-13 parcial | MIXED_PROTECTED | Solo metadatos publicados del master |
| TRAIN legado purgado / quality-v1 | TRAIN_EXHAUSTED | Reproducción autorizada acotada y resultados ya publicados |
| Discovery Validation / Final Test | PROTECTED_BOUNDARIES_INCOMPLETE | Bloqueados, incluido el tail del master |
| Historical Holdout | PROTECTED_UNKNOWN_EXTENT | Bloqueado aunque no se conocen sus límites |
| Reserva C+F e históricos B | RESERVED_EXPOSED_DIAGNOSTIC | Aislamiento de reserva, ninguna reasignación |
| B+C desde su corte exclusivo | RESERVED_BC_QUARANTINED | Solo estudio B+C, sin importación histórica externa |
| Otros periodos, incluidos los anteriores al master | UNCLASSIFIED | Sin consultas de contenido hasta verificar roles |

La ruta de adquisición extensa debe comenzar con intervalos permitidos verificables. El controlador existente proporciona límites de consulta, vintages y reanudación. Se mantuvieron B+C y el terminal activo sin cambios de configuración. Las ventanas OHLC sin Bid/Ask utilizable se clasificarán separadamente y sus barras servirán para descripción, sin simular fills exactos.

[Recibo de consulta, matriz y hashes](../research/studies/historical_return_20261108/sha256.json).

[Resolución de reservas, alcance exacto y nuevas comprobaciones](HISTORICAL_MEMBERSHIP_RESOLUTION.md).
