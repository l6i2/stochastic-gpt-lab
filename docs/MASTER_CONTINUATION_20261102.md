# Continuación de la ejecución maestra — 2 de noviembre de 2026

**Corte: 08:34:46 Ecuador.** Se continúa desde
`3eb5dceb259c8f75769e21ff6fc79913f6029d11`; no se reinicia el estudio, su captura,
sus contadores científicos o sus contratos. Evidencia incremental:
`research/studies/master_continuation_20261102_v1/`.

## Fases realmente ejecutadas y pendientes

| Fase maestra | Resultado real |
|---|---|
| 1. Invariantes | Verificadas por el sello anterior y pins actuales; sin cambios de estrategia o datos |
| 2. Estado real | Revisado de nuevo por evidencia material: los antiguos procesos ya no existían; se recuperó la pila autorizada |
| 3. 259/284 | Contraste previo conservado sin nuevas consultas; omisión relativa demostrada, causa exacta por evento sin traza |
| 4. Captura real | Quotes nuevos y consumo real verificados; no se certifica captura completa ni avance de señales |
| 5. Pipeline | Implementación conservada y progreso diagnóstico permitido; contexto continuo/features/señales reales todavía incompletos |
| 6. Temporalidad | Diagnóstico nativo permitido; procedencia UTC externa y obligaciones del contrato siguen pendientes |
| 7. Ecuador/DST | Implementado y conservado; no se rediseñó ni desplazaron timestamps |
| 8. Membership/exposure | Prefijo propio verificable; roles históricos desconocidos no se inventan ni cierran |
| 9. Madurez/dashboard | Monitor automático operativo; datos y madurez pendientes |
| 10. Estrategia histórica | Informe autorizado anterior completo dentro de su alcance; no se repitió scoring ni investigación |
| 11. Entrenamiento reproducible | Runner, protocolo, whitelist y presupuesto preparados; sin integración real de dataset admitido ni fit |
| 12. Gate único | Implementado, vigente y BLOCKED; sin solicitud prematura |
| 13. Recuperación | Pila reanudada y defecto de supervisión del guardian reparado; alcance y pruebas abajo |
| 14. Tests | 40 regresiones pertinentes PASS; suite completa previa retenida, no repetida |
| 15. Publicación | Commit/push normal y verificación final de HEAD identifican esta entrega |
| 16. Reporte | Este delta único y su índice de fases |
| 17. Autonomía | Tareas seguras completadas; monitorización continúa, sin eludir los bloqueos científicos |

Implementar o preparar una fase técnica **no significa** completar su evidencia
científica. Por eso `phase_audit.json` y `summary.json` distinguen preparación
terminada de validación de datos/ejecución real pendiente.

## Reparación necesaria, sin repetir infraestructura aprobada

Al empezar, el dashboard y guardian conservaban reportes de la noche anterior;
los PIDs antiguos de XM, guardian, worker y reporter no estaban activos. La
primera comprobación dio XM_NOT_RUNNING y HEARTBEAT_OVERDUE. No se presentaron
esos reportes antiguos como una captura actual ni se atribuyó el cierre a una
causa no demostrada.

Se inició el **guardian ya existente**, que recuperó los componentes autorizados.
XM volvió a estar conectado en DEMO, con US30Cash e identidad de carpeta correcta.
Los reinicios del observador quedaron en segmentos nuevos del mismo capture ID;
el prefijo original y sus checkpoints fueron preservados. No se descargaron
ticks para rellenar la interrupción ni se seleccionó un nuevo inicio científico.

La ausencia del guardian reveló una carencia concreta: el arranque HKCU al
iniciar sesión no reanuda un guardian desaparecido durante la misma sesión.
Se añadió solamente `StochasticGPTLab_PC_A_RecoveryGuardian_v1`, tarea del usuario
con permisos **Limited/Interactive**, al logon y cada cinco minutos. Ejecuta el
mismo script existente; mutex y MultipleInstances impiden duplicación. No cambia
políticas globales de Windows, energía, red o batería ni tareas del otro proyecto.
Necesita una sesión del usuario; no se promete operación headless sin logon.

La prueba mediante Task Scheduler relanzó el guardian de PID 8672 a 25456.
XM 27800 y worker 8836 conservaron sus PIDs y continuaron trabajando. Se probó
el mecanismo de ejecución/relaunch y se verificó la programación periódica;
no se presenta como una prueba de reinicio físico ni de un futuro fallo natural.
La recuperación tras reboot físico sigue pendiente de un reboot natural.

