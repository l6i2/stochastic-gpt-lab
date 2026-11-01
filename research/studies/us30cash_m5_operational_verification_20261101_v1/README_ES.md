# Verificación operativa — 1 noviembre 2026

## Conclusión basada en datos reales

**La ingestión de heartbeats funciona; el pipeline de mercado completo NO ESTÁ DEMOSTRADO.** No se presenta instalación, un proceso vivo ni tests sintéticos como prueba de ticks→M5→features→señales. Corte **2026-11-01T10:06:23.321338-05:00**, horario Ecuador; estas etiquetas del host no certifican generación UTC del broker.

En dos muestras separadas por **21.394 s** se observaron **+4 callbacks raw** y **+4 registros consumidos por el worker**, todos heartbeats reales. No hubo nuevos ticks. El total al final del par fue **4346 callbacks**, cero ticks de mercado, cero ticks consumidos en cuarentena, cero M1/M5 completados y cero M5 rechazados. Los rechazados no crecen porque no existen buckets de precio que procesar. Features reales=0; BUY=0; SELL=0; warmup=0/350; consecutivas=0/800; barras posteriores=0/100; soporte evaluable=0/200 (0 BUY/80, 0 SELL/80).

`first.json`, `last.json` y `progress.json` preservan ambas observaciones y los deltas. `ledger_verification.json` conserva la verificación posterior de prefijos; `later_prefix_integrity.json` amplía esa comprobación hasta 4380 registros sin sustituir la muestra anterior. La captura puede seguir creciendo después de estos cortes; los números no se suman entre snapshots.

## Proceso, recursos y cursor

Hay un worker de procesamiento real PID 13132, más su launcher .venv, identificado por relación padre-hijo. No hay otro worker inesperado. El launcher no es un segundo lector. Memoria privada combinada en la muestra: **17.67 MiB**; CPU del worker promedio durante la ventana: **0.876% de un núcleo**. Son mediciones observadas, no un límite de memoria garantizado ni evidencia de estabilidad ilimitada de Windows.

Se verificaron íntegramente las cadenas hash raw y derivada hasta sus checkpoints, el conteo de artifacts por tipo y los contadores de barras contra el estado. Se recomputó el número real de callbacks/ticks del prefijo consumido y se compararon posición byte, número de filas y chain head con el cursor del worker. Ruta, identidad y cursor coinciden con la captura autorizada; no hay evidencia de proceso detenido, ruta equivocada o cursor saltado que explique las cero barras. No se abrió ninguna fila de datasets protegidos.

Se conserva el prefijo anterior al cambio de versión y los prefijos raw del comprobante de reinicio idempotente previamente realizado. La actualización no reinició IDs ni datos y el avance actual no duplica procesamiento de fuente. **No se provocó otro reinicio del worker, MT5 ni Windows en esta auditoría**: se reutilizó y verificó aquel comprobante real; no es prueba de reinicio físico de la PC.

## Por qué no hay barras

La causa inmediata demostrada es **ausencia de notificaciones ONTICK_LATEST_QUOTE en la nueva captura**. El observador emite HEARTBEAT y el worker los consume; ninguno contiene un precio usable para construir velas. Una cotización cacheada de MT5 no se convierte en un evento prospectivo ni se copia al raw.

La instancia XM correcta estaba **conectada en las dos muestras**. SymbolInfoTick devolvió la misma etiqueta nativa cacheada **1793401199637**; no cambió durante la ventana. El primer chequeo previo sí vio desconexión, y el journal de MT5 registra desconexiones, autorizaciones correctas y sincronización posteriores, sin fallos de autenticación identificados por el filtro. Se preserva solo contexto categórico, hora del log y hash del archivo, nunca mensajes con cuentas, servidores de acceso, IP o credenciales. Esa evidencia muestra reconexión automática; no prueba disponibilidad de cotizaciones de US30Cash.

El día cliente es domingo. El snapshot específico XMGlobalSC-MT5 5 guardado el 28 octubre enumera sesiones de cotización de lunes a viernes y ninguna de fin de semana. La página oficial genérica [XM execution policy](https://www.xm.com/execution-policy) describe negociación semanal dependiente del producto y posibles horarios extendidos. **Esto hace compatible la ausencia de ticks con cierre de fin de semana, pero no certifica el calendario exacto actual de US30Cash ni explica por sí solo las desconexiones.** No se extrapoló una hora de reapertura, DST u offset fijo; calendario sigue PARTIAL.

Se separan causas y bloqueos: no hay evidencia actual de error de agregación, porque no recibió ticks que agregar. La dependencia temporal, el membership incompleto y los gaps impiden admisión científica incluso si aparecen barras; no se usan como explicación ficticia de por qué todavía no existe ningún bucket de precio. En el corte hay 19 gaps y 5 inicios de desconexión; el mayor mide 43442235 ms. No se rellena ni se interpreta automáticamente como cierre del mercado.

## Acciones y siguiente estado

No se encontró un fallo técnico de ruta, cursor o proceso que justificara reemplazar componentes o reiniciar productores. Se deja la captura, el worker y la reconexión ya instalada funcionando. No se añadió infraestructura persistente ni otra tarea/daemon; la herramienta nueva es un auditor de solo lectura reutilizable:

    .venv\Scripts\python.exe tools\verify_prospective_operation.py --out outputs\operacion_<id_nuevo> --seconds 20

Siete tests nuevos validan que el informe no confunda heartbeat con tick, caché con evento nuevo, crecimiento de ticks con pipeline completo o un launcher con segundo worker; rechazan regresión de contadores/identidad, preservan desconexión como causa observable y no calculan CPU entre boots distintos. No se repitieron pruebas aprobadas de instalación, energía, indicadores nativos o fixtures del procesador.

Todos los datos capturados y derivados permanecen separados y QUARANTINED; admitidos=0, DATASET_HASH=null. Membership/exposure del prefijo son trazables, pero independencia legado y procedencia temporal siguen pendientes. CAUSAL_AUDIT=FAIL; DATASET_MATURITY=NOT_READY; TRAINING_READINESS=BLOCKED. Discovery Validation e Historical Holdout bloqueados; Final Test LOCKED; DEMO DISABLED; LIVE_TRADING=false. Sin labels, entrenamiento, scoring, órdenes ni cambios al otro proyecto.

El siguiente paso automático es recibir ticks reales, contrastar barras cerradas y observar crecimiento real de features/señales bajo los controles existentes. Hasta entonces no se declara operativo extremo a extremo. No hay intervención manual inevitable demostrada ahora; no se pide ejecutar un probe o reinicio para forzar un PASS.
