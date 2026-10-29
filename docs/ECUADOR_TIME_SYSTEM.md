# Sistema horario unificado: Ecuador primero

`python/time_semantics.py` es la API pública central. Reutiliza el mapping nativo y tzdata 2026.5 congelada; no sustituye los contratos causales. America/Guayaquil es la vista principal. America/New_York se convierte con reglas históricas IANA, sin fórmulas DST fijas.

## Uso

Desde la raíz: `.venv\Scripts\python.exe tools/time_report.py` genera `outputs/pc_a/time_display/time_report.html` y JSON. `--date YYYY-MM-DD` selecciona la fecha de referencia. La fecha predeterminada se calcula en Ecuador. El reporte muestra Ecuador, Nueva York, XM y UTC simultáneamente; XM queda no verificado donde falta correspondencia demostrada.

- `instant_display(datetime_aware, basis=...)`: recepción local o referencia, con procedencia explícita. Una recepción convertida no certifica un evento del broker.
- `event_display(NativeTimestamp, mapping)`: operaciones, señales y barras. Conserva exactamente el timestamp y hash originales. Solo llama al normalizador existente con mapping verificado, servidor/símbolo coincidentes y un único intervalo cubierto. Sin prueba, devuelve QUARANTINED y las horas de evento convertidas vacías; muestra el número original XM sin reinterpretarlo.
- `chart_points(values, mapping)`: adaptador de etiquetas para gráficos y futuras evaluaciones. Mantiene orden y multiplicidad; conserva `utc_msc` como clave causal, nunca ordena por una etiqueta local y nunca se usa para decidir admisión científica. No lee datasets ni cambia gráficos originales.
- `new_york_wall_to_utc`: rechaza horas inexistentes y exige fold para la hora repetida de otoño. `new_york_dst_changes(year)` encuentra las transiciones históricas exactas en la base congelada.
- `new_york_reference_session(date)`: referencia nominal NYSE 09:30–16:00 ET en Ecuador. No es calendario efectivo ni permiso de ejecución: fines de semana, feriados y cierres anticipados se etiquetan como no evaluados. No modifica ventanas de entrada.

El offset XM mostrado por periodo proviene exclusivamente de los segmentos certificados existentes. `native_utc_offset_seconds` y `server_utc_offset_seconds` pueden ser distintos; nunca se deduce uno del otro. Un periodo no cubierto, identidad diferente o solapamiento permanece sin conversión. Hoy no hay periodos autorizados para el servidor actual, por lo que XM_SERVER_MAPPING=PARTIAL, no PASS.

## Integraciones

El supervisor `tools/research_station.py` añade vistas de recepción/activación/última captura y referencia NY a su reporte, sin cambiar `pc_a_raw_archive.py`, cursors, CSV, manifest ni cadena de hashes. No hace falta reiniciar MT5. `python/session_runtime_status.py` muestra recepción y evento por separado manteniendo sus rechazos de ejecución. `controller/progress.py` añade una vista derivada del último timestamp de señal; una identidad de servidor ausente sigue bloqueada. No abre nuevos bloques ni cambia señales. Para futuras evaluaciones, el adaptador público trabaja sobre timestamps ya admitidos y conserva los IDs/hash causales originales; no se ejecutó entrenamiento ni evaluación protegida.

Los gráficos nativos del terminal MT5 siguen usando etiquetas originales del servidor. La presentación ecuatoriana se implementa en las vistas del proyecto y adaptadores de gráficos, sin parchear el terminal ni alterar velas. Los reportes/datasets congelados conservan sus archivos y se complementan con nuevas vistas, no se reescriben.

## Referencias y alcance

La sesión nominal [NYSE](https://www.nyse.com/markets/hours-calendars) es 09:30–16:00 ET. En Ecuador equivale normalmente a 08:30–15:00 con EDT y 09:30–16:00 con EST. Sus feriados y cierres anticipados impiden usar esa referencia como calendario efectivo. [XM](https://www.xm.com/equity-indices) remite al acceso de cuenta para horarios. Se reutilizan observaciones nativas selladas del servidor XMGlobalSC-MT5 5; no prueban excepciones históricas ni permiten convertir sus horas semanales a Ecuador sin mapping certificado. El reporte mantiene sus etiquetas originales.

49 tests afectados PASS: conversiones invierno/verano; DST 2006/2026; gap/fold; límites e identidad del mapping; preservación de originales, multiplicidad y hash causal; bloqueo sin correspondencia; contratos causales y runtime existentes. Comprobación estática sin órdenes PASS. Todos los sellos de fuentes v10 fuera de cuatro integraciones de presentación y la referencia versionada del certificador permanecen iguales. La auditoría de datos real sigue FAIL por procedencia UTC/calendario, independientemente de que las pruebas de software pasen.

DISCOVERY_VALIDATION=BLOCKED, FINAL_TEST=LOCKED, DEMO=DISABLED, LIVE_TRADING=false. No se activa cohorte, metadata preparada ni entrenamiento.
