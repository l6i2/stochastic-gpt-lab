# Recuperación PC A

Desde PowerShell:

```powershell
Set-Location "$env:USERPROFILE\Documents\Codex\stochastic-gpt-lab-full-pipeline"
powershell -NoProfile -File tools/start_research_station.ps1
```

Después de reiniciar:

```powershell
powershell -NoProfile -File tools/resume_research_station.ps1
```

Ambos comandos son preflight read-only y fallan cerrado; aún no arrancan collector ni health monitor. No modifican checkpoints ni crean datos. Estado: outputs/pc_a/station_status.json.

Para continuar la preparación: corregir Windows Time mediante UAC normal, verificar XM DEMO y US30Cash, completar la compilación local y pruebas del controlador, ejecutar tools/local_finalize.ps1 para la captura simultánea nueva. No reutilizar evidencia de reloj de la otra PC. No cambiar PASS a mano; revisar mapping externo y causalidad según docs/LOCAL_PC_FINAL_STEPS.md.

Antes de collector recuperar paquete/manifiesto/cursor con SHA-256. Si no se demuestra continuidad, mantener BLOCKED y documentar decisión científica del nuevo segmento. No backfill, scoring, labels ni outcomes.

No registrar credenciales en archivos o chats. GitHub login debe completarse en el navegador oficial con almacenamiento seguro de credenciales del sistema; nunca habilitar almacenamiento en texto plano. Configuración móvil: interfaz oficial Settings > Connections > Control this Mac or PC; pendiente de autorización y verificación. Documentación: https://learn.chatgpt.com/docs/remote-connections.

No abrir FINAL_TEST, no activar DEMO, shadow, evaluator u órdenes. No crear tarea de inicio hasta aceptar el entorno y continuidad.

Para esta migración, después de verificar XM DEMO, ejecutar la captura con el sello específico de PC A:

```powershell
powershell -NoProfile -File tools/local_finalize.ps1 -SourceManifest configs/pc_a_source_hashes_20261028_v4.json
```

Comprobar el sello sin conectar MT5:

```powershell
.venv\Scripts\python.exe python/local_finalize.py --check-handoff --source-manifest configs/pc_a_source_hashes_20261028_v4.json
```

Cada cambio posterior en código sellado exige revisión y un manifiesto nuevo. El sello es integridad de fuentes; no certifica mapping, continuidad, causalidad, DEMO ni permisos de evaluación.

Recompilar exclusivamente los dos artefactos necesarios de esta PC sin ejecutar probes:

```powershell
.venv\Scripts\python.exe tools/deploy_pc_a_diagnostics.py
```

Windows Time quedó en inicio automático. Su configuración anterior se conserva en outputs/pc_a/clock_repair_*/service_before.json. No inferir PASS de attestación de una resincronización exitosa.


El capturador actual espera sin caducidad antes del inicio nativo, con caché acotada. No repitas el script si ya creó archivos: conserva la evidencia y prepara un nonce nuevo. El proceso de análisis espera capture.json y verifica el sello antes de procesarlo; no cambia gates. Ruta de captura activa: outputs/pc_a/active_clock_capture.json. Después de reinicio, no supongas que estos procesos sobrevivieron; exige una captura nueva si no existe una completa.

La captura de PC A ya terminó y fue auditada. No repetir el probe para resolver mapping/metadata: son bloqueos distintos. Para revalidar los bytes locales sin ejecutar MT5 de nuevo, usar --resume-folder con la carpeta de outputs/pc_a/active_clock_capture.json y --source-manifest configs/pc_a_source_hashes_20261028_v4.json; el wrapper creará otro informe sin sobrescribir el original.

Antes de colección hacen falta un contrato externo revisado native/UTC con segmentos acotados y evidencia SHA-256, y resolver la no equivalencia del metadata congelado sin reescribir la cohorte. La captura actual no autoriza extender offsets a otras fechas o servidores ni rellenar gaps. Solicitud para recuperar evidencia: docs/PC_A_EXTERNAL_EVIDENCE_REQUEST.md.
