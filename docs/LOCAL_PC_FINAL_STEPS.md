# Acciones inevitables en la PC

## STEP 1

Abrir PowerShell en la raíz del checkout existente `stochastic-gpt-lab` y actualizar:

```powershell
git fetch origin
git checkout research/full-pipeline
git pull --ff-only origin research/full-pipeline
```

Resultado: rama actualizada sin conflictos. Si falla, conservar cambios locales;
no hacer reset, rebase ni force push. Resolver el conflicto antes de continuar.

## STEP 2

En esa misma raíz, preparar dependencias y abrir la instalación XM/MT5 habitual,
conectada a la cuenta DEMO existente. No activar trading ni cambiar cuentas.

```powershell
if (-not (Test-Path .venv\Scripts\python.exe)) { py -3.12 -m venv .venv }
.venv\Scripts\python.exe -m pip install -r configs\controller_requirements.txt
powershell -ExecutionPolicy Bypass -File tools\local_finalize.ps1
```

Resultado: carpeta nueva `outputs/local_clock_attestation/cloud_<nonce>/`,
compilación 0 errores/0 warnings y una instrucción Navigator. Si hay varios
terminales, repetir con `-TerminalPath 'RUTA_REAL\terminal64.exe'`; no elegir otra
instalación al azar. Si falla Python/Windows Time/compilación, consultar
`docs/CLOCK_ATTESTATION_RUNBOOK.md` y los logs de esa carpeta; conservar evidencia.

## STEP 3

En MT5, ejecutar exactamente la ruta impresa:

```text
Navigator -> Scripts -> ResearchDiagnostics -> cloud_<nonce> -> FullClockAndTimeSemanticsProbe
```

Conservar RunId por defecto. Esperar unos 50 segundos; el wrapper detecta
`CLOCK_ATTESTATION_END` y continúa sin otra interacción. Revisar la ruta exacta de
`final_report.json` impresa en consola. Si no llega END/captura completa en seis
minutos, conservar el informe y repetir STEP 2 con una ejecución nueva tras
resolver el error. No se reutiliza ni sobrescribe una captura.

## STEP 4

Revisar localmente el informe y aportar la correspondencia native/UTC externa y
la evidencia causal faltante. El probe no certifica el offset del broker ni corrige
la no equivalencia del metadata histórico. No escribir PASS a mano para sortearlo.
Ruta reservada para evidencia privada: `outputs/local_clock_inputs/`.

Con mapping externo revisado y sellado presente, ejecutar desde la raíz:

```powershell
.venv\Scripts\python.exe python\validate_clock_mapping.py --mapping outputs\local_clock_inputs\mapping.json --output outputs\local_clock_inputs\mapping_validation.json
.venv\Scripts\python.exe python\manifest_chain_handoff.py --cohort-root outputs\future_validation_cohort\cohort_20261019 --evidence-dir outputs\local_clock_inputs\manifest_history --output outputs\local_clock_inputs\manifest_chain_report.json
```

Resultado: contrato de mapping validado o BLOCKED; cadena VERIFIED/PARTIAL con
prefijo UNVERIFIABLE_PRE_ANCHOR si faltan bytes. Los reportes son de creación única;
usar otro nombre para una revisión nueva. Si no existe evidencia externa o un
antecesor, mantener el bloqueo: no reconstruir ni inventar historia. La revisión
causal y la revisión del snapshot de sesiones capturado por el master son necesarias antes de cualquier
aceptación operativa; el runtime expira la evidencia vieja y falla cerrado.
MAIN_K ya tiene evidencia PASS y no requiere nueva prueba ni dataset.

Estos cuatro pasos preparan y revisan evidencia; no autorizan evaluación, DEMO,
shadow ni trading. Un reloj correcto por sí solo no elimina los bloqueos restantes.
