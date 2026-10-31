# Verificación final de estabilidad PC A

La energía fue consultada de nuevo: AC suspensión 0, hibernación 0, tapa 0 (no hacer nada). Batería preservada: suspensión 180 segundos, tapa suspender, hibernación 2147483647. Se conserva el snapshot original y el comando de restauración. La política es compartida por Windows; no es aislamiento energético por proyecto.

Existe un XM terminal64.exe (PID 7524 en la muestra), un watchdog y un supervisor de recuperación. El capturador Python tiene un lanzador .venv/pythonw y su hijo runtime: relación padre-hijo, no dos lectores independientes. La exclusión usa mutex del watchdog y lock del capturador. La tarea RawQuarantine heredada continúa intacta; su resultado 267009 indica tarea actualmente en ejecución. La tarea ProspectiveUTC tiene resultado 0. No se eliminan procesos por conteo ni se cierran productores. Las mediciones RAM son una muestra: memoria privada y working set se distinguen, sin afirmar ausencia global de presión de memoria. La RAM disponible de todo Windows varía; no se cambian procesos ajenos ni configuración de paginación.

El supervisor consulta procesos cada 30 segundos (antes 15). Verifica NTS y comprobantes de reinicio con procesos cortos cada 60 segundos, independientemente; NTS conserva su cadencia propia de cinco minutos, lock y timeouts. El índice NTS avanzó durante la verificación con Cloudflare autenticado y el segundo origen no disponible. No se hicieron probes manuales nuevos ni cambios del reloj. Los comprobantes se escriben atómicamente, validan prefijos y no mutan checkpoints originales. No se crea un daemon adicional permanente. Un supervisor se actualizó sin cerrar MT5 ni el capturador.

## Próximo reinicio natural

HKCU Run de captura y recuperación permanece configurado; requiere iniciar sesión Windows. No hay autologin, contraseña ni reinicio automático. Cada minuto se conserva en outputs/pc_a_stability/restart/latest_pre_restart.json el ID, BootId, segmento, cursores, chain heads, hash del manifiesto, prefijos de journal y fuente nativa. Es el último comprobante seguro periódico, no un gancho garantizado en el instante exacto del apagado. Una falla de lectura conserva el comprobante previo y deja error/reintento.

Después de cambiar BootId, el verificador exige que permanezcan idénticos los prefijos anteriores; espera un segmento nuevo con callback reciente del mismo capture ID. Guarda comparación pendiente una vez por transición y comparación exitosa inmutable, con referencia persistente al último evento. Los logs y cadenas anteriores permanecen. No resta contadores monotónicos entre boots ni certifica duración UTC del apagado. Un cambio de boot observado y reanudación no prueba un ciclo físico de alimentación ni certificación causal/UTC del broker. La prueba real permanece PENDING; fixtures sintéticos nunca se presentan como reinicio real.

La política actual limita intentos de abrir XM a uno por 120 segundos dentro de la vida del supervisor; solo lo abre si está ausente y pasan los controles de perfil/binario previamente publicados. No mata MT5 vivo por desconexión ni intenta relogin con credenciales. Mantiene cuarentena durante red caída, ausencia de callbacks o cambio de sesión. El watchdog conserva recuperación idempotente y los intervalos faltantes se registran, sin backfill.

## Continuidad y límites

Hay 8 gaps acumulados en la muestra. Se preservan los seis previos y dos adicionales de 18.422 y 13.391 segundos, posteriores al cambio de energía, con conexión true a ambos extremos. Su causa queda indeterminada; no se atribuye a suspensión ni se afirma pérdida cero de eventos. El máximo sigue en 4066484 ms. Los heartbeats avanzan; hasta esta muestra la captura nueva contiene cero ticks. No se certifica completitud de mercado por procesos sanos.

34 tests Python PASS y seis comprobaciones sintéticas PowerShell PASS. Incluyen avance append-only, truncamiento/cambios de prefijos, cambio de identidad/manifiesto, mismo boot sin prueba de reinicio, nuevo boot sin segmento fresco y rechazo de checkpoints incompletos. No se reinició Windows, cerró la tapa ni provocó desconexión o crash de productores.

No se ejecutó ninguna escritura ni operación de control dirigida al otro proyecto. No existe un inventario previo de todos sus archivos para certificar que ningún actor externo los cambió; ese límite se declara en el resultado. Se conservaron scripts/contratos congelados y tareas anteriores. No se vuelve a usar datos protegidos, no hay entrenamiento, scoring, DEMO u órdenes. CAUSAL_AUDIT=FAIL; TRAINING_READINESS=BLOCKED; LIVE_TRADING=false.

Restauración desde el repositorio, sin cerrar productores:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\restore_research_stability.ps1

Próximo estado: observación automatizada en cuarentena y comprobación pasiva después del siguiente arranque natural. No hay solicitud de reinicio inmediato ni intervención manual pendiente.
