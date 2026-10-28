# PC A: estado de preparación

Checkout exclusivo en Documents/Codex/stochastic-gpt-lab-full-pipeline, rama research/full-pipeline. No se reutilizó el WSL existente ni archivos de otros proyectos.

Windows 11 Home x64, Intel i5-1135G7 (4 cores/8 threads), RAM visible 7.74 GiB. Menos de 1 GiB libre en la auditoría inicial: LOW_MEMORY_MODE=true, ejecución secuencial y límites de threads locales al launcher.

Python 3.12.14 en .venv con requirements.txt y configs/controller_requirements.txt; pip check y compileall correctos. Suite final: 246 tests, 9 omitidos por g++ ausente. Se corrigió el cierre de SQLite en ShadowRecorder conservando la transacción durable; shadow sigue deshabilitado. MAIN_K: evidencia retenida con hashes verificados, sin repetir parity. Se preservan los bytes LF del EA sellado.

XM MT5 instalado desde el sitio oficial, instalador con firma MetaQuotes válida. Cuenta DEMO, conexión y US30Cash todavía sin verificar. Compilación local y hashes: outputs/pc_a/compile_verified.json (dos artefactos verificados; C2 completo pendiente). C3/C4/C5 pendientes de una sesión DEMO verificada; no se ejecutaron históricos.

Reloj Windows inicial: leap indicator 3, stratum 0, Local CMOS Clock, sin sincronización previa. Resync sin elevar: acceso denegado. CLOCK_ATTESTATION, NATIVE_TO_UTC_MAPPING, TEMPORAL_CAUSALITY y CAUSAL_AUDIT pendientes. No basta corregir Windows: faltan captura simultánea y mapping externo revisado.

No apareció un paquete de transferencia en la búsqueda acotada a Documents/Downloads y directorios habituales del usuario. No se restauraron ni inventaron datos. Collector bloqueado: continuidad no demostrada. No se crearon tareas ni se iniciaron monitores o captura; faltan cursor/manifiesto y decisión sobre segmento si no se recupera la cohorte.

Launcher y resume son preflight read-only; retornan BLOCKED. El arranque de componentes aún no está aceptado. No confundir preparación de herramientas con estación lista.

FUTURE_EVALUATOR=READY_BUT_GATED; DRIFT_MONITOR=READY (tooling, sin baseline real); SHADOW_MODE=READY_BUT_DISABLED; SHADOW_ORDER_COUNT=0; DEMO_EXECUTOR=READY_BUT_DISABLED_FULL (mocks, sin adaptador de órdenes); DISCOVERY_VALIDATION=BLOCKED; FINAL_TEST=LOCKED; DEMO=DISABLED; LIVE_TRADING=false.

GitHub CLI instalado por winget en alcance de usuario; autenticación pendiente. Implementación publicada por el conector GitHub con fast-forward; CLI sin sesión propia. Supervisión móvil pendiente de configuración oficial y verificación de cuenta, sin ampliar permisos de acceso por métodos alternativos.

OTHER_PROJECT_TOUCHED=NO: no escrituras intencionales fuera del proyecto salvo instalación de herramientas, nueva instancia XM y sus carpetas oficiales. Ningún proyecto ajeno fue modificado. La búsqueda fue acotada, no una auditoría completa de todo el disco.

Compilación comprobada: StochasticBarDecisionResearchEA y FullClockAndTimeSemanticsProbe, ambos 0 errores/0 advertencias, EX5 y hashes presentes. Las plantillas MainKNativeParity y SnapshotCausalProbe no se pueden desplegar directamente: necesitan generación/contexto del controlador. Se retiraron exclusivamente nuestras copias incompletas; los errores iniciales se conservan en logs. MAIN_K no necesita repetición local. C2 parcial para el conjunto completo del controlador, sin declarar C1-C5 PASS.

## Revalidación local posterior

Windows Time fue configurado con inicio automático y permanece Running. NTP reporta leap=0, stratum=5 y fuente time.windows.com. Stripchart: aproximadamente -0.18 a -0.23 s; quorum independiente: reloj local fuera del intervalo de red (adelanto aproximado de 0.14-0.17 s). WINDOWS_CLOCK_SYNC=PASS a nivel del servicio del sistema; no constituye CLOCK_ATTESTATION=PASS ni autoridad causal. Se conserva la evidencia local en outputs/pc_a y clock_repair_*.

Se restauraron exactamente los bytes LF auditados de 219 archivos que Git había convertido a CRLF, solo cuando el hash normalizado coincidía con el sello original. La configuración global de Git permanece intacta; .gitattributes fija LF en nuevos checkouts. CLOUD_SOURCE_HASHES.json no se modifica. Los cambios revisados de PC A se sellan aparte en configs/pc_a_source_hashes.json, con hash del manifiesto original y cobertura completa. El wrapper acepta -SourceManifest explícito y sigue rechazando omisiones y archivos alterados.

