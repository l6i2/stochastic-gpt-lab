# Avance de adquisición y madurez B+C

El corte de esta revisión registra **5451 ticks, 35 M1 y 7 M5** verificadas en cuarentena. Hay 0 M5 rechazadas y 0 admitidas. Los intervalos adquiridos forman un prefijo nativo contiguo desde `1794193800000`. Se revalidaron hashes, OHLC, volumen, BID/ASK, escala y orden de timestamps, membership y checkpoint. Se conservan los vintages y la procedencia histórica XM. El instante UTC de generación y la recepción original de los ticks históricos siguen sin certificación.

El último intervalo verificado fue **2026-11-09 03:40 a 2026-11-09 03:45 XM nativo**, con extremo final excluido, manifest `70fa9b58e8ee79f2b3e1ac43d238c78a8cfa798c8c7602f42f1a362e78bec142` y reloj de primera recuperación `2026-11-09T01:47:52.707354+00:00` según el host. Se adquirió mediante las consultas acotadas de MT5 dentro de la reserva posterior al corte exclusivo.

| Requisito | Avance |
|---|---:|
| Contexto | 7/350 |
| Señales | 0/800 |
| Barras posteriores | 0/100 |
| Evaluables | 0/200 |
| BUY y SELL evaluables | 0/80 y 0/80 |
| Folds por lado | 0/3 y 0/3 |

Calendario PARTIAL. La especificación nativa observada de XMGlobalSC-MT5 5 muestra cotización de lunes a viernes, 01:00 a 24:00 nativo. Una sesión ordinaria admite hasta 276 M5. Alcanzar las 350 requiere validar al menos una transición. Se necesita evidencia fechada aplicable a ese servidor y símbolo, incluidas excepciones y cobertura en los bordes observados. Se preserva el cierre de cada intervalo y la separación entre sesiones mientras falte esa prueba.

El próximo oráculo requiere 15 M5 propias. Los hitos 30/276/350 siguen programados. La revisión ahora reutiliza un PASS sellado cuando coinciden el inicio, el hito y los hashes ordenados del prefijo. Las 27 pruebas B+C pasaron. El estado de admisión es `WAITING_FOR_DATA` y el paquete permanece en cuarentena.

La tarea existente conserva su disparador cada cinco minutos y al iniciar sesión en Windows, con presupuesto de dos intervalos y el reintento acotado ya verificado. La tarea informó código 0. No se registró un error nuevo en el último worker observado. El guardian siguió activo y verificó el checkpoint. El arranque físico sigue pendiente de observación natural. La adquisición requiere PC A encendida y la sesión local iniciada. Al volver, el worker reanuda el cursor y recupera únicamente los intervalos cerrados permitidos. Los conjuntos protegidos permanecen cerrados. Cero órdenes y cero entrenamientos.

[Estado estructurado, auditoría y hashes](../research/studies/bc_train_future_eval_v1/maturity_progress_20261108/sha256.json).
