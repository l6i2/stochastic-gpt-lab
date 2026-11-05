# Propuesta única — dataset de observaciones nativas para investigación offline

Estado: **PROPOSED_NOT_ACTIVE**. No modifica contratos, productor ni datos.
No autoriza entrenamiento, scoring, cohortes científicas ni trading.

## Problema demostrado

El productor original registra `OnTick → SymbolInfoTick`, calcula un hash por
callback y hace FileFlush por registro; OnTimer registra heartbeats cada 5 s.
La cola NewTick de MT5 no acumula otro NewTick cuando ya existe uno pendiente o
en ejecución. Por tanto este mecanismo no garantiza todos los ticks del broker.
CopyTicks puede sincronizar y descargar faltantes del servidor: no demuestra
recepción original. Véanse las fuentes oficiales al final.

El contrato vigente exige 350 M5 propias con cobertura exacta y semillas vinculadas
al origen, luego 800 señales y 100 barras posteriores. Solo la captura original
post-activación, sujeta a esas pruebas, puede aportar al contador actual. El ensayo
de snapshots está autorizado solo para diagnóstico. No se transfiere ningún dato.

La reconstrucción del ledger al inicio de esta revisión dio 21 M5 completas
acumuladas, máximo histórico de cuatro consecutivas, cero actuales y 119
rechazadas. Los 119 rechazos incluyen diferencia de hash de secuencia BID;
90 incluyen diferencia de conteo. Las razones se solapan. Esto no atribuye todos
los casos a coalescencia: también hay callbacks indistinguibles, desconexiones,
gaps y referencias incompletas. Volumen/OHLC iguales no prueban secuencia igual.
Una comparación nueva de un minuto tuvo 104 callbacks y 104 filas de base,
con 104 coincidencias de tiempo/BID/ASK y flags iguales; no hay fundamento para
corregir globalmente flags o mezclar BID y ASK para producir PASS.

El contador persistido coincide con una reconstrucción independiente del ledger.
No se encontró un error de suma que permita recuperar el warmup. Además
`protocol_stream_unbroken=false` conserva una interrupción del intento científico;
no se vuelve a true al reparar procesos ni alcanzar una racha posterior.

350 M5 equivalen a 1.750 minutos de barras. Si una sesión nativa es más corta y
todo cierre normal reinicia contexto, el contrato puede ser incompatible con
alcanzar ese número en una sesión. **No se declara demostrado ese límite para
XM** sin calendario nativo vigente y excepciones; el comportamiento de cierre
no se modifica basándose en horarios genéricos de NYSE ni en esa hipótesis.

## Cambio propuesto, limitado a un estudio futuro

Autorizar un anexo separado para un **nuevo dataset de observaciones de base
nativa**, con corte futuro, ID, rutas y asignación de rol exclusivos. Sustituir
solo para ese estudio la prueba de recepción original de cada tick por pruebas
de primera disponibilidad de cada snapshot, secuencia nativa íntegra almacenada,
doble consulta exacta, paridad M1/M5 y causalidad por prefijos en replay offline.
No llamar a esto certificación del instante físico de generación ni captura
original de cada tick. La recepción y NTS permanecen como evidencias separadas.

El replay conserva US30Cash M5, Stochastic 5/3/3, cruces MAIN_K 20/80,
BUY/SELL, FOLLOW/INVERT, entrada nativa de la siguiente barra, Bid/Ask originales,
TP240/SL180/TIME_EXIT100, sin SKIP. La disponibilidad de las features en replay
se demuestra por prefijo nativo; **no equivale** a que estuvieran calculadas en
vivo en el instante de aquella entrada. No se usaría esta admisión offline como
autorización o evidencia de ejecución en vivo.

Conservar 350 barras propias observadas después del corte, semillas HA/ATR
completas, 800 señales consecutivas, 100 barras posteriores y soporte 200/80/80,
sin reducir umbrales. Proponer continuidad a través de cierres normales solo
cuando horario nativo específico y excepción aplicable estén demostrados y la
estación siga supervisada; jamás puentear suspensión, desconexión o cobertura
desconocida. El resto segmenta y permanece en cuarentena. No modificar este
comportamiento en la versión instalada antes de aprobación y pruebas separadas.

## Criterios previos a la activación/admisión

1. Aprobación explícita del anexo, versión y productor futuros; inicio real nuevo
   posterior a esa decisión. Cero adopción retrospectiva del ensayo actual.
2. Asignación forward-only exclusiva documentada, cierre de incorporaciones
   anteriores sin modificar sus reservas originales, y exclusión de roles
   protegidos o desconocidos. No afirmar recuperado el membership legado.
3. Cadena append-only, primera observación y final de consultas registrados;
   orden, duplicados, resultados completos y límites nativos exactos verificables.
4. Paridad exacta OHLC/volumen/orden de ticks con evidencia reproducible; cualquier
   lectura parcial, mutación entre consultas o volumen distinto → cuarentena.
5. Contexto/semillas y features vinculados a esa procedencia. Whitelist congelada
   de seis features; no agregar hipótesis con históricos expuestos.
6. Calendario verificable para cualquier continuidad entre sesiones. Sin prueba,
   fail-closed; no estimar horarios ni excepciones.
7. Prerregistro, hashes, plan cronológico/purga y presupuesto vigentes. Dataset
   sellado y gate completo antes de solicitar autorización específica de fits.

## Riesgos y decisión futura

La base del broker puede revisarse y la doble lectura solo certifica estabilidad
observada, no inmutabilidad futura. El ensayo ya mostró un M1 con volumen distinto
pese a dos lecturas iguales; ese intervalo no se corrige ni admite. La hora física
de generación sigue sin certificación independiente. El riesgo de exposición,
dependencia temporal y sesgo de feed permanece sujeto al protocolo estadístico.

La decisión científica exacta sería autorizar este **nuevo dominio de admisión
offline y su regla explícita de continuidad**, manteniendo el contrato actual
intacto. Aún no se activa ni se pide autorización para entrenar: faltan los
recibos exigidos. Reparaciones operativas ordinarias no requieren esa decisión.

Fuentes oficiales consultadas el 3 de noviembre de 2026:

- [OnTick: serialización y coalescencia NewTick](https://www.mql5.com/en/docs/event_handlers/ontick).
- [CopyTicks: base local y sincronización desde servidor](https://www.mql5.com/en/docs/series/copyticks).
