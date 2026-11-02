# Ensayo real del productor alternativo — PC A

Corte Ecuador: 2026-11-02T15:50:32.565505-05:00. Capture ID `dbsnap_a5b5b6a8d777455d9cc63c8ca8690942`.
Instalación, ejecución y compilación Python verificadas. Usa la [API oficial Python
MT5](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py), sin instalar
otro EA ni cambiar gráficos/perfiles anteriores. MQL5/MetaEditor no son necesarios.

## Resultado observado

M1 verificadas: **31**, de ellas **28**
recalculadas por el auditor con grid explícito. M5 verificadas: **2**;
rechazadas: **0**; consecutivas actuales/máximo:
**2/2**. Ticks por primera consulta
M5: [991, 1046]. No se suman lecturas repetidas ni ventanas M1/M5
solapadas como ticks únicos recibidos.350 barras y madurez científica no demostradas.
Warmup científico admitido/incremento de captura anterior: **0/0**.

Cada snapshot conserva todos sus campos, primera observación/read_start/read_end,
boot, contador monotónico, procedencia y versión/grid. Dos consultas iguales y
CopyRates deben coincidir exactamente en secuencia, OHLC y volumen BID para obtener
VERIFIED_DATABASE_VIEW_ONLY. No se afirma recepción original: MT5 puede sincronizar
datos con el servidor. Las cotizaciones leídas en vivo son un tipo de registro
distinto de los snapshots de base. No se modifican timestamps ni se usa TimeTradeServer
como fuente independiente. La hora física de generación continúa sin certificar.

Auditoría SQLite independiente: **2667 registros** encadenados,
head `4ceeeb55daa4105770d64b8036dd7a4bf47d4bc42ca1a29c8dc16001f85c6ba6`; checkpoints/counters recomputados, no solo proceso vivo.
No se publican arrays de ticks, credenciales o datos de cuenta. Tres M1 de la primera
vintage sin grid explícito se conservan en cuarentena y se identifican como no
recalculadas estrictamente; fuentes/pins de cada versión preservados sin reescribir
el manifest original.

## Interrupciones y correcciones

Se ensayó una terminación controlada únicamente del productor nuevo: watchdog
relanzó el proceso; mantuvo head/datos y abrió corte futuro, sin backfill. Un arranque
duplicado fue rechazado por lock. Windows registró suspensiones reales en batería,
incluida11min17s y otra de casi3min; se excluyeron los periodos perdidos. El detector
actual consulta SleepEntered=true en el log System y comprueba cambios antes de
aceptar ventanas. No atribuye un cierre normal del mercado sin evidencia.

El prototipo mostró otro defecto real: una llamada de identidad a MT5 duró8,15s y
se sumaba incorrectamente al silencio entre polls. Se corrigió delimitando el tiempo
entre fin de operación/inicio de siguiente, sin aumentar el umbral10s. Las lecturas
API mantienen sus intervalos explícitos; un evento real de suspensión durante
consulta invalida la ventana. Se conservan los rechazos y las versiones previas.
También se eliminó el barrido global de procesos en cada poll manteniendo identidad,
DEMO, servidor, carpeta y grid antes/después de consultar. No se modificó el productor
original ni se pretendió corregir datos históricos.

## Automatización y límites

Task Scheduler rechazó la tarea nueva por permisos; se instaló/verificó un arranque
por usuario HKCU Run y watchdog separado con mutex. El servicio anterior y sus tareas
permanecen intactos. Una auditoría independiente se dispara al aumentar M5 y no se
repite sobre el mismo contador. Prueba física de reboot pendiente de reinicio natural.
Operación requiere usuario conectado, PC despierta y XM disponible.

Hubo autorización adicional expresa de máximo20min para [SetThreadExecutionState](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate).
La solicitud fue **liberada** a 2026-11-02T20:39:18.723708+00:00; duración registrada
1200.125s (incluye planificación del cierre). Ningún perfil
energético o valor de batería fue modificado; no hay inhibición permanente.

34 tests PASS, compileall, sintaxis PowerShell y diff check correctos. Incluyen
límites, errores de consulta, pérdida/duplicados, multiplicidad mismo milisegundo,
persistencia, reinicio, identidad REAL/UNKNOWN, lecturas lentas, suspensión y
liberación de energía. Estrés sintético20.000filas; no se saturó MT5 real.
Memoria al corte: 11.65MiB residente/
253.53MiB privada. Ver runbook y JSON del ensayo.

Se corrigió además el monitor Windows PowerShell: ahora verifica el recibo de
finalización y los hashes de los tres artefactos de auditoría, sin depender del
código de salida del launcher. Se usa SHA256 de .NET porque Get-FileHash no estaba
disponible en ese host. La ejecución automática y su checkpoint fueron comprobados.

## Conclusión y gobernanza

El resultado mide exclusivamente vistas verificables de la base del terminal;
no garantiza350 M5, completitud de eventos del broker, UTC físico o admisión.
Quedan pendientes continuidad larga, estabilidad frente a revisiones posteriores,
calendario, membresía/independencia y causalidad aplicable bajo metodología autorizada.
Este ensayo diagnóstico está registrado como expuesto; no se convierte por defecto
en futuro TRAIN. Las sesiones/gaps no se reinterpretan para acelerar madurez.

La captura y supervisión nuevas continúan automáticamente y en cuarentena. Fuentes,
contratos, productor anterior y todos los hashes v46 verificados intactos. No acceso
a conjuntos protegidos, scoring, entrenamiento, DEMO ni órdenes. CAUSAL_AUDIT global
FAIL; DISCOVERY_VALIDATION=BLOCKED; HISTORICAL_HOLDOUT/FINAL_TEST=LOCKED;
LIVE_TRADING=false. No se requiere un paso manual operativo ahora.
