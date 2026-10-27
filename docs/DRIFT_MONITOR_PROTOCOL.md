# Drift monitor — READY (tooling)

Sin baseline real ajustado, sin stream conectado, sin comparación de cohorte.
READY significa productor compartido y comparador probados con fixtures. No es
validación de distribución real ni activación automática.

`python/drift_feature_stream.py` es el único productor para baseline TRAIN y
stream futuro. Ambos consumen el mismo esquema de barras cerradas, quote
normalizado y decision_time UTC explícito. Rechaza inputs extra, timestamps
futuros, quotes stale, barras duplicadas/no monotónicas y OHLC inválido.
Warmup produce missingness; se declara el mismo origen de warmup y source hash.
MAIN_K usa ratio-of-sums 5/3/3, ATR14 simple, referencia mediana de los 288 ATR
anteriores, volumen relativo a 20 barras anteriores y cuerpo HA/ATR causal.
No modifica señales de estrategia ni el metadata de maturity congelado.

Whitelist v2 exacta en `configs/drift_feature_whitelist.json`: stoch_main_k,
spread, atr14_over_previous_288_bar_median, relative_tick_volume_20, ha_body_atr.
El whitelist v1 no implementado se conserva como `drift_feature_whitelist_v1.archived.json`.
Se excluyen distances de Volume Profile sin productor común probado; no se
sustituyen por cifras inventadas. Baseline, CSV futuro y bins deben tener
exactamente el mismo conjunto; definiciones y productor están ligados por hash.

El builder `python/drift_baseline.py` exige matriz feature-only TRAIN, provenance
con split=TRAIN, feature_only=true, normalized_utc_verified=true, matrix_sha256 y
producer_sha256. No es un permiso para generar o leer TRAIN/stream automáticamente.
Crear el baseline solo tras disponer del input normalizado autorizado:

```text
python python/drift_baseline.py --matrix <TRAIN_features.csv> --provenance <TRAIN_features_provenance.json> --output <baseline.json>
python python/drift_monitor.py <future_features_only.csv> --whitelist configs/drift_feature_whitelist.json --baseline <baseline.json> --feature-definition configs/drift_feature_whitelist.json --producer-source python/drift_feature_stream.py --output <drift_report.json>
```

Los bins están fijados en el productor; no hay ajuste a outcomes. Comparación
PSI/missingness, cobertura de sesión/régimen/volatilidad, spread, latencia y gaps
usan solo features o metadata. PnL, labels, outcomes, win rate, PF y future_return
son prohibidos incluso si se intentan añadir al whitelist. Los conteos deben ser
enteros no negativos. No hay scoring, ranking ni tuning.

[Estado actual](PROJECT_STATUS.md) · [protocolo anterior](archive/pre_cloud_20261027/DRIFT_MONITOR_PROTOCOL.md).
