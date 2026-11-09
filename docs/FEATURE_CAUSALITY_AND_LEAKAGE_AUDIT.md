# Causalidad y controles de leakage

Se verificó para las 28 entradas el orden entre último timestamp declarado de feature, señal y entrada. Para los 3.279 snapshots se verificaron identidad del camino, orden posterior a la entrada, marcas anteriores o iguales al cutoff y snapshots anteriores a la salida. Cada BID/ASK de marca coincide exactamente con el tape a su timestamp. La salida se usa en este control de pertenencia del snapshot. Se excluye de los predictores.

El agregador exige M5 completas para M15, M30 y H1 y no usa el bucket en formación. Tres regresiones verificaron cierre exacto, rechazo de componentes faltantes e invariancia ante cambios futuros. También pasaron cuatro pruebas existentes de temporalidad.

Pivotes y divergencias deben publicar su hora de confirmación. Rupturas y retesteos requieren nivel fijado antes del evento. El perfil necesita ticks y reglas de bins con cutoff, sin usar extremos futuros para fijar la grilla. ATR, EMA y Heikin Ashi requieren linaje de sus semillas. Los campos derivados exportados no se certificaron íntegramente. La disponibilidad nativa comprobada no demuestra UTC de generación ni la sesión de Nueva York.

La whitelist candidata queda inactiva. Se preservan TP 240, SL 180, TIME_EXIT 100, contratos, reservas protegidas y estrategia.

[Recibos y hashes](../research/studies/us30cash_xm_historical_ai_development_v1/technical_context/sha256.json).
