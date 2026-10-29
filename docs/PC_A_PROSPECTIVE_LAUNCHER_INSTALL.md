# Instalación del lanzador en Scripts de XM MT5

La instancia abierta fue comprobada mediante MetaTrader5.terminal_info(): instalación XM Global SC MT5 Terminal, data folder 20C285FE08971A9A2E814AAC44AFC9D2, servidor XMGlobalSC-MT5 5, conexión activa y trade_allowed=false. No se publican identificadores de cuenta.

El capturador anterior es un Expert Advisor: ProspectiveUtcObserver.mq5/ex5, en MQL5/Experts/ResearchDiagnostics. No aparece bajo Scripts porque OnTick solo corresponde a EAs. Sus archivos y hashes se conservaron.

Se creó un Script separado StartProspectiveUtcObserver.mq5 y se compiló su EX5 en MQL5/Scripts/ResearchDiagnostics/PC_A usando MetaEditor de esa misma instalación. Compilación: 0 errores, 0 advertencias. Se exige binario fresco, fuente instalada idéntica al repositorio y preservación de todos los scripts preexistentes del directorio. installation.json registra rutas y SHA256 exactos, incluido el probe previamente aprobado.

El lanzador no consulta historia ni envía órdenes. Cuando se ejecute, valida entorno fijado y Algo Trading desactivado, evita otro observador ya adjunto y abre un gráfico dedicado US30Cash M1. Encola una plantilla con el EA existente y expertmode=0; no reemplaza el EA del gráfico actual. El testigo UTC independiente continúa como proceso Python programado, no como fuente UTC inventada dentro del script.

La [API oficial ChartApplyTemplate](https://www.mql5.com/en/docs/chart_operations/chartapplytemplate) indica que true confirma la puesta en cola, no la ejecución completa. Por ello el lanzador imprime QUEUED_NOT_CERTIFIED y el monitor debe observar SESSION_START/callbacks antes de declarar funcionamiento. La plantilla incluye solo el observador y el indicador de precio Main. La carga real de la plantilla todavía no se ha ejecutado/verificado.

La instalación se automatiza con `python tools/install_prospective_launcher.py`. El instalador no ejecuta el script, no cambia permisos de trading/DLL y no modifica probes aprobados. No hay API disponible para actualizar Navigator de esta instancia sin interacción; no se usan mensajes Win32 no documentados ni se reinicia el terminal. Única acción manual indicada: clic derecho en Scripts → Actualizar. No se pide ejecutar el lanzador en este paso.

Instalación verificada no equivale a captura en funcionamiento ni certificación UTC. Se conservan las puertas científicas cerradas, DEMO=DISABLED y LIVE_TRADING=false.
