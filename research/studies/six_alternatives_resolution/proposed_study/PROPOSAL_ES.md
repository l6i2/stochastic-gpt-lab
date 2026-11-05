# Estudio propuesto de observaciones nativas offline

`US30CASH_M5_NATIVE_OBSERVATIONS_20261105_PROPOSED` permanece en preparación.
La captura científica tendría un ID nuevo y un inicio real posterior a su
autorización. Su primera observación y hash de dataset están pendientes.
El ensayo técnico actual aporta evidencia de capacidad del productor.

## Cobertura y tiempo

La unidad primaria propuesta es el snapshot de la base nativa de US30Cash.
Cada extracción conserva identidad, intervalo nativo, primera observación,
contador monotónico, dos lecturas y sus hashes, BID/ASK, flags y velas nativas.
La aceptación exige igualdad exacta de consultas, secuencia y agregados M1/M5.
Un error, revisión entre lecturas o volumen distinto coloca el intervalo en
cuarentena. Se conserva el origen retrospectivo de los ticks recuperados.

La causalidad se comprobaría por prefijos nativos en replay offline y por la
disponibilidad registrada de los snapshots. La generación física UTC y la
disponibilidad de ejecución en vivo tienen garantías pendientes. Los recibos
NTS mantienen sus cotas condicionales y errores de cuantización/deriva explícitos.

El contrato vigente de callbacks exige su secuencia exacta. El anexo propuesto
requiere aprobación específica para usar observaciones de base como evidencia
de un nuevo estudio offline. Los originales y sus contratos se conservan.

## Warmup y sesiones

Se retienen 350 barras propias, primeras 800 señales consecutivas, 100 barras
posteriores, 200 evaluables, 80 por lado y tres folds por lado. Las semillas
HA/ATR nacen dentro del dataset nuevo. El horario nativo observado el 28 de
octubre en XMGlobalSC-MT5 5 ofrece 23 horas de cotización por sesión, hasta
276 M5. Ese recibo necesita vigencia y excepciones verificadas para aplicarse
al dataset nuevo. Un reset obligatorio entre sesiones de esa duración impide
reunir 350 barras dentro de una sola sesión.

Se propone conservar contexto entre cierres normales únicamente con calendario
nativo y excepción aplicable demostrados, estación supervisada y continuidad de
observación verificable. Suspensión, desconexión o cobertura desconocida segmentan
la captura. La definición requiere aprobación y validación antes de instalarla.
La versión ensayada mantiene su regla conservadora de epochs.

## Independencia, estadística y admisión

Se requiere asignación de rol exclusiva hacia adelante y exclusión verificable
de los intervalos protegidos. El fin desconocido de una reserva previa impide
demostrar no solapamiento por una fecha elegida. Se necesita evidencia original
o una decisión científica expresa sobre el alcance futuro de las reservas.

La whitelist propuesta hereda las seis definiciones congeladas. La regresión
logística L2 tiene BUY/SELL separados, FOLLOW/INVERT, cuatro folds cronológicos
con purga y ocho ajustes planificados. El presupuesto autorizado sigue en cero.
Se conservan las cuatro hipótesis primarias, controles de multiplicidad,
bootstrap por señal y bloques de 451 barras, censura y reglas de parada.
Los criterios completos están en `statistical_protocol.json` y sus referencias
selladas. La estrategia conserva Stochastic 5/3/3, niveles 20/80, TP240, SL180,
TIME_EXIT100, entrada en la siguiente M5 y semántica Bid/Ask.

El paquete exige dataset íntegro y sellado, membership, cobertura, seeds,
disponibilidad de features, ausencia de leakage y autorización específica de
entrenamiento. El ejecutor vigente permanece sujeto a su allowlist y a su
validador contractual. La adopción de este estudio necesitaría integrar su
contrato aprobado antes de emitir un grant. Las pruebas aquí usan exclusivamente
metadatos sintéticos y rechazo de ejecución sin grant.

Una aprobación metodológica futura autorizaría el dominio de observaciones
nativas y la regla de continuidad descrita. La autorización de entrenamiento
se vincularía posteriormente al dataset, protocolo, código y presupuesto sellados.
