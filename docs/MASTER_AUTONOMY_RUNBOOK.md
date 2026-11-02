# Runbook único — autonomía PC A

Desde este repositorio: `powershell -NoProfile -File tools/research_control.ps1 STATUS` o `powershell -NoProfile -File tools/research_control.ps1 RESUME`.
STATUS lee reportes e informa antigüedad. RESUME valida y solicita únicamente la tarea guardian existente; mutex y checkpoints evitan duplicados. No instala infraestructura ni ejecuta entrenamiento. Requiere sesión de usuario. Dashboard y JSON persistentes: outputs/research_readiness/index.html y status.json. Guardian30s/reporter60s; tarea cada5min. Reboot físico pendiente de reinicio natural, no provocado.

Corte02/11/2026 09:35:55 Ecuador: +3.280 ticks (16.150 acumulados); dos muestras separadas10,59s: +48 callbacks/heartbeats,+46 ticks,+44 filas procesadas. XM conectado con cotizaciones recientes, calendario completo no certificado.

+2 M5 aceptadas (6 totales),+2 rechazadas (30 totales),+2 features (6 totales). Nuevas válidas:381/381 y521/521 BID con secuencia exacta. Rechazadas:797/797 con hash distinto/callbacks indistinguibles y1562/1565 con tres actualizaciones ausentes. Causa por evento no demostrada. Warmup continuo actual0/350 tras nuevos rechazos: faltan350; no confundir seis acumuladas con continuidad. BUY/SELL0, consecutivas0/800, posteriores0/100, evaluables0/200 y0/80 por lado. Cuatro segmentos en cuarentena, uno vacío; certificados0. Recálculos previos no sumados.

259/284: adjudicación publicada reutilizada,25 payloads BID ausentes, sin explicación por duplicados; scheduling/pérdida exacta no registrada. No nuevas consultas ni repetición de regresión. Los segmentos posteriores avanzan sin admitir la ventana antigua.

Membership del nuevo tail: identidad, fuente, hashes, secuencias y cursores verificados. Independencia/admisión completa pendientes. Exposure delta encadenado sin sobrescribir originales. Cutoff de features nativas verificado, pero historia corta/semillas insuficientes; CAUSAL_AUDIT global FAIL. Generación UTC y deriva no acotadas. NTS201 registros al snapshot; autenticación,offset,cotas y cadencia real en nts_receipt.json, sin inferir generación ni offset fijo.

Worker único:15,43MiB residente/254,09MiB privada,CPU1,92% de un núcleo entre muestras; cuatro filas en tránsito al snapshot. PID cambió respecto al informe anterior, recuperación observada con checkpoint preservado; causa de terminación previa no demostrada. Guardian activo,1XM/1watchdog, sin acciones nuevas en último reporte. No hubo cierre de programas ni modificación del otro proyecto.

Paquete/prerregistro/whitelist y todos sus hashes verificados. Logística BUY/SELL separada,FOLLOW/INVERT,4folds,máximo8fits. Runner/gate existentes; cero grants, admisión, entrenamiento, scoring o acceso protegido.14 tests relevantes PASS; compileall y sintaxis PowerShell PASS. No se repitieron50 tests ni probes aprobados.

Pendiente:350M5 propias continuas y semillas,800señales,100barras posteriores,200evaluables/80BUY/80SELL y folds; cobertura,membership,causalidad aplicable,dataset sellado y autorización específica. La continuidad protocolaria previa sigue rota: no se reinició el contrato ni activó una frontera científica. No depende solamente de esperar cotizaciones. No solicitud científica prematura.

Supervisión/captura/worker/NTS/reportes existentes continúan. No reanalizar ventanas sin evidencia nueva. COLLECTING_QUARANTINED; DATASET_ADMITTED=false; TRAINING_AUTHORIZED=false; TRAINING_COMPLETED=false. Manual:ninguna ahora. DISCOVERY_VALIDATION=BLOCKED; HISTORICAL_HOLDOUT/FINAL_TEST=LOCKED; DEMO=DISABLED; LIVE_TRADING=false.
