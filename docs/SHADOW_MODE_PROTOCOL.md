# Shadow — READY_BUT_DISABLED

`SHADOW_ORDER_COUNT=0`, `DEMO=DISABLED`, `LIVE_TRADING=false`.
`python/shadow_mode.py` tiene únicamente decisiones hipotéticas, logging de
features/hash, spread, latencia y un adaptador MT5 con allowlist read-only.

Por defecto está deshabilitado. Antes de invocar la política exige candidato,
símbolo US30Cash, UTC explícito, causalidad, quote fresco y runtime session guard.
Desconexión, estado market desconocido, vacaciones desconocidas, calendario/reloj
no reconciliado y datos futuros/stale impiden la decisión. No hay reconexión que
active decisiones sin observaciones nuevas válidas.

Una reserva SQLite durable por signal_id ocurre antes de llamar a la política.
Reinicio, crash entre reserva y logging o señal duplicada impiden repetirla.
El JSONL se escribe con flush/fsync; un fallo de disco propaga error y no permite
órdenes. Conservar juntos JSONL y su `.sqlite3`; no reiniciar el estado borrándolos.
Cada registro fuerza orders_sent=0 y order_count=0. No existe broker order API.
Las pruebas son sintéticas; no se activó shadow ni se leyó la cohorte real.

[Estado actual](PROJECT_STATUS.md) · [protocolo anterior](archive/pre_cloud_20261027/SHADOW_MODE_PROTOCOL.md).
