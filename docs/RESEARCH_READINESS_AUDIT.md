> HISTORICAL SNAPSHOT: preserved evidence, not current operational authority. Current status: [PROJECT_STATUS.md](PROJECT_STATUS.md); Cloud audit: [CLOUD_PREPARATION_AUDIT.md](CLOUD_PREPARATION_AUDIT.md).

# Research readiness audit — 2026-10-19

## Evidence scope

The audit read only `outputs/splits/train.parquet` (SHA-256
`4823eb1aa4ca08899ffcbcff957b4dfb726b30c9dd074a2c968efb1f133bb1c1`). It did
not open the Discovery Validation partition, FINAL_TEST, the combined large
quality-v1 snapshot table, or the future cohort. Counts below apply only to
that frozen signal-level TRAIN file, not to every raw schema-3 artifact.

It contains 12,243 unique signals from 2023-12-20 through 2025-08-19: 5,712
BUY and 6,531 SELL; no duplicate signal IDs. All 12,243 rows have
`feature_max_time_msc <= signal_time_msc`, HA status `ready`, ATR percentile,
spread, and ATR. `vp_30m_status` is `available_coverage_unverified` for every
row, and the recorded volume source is tick volume. This does not establish
real-volume availability or verified Volume Profile coverage.

## Readiness findings

- **Dataset integrity / causal signal features:** pass for the inspected
  TRAIN event file only; the isolation incident for legacy Discovery
  Validation remains POTENTIAL and that split remains blocked.
- **BUY/SELL and sessions:** both sides have adequate descriptive counts;
  the session counts are New_York 4,686, Asia 4,287, London 2,727, Other 543.
  These are descriptive, not selection evidence.
- **Latency and replay:** schema-3 ordered-quote replay and frozen HOLD
  baseline were validated for allowed historical blocks. New V2 policy
  results have not been run; the quote-friction source/fold metadata must be
  independently verified before execution.
- **Volume/Profile:** tick volume is present; real volume is not established.
  Profile coverage is explicitly unverified. These features are not ready for
  candidate claims.
- **MFE/MAE and trajectory:** historical every-bar snapshots and quote tapes
  exist, but no dynamic-exit hypothesis passed R2-R4. Their train-round report
  documents fold, side, session, latency, and concentration failures. Those
  rules remain rejected.
- **Model calibration / deployment:** no credible candidate, no calibration
  evidence on an uncontaminated holdout, no frozen model, and no execution
  adapter. DEMO executor is not ready.
- **Prospective data:** scheduled collector is enabled but has captured zero
  rows. Health status reports no running MT5 terminal, account mode UNKNOWN,
  and `BLOCKED_MT5_XM_DEMO_NOT_VERIFIED`. It fails closed and makes no orders.

## Decision

TRAIN-only V2 preregistration is frozen, but no V2 result is claimed. The
current evidence supports `NO_CREDIBLE_CANDIDATE`; TRAIN research is
incomplete for the new preregistered family because the required source and
fold replay inputs have not been verified. Do not open either holdout, create
a candidate, or enable DEMO. Close the legacy Validation contamination issue
only with independent provenance evidence; none is claimed here.