Compilación revalidada con bytes actuales del repo e includes: EA StochasticBarDecisionResearchEA y FullClockAndTimeSemanticsProbe, ambos PASS (0 errores, 0 advertencias), EX5 recién generados y hashes. Resumen actualizado: outputs/pc_a/compile_verified.json. Los logs iniciales fallidos de plantillas se conservan como evidencia, sin copias inválidas en Navigator.

XM tiene un formulario de apertura de cuenta pendiente; no se ha enviado, no se han introducido credenciales ni documentos mediante automatización. Cuenta UNKNOWN, API attach timeout -10005; XM_DEMO y US30Cash pendientes. No se ejecuta ningún probe mientras la cuenta sea UNKNOWN/REAL. C1/C3/C4/C5 siguen pendientes y C2 solo cubre los dos artefactos compilados.

Publicación: implementación f99222b0e8fd676c3f5da1901c31d07f9531addb publicada y verificada mediante el conector GitHub autenticado como l6i2, actualización fast-forward con expected SHA y force=false. Checkout actualizado con git fetch y git merge --ff-only, sin conflictos. GitHub CLI permanece sin sesión propia; no bloquea la publicación mediante el conector. Fuente custom PC_A_SOURCE_HASHES revalidada tras publicación. La estación todavía no está aceptada para continuar colección; ver PC_A_HANDOFF.json.


## Verificación XM DEMO y captura preparada

XM DEMO, conexión y US30Cash verificados programáticamente; Market Watch habilitado. Símbolo: digits=2, tick_size=0.01, trade_mode=4; dos barras M5 recientes disponibles. No se reconstruyó historia ni se enviaron órdenes. C1_ENV=PASS. El controlador compila tanto StochasticBarDecisionResearchEA como StochasticIntratradeResearchEA con 0 errores y 0 advertencias. C3/C4/C5 operativos siguen pendientes; no se ejecutó backtest.

Se corrigieron los argumentos con espacios y el retorno de MetaEditor, que puede ser 1 en builds correctos. Se exige log limpio y EX5 nuevo. La espera manual ahora no consume el timeout de la captura: la captura nativa sigue limitada después de arrancar el probe. La prueba de regresión simula una demora humana superior al timeout.

Capturador Windows armado mediante UAC normal, proceso elevado verificado; lectura de Windows Time solamente. Ruta activa en outputs/pc_a/active_clock_capture.json. Analizador de finalización preparado para generar final_report.json automáticamente al completarse la captura. No se mezclan los intentos incompletos anteriores. Fuente sellada actual: configs/pc_a_source_hashes_20261028_v4.json. 246 pruebas: 237 correctas, 9 omitidas por g++ ausente; compileall y verificación estática sin órdenes correctos. Reloj científico, mapping, causalidad y continuidad de cohorte continúan bloqueados a falta de evidencia real.

## Captura local completada

CLOCK_ATTESTATION=PASS, WINDOWS_CLOCK_SYNC=PASS y SIMULTANEOUS_OVERLAP=PASS para el intervalo capturado por cloud_c0c00e95d42c41ee. 50 frames / 150 registros, sin errores y 0 órdenes. Referencias independientes disponibles, Windows UTC dentro de sus intervalos y consultas privilegiadas w32tm válidas. Sellos de audit, fuente, EX5, CSV, markers y snapshot de sesiones revalidados. Resumen publicable: configs/pc_a_clock_attestation_20261028.json; evidencia cruda solo local.

El probe genérico anterior LOCAL_RUN_ID se conserva sin emparejar y no fundamenta este PASS. Navigator PC_A usa alias NTFS al mismo archivo/hash del probe preparado. El capturador y el analizador terminaron. No repetir la captura completada ni sobrescribir sus artefactos.

El servidor observado es XMGlobalSC-MT5 5, US30Cash; +7200 segundos es solo una observación, no certifica mapping ni DST. NATIVE_TO_UTC_MAPPING continúa bloqueado; el preparado fue probado y rechazado con NATIVE_UTC_MAPPING_UNVERIFIED. El snapshot de sesiones pasó estructura, con holidays UNKNOWN y mapping UNVERIFIED, sin activación.

La auditoría causal reprodujo FROZEN_METADATA_NATIVE_TRIGGER_PARITY_NOT_ESTABLISHED. Contraejemplo sintético: metadata congelada 30.6667 frente a cálculo nativo 5.2381; caso plano 50 frente a 100. Los soportes de madurez existentes no son utilizables para afirmar paridad con el trigger nativo. No se modificaron la especificación sellada, la estrategia ni la cohorte. No se leyeron labels, PnL u outcomes. MAIN_K de la estrategia conserva su PASS nativo independiente; el fallo corresponde al contrato de metadata/health congelado.

PC_A_READY=false: mapping externo revisado, contrato causal y continuidad de cohorte siguen pendientes. Collector, scoring, evaluación, shadow, demo executor y órdenes no se activaron. FINAL_TEST=LOCKED, DISCOVERY_VALIDATION=BLOCKED, DEMO=DISABLED, LIVE_TRADING=false.
