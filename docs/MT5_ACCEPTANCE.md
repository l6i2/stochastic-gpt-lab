# Aceptación pendiente en MetaTrader 5

Estas comprobaciones requieren el terminal del broker y no se sustituyen por las pruebas Python/C++. Conservar Journal, build de terminal, parámetros, fechas, código fuente y hash del dataset.

1. Compilar `StochasticResearchEA.mq5` con `ResearchCore.mqh` al lado, en MetaEditor moderno. Resolver y registrar cualquier error/advertencia antes de usarlo. No hay un `.ex5` precompilado en este proyecto.
2. Probar inicialización en gráfico normal/demo: debe fallar. Probar `LIVE_TRADING=true` en tester: debe fallar. Probar modo optimización: debe fallar. Comprobar que no se genera ninguna orden real ni del tester (sólo simulación interna).
3. En histórico conocido o símbolo custom con ticks controlados, comparar K/D contra indicador nativo 5/3/3 SMA Low/High. Verificar cruces 20→>20 y 80→<80; igualdad actual no dispara. Repetir con SIGNAL_D. No usar cruce K/D como referencia.
4. Inspeccionar una BUY y SELL: precio de entrada igual al Ask/Bid del primer tick siguiente; cutoff precede ese tick; salidas usan cotización opuesta. Revisar spread variable y gaps de SL. TP exacto 240, SL normal −180, gap puede ser peor.
5. Histórico lateral suficiente: comprobar TIME_EXIT tras exactamente 100 barras observadas. Probar barrera en el tick de vencimiento (barrera tiene precedencia).
6. En BAR_CONSERVATIVE, crear vela con ambas barreras y apertura entre ellas: debe ganar SL para cada trade correspondiente. Revisar también gap de apertura conocido. El resultado Ask es aproximado y debe etiquetarse.
7. Solapar al menos tres señales. Confirmar independencia de ambas direcciones y de distintas señales; contar salidas de zona en el periodo y cotejar `signals=rows_written=filas CSV`.
8. Terminar test con trades abiertos: deben aparecer END_OF_DATA con PnL/ventaja vacíos. Una señal cuyo FOLLOW acabó pero INVERT no debe conservar ambos estados.
9. Inspeccionar ticks crudos dentro de una ventana corta: sumar bins, POC, VAL/VAH al 70 %, nodos y distancias. Tick posterior al cutoff no puede cambiar el perfil. Repetir con tick activity y, sólo si broker soporta, real trade volume. Revisar `copy_error` y metadata de cobertura.
10. Comparación de prefijo: ejecutar mismo inicio/prehistoria con dos fechas finales distintas; para señales comunes todas las **features** deben ser iguales (excepto ninguna). Sólo etiquetas censuradas pueden completarse. Esto es una prueba de integración fuerte contra lookahead.
11. Probar cruce de sesión, fin de semana y cambios DST; verificar UTC/NY con una fuente confiable del calendario del broker. Los nombres de sesión son buckets NY documentados.
12. Ejecutar validador con audit, conversión Parquet y análisis TRAIN. Confirmar que FINAL_TEST no tiene informe. Verificar que abortos y archivos truncados se rechazan.

No marcar esta lista completada sin evidencia del terminal. Una respuesta exitosa de CopyTicksRange no certifica cobertura total ni que el tester esté usando ticks reales en cada tramo: revisar los avisos de sustitución por ticks modelados del tester.

## Aceptación HA adicional (schema 1.1)

Copiar también `HeikinAshiCore.mqh` junto a los otros dos archivos antes de compilar. Comprobar que el seed corresponde a la primera barra de prehistoria cargada; HA debe actualizarse aun en barras sin señal y conservar seed/count durante todo el run. Con menos de 276 barras procesadas, seguir obteniendo señales Stochastic con HA vacío; desde 276, comparar la serie y sus ventanas con un cálculo secuencial de esas mismas barras. Extender la fecha final sin cambiar inicio/prehistoria debe conservar todas las features HA anteriores. Comparar señales, entradas y resultados con la versión anterior para el mismo histórico: deben coincidir. Revisar streaks largos y metadata de censura. No confundir HA sintético con precios de entrada/salida.
