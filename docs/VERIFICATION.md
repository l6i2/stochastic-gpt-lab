# Verificación realizada

Fecha: 2026-10-10. Proyecto nuevo: `/workspace/stochastic-gpt-lab`, con repositorio Git propio. Todas las escrituras del proyecto están dentro de ese directorio. No se abrió, modificó ni cambió rama de `asistente-trader-ia`.

## Evidencia local

Entorno: Python 3.12.14, pandas 2.2.3, numpy 2.3.5, pyarrow 24.0.0; pyarrow instalado en `.venv` local al proyecto. La `.venv` de esta verificación reutiliza pandas/numpy preinstalados; para otra máquina seguir la instalación aislada completa del README.

```text
.venv/bin/python -m unittest discover -s tests -v
Ran 16 tests
OK

.venv/bin/python -m compileall -q python tests
Completado sin errores
```

El contrato enumera 269 columnas y 171 features numéricas causales. Los registros de pruebas son sintéticos, creados temporalmente y eliminados al terminar. No son datos históricos ni evidencia de rentabilidad.

Cobertura:

- Compilación C++17 con `g++ -Wall -Wextra -Werror` y ejecución del núcleo escalar `ResearchCore.mqh` que el EA incluye directamente. Comprueba salida de zonas (incluidas igualdades), inversión, precios Bid/Ask, spread/PnL, límites de TP/SL, timeout, prioridad SL en vela ambigua, gaps y cronología de entrada.
- Validación de parámetros exactos, identidades únicas, timestamps crecientes, mapping, cotizaciones, PnL/ventaja y audit de conteos.
- Rechazo de timestamps de features/perfiles futuros y entradas prematuras. Prueba por perturbación de ticks futuros en el oráculo Python de perfil. Comprobación de fuentes separadas tick activity/real volume y de flags de trade.
- Inspección estática del EA: protección tester/live/optimización, ausencia de funciones de envío de órdenes, lectura desde barra cerrada y cutoff explícito de CopyTicksRange.
- Pérdidas, empates, censura, particiones 60/20/20, purga, walk-forward sin FINAL_TEST y cortes TRAIN invariantes a cambios futuros.
- CLI completa: validación CSV, análisis TRAIN, rechazo de acceso implícito a FINAL_TEST, evaluación final explícita con hipótesis.
- CSV→Parquet→lectura con igualdad de todos los valores y tipos pandas, validación del Parquet con audit y ejecución walk-forward sobre Parquet.

## Lo que no se ha verificado aquí

No están instalados MetaTrader 5, MetaEditor ni Wine. **El EA completo no se ha compilado con el compilador MQL5 ni se ha ejecutado en Strategy Tester.** Compilar el núcleo compartido como C++ no equivale a compilar el EA: faltan verificar API, buffers nativos, semántica de ticks, I/O y ciclo de eventos de MT5. La inspección estática y el oráculo Python tampoco prueban por sí solos la causalidad de un backtest real.

No se han recibido histórico del broker ni código original de la estrategia. No se ha ejecutado backtest de mercado, generado dataset histórico ni validado equivalencia con la implementación original. El uso de MAIN_K, SMA/LowHigh, reglas de llenado, sesiones y calendario está documentado para esa comparación.

Completar `MT5_ACCEPTANCE.md` antes de considerar validada la ejecución en el terminal. En particular, comprobar la invariancia de features comunes al extender la fecha final del backtest, la primera cotización de entrada y los perfiles contra ticks crudos.

## Limitaciones explícitas

- `ConfirmRealTickTesterMode` es una confirmación manual; el EA no puede certificar la modalidad ni detectar todos los tramos que MT5 sustituya por ticks modelados.
- CopyTicksRange puede entregar cobertura incompleta aun sin error; todos los perfiles válidos se etiquetan coverage_unverified. Descargar ticks y revisar el Journal.
- Los seis perfiles se recalculan por señal en consultas horarias; se limita memoria por chunk/bins, pero perfiles de sesiones pueden resultar costosos en feeds densos. No se implementa caché persistente ni muestreo de ticks que altere el perfil.
- BAR_CONSERVATIVE aproxima Ask con spread de la barra y proporciona cotas MFE/MAE; no es equivalente a ticks Bid/Ask reales.
- Hora UTC/NY depende de inputs correctos del broker; DST US desde 2007, sin calendarios históricos especiales ni resolución general de horas server repetidas.
- PnL en unidades de precio; no moneda, comisiones, swap, slippage adicional o restricciones de cuenta. No hay operaciones live.
- Secuencias extremas que excedan la ventana de 350 barras se marcan censuradas. La estabilización de indicadores depende de la prehistoria MT5.
- El guardado requiere finalización normal para audit y filas pendientes; un corte abrupto produce un artefacto incompleto que debe rechazarse.
- Los controles de FINAL_TEST exigen intención explícita e hipótesis, pero no pueden impedir que un investigador vuelva a consultar un archivo por fuera del programa.

## Extensión causal Heikin Ashi — schema 1.1

Verificación adicional sobre el commit base `3844d04079145865a43d1fce0a17240b34c69d69`, sin reescribirlo:

```text
.venv/bin/python -m unittest discover -s tests -v
Ran 28 tests
OK

.venv/bin/python -m compileall -q python tests
Completado sin errores

git diff --check
Sin errores
```

Se mantienen las 16 pruebas anteriores y se añaden 12 pruebas HA. El núcleo `HeikinAshiCore.mqh` usado por el EA se compila y ejecuta directamente mediante `tests/ha_native.cpp` con C++17, `-Wall -Wextra -Werror`. Las 54 features se comparan contra un oráculo batch independiente con 500 barras sintéticas. Se comprueban seed, recurrencia, warmup, atenuación del seed, cuerpo/mechas, ventanas, streaks de 400 barras, censura izquierda, dojis, rango cero y rechazo de duplicados.

Pruebas anti-lookahead: mutar barras futuras no cambia ningún valor anterior; el cutoff excluye la vela de entrada; HA de señal se alinea con barra cerrada; ratios/streaks se contrastan con prefijos exclusivamente pasados. El validador rechaza HA futura, desalineada o publicada antes de warmup. Los tests existentes de FINAL_TEST y walk-forward siguen pasando con schema 1.1. La conversión CSV/Parquet también conserva los campos HA y sus faltantes. Se verifica además el análisis de archivos legacy 1.0 sin HA.

La regresión compara byte a byte `ResearchCore.mqh` y toda la implementación de simulación virtual (desde OpenTrade hasta Flush) con el commit base. Permanecen sin cambios señal Stochastic, BUY/SELL, TP=240, SL=180, TIME_EXIT=100, FOLLOW/INVERT y LIVE_TRADING=false. HA se actualiza antes de comprobar si hay señal y no interviene en esa decisión.

Se revisó el diff de implementación/documentación. Nuevo contrato: 329 columnas, 225 features numéricas causales (54 HA), con 6 campos adicionales de metadata HA. Interacciones limitadas a 30 pares descriptivos fijos; cortes continuos TRAIN-only y sin selección automática de reglas.

Sigue pendiente compilar el **EA completo con MetaEditor** y ejecutar la aceptación con datos del broker: este entorno no tiene MT5. La compilación nativa verifica los núcleos compartidos, no el ciclo de eventos ni las APIs del terminal. No se ejecutó trading live ni se tocó `asistente-trader-ia`.
