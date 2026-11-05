# Verificación del warmup y recuperación de captura

La reconstrucción independiente del ledger confirmó 28 M5 originales acumuladas,
156 rechazadas, un máximo de cuatro consecutivas y una racha actual de cero en el
corte del 4 de noviembre. Frente a 89.113 callbacks y 359 M1 del corte anterior,
se observaron 138.325 callbacks y 491 M1. La cifra de warmup científico es 0/350.
Los hashes del checkpoint y las entradas verificadas respaldan el contador.

En la M5 con apertura nativa 1793719500000, los 1.262 callbacks BID coincidieron
en conteo, OHLC y volumen con MT5. Al comparar tiempo, BID, ASK y flags, apareció
una repetición adicional y faltó una tupla presente en la referencia. El rechazo
por secuencia distinta es correcto. Los rechazos acumulados incluyen además
referencias incompletas, gaps y desconexiones. El motivo de cada intervalo se
puede consultar en el ledger y el monitor informa el último rechazo M5.

Windows registró el cierre limpio de XM seguido por suspensión/hibernación entre
las 20:29 del 2 de noviembre y las 08:11 del 3 de noviembre, hora de Ecuador. El
proceso sin ventana después de reactivarse impidió recuperar callbacks. Se
preservaron manifiestos y cursores, se recuperó XM y se reiniciaron clientes IPC
atascados. El guardian ahora detecta procesos sin ventana y sin callbacks con
recibo fresco del collector. Los supervisores recuperan clientes IPC sin avance
tras una gracia operativa de cinco minutos. El corte nuevo conserva el intervalo
perdido. El evento posterior con XM ausente y boot 112 tiene causa iniciadora sin
adjudicar. Se deshabilitó Algo Trading tras comprobar que el terminal recuperado
lo permitía y se verificó `terminal_trade_allowed=false` mediante la API.

La auditoría del ensayo separado confirmó dos M5 nuevas consecutivas de la época
22. Verificó ambas consultas, paridad nativa exacta, el checkpoint y el prefijo
conservado entre ejecuciones independientes. El ensayo es diagnóstico y aporta
cero barras al warmup. El productor original no demostró esa racha en la ventana
de prueba posterior a la reparación. Solo el productor original postactivación
puede aportar al warmup conforme al contrato vigente.

Los recibos reproducibles están en `research/studies/warmup_resolution_20261103_v1/`.
El comando `.\tools\research_control.ps1 STATUS` presenta el estado vivo y la
reconstrucción del contador. La propuesta científica separada conserva los
umbrales y queda pendiente de revisión.

[Propuesta científica](WARMUP_SCIENTIFIC_PROPOSAL_20261103.md)
