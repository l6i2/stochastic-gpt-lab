> Continuación 2026-10-29 (Ecuador): este documento conserva el procedimiento/snapshot inicial. PC A ya completó una captura sellada PASS de alcance limitado. No repetirla como siguiente paso. Estado vigente y comandos: [PROJECT_STATUS.md](PROJECT_STATUS.md) y [LOCAL_PC_FINAL_STEPS.md](LOCAL_PC_FINAL_STEPS.md).

# Clock attestation

`READY_FOR_LOCAL_ATTESTATION`; evidencia Windows/MT5: `LOCAL_REQUIRED`.
Las capturas históricas fallidas permanecen intactas; no son un PASS actual.

Procedimiento único: [CLOCK_ATTESTATION_RUNBOOK.md](CLOCK_ATTESTATION_RUNBOOK.md).
Comando: `powershell -ExecutionPolicy Bypass -File tools/local_finalize.ps1`.
El master `tests/mql5/FullClockAndTimeSemanticsProbe.mq5` combina las observaciones
del ClockAttestationProbeV2 con las sesiones read-only del SessionCalendarProbe.
No modifica ninguno de esos probes históricos. Native compile/run: LOCAL_REQUIRED.

`python/time_semantics.py` es la API pública: conversiones native/tick delegan a
`native_time_mapping.py`; causalidad delega a `temporal_causality.py`. Ecuador usa
America/Guayaquil (UTC-5), Nueva York America/New_York con tzdata 2026.5 congelado.
Server UTC requiere segmentos externos verificados; la vista server no se usa
para causalidad. No se infiere offset por tick age ni se aplica doble conversión.

Reglas: `feature_max_time <= decision_time`, `quote_time <= decision_time`.
Se comparan instantes UTC, incluso en folds DST; un milisegundo futuro se rechaza.
El límite de stale quote existente de cinco segundos es antigüedad máxima,
no tolerancia hacia el futuro. El raw hash no se sustituye por el hash derivado.

El wrapper produce evidencia y reporta bloqueos. No activa mappings, no corrige
relojes y no declara causalidad completa. Véase [auditoría](CLOUD_PREPARATION_AUDIT.md)
y [capturas anteriores](archive/pre_cloud_20261027/CLOCK_ATTESTATION.md).
