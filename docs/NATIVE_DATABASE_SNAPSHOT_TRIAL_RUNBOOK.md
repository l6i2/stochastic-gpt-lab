# Productor separado de snapshots MT5 — PC A

Autorización: `research/studies/native_database_producer_trial_20261102_v1/authorization.json`.
Solo ensayo observacional en cuarentena; sin admisión, entrenamiento, scoring u órdenes.
La captura anterior, sus contratos y su productor no se modifican.

## Implementación y procedencia

`tools/native_database_snapshots.py` utiliza el paquete oficial MetaTrader5 de Python
con la instancia XM ya identificada. No instala otro EA ni modifica gráficos/perfiles.
Compilación Python comprobada; compilación MQL5 no aplicable. La identidad DEMO,
servidor, carpeta, chart BID y grid se comprueban antes/después de consultar.

ID propio `dbsnap_a5b5b6a8d777455d9cc63c8ca8690942`; carpeta exclusiva
`outputs/native_database_snapshots_v1/<ID>/`. Manifest de origen inmutable y pins de
código versionados. La primera versión del fuente se conserva para reproducibilidad.
Tres M1 iniciales carecen de grid explícito por snapshot: se conservan en cuarentena,
se identifican como vintage inicial y el auditor no las presenta como recalculadas.
La versión activa añade grid y hash del pin a cada consulta.

Tipos de registro distintos:

- `LIVE_LATEST_STATE_POLL`: lectura de la última cotización, acotada por relojes
  locales de inicio/fin; no es recepción del evento original ni secuencia exhaustiva.
- `DATABASE_QUERY_OBSERVATION`: contenido íntegro de CopyTicksRange dentro de
  [inicio,fin), límites de consulta, primera observación/read_end, boot y monotónico.
  MT5 puede descargar datos; la recepción original de cada tick es desconocida.
- `DATABASE_SNAPSHOT_PAIR`: dos lecturas de una ventana cerrada con hashes iguales,
  secuencia completa conservada y paridad exacta con CopyRates M1/M5.
  Es `VERIFIED_DATABASE_VIEW_ONLY`, no certificación UTC ni captura callback.

No se usa TimeTradeServer como reloj independiente. Horas XM permanecen como
coordenadas nativas; no se desplazan. Reloj de Windows no auto-certifica UTC.

## Cobertura, continuidad y recursos

Poll nominal2s. Rangos cerrados M1/M5; límite20.000 filas/1.600.000bytes por consulta.
Sin truncación, ordenamiento correctivo, deduplicación por valores ni eliminación
de ticks idénticos dentro del mismo milisegundo. Una segunda lectura distinta o
paridad incorrecta rechaza la ventana. Los datos recuperados nunca se convierten
en prueba de recepción en vivo.

Arranque/reinicio/desconexión/cambio de PID/boot/regresión de reloj/gap de observación
crean un corte nuevo y reinician la continuidad candidata. El primer bucket parcial
no cuenta. No se consulta el cursor viejo para rellenar pérdidas. El criterio de10s
es el umbral de salud de dos timers5s ya existentes: no es tolerancia de precios,
timestamps o aceptación científica. Los gaps nativos de minutos se segmentan
conservadoramente sin inventar calendario o causa de sesión.

SQLite WAL/FULL: eventos, estado y checkpoint ligado por hash se confirman juntos;
triggers impiden editar/borrar registros. Un lock impide productores simultáneos.
Un reinicio de proceso conserva datos/head/counters totales y abre época nueva;
no hereda continuidad para reparar el hueco. El contador `consecutive_m5_database_view`
es exclusivo del ensayo. `scientific_warmup=0` siempre; ningún contador modifica el
warmup350 ni el protocolo anterior.

## Operación autónoma

Windows rechazó crear la tarea nueva (acceso denegado); no se alteraron tareas previas.
Se verificó un arranque alternativo en HKCU Run, solo de este usuario, y un watchdog
independiente con mutex y reinicio del productor. Requiere logon; no prueba reboot
físico. El watchdog produce una auditoría independiente cuando aumenta el contador
M5, sin repetirla sobre el mismo progreso. La interrupción real de Windows es un
gap, no una ocasión para descargar y rellenar la captura.

Estado pequeño: `outputs/native_database_snapshots_v1/<ID>/status.json`.
Salud watchdog: `outputs/native_database_snapshots_v1/watchdog_status.json`.
Auditorías automáticas: `outputs/native_database_snapshots_v1/monitor_reports/`.

Verificación manual opcional, sin iniciar otro productor:

```
.venv\Scripts\python.exe tools/audit_native_database_trial.py --out outputs/native_database_snapshots_v1/audit_NUEVO_ID
```

Reinstalación/reanudación idempotente del watchdog:

```
powershell -NoProfile -File tools/install_native_database_watchdog.ps1
```

Deshabilitar únicamente este ensayo y quitar su arranque; conserva todos los datos:

```
powershell -NoProfile -File tools/install_native_database_watchdog.ps1 -Remove
```

No modifica políticas energéticas/batería. Las suspensiones observadas se registran
como interrupciones. La operación ininterrumpida exige que Windows permanezca
despierto y XM conectado; no se promete350 barras ni se relajan criterios por ello.

La medición de salud distingue silencio **entre** operaciones de los intervalos de
lectura de API registrados. Un bloqueo de identidad de8,15s reveló una falsa
clasificación de gap del prototipo; se corrigió midiendo desde el fin de la operación
anterior hasta el inicio de la siguiente, conservando el umbral10s. Windows Kernel
Power507 con `SleepEntered=true` se consulta mediante EvtQuery; una suspensión nueva
fuerza corte aun si ocurre durante una consulta. No se utiliza ese intervalo de API
como prueba de recepción de ticks en vivo. También se evita enumerar todos los
procesos cada2s, sin omitir identidad/DEMO/grid ni cambiar el código anterior.

Hubo autorización adicional explícita para una solicitud temporal de energía de
máximo20min: `tools/temporary_snapshot_trial_awake.py`. No se instala en el arranque;
libera la solicitud al salir o vencer el plazo, sin modificar el perfil. La autorización
y liberación real están en las evidencias del ensayo. No se solicita energía fuera
de ese plazo, ni se impide un cierre de tapa/suspensión manual del usuario.

DISCOVERY_VALIDATION=BLOCKED; HISTORICAL_HOLDOUT/FINAL_TEST=LOCKED;
DEMO=DISABLED; LIVE_TRADING=false. Todas las salidas permanecen en cuarentena.
