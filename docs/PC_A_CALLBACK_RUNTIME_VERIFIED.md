# Captura prospectiva nativa: funcionamiento observado

Revisión del 29 de octubre de 2026, horario principal America/Guayaquil. La captura ya registra OnTick y heartbeat reales: ACTIVE_CALLBACKS_QUARANTINED. No se declara certificación UTC ni exhaustividad de ticks.

Dos observaciones verificadas muestran 1.029 y 1.059 callbacks de ticks, incremento de 30. Existen tres archivos de sesión: el arranque fallido original se conserva, una sesión posterior contiene 234 ticks y SESSION_END, y la sesión actual continúa con heartbeat reciente. No se interpreta automáticamente cada sesión como reinicio de Windows.

Se verificaron cadenas SHA, secuencias, unidades, prefijos anteriores y espejo local. Se copiaron prefijos completos y acotados a snapshots inmutables locales, y se publican sus hashes y chain heads sin los quotes. Las fuentes v16 permanecen iguales. No se repitieron tests de software ya aprobados ni probes históricos.

En la primera observación había 12 quotes adyacentes idénticos, preservados sin deduplicar, y cero retrocesos de timestamps nativos o registros de desconexión. El mayor intervalo entre heartbeats fue 46.469 ms. Esto es una separación observada, no una prueba de pérdida de ticks ni de cierre del mercado; puede intervenir la cola/procesamiento y OnTick puede coalescer notificaciones. No se certifica cobertura exhaustiva, ni se usa ausencia de registros de desconexión como prueba de continuidad absoluta.

La tarea del testigo/monitor finalizó con código 0. El collector anterior tenía un fallo reciente (resultado 1; también se observó un rechazo del programador). Se ejecutó una colección controlada y luego una ejecución desde Task Scheduler: resultado final 0. El archivo conservó identidad prospective_20261028T175047_3ac8b527 y avanzó de 568 a 571 segmentos, sin reiniciar cursores ni mezclar datos. La causa del fallo anterior no quedó establecida y no se inventa. La recuperación observada no garantiza ausencia de fallos futuros.

UTC externo sigue siendo diagnóstico. La referencia independiente del mismo evento, incertidumbre defendible, mapping y calendario fechado permanecen pendientes. Todos los segmentos siguen QUARANTINED; CAUSAL_AUDIT=FAIL y TRAINING_READINESS=BLOCKED_BY_RESEARCH_GOVERNANCE. Ninguna puerta científica se abrió: DISCOVERY_VALIDATION=BLOCKED, FINAL_TEST=LOCKED, DEMO=DISABLED, LIVE_TRADING=false. No se necesita una acción manual para que la captura continúe.


Durante la publicación se incorporó por fast-forward la actualización remota d266561 (handoff/documentación vigente y guard portable del testigo). Se revisaron los cambios sin sobrescribirlos; el test nuevo de rechazo no-Windows pasó en PC A. El sello v17 registra esas diferencias frente a v16, conservando los sellos históricos. La captura observada previamente no se reinterpreta.
