# Propuesta separada: observación de base nativa MT5

**INACTIVA. No es una modificación del productor autorizado ni un dataset admitido.**
No instala EA, servicio o tarea; no altera estrategia, protocolos ni cohortes.

## Incompatibilidad demostrada

El protocolo vigente `research/studies/us30cash_m5_native_pretrain_v1/PROTOCOL_ES.md`
mantiene productor/estrategia y exige350 M5 propias, semillas vinculadas, primeras800
señales consecutivas,100 barras posteriores y soporte200/80/80/folds. El plan reconoce
`RAW_CALLBACKS_QUARANTINED_NOT_EXHAUSTIVE_FEED_PROOF`. La autorización de recolección
no transforma esos callbacks en una fuente exhaustiva.

La función [OnTick](https://www.mql5.com/en/docs/event_handlers/ontick) no encola cada
nuevo evento mientras ya existe uno pendiente/en ejecución. La propia documentación
de [CopyTicks](https://www.mql5.com/en/docs/series/copyticks) especifica que OnTick es
una notificación de cambios, posiblemente de varios ticks. Aumentar prioridad,
optimizar FileFlush o usar OnTimer no crea una garantía ausente de la interfaz.
OnTimer actual solo registra heartbeat. Hashes y secuencias locales prueban la
integridad de lo registrado, no que se haya registrado cada actualización del broker.

CopyTicks/CopyTicksRange permiten obtener una secuencia desde la base del terminal;
también pueden sincronizar y descargar registros ausentes del servidor. No exponen
un indicador fiable por fila «recibido en vivo en esta sesión» frente a «descargado».
Tampoco proporcionan un ID universal que permita deduplicar todos los eventos por
time_msc/Bid/Ask/flags. Por ello no se puede garantizar con estas APIs públicas la
prueba estricta de recepción exhaustiva por callback y prohibición de sustitución.
No se afirma que todas las ventanas fallen ni que MT5 no pueda producir velas:
algunas secuencias coinciden exactamente, pero no hay garantía de350 consecutivas.

## Alternativa A — otro estudio nativo con procedencia explícita

Someter a aprobación un protocolo separado de **snapshots de base nativa observados
durante una adquisición futura**, conservando el contrato actual intacto. Fuente:
`TERMINAL_DATABASE_QUERY`, nunca `ONTICK_LATEST_QUOTE`. El estimando es un replay
nativo de la estrategia congelada, no una prueba de recepción o ejecución en vivo.
La autorización debe permitir expresamente esta clase de procedencia; si la
prohibición actual de consultas posteriores es absoluta, esta alternativa no es
admisible bajo ese contrato y permanece inactiva.

### Diseño del productor futuro (no implementado/activado)

1. ID/carpeta/manifest/hash propios y rol nuevo autorizado; no adoptar estos ensayos,
   históricos, cohortes o seeds previos. Inicio real registrado después de aprobación.
2. OnTick como disparador ligero; OnTimer para consultar incrementalmente la base
   con CopyTicks(COPY_TICKS_ALL). Nunca identificar un disparador con un tick.
3. Por consulta: límites nativos, boot/session, contador monotónico al inicio/fin,
   primera observación local/UTC condicional, conexión, error GetLastError y contenido
   original completo. Registrar el límite de disponibilidad después de terminar la
   lectura; no inventar timestamps individuales de recepción.
4. Cursor inclusivo del último milisegundo y prefijo por posición/hash. Repetir el
   milisegundo fronterizo y verificar el prefijo completo; conservar multiplicidad y
   orden. No deduplicar por valor ni desplazar timestamps. Una revisión del prefijo
   crea una vintage distinta y cuarentena; nunca reemplaza silenciosamente datos.
5. Batches pequeños con límite de filas/memoria, siempre explícitos. Timeout, buffer
   saturado, error o conexión perdida impiden marcar completo. No truncar y aceptar.
   Archivo append-only/hash-chain por batch, flush verificable; no FileFlush por tick.
6. Reinicio/desconexión/gap: cerrar segmento, conservar originales y crear un corte
   nuevo después de anclar el origen. No consultar desde el cursor antiguo para
   rellenar la interrupción. Las primeras barras parciales no cuentan.
7. Barras cerradas por rangos nativos [inicio,fin), no por ausencia de ticks. Comparar
   multiplicidad, secuencia y OHLC/volumen con la base/CopyRates. Dos snapshots iguales
   solo prueban repetibilidad de esa vista; no exhaustividad de recepción del broker.
8. Features y MAIN_K idénticos. Replay y disponibilidad física son afirmaciones
   separadas; ninguna feature puede usar filas posteriores a la decisión simulada.
   Si el primer visto ocurrió después de la decisión, no atribuir disponibilidad en
   vivo retrospectiva. Validar entry/same-bar/seeds en tester nativo aislado permitido.
9.350 barras propias y800/100/200/80/80/folds sin cambios; no heredar progreso actual.
   Mantener admisión, entrenamiento y scoring bloqueados hasta pruebas y grants.
10. Calendario/DST solo con evidencia de sesiones; incertidumbre explícita. No
    equivalencia automática NYSE/US30Cash ni generación UTC desde TimeTradeServer.

### Aceptación antes de activar y después de recoger

Antes: autorización específica de metodología/fuente/rol, hashes del productor,
identidad de instalación y exclusión de conjuntos protegidos, plan de recursos y
protocolo de interrupciones. Ensayos sintéticos deben rechazar errores/ambigüedad.
Luego: corrida real aislada con batches, consultas y fallos trazables; comparación
nativa por cada intervalo; prueba de recuperación sin backfill; causalidad de todas
las features; membresía y madurez propias. Ninguna de esas condiciones está cumplida
por el simple hecho de diseñar el sistema o verificar un minuto de referencia.

## Alternativa B — mantener exigencia estricta de recepción

Obtener una fuente autorizada por el broker con secuencias/IDs de eventos y evidencia
de recepción verificable, documentando pérdidas y reconexiones. No consta que XM
ofrezca aquí acceso a una interfaz con esas garantías: disponibilidad, contrato y
especificación son dependencias externas pendientes. No inventar un feed FIX/SDK.

## Decisión exacta pendiente

Autorizar únicamente el desarrollo y ensayo de un productor nuevo e independiente,
para un protocolo diagnóstico separado que acepte **primera observación de snapshots
de base MT5**, sin atribuir recepción en vivo o generación UTC. Mantener productor,
captura y contrato vigentes intactos. Esta decisión no autoriza activar una cohorte
científica, admitir datasets, completar huecos, entrenar, hacer scoring ni operar.
Sin esa aprobación no se instala ni ejecuta un productor nuevo. `review.py` es solo
un validador offline de la propuesta; no dispone de API de activación ni acceso MT5.
