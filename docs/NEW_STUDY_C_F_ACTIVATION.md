# Activación del estudio C + F en PC A

La autorización expresa permite un nuevo contrato de observaciones nativas
offline. El estudio está activado **en cuarentena**. No admite el dataset ni
autoriza entrenamiento. Los contratos y productores anteriores permanecen intactos.

El contrato, autorización, dependencias heredadas y recibos están en
`research/studies/us30cash_m5_native_observations/`. Los IDs definitivos y cifras
verificadas se publican en `operational_receipt.json` y `runtime_status.json`.
El estado actualizado por el supervisor está en
`outputs/us30cash_m5_native_observations/status.json`.

## Procedencia y alcance

Se reutiliza el productor C del ensayo autorizado, con identidad científica,
directorio, SQLite append-only, hashes y checkpoints nuevos. No se importaron
observaciones antiguas. El productor usa las consultas nativas de la instalación
XM identificada, sin enviar órdenes ni cambiar sus opciones de trading.
No necesita un EA nuevo: el controlador Python existente proporciona snapshots
de la base nativa. El probe MQL5 de calendario existente se instaló y compiló
separadamente; no se modificó el observador aprobado.

El inicio estimado por NTS es **2026-11-05 08:40:06.758744 Ecuador**,
con intervalo UTC 13:40:06.458942–13:40:07.058546. La cota es condicional al
error anunciado por el servidor temporal, no una certificación metrológica
absoluta. La autorización se observó antes del corte; no se inventó una hora de
envío del mensaje humano. La primera lectura local quedó registrada a las
08:40:07.446245 Ecuador, con boot y contador monotónico.

Cada consulta conserva su primera observación, dos lecturas, filas BID/ASK y
flags nativos, intervalo, identidad y hashes. CopyTicks es una lectura de base
retrospectiva: la recepción original de cada tick y su generación física UTC
**no están demostradas** por este mecanismo. No se presenta como OnTick completo.

## Causalidad, barras y persistencia

Solo se incorporan intervalos posteriores al corte de su epoch. La aceptación
exige igualdad exacta de las dos vistas y de sus agregados con MT5. La capa C+F
exige además cinco M1 propias y paridad exacta OHLC y tick volume con M5.
Ausencia de minuto o discrepancia excluye la barra y reinicia su contexto.
No se rellena ni se reemplaza silenciosamente un intervalo.

Se reutilizan MAIN_K 5/3/3, cruces 20/80 y las seis definiciones congeladas.
Los prefijos, dependencias, semillas HA/ATR, cálculo y reloj de disponibilidad
quedan hashados. La disponibilidad física probada es anterior al uso offline;
no se afirma disponibilidad en la entrada original del mercado. La paridad
nativa iATR sigue pendiente y no se atribuye PASS a todas las features por
calcular sus primeros valores incompletos. No se amplía la whitelist.

La revisión técnica v2 hizo atómica la persistencia del contexto y añadió la
paridad entre las cinco M1 y M5. Conservó el manifest original y registró un
pin nuevo de implementación. La recuperación real abrió epoch 2 con corte
nuevo, sin rellenar el intervalo del reinicio. La primera observación del estudio
se conserva. La auditoría de lectura independiente verifica cadena, checkpoint,
reproducibilidad de consultas y preservación del prefijo entre ejecuciones.

## Continuidad y calendario

La regla aprobada permite puentear un cierre programado solo con recibo de
calendario vigente, excepción aplicable, identidad y observación conectada sin
suspensión ni huecos. No genera barras en el cierre. Las pruebas sintéticas
rechazan prueba incompleta, desconexión y poll gap mayor al límite existente.

No hay transición real certificada todavía. La lista de recibos de calendario
aprobados está vacía; el runtime conserva el comportamiento conservador.
La observación semanal antigua de 23 horas no certifica vigencia ni feriados
actuales. Compilar o ejecutar el probe no prueba haber recuperado sus resultados.
Por tanto, la capacidad de reunir 350 M5 entre sesiones **sigue sin demostrar**.

## Roles, protocolo y puertas

El ledger nuevo demuestra pertenencia de sus artefactos e intervalos a su ID.
No demuestra exclusividad frente a reservas previas de extremo desconocido.
`RESERVATION_SCOPE_DECISION_REQUEST.md` contiene una única decisión concreta;
no fue aplicada. Los datos siguen en cuarentena sin scoring.

El protocolo vinculado conserva 350 M5, primeras 800 señales, 100 barras
posteriores, 200 evaluables, 80 por lado y tres folds evaluables por lado.
Mantiene BUY/SELL separados, FOLLOW/INVERT, TP240, SL180 y TIME_EXIT100.
Se preservan logística L2, cuatro folds cronológicos purgados y ocho ajustes
planificados; **ajustes autorizados = 0**. No se ejecutó fit, optimización o PnL.
El ejecutor existente sigue rechazando ejecución sin dataset admitido y grant
específico hash-bound; no se emitió grant ni se amplió su allowlist.

`NEW_STUDY_DATASET_ADMISSION` implementa los cinco estados autorizados. Su
estado actual es WAITING_FOR_EVIDENCE. La puerta de entrenamiento permanece
BLOCKED_NO_SPECIFIC_TRAINING_GRANT. CAUSAL_AUDIT global no cambia a PASS.
Discovery Validation, Historical Holdout y Final Test siguen cerrados;
DEMO=DISABLED, LIVE_TRADING=false, terminal_trade_allowed=false.

## Automatización y reproducción

El guardian existente supervisa un único propietario del productor C+F y
recupera su proceso si falta o su estado queda obsoleto. El launcher de venv y
su proceso hijo no son dos propietarios de SQLite: el bloqueo exclusivo impide
escritores simultáneos. Se reusan XM, NTS y monitor; no se reinició XM.
La recuperación tras un próximo reinicio físico sigue siendo una prueba futura.

Auditoría sin escribir en la captura:

```powershell
.\.venv\Scripts\python.exe tools/audit_cf_study.py --out outputs/cf_audit_nuevo
# Para demostrar preservación de prefijo, añadir --previous outputs/cf_audit_anterior
.\.venv\Scripts\python.exe tools/autonomous_research_status.py
```

No reutilizar un directorio de auditoría existente. Los recibos publicados son
snapshots acotados: el estado vivo seguirá avanzando después del commit.
