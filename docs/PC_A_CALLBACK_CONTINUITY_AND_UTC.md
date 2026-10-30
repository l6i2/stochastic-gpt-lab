# Continuidad y correlación prospectiva de PC A

La captura permanece read-only, activa y en cuarentena. No se recompila ni reinicia el EA; no hay backfill ni mezcla con los históricos. Ecuador continúa como vista principal. El snapshot publicado contiene el estado observado y sus prefijos; no promete continuidad futura.

## Hueco de 46 segundos

El intervalo entre heartbeats es 46.469 ms: secuencia 831 a 833, con un tick observado en 832. Uptime y contador del programa avanzaron aproximadamente el mismo intervalo. Los extremos registran connected=true; la secuencia y cadena son válidas. La ventana host fue 29/10/2026 21:32:52–21:33:38 en Ecuador (UTC del host no certificado para eventos XM).

La revisión acotada de logs de MT5 no encontró mensajes coincidentes de desconexión/carga/error de escritura/cierre. La consulta de eventos System de Windows para suspensión, reanudación, arranque y apagado no encontró eventos coincidentes; el contexto automatizado registra expresamente NO_MATCHING_EVENTS. Esto no prueba ausencia de una desconexión breve ni de un bloqueo. No hay medidas del tiempo dentro de cada handler, de ocupación de la cola ni una fuente independiente exhaustiva de eventos. La causa continúa UNDETERMINED y la pérdida real de ticks UNVERIFIED. Una pausa del mercado por sí sola no explica la demora de un timer; tampoco queda certificada como causa. No se inventa una atribución.

[OnTimer](https://www.mql5.com/en/docs/event_handlers/ontimer) y [OnTick](https://www.mql5.com/en/docs/event_handlers/ontick) comparten procesamiento secuencial por aplicación y pueden omitir notificaciones del mismo tipo si ya están pendientes/en proceso. Contigüidad de secuencias significa continuidad de registros escritos, no exhaustividad de eventos del broker.

## Monitor automático e integridad

La nueva función callback_continuity analiza solo el espejo de la captura nativa previamente verificado. Conserva cada incidencia como archivo de creación exclusiva con ID estable derivado de sesión y secuencias, hash del prefijo y primera observación. Contextos posteriores se guardan aparte sin reescribir la incidencia. Se registran conexión en extremos, tick callbacks intermedios, contadores y duración. El disparador operativo son dos periodos nominales de EventSetTimer(5); no es tolerancia de aceptación científica ni un número certificado de eventos perdidos.

Cada incidencia nueva provoca una consulta System acotada de contexto, con estado OK/NO_MATCHING_EVENTS/QUERY_FAILED y límite explícito de 200 registros. Los datos contextuales no determinan automáticamente causalidad. El monitor conserva las fallas y deja causa desconocida si no hay prueba. Ninguna ausencia de ticks se convierte en cierre del mercado.

Se generan segmentos no solapados en el dominio de uptime de cada sesión, separando ventanas con incidencias de las restantes. Los extremos y registros terminales quedan explícitos; no se convierten a UTC ni se unen sesiones por su número de uptime. Todos los segmentos son QUARANTINED por falta de procedencia temporal; las ventanas sin incidencia tampoco se certifican. Se conserva el estado de sesiones anteriores, incluida la fallida original y una cerrada correctamente. No se provoca un reinicio para probarlo ni se afirma recuperación completa tras Windows solo por ver otro session_id.

## Correlación externa reproducible

El testigo ahora retiene respuesta NTP en hex, nonce de solicitud, RTT, stratum, leap indicator, precisión y root delay/dispersion anunciados. Se reprodujo localmente la decodificación de las tres respuestas con el nonce y coincidió exactamente con server_transmit_ns. Esos errores son anunciados por un servidor no autenticado: no constituyen una garantía de precisión absoluta.

En el instante de anclaje se guardan brackets del GetTickCount64 de Windows junto al contador Python. El modelo proyecta un intervalo de recepción al uptime del último callback de una sesión reciente y conserva al lado su timestamp nativo original. La proyección declara expresamente el supuesto de contador compartido y deriva cero, y enumera componentes sin cota: cuantización, deriva, error absoluto del servidor y demora de cola. Por tanto no se usa como UTC del evento ni como mapping autorizado. Se preservan las referencias TLS como corroboración diagnóstica; no se usa TimeTradeServer.

El snapshot de correlación sigue mostrando que una hora del host razonable no certifica el origen del evento. La consistencia time_msc//1000==time está comprobada por el verificador nativo, pero la diferencia entre etiquetas nativas y recepción no se instala como offset. Los timestamps futuros no se evalúan mediante una conversión inventada.

## Validación y preparación científica

20 pruebas afectadas PASS: incidencias con ticks intermedios, ausencia de falsa clasificación por mercado inactivo, IDs estables, segmentos no solapados, proyección explícitamente no certificada, cadenas, truncamiento, prefijos, nonce y referencias diagnósticas. Se verificó funcionamiento real del monitor actualizado: tarea con resultado 0 y producción de incidencias/contextos/testigo. La captura observada continuó ACTIVE_CALLBACKS_QUARANTINED. No se reejecutó la auditoría causal sobre datos ambiguos: sigue FAIL por el prerrequisito de normalización no demostrado.

Se reutilizó el preparador científico data-free: inventario de componentes y plantillas, sin abrir etiquetas/Validation/Final Test ni exponer fit o búsqueda adaptativa. El collector original y la captura callback tienen carpetas/cadenas/identidades separadas. El módulo horario y los contratos congelados permanecen idénticos.

CERTIFIED_SEGMENTS=[]; NATIVE_TO_UTC_MAPPING=UNVERIFIED; calendario PARTIAL; TRAINING_READINESS=BLOCKED_BY_RESEARCH_GOVERNANCE. DISCOVERY_VALIDATION=BLOCKED; FINAL_TEST=LOCKED; DEMO=DISABLED; LIVE_TRADING=false. No se requiere intervención manual.
