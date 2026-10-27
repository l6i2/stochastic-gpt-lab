# Clock attestation — ejecución local read-only

Estado Cloud: `READY_FOR_LOCAL_ATTESTATION`. Windows/MT5 nativo: `LOCAL_REQUIRED`.
Captura nominal: 50 segundos, 50 frames, 150 lecturas; preparación y revisión usuales
5–10 minutos si Windows ya está sincronizado y XM conectado. Reparar el servicio de
hora u obtener correspondencia certificada del broker puede requerir más tiempo.
No se promete cerrar esas dependencias en diez minutos.

Desde la raíz del checkout en Windows, con XM abierto en una cuenta DEMO existente:

```powershell
powershell -ExecutionPolicy Bypass -File tools/local_finalize.ps1
```

El comando lee `outputs/status/CLOUD_HANDOFF.json`, exige la rama y ascendencia Git correctas,
verifica los hashes publicados de código/documentación,
identifica el único `terminal64.exe` abierto (o acepta `-TerminalPath`), verifica
XM conectado y DEMO mediante lecturas, y usa el MetaEditor de esa instalación.
No cambia cuenta, reloj, Task Scheduler, AutoTrading ni configuraciones del terminal.
Consulta `w32tm /query /source`, `/status`, `/configuration` y un stripchart NTP;
la referencia independiente requiere quorum NTP y corroboración HTTPS/TLS.

Genera un directorio nuevo `outputs/local_clock_attestation/cloud_<nonce>/` y
compila el template `tests/mql5/FullClockAndTimeSemanticsProbe.mq5` con un RunId nuevo.
Exige un EX5 nuevo y `0 errors, 0 warnings`; source, template y EX5 quedan hasheados.
La compilación y ejecución MT5 no se han probado en Cloud.

Cuando la captura Windows está armada imprime UNA instrucción:

```text
Navigator -> Scripts -> ResearchDiagnostics -> cloud_<nonce> -> FullClockAndTimeSemanticsProbe
```

Ejecutar ese script en un gráfico, conservar su RunId por defecto y aceptar.
No se requiere presionar Enter en la consola. El watcher continúa automáticamente.
Debe estar disponible el feed de `US30Cash`, `EURUSD` y `USDCHF`; `tick_ok=0` falla.
No habilitar DLLs ni trading. El script no contiene API de órdenes.

Archivos en el Data Folder de esa misma instalación:

- `MQL5/Scripts/ResearchDiagnostics/cloud_<nonce>/FullClockAndTimeSemanticsProbe.mq5` y `.ex5`.
- `MQL5/Files/cloud_<nonce>_native.csv` y `cloud_<nonce>_markers.txt`.

Archivos locales en el directorio de evidencia:

- `run.json`, `compile.log`, `watcher.log`, `ready.json`.
- `capture.json` (o `partial_capture.json` ante timeout).
- `native.csv`, `markers.txt`, `hashes.json`, `audit.json`, `audit.json.sha256`.
- `analysis.json`, `final_report.json`.

El wrapper llama al parser `python/analyze_clock_attestation.py`. Para una captura
completa todavía no analizada, el comando equivalente es:

```powershell
.venv\Scripts\python.exe python\analyze_clock_attestation.py --folder outputs\local_clock_attestation\cloud_<nonce>
```

`simultaneous_overlap=PASS` exige 50 frames completos, orden monotónico, bracket
Windows antes/después, unidades coherentes y BEGIN/END de este RunId.
`clock_attestation=PASS` adicionalmente exige reloj Windows dentro de los intervalos
independientes y consultas w32tm exitosas. No se introduce tolerancia causal futura.
El audit anterior conserva sus campos originales; `analysis.json` distingue la
aceptación de captura del mapping operativo.

**Mapping separado:** observar `TimeTradeServer-TimeGMT` o un tick antiguo no prueba
un offset. Cuando exista evidencia externa revisada, suministrar el contrato sellado
compatible con `native_time_mapping.load_mapping`:

```powershell
.venv\Scripts\python.exe python\validate_clock_mapping.py --mapping outputs\local_clock_inputs\mapping.json --output outputs\local_clock_inputs\mapping_validation.json
```

El JSON necesita status PASS, identidad del servidor/símbolos, segmentos acotados,
`evidence_file`, `evidence_sha256` y sidecar `.sha256`. Su evidencia necesita
`clock_attestation=PASS`, `native_to_utc_mapping=PASS`, al menos 50 `complete_frames`
y los mismos `authorized_segments`. El validador comprueba bytes y contrato; no
convierte una afirmación manual en autenticidad certificada. Resultado máximo:
`EXTERNAL_CONTRACT_VALIDATED`, `external_authenticity=MANUAL_REVIEW_REQUIRED`.
El preparado `configs/native_time_mapping_v1.prepared.json` debe seguir siendo rechazado.
No extender los segmentos a fechas/DST no observados; no modificar datos históricos.

Si falla el reloj: revisar `w32_before/w32_after`, servicio Windows Time y ajustes
normales de Windows; sincronizar localmente y repetir con nonce nuevo. Si falla
compilación o no llega END en seis minutos: conservar logs, resolver el problema y
repetir. Nunca borrar ni reciclar evidencias anteriores. La política corporativa
puede prohibir PowerShell; alternativa:
`.venv\Scripts\python.exe python\local_finalize.py`.

El wrapper devuelve código 2 mientras quede mapping/causalidad por revisar, incluso
con captura PASS; no es permiso de evaluación ni de trading. `FINAL_TEST=LOCKED`,
`DISCOVERY_VALIDATION=BLOCKED`, `DEMO=DISABLED`, `LIVE_TRADING=false` siempre.

El master también escribe `MQL5/Files/cloud_<nonce>_sessions.txt`. El parser
`python/session_evidence_parser.py` crea `session_review_<nonce>/session_observations.json`
y su seal: estructura validada, vacaciones UNKNOWN, mapping UNVERIFIED, sin activar.
El informe final incorpora el diagnóstico causal sintético y la cadena de manifests
local, si existe; nunca abre raw, labels ni outcomes.

Para revalidar una captura completa conservada, sin volver a ejecutar MT5:

```powershell
powershell -ExecutionPolicy Bypass -File tools/local_finalize.ps1 -ResumeFolder outputs/local_clock_attestation/cloud_<nonce> -Mapping outputs/local_clock_inputs/mapping.json
```

Se verifican los hashes originales y se genera otro informe sin sobrescribir el
anterior. Una captura parcial exige una ejecución nueva; no se completa con datos
viejos ni se amplía un segmento de mapping sin evidencia.
