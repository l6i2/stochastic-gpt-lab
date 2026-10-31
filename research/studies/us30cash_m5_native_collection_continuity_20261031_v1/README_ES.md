# Continuación de captura — interrupción observada, 2026-10-31

La captura `us30cap_15cbddec947f42c98219caa4cec978f2` sigue activa y en cuarentena.
Su ID, inicio, segmentos originales, autorización y ledger de cierre de reserva
no se modifican. No se abrió ningún conjunto protegido ni se ejecutó scoring,
fit, entrenamiento, query histórica o probe nativo/UTC repetido.

## Evidencia nueva

Se detectaron **tres gaps entre callbacks**, de 4.066.484 ms, 27.594 ms y 15.609 ms.
El mayor dura **67 minutos y 46,484 segundos**. Los labels del reloj del host
sitúan sus extremos aproximadamente entre **13:47:37 y 14:55:24, hora Ecuador**.
No son timestamps UTC independientes del evento broker ni se usan para normalizarlo.

Antes/después del gap mayor, las secuencias nativas son 303 y 304, en la misma
sesión y BootId 111. El extremo previo registra connected=true y el posterior
connected=false. Se observó después reconexión. Las cadenas y secuencias verificadas
siguen íntegras: eso prueba el orden de registros existentes, **no que el broker
no generó ticks perdidos ni que OnTick entregó todos los eventos**.

`power_context.json` contiene cuatro eventos originales de Windows Kernel-Power:
entrada 506 a Modern Standby por **Lid**, salida/entrada intermedia por
`Austerity Battery Drain Budget Exceeded` y salida 507 por **Lid**. Sus labels
Windows encuadran el gap largo. Corroboran suspensión moderna y la posterior
desconexión observada, sin convertir correlación de reloj local en certificación
de generación XM. No se cambió energía, suspensión, tapa, login ni otra aplicación.

El intervalo interrumpido queda **QUARANTINED**. No se fabrican callbacks, ticks,
velas, timestamps ni continuidad; no se hace backfill. No se presume que un sábado
o la falta de ticks prueban cierre de mercado: el calendario específico no se
certificó en esta revisión.

## Mejora de supervisión dentro de la autorización vigente

Se añadió `controller/capture_continuity_monitor.py`, integrado exclusivamente en
el colector nuevo. Verifica incrementalmente el prefijo del journal contra un
checkpoint, hashes y secuencias. Mantiene cursor/summary derivados separados de
datos originales y emite hechos de incidentes en archivos exclusivos e inmutables.
Repetir la auditoría o recuperar el cursor no duplica ni cambia incidentes.

Detecta gaps de dos periodos nominales del timer de 5 s, transiciones de conexión,
regresiones nativas y truncación/cambio de journal. Diez segundos es un disparador
diagnóstico heredado del timer, **no una tolerancia de calidad/causalidad**.
El estado actual expone la interrupción histórica junto al heartbeat reciente:
`ACTIVE_QUARANTINED` ya no puede interpretarse como cobertura continua certificada.
El contexto Windows aquí publicado procede de consulta read-only; el monitor
automático conserva hechos y no inventa una causa cuando falte contexto.

El código revisado cambia solo el hook/estado de `controller/authorized_capture.py`;
los demás archivos del seal v27 se verificaron sin cambios. El pin de despliegue
nuevo se conserva versionado. Se relanzó únicamente el proceso de captura propio
validado; el watchdog lo recuperó con el mismo capture ID, segmento, manifiesto y
cursor. MT5 y los observadores anteriores siguieron activos. No se reinició PC.

Los informes previos publicados permanecen intactos. Las versiones de diagnóstico
de restart quedan también retenidas en `maintenance_evidence`; una copia raw del
informe inicial se verificó byte a byte contra el SHA original conservado en el
informe publicado. No se reconstruyeron ni alteraron datos de mercado.

## Validación y siguiente estado

**27 pruebas afectadas PASS**, cero fallos/errores/skips: idempotencia incremental,
incidentes inmutables, recuperación de cursor, truncación sin callback nuevo,
restarts, frontera de captura y alcance limitado de autorización. Se reutilizó la
evidencia nativa previamente aprobada; no se recalcularon sus indicadores o auditorías
causales sin ticks/material nuevos.

La instantánea registra heartbeats y todavía cero ticks. La captura continúa
automáticamente en cuarentena con monitor pasivo; no se afirma cobertura de quotes,
M5, independencia o disponibilidad de features reales. Si Windows vuelve a dormir,
el intervalo se registrará como interrupción al reanudarse, no se rellenará.

DATASET_ADMISSION=BLOCKED; CAUSAL_AUDIT=FAIL_GLOBAL_UNCHANGED;
TRAINING_READINESS=BLOCKED; SCORING=NOT_AUTHORIZED; LIVE_TRADING=false.
Discovery Validation/Historical Holdout siguen BLOCKED, Final Test LOCKED,
DEMO DISABLED. No se necesita intervención humana para mantener la supervisión.
