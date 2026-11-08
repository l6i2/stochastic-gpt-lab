# Preparación C+F del fin de semana del 7 de noviembre de 2026

La preparación offline queda verificada en su alcance diagnóstico. El ensayo aislado de 300 barras sintéticas produjo 287 comparaciones exactas de la variante iATR, 300 comparaciones exactas de HA Open/High/Low/Close y 25 direcciones HA desde el hito 276. Pasaron 66 pruebas. El dataset propio conserva 88 M5 verificadas acumuladas, 0 consecutivas y 0 elegibles. La admisión y el entrenamiento siguen bloqueados.

## iATR y reparación preparada

La implementación vigente excluye la primera barra del cálculo inicial de True Range, suma 14 rangos con cierre previo y expone ATR desde la barra 15. La variante diagnóstica inicia el primer rango con high-low, suma los primeros 14 rangos en orden binary64 y aplica value += (TR_actual-TR_saliente)/14. La semilla y el orden de operaciones explican que una misma media en aritmética real difiera al redondear cada operación.

Los exports permitidos de los epochs 13 y 26 siguen aportando cinco valores únicos a la variante. El ensayo sintético añade 287 comparaciones sin discrepancia. La implementación de producción discrepa en 36 valores sintéticos. La suma directa de cada ventana tampoco reproduce siempre la recurrencia nativa. El recibo conserva los valores hexadecimales y los hashes del código compilado y del CSV. La descripción pública de ATR de MetaQuotes define True Range y una media de esos rangos. La prueba específica de este terminal procede del export nativo. [MetaQuotes ATR](https://www.mql5.com/en/code/12)

La variante está versionada como diagnóstico en native_seed_diagnostic. Su promoción requiere la prueba real de 30 M5 propias, revisar la compatibilidad de la inicialización con el contrato, generar la identidad de implementación correspondiente y validar las dependencias del certificado retenido. El fragmento congelado mantiene su pin original. Este informe no cambia su definición ni autoriza entrenamiento. No se utiliza tolerancia para obtener paridad.

## Heikin Ashi y causalidad

El oráculo propio ahora exporta y compara los cuatro precios HA, además de dirección y readiness. La semilla es (Open+Close)/2 para HA Open y (Open+High+Low+Close)/4 para HA Close. Cada Open posterior usa el Open y Close HA anteriores. High y Low incluyen el rango original y los dos precios HA. La prueba nativa sintética coincidió exactamente en todas las 300 barras. Las 25 direcciones desde la barra 276 también coincidieron.

Las pruebas de mutación de barras futuras conservan las salidas anteriores. La serialización y restauración del contexto a mitad del prefijo reproduce exactamente las salidas y el estado final. Se probaron los límites 15/276/350, el vínculo de semillas con su primer hash, el rechazo de semillas ajenas y la disponibilidad de barra cerrada. La paridad HA completa del dataset propio espera el hito de 276 barras propias. La auditoría causal global sigue FAIL.

## Calendario y horas

La metadata nativa recuperada para XMGlobalSC-MT5 5 / US30Cash declara los siguientes intervalos en etiquetas nativas. El extremo 24:00 representa el final del día.

| Días nativos | Cotización | Negociación |
|---|---|---|
| Lunes a jueves | 01:00–24:00 | 01:05–23:55 |
| Viernes | 01:00–24:00 | 01:05–23:50 |
| Sábado y domingo | Sin sesiones enumeradas | Sin sesiones enumeradas |

Este calendario semanal no acredita excepciones históricas ni permite convertir por sí solo la reapertura a Ecuador. El cierre del domingo en etiquetas nativas no describe por sí mismo el domingo ecuatoriano. La web pública de XM remite a iniciar sesión para consultar todos los horarios. Sigue faltando evidencia fechada aplicable al servidor y símbolo para las excepciones. [Horarios de índices de XM](https://www.xm.com/pt/equity-indices)

El horario de verano de Estados Unidos terminó el 1 de noviembre de 2026. Las conversiones de visualización usan America/Guayaquil y America/New_York. Por ejemplo, 16:00 UTC corresponde el 31 de octubre a 11:00 Ecuador y 12:00 Nueva York, y el 7 de noviembre a 11:00 en ambas ciudades. Estos ejemplos de zona horaria no certifican el tiempo de generación de un tick. El mapping XM queda pendiente. [Fechas oficiales de USNO](https://aa.usno.navy.mil/calculated/daylightsaving?submit=Get+Data&year=2026)

## Reapertura y recuperación

IPC confirmó conexión demo, identidad del servidor y símbolo, y terminal_trade_allowed=false. La última cotización nativa continúa en 1794009599968. El estado operativo es CONNECTED_AWAITING_NEW_NATIVE_QUOTES. La metadata semanal es consistente con el cierre del fin de semana. La ausencia de ticks por sí sola no decide el estado del mercado.

El reporter existente mantiene reopening_watch.json ligado a un registro y head ya verificados. Al detectar el primer timestamp nativo superior al baseline, guarda la cotización observada, límites de recepción, referencia al registro, cambios de boot y epoch del checkpoint y posibles registros que quedaron fuera de la cola inspeccionada. Se ejecuta el verificador de transición existente para enumerar la evidencia faltante. La observación permanece en cuarentena y bridge_allowed permanece false.

Un recibo por baseline y una prueba de pérdida de checkpoint evitan duplicar el aviso. Si faltó una ventana de inspección, el registro lo declara. El dato representa la primera cotización encontrada por este monitor en la evidencia disponible. La certificación de una transición necesita además calendarios que la delimiten, excepción exacta del broker y cobertura continua. Los epochs separados por pérdida de cobertura conservan su separación.

Guardian, NTS, captura y reporter usan las tareas y locks existentes. El inicio de sesión y la repetición de la tarea continúan configurados. Se recargó únicamente el reporter para cargar la ampliación. El terminal de investigación activo se preservó durante el ensayo aislado. La recuperación después de un reinicio físico adicional sigue pendiente de una observación natural. Las políticas globales de energía no cambiaron.

## Entrenador y admisión

Se verificó la preparación de logística L2 con instancias BUY/SELL distintas, escalado exclusivamente en TRAIN de cada fold, whitelist congelada, cuatro folds cronológicos purgados, FOLLOW/INVERT y presupuesto máximo de ocho fits. Las pruebas sintéticas usan estimadores simulados. Se verificaron rechazos antes de cargar datasets o consumir presupuesto cuando faltan admisión o grant. El ejecutor sigue deshabilitado y los fits científicos son cero.

Faltan 350 M5 propias consecutivas, 800 señales consecutivas, 100 M5 posteriores, 200 señales evaluables, 80 BUY, 80 SELL y tres folds evaluables por lado. También siguen pendientes las semillas propias, la evidencia de transición, cobertura y causalidad requeridas, el sellado del dataset y el grant específico.

## Reproducción y siguiente acción

Los [recibos y el export sintético](../research/studies/us30cash_m5_native_observations/weekend_20261107/) incluyen la receta determinista, los hashes y replay.py. Desde la raíz del repositorio, ejecutar .venv/Scripts/python.exe research/studies/us30cash_m5_native_observations/weekend_20261107/replay.py comprueba el hash del código MQL5 generado, el export, HA y ATR sin iniciar MT5 ni leer el dataset propio.

La adquisición continuará al llegar cotizaciones nuevas y ejecutará los hitos 15/30/276/350 del epoch correspondiente. El monitor publicará la primera cotización observada y su evaluación de transición. Dataset admission permanece WAITING_FOR_EVIDENCE. DISCOVERY_VALIDATION=BLOCKED, HISTORICAL_HOLDOUT=LOCKED, FINAL_TEST=LOCKED, DEMO=DISABLED, LIVE_TRADING=false, terminal_trade_allowed=false, TRAINING_EXECUTED=false y PROTECTED_SCORING=false. Cero órdenes.
