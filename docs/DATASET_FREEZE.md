# Dataset freeze: `stochastic_master_v1`

Status: frozen local artifact; raw research CSV and Parquet files are excluded from Git. Rebuilds must use a new dataset version and must not overwrite this version.

- Broker / instrument: XM Global Limited / `US30Cash`
- Timeframe and model: M5 / Every tick based on real ticks
- Available real-tick coverage: server time 2023-12-20 through 2026-10-13 (partial endpoint)
- First/last signal server time: 2023.12.20 02:05:00 / 2026.10.12 23:40:00
- Signals / rows: 20,422; schema 1.1; 329 columns
- Source code HEAD: `ced3b6d9e469dadf76a4771049c994e476f19329`
- Parquet SHA-256: `e2c05a24551078efb584cc4732b796846f3b98793d21978522b36be141de59c1`
- Source periods: 2023-12-20..2023-12-31, 2024, 2025, 2026-01-01..2026-10-13
- Exact boundary duplicates removed: 0
- Split: chronological 60/20/20; 12,243 purged TRAIN, 4,077 purged DISCOVERY_VALIDATION; a separate FINAL_TEST file was not written.
- Integrity warnings: 2023 has generated tester ticks in 1,230 mismatched-price minute bars; 2024 has 210 such minutes. See the local master audit and status CSV.

The full master contains the chronological held-out tail because it is the source for the requested complete dataset. Discovery tooling must select TRAIN or DISCOVERY_VALIDATION explicitly. No held-out result has been computed; do not load or evaluate FINAL_TEST before explicit user authorization.
