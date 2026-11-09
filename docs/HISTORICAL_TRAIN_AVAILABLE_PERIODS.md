# Periodos disponibles para TRAIN histórico

TRAIN nuevo autorizado y verificable: **0 M5, 0 ticks y 0 señales**. Primera y última fecha TRAIN pendientes. Los conteos se refieren a la admisión y elegibilidad, y no describen la profundidad total de XM.

El **2 de enero de 2024** está disponible para diagnóstico fijo. Contiene 1.376 M1, 276 M5, 79.211 ticks y 28 señales verificables, con 13 BUY y 15 SELL. El baseline virtual FOLLOW/INVERT conserva Bid/Ask, TP 240, SL 180 y 100 barras de horizonte. [Baseline reproducido](STOCHASTIC_HISTORICAL_BASELINE.md).

Se descargó y preservó localmente un vintage nuevo entre las 01:05 y 01:10 XM nativo del día autorizado. Los 96 ticks tienen BID/ASK válidos y coinciden en timestamp y precios, en el mismo orden, con el archivo sellado. El recibo registra hash, procedencia y hora de recuperación. Los conteos históricos siguen siendo los del archivo original. Las M1/M5 se verificaron con el archivo nativo sellado, ya que las consultas Python de barras del día se rechazaron por responder fuera de la ventana. [Recibo del vintage](../research/studies/historical_membership_resolution_20261108/fixed_day_vintage.json).

Para un TRAIN nuevo hacen falta quotes Bid/Ask verificadas a lo largo del calentamiento, entradas, trayectorias y salidas de cada segmento autorizado, con paridad OHLC y volumen y gaps explícitos. También hace falta probar que toda esa ventana de dependencias queda fuera de periodos protegidos y expuestos.
