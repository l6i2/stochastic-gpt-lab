# PC A: estado de preparación

Checkout exclusivo en Documents/Codex/stochastic-gpt-lab-full-pipeline, rama research/full-pipeline. No se reutilizó el WSL existente ni archivos de otros proyectos.

Windows 11 Home x64, Intel i5-1135G7 (4 cores/8 threads), RAM visible 7.74 GiB. Menos de 1 GiB libre en la auditoría inicial: LOW_MEMORY_MODE=true, ejecución secuencial y límites de threads locales al launcher.

Python 3.12.14 en .venv con requirements.txt y configs/controller_requirements.txt; pip check y compileall correctos. Suite final: 245 tests, 9 omitidos por g++ ausente. Se corrigió el cierre de SQLite en ShadowRecorder conservando la transacción durable; shadow sigue deshabilitado. MAIN_K: evidencia retenida con hashes verificados, sin repetir parity. Se preservan los bytes LF del EA sellado.

XM MT5 instalado desde el sitio oficial, instalador con firma MetaQuotes válida. Cuenta DEMO, conexión y US30Cash todavía sin verificar. Compilación local y hashes: outputs/pc_a/compile_manifest.json (verificar el resultado completo antes de aceptación C2). C3/C4/C5 pendientes de una sesión DEMO verificada; no se ejecutaron históricos.

Reloj Windows inicial: leap indicator 3, stratum 0, Local CMOS Clock, sin sincronización previa. Resync sin elevar: acceso denegado. CLOCK_ATTESTATION, NATIVE_TO_UTC_MAPPING, TEMPORAL_CAUSALITY y CAUSAL_AUDIT pendientes. No basta corregir Windows: faltan captura simultánea y mapping externo revisado.

No apareció un paquete de transferencia en la búsqueda acotada a Documents/Downloads y directorios habituales del usuario. No se restauraron ni inventaron datos. Collector bloqueado: continuidad no demostrada. No se crearon tareas ni se iniciaron monitores o captura; faltan cursor/manifiesto y decisión sobre segmento si no se recupera la cohorte.

Launcher y resume son preflight read-only; retornan BLOCKED. El arranque de componentes aún no está aceptado. No confundir preparación de herramientas con estación lista.

FUTURE_EVALUATOR=READY_BUT_GATED; DRIFT_MONITOR=READY (tooling, sin baseline real); SHADOW_MODE=READY_BUT_DISABLED; SHADOW_ORDER_COUNT=0; DEMO_EXECUTOR=READY_BUT_DISABLED_FULL (mocks, sin adaptador de órdenes); DISCOVERY_VALIDATION=BLOCKED; FINAL_TEST=LOCKED; DEMO=DISABLED; LIVE_TRADING=false.

GitHub CLI instalado por winget en alcance de usuario; autenticación pendiente. Commit y push pendientes. Supervisión móvil pendiente de configuración oficial y verificación de cuenta, sin ampliar permisos de acceso por métodos alternativos.

OTHER_PROJECT_TOUCHED=NO: no escrituras intencionales fuera del proyecto salvo instalación de herramientas, nueva instancia XM y sus carpetas oficiales. Ningún proyecto ajeno fue modificado. La búsqueda fue acotada, no una auditoría completa de todo el disco.

Compilación comprobada: StochasticBarDecisionResearchEA y FullClockAndTimeSemanticsProbe, ambos 0 errores/0 advertencias, EX5 y hashes presentes. Las plantillas MainKNativeParity y SnapshotCausalProbe no se pueden desplegar directamente: necesitan generación/contexto del controlador. Se retiraron exclusivamente nuestras copias incompletas; los errores iniciales se conservan en logs. MAIN_K no necesita repetición local. C2 parcial para el conjunto completo del controlador, sin declarar C1-C5 PASS.

## Revalidación local posterior

Windows Time fue configurado con inicio automático y permanece Running. NTP reporta leap=0, stratum=5 y fuente time.windows.com. Stripchart: aproximadamente -0.18 a -0.23 s; quorum independiente: reloj local fuera del intervalo de red (adelanto aproximado de 0.14-0.17 s). WINDOWS_CLOCK_SYNC=PASS a nivel del servicio del sistema; no constituye CLOCK_ATTESTATION=PASS ni autoridad causal. Se conserva la evidencia local en outputs/pc_a y clock_repair_*.

Se restauraron exactamente los bytes LF auditados de 219 archivos que Git había convertido a CRLF, solo cuando el hash normalizado coincidía con el sello original. La configuración global de Git permanece intacta; .gitattributes fija LF en nuevos checkouts. CLOUD_SOURCE_HASHES.json no se modifica. Los cambios revisados de PC A se sellan aparte en configs/pc_a_source_hashes.json, con hash del manifiesto original y cobertura completa. El wrapper acepta -SourceManifest explícito y sigue rechazando omisiones y archivos alterados.

Compilación revalidada con bytes actuales del repo e includes: EA StochasticBarDecisionResearchEA y FullClockAndTimeSemanticsProbe, ambos PASS (0 errores, 0 advertencias), EX5 recién generados y hashes. Resumen actualizado: outputs/pc_a/compile_verified.json. Los logs iniciales fallidos de plantillas se conservan como evidencia, sin copias inválidas en Navigator.

XM tiene un formulario de apertura de cuenta pendiente; no se ha enviado, no se han introducido credenciales ni documentos mediante automatización. Cuenta UNKNOWN, API attach timeout -10005; XM_DEMO y US30Cash pendientes. No se ejecuta ningún probe mientras la cuenta sea UNKNOWN/REAL. C1/C3/C4/C5 siguen pendientes y C2 solo cubre los dos artefactos compilados.
