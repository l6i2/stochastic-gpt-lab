# Primera adquisición real B+C

Se observaron cotizaciones nuevas de US30Cash en XMGlobalSC-MT5 5. La primera registrada por el worker después del corte fue `time_msc=1794193587199`, BID 51576.0, ASK 51582.0, observada a las 2026-11-08 20:06:27 en Ecuador según el reloj del host. El valor nativo se conservó íntegro. El instante UTC de generación sigue sin certificación independiente.

El corte exclusivo se conserva en el manifiesto de activación. La primera observación fijó el límite de consulta `1794193800000` al comienzo de la siguiente M5 nativa. El intervalo en formación al observar la cotización quedó fuera. La recuperación usa consultas nativas acotadas a barras cerradas desde ese límite. Cada vintage registra origen retrospectivo y hora de primera consulta. La recepción original de los ticks recuperados sigue sin demostrarse.

| Indicador | Resultado |
|---|---|
| Adquisición | ACTIVE_HISTORICAL_TRAIN_QUARANTINED |
| Ticks adquiridos | 805 |
| BID/ASK inválidos | 0 |
| M1 verificadas | 5 |
| M5 verificadas | 1 |
| M5 rechazadas | 0 |
| Contexto técnico consecutivo | 1/350 |
| Señales de TRAIN | 0/800, BUY 0, SELL 0 |
| Admisión | WAITING_FOR_DATA |

El cotejo volvió a calcular la paridad con los payloads locales. Comprobó los hashes de ticks, M1 y M5, el orden y la escala de timestamps, la correspondencia del vintage con el ledger y la integridad del checkpoint. Para cada barra aceptada verificó OHLC y volumen en M1→M5, y OHLC de BID y conteos BID de ticks→M1. El contexto derivado conserva rol TRAIN_CONTEXT y cuarentena. La cadena verificada tiene 114 entradas y cabeza `1aac76780d16229cdda42e114d2e837b7c8a9da0a10203ab08ff912751df79b9`. Los hashes fijados de la reserva anterior coinciden.

La conexión IPC falló mientras la instancia XM anterior no respondía. Se verificó el checkpoint antes de detener ese proceso. La nueva instancia se identificó como el mismo terminal XM y se verificó `terminal_trade_allowed=false`. La ejecución programada volvió a obtener cotizaciones con resultado 0. El guardian renovó su estado. La prueba cubre recuperación del terminal y persistencia del cursor entre ejecuciones. La recuperación tras apagado físico sigue pendiente de un arranque natural.

El primer intento tras el cierre de la barra esperó por memoria disponible. Se midieron 284 MiB frente a un mínimo de 384 MiB. Al recuperarse el margen, el worker reanudó la adquisición desde el mismo cursor con la protección vigente.

El worker existente continúa cada cinco minutos. Los oráculos siguen vinculados a los hitos 15/30/276/350. Faltan contexto suficiente, señales, horizontes posteriores, soporte por lado y folds, paridad de prefijos y revisión de causalidad, continuidad y calendario. La admisión y el permiso específico de entrenamiento siguen pendientes. Los conjuntos protegidos permanecen cerrados. DEMO está deshabilitado, LIVE_TRADING es false y hubo cero órdenes y cero entrenamientos.

[Recibo estructurado y hashes](../research/studies/bc_train_future_eval_v1/first_live_acquisition_20261108/sha256.json).
