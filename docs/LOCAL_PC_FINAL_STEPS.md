# Pasos pendientes en PC A

## STEP 1

En PowerShell, desde la raíz del checkout existente:

```powershell
git fetch origin
git checkout research/full-pipeline
git pull --ff-only origin research/full-pipeline
.venv\Scripts\python.exe python\local_finalize.py --check-handoff
```

Esperado: `HANDOFF_VALID; LOCAL_REQUIRED; no terminal connection`.
El comando verifica la rama, ascendencia y manifest vigente, sin capturar ni
conectar. Si falla un hash, no editar seals ni hacer reset; conservar el error y
revisar cambios locales. El handoff original de octubre 27 fue sustituido por
los avances PC A; no volver a ejecutar su captura de reloj completada.

## STEP 2

En el XM/MT5 habitual, mantener Algo Trading y DLL desactivados. Ejecutar una vez:

```text
Navigator -> Scripts -> ResearchDiagnostics -> PC_A -> StartProspectiveUtcObserver
```

El script ya apareció y fue verificado en Navigator. No requiere reinstalar ni
actualizar el árbol según el último snapshot. Debe recargar solo el observador
US30Cash corregido, sin sustituir otros EAs. `QUEUED_NOT_CERTIFIED` solo confirma
encolado; esperar al menos 15 segundos con feed activo. Si falla o no aparece,
conservar Journal y seguir `docs/PC_A_NAVIGATOR_INSTALL_VERIFIED.md`; no reiniciar
MT5, cambiar permisos ni habilitar trading para solucionarlo.

## STEP 3

Desde la misma raíz de PowerShell:

```powershell
.venv\Scripts\python.exe tools\prospective_utc_station.py --offline
```

Revisar `outputs/pc_a_prospective_utc/status.json`. Con mercado/feed activo se
esperan una sesión nueva, heartbeats recientes y callbacks tick; el máximo estado
es `ACTIVE_CALLBACKS_QUARANTINED`, nunca aceptación UTC o TRAIN. Sin ticks, con
heartbeat vencido o error de cadena: conservar archivos y reportar el estado;
no deduplicar, reparar prefijos ni reconstruir recepción prospectiva con historia.
`last_failure.json` conserva errores de validación. Este comando no consulta NTP,
no arranca EAs y no envía órdenes.

Persisten dependencias externas: evidencia independiente del mismo evento XM,
mapping acotado, incertidumbre/cola y calendario fechado del servidor exacto.
Revisar `docs/PC_A_TIME_PROVENANCE_REQUIREMENTS.md` y las plantillas existentes
antes de aportar evidencia. No contactar al broker automáticamente ni convertir
un offset observado en PASS. La captura activa por sí sola no resuelve estos gates.

Todos los pasos mantienen DISCOVERY_VALIDATION bloqueado, FINAL_TEST locked,
DEMO deshabilitado y LIVE_TRADING=false.
