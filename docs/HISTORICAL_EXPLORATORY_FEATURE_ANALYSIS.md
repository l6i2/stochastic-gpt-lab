# Disponibilidad de features para el estudio exploratorio

Las 28 señales pasaron la comprobación de orden temporal declarado hasta la decisión. Las seis columnas de la whitelist tienen valores finitos para los 13 BUY y los 15 SELL. MAIN_K y OHLC se verificaron por replay. La primera señal requiere contexto previo a la ventana, y los campos finitos por sí solos no verifican las dependencias y semillas de ATR y Heikin Ashi. La validación de la matriz causal para fit queda pendiente.

Volumen relativo y volatilidad aparecen como diagnósticos de disponibilidad. Las columnas EMA inspeccionadas tienen valores finitos, pero se conservan fuera de la whitelist. Las columnas de ruptura buscadas no están disponibles en el exportador fijo usado. Tendencia, estructura y horario de Nueva York quedan fuera de la matriz de fit. Para agrupar por horario hace falta mapping temporal verificable. MFE, MAE y estados posteriores a la entrada permanecen como resultados.

Se comparó disponibilidad por lado. El soporte posterior a la purga impide contrastar asociaciones con rigor. Se registraron cero hipótesis nuevas y cero fits.

[Recibos y hashes](../research/studies/us30cash_historical_exploratory_ai_v1/sha256.json).