Inspección/reinstalación idempotente: `tools/ensure_research_guardian.ps1` /
`tools/ensure_research_guardian.ps1 -Install`. Restauración de esta incorporación:

```powershell
Unregister-ScheduledTask -TaskName 'StochasticGPTLab_PC_A_RecoveryGuardian_v1' -Confirm:$false
```

## Avance real cuantificado

| Evidencia | Resultado al corte |
|---|---:|
| Callbacks de quote procesados, total | 6.011 |
| Nuevos frente al checkpoint maestro publicado (4.739) | +1.272 |
| Nuevos durante la observación posterior a recuperación | +671 |
| M5 nuevos frente al corte maestro | 0; total conservado: 2 |
| M1 total | 34 |
| Prefijos reales de features nuevos | 0; total conservado: 2, incompletos |
| BUY / SELL nuevos y totales | 0 / 0 |

Son callbacks/snapshots, no una afirmación de eventos únicos exhaustivos del
broker. `runtime.json` conserva ambas muestras, identidad XM y progreso de
consumo; `prefix_receipt.json` verifica los bytes y cadenas realmente procesados.
Los dos M5 y prefijos de features anteriores no se vuelven a contar como nuevos.

No hay un bloqueo técnico global que descarte automáticamente toda barra futura
por la ventana antigua 259/284. El procesador sigue contrastando intervalos y
segmentos posteriores. La nueva regresión crea una ventana antigua inválida y
un segmento posterior válido: este último genera barra y feature, conserva
contexto propio y mantiene admisión/soporte científico en cero. No se cambia
el flag del protocolo ni se transforma una selección de ventanas en 800 señales
consecutivas. Los rechazos reales actuales siguen impidiendo acumular warmup.

## Discrepancia conservada y bloqueos científicos

La evidencia sellada anterior demuestra 259 snapshots BID frente a 284 payloads
BID de referencia: faltan 25, no hay BID sobrantes ni duplicados idénticos. Los
diez snapshots sin flag BID explican 269 quotes frente a 259 BID, **no** la
diferencia 259/284. No es un simple cambio de definición entre los dos conteos
BID ni se encontró un error de aritmética del agregador que la elimine.

Es una omisión relativa a la referencia. La coalescencia documentada de OnTick
y el muestreo del último quote son mecanismos compatibles; no hay IDs únicos
del broker o traza de scheduler que permitan atribuir cada omisión a una causa
exacta. No se repitieron consultas sobre la misma ventana ni se presentó una
optimización de I/O no demostrada como una reparación. La ventana permanece
en cuarentena. Véase el contraste sellado en el expediente maestro anterior.

El paquete técnico/protocolo/whitelist/runner ya está preparado. No están
completos el dataset independiente admitido, cobertura, membership científico,
semillas y causalidad conforme al contrato. No se genera otra solicitud de
autorización ni se ejecuta entrenamiento. La recuperación legacy permanece
cerrada salvo una fuente nueva; su ausencia no frena la captura diagnóstica.

**Dependientes de datos futuros:** 350 M5 propios continuos, 800 señales base
consecutivas, 100 barras posteriores y soporte 200/80/80 con los folds requeridos.
El dashboard existente los supervisa sin repetir intentos sobre datos iguales.

**No dependientes solo de esperar:** cobertura de ventanas con omisiones,
membership/roles protegidos desconocidos, procedencia temporal y reglas del
contrato aplicable, y autorización específica. La espera no rellena pérdidas,
demuestra UTC de generación ni cambia un contrato congelado. Cualquier regla
prospectiva diferente requiere decisión científica explícita separada.

40 tests pertinentes PASS, más comprobaciones reales de tarea, recuperación y
prefijos. Se conserva el resultado anterior de 498 tests (489 PASS, 9 SKIPPED)
sin repetirlo. No hubo nuevos probes MT5, lectura protegida, entrenamiento,
scoring, cambios de estrategia, timestamps, cohortes o datos originales.

NEXT_STATE: captura restaurada y supervisada, segmentos diagnósticos válidos en
cuarentena, monitor/gate activos. Sin intervención manual inmediata.
DISCOVERY_VALIDATION=BLOCKED; HISTORICAL_HOLDOUT=LOCKED; FINAL_TEST=LOCKED;
DEMO=DISABLED; LIVE_TRADING=false; CAUSAL_AUDIT=FAIL; TRAINING_READINESS=BLOCKED.
