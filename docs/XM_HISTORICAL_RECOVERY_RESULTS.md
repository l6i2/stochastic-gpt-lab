# Resultados de recuperación histórica XM

Se implementó y ejecutó el registro B separado. En el corte publicado se consultaron 302 intervalos que cubren 26 gaps delimitados por observaciones nativas posteriores al corte autorizado. Se recuperaron 246.397 ticks, 1.295 M1 y 251 M5. Los 26 gaps devolvieron algún dato. No quedan requests delimitados sin intentar en este corte.

| Comprobación | Resultado |
|---|---|
| Bid/Ask válido | 246.397 filas, cero inválidas |
| M1 agregadas contra M5 nativas | 251 comparaciones exactas |
| OHLC de ticks contra M1 | 1.295 comparaciones exactas |
| Volumen por flags BID frente a M1 | Cero diferencias en esas M1 |
| Filas idénticas dentro de cada consulta | Cero en la selección vigente |
| M1 ausentes | 60, todas fuera de QUOTE según la metadata semanal observada |
| Historial A | 88 M5, 0 consecutivas, 0 elegibles, prefijo conservado |
| Órdenes, fits científicos y scoring protegido | Cero |

La ausencia de esas 60 M1 es consistente con un cierre semanal observado. No constituye por sí sola una certificación de excepciones ni se rellena con barras. Otros 18 registros de interrupción esperan una cotización nativa posterior que permita delimitar su intervalo. No equivalen necesariamente a 18 incidentes físicos distintos.

## Defecto corregido y alternativas

La repetición controlada sobre dos minutos obtuvo 682 ticks con date_to inmediatamente anterior al extremo y 688 con el extremo inclusivo. Los 682 ticks iniciales son un prefijo idéntico. Los seis adicionales están en el último segundo del intervalo. La corrección mantuvo los seis y filtró las filas del extremo superior, dejando OHLC y volumen exactos. El intento inicial permanece archivado.

CopyRates/CopyTicksRange MQL5 se compilaron y ejecutaron en el terminal aislado. Su conexión no estaba disponible y la solicitud de ticks devolvió 4403. Esa alternativa no acreditó recuperación real. La ruta Python del XM activo completó la descarga. El controlador Strategy Tester quedó sin ejecutar por falta del manifiesto original de splits requerido por su gate. No se modificó ese gate.

## Reconstrucción causal diagnóstica

Se eligió el primer bloque recuperado con 30 M5 contiguas y sus M1 completas, sin selección por rendimiento. En el oráculo nativo aislado, MAIN_K tuvo error absoluto máximo cero, el candidato ATR coincidió en 17 valores y HA Open/High/Low/Close coincidió en las 30 barras. Se observaron dos señales BUY y ninguna SELL dentro de ese bloque diagnóstico. Esos conteos no se transfieren al estudio prospectivo.

El bloque reconstruido fue descargado después de sus eventos. No acredita disponibilidad en el instante original de entrada. HA propio a 276 y ATR propio de C+F siguen pendientes; el cálculo de producción conserva su versión congelada. La auditoría causal global sigue FAIL y la admisión permanece cerrada.

## Integridad y automatización

La auditoría completa verificó 320 recibos y sus payloads locales, incluyendo intentos conservados que no entran en los totales vigentes. La repetición sin nuevos intervalos no volvió a consultar ni a descargar datos y conservó el head. Pasaron 35 pruebas de recuperación, fallos API y alternativa, protección, bordes de milisegundos, hashes, interrupción simulada, persistencia, duplicados e aislamiento.

La tarea nueva inicia con la sesión de Windows y se repite cada cinco minutos. Se observó una ejecución programada con resultado cero. Guardian, NTS y productor C+F conservan sus tareas. No se provocó un apagado ni se cambiaron políticas de energía.

Los primeros recibos guardaban los números de registros que originaron los gaps. En esta auditoría se añadió su vínculo con el índice verificado; las consultas futuras incorporan directamente el head del índice. Se conserva esa distinción de vintage. La procedencia identifica terminal, servidor y hashes; no es una firma criptográfica del broker ni certificación UTC de generación.

Los payloads permanecen en PC A. Los [recibos publicados](../research/studies/xm_historical_recovery_20261108/results.json), [índice de archivos](../research/studies/xm_historical_recovery_20261108/archive_index.json) y [ledger de exposición](../research/studies/xm_historical_recovery_20261108/exposure_ledger.json) permiten comprobar sus hashes contra el archivo local. La reproducción de indicadores reales requiere ese archivo autorizado.

La [propuesta híbrida](XM_HYBRID_DATASET_FEASIBILITY.md) queda inactiva. La descarga no convierte los intervalos reservados a C+F en datos independientes. TRAINING_EXECUTED=false, PROTECTED_SCORING=false, DEMO=DISABLED y LIVE_TRADING=false.
