# Intra-trade snapshot schema 2.0

This source is produced by the separate `StochasticIntratradeResearchEA`. The frozen entry EA remains unchanged. The tester must use US30Cash M5, real ticks, optimization OFF, `TICK_QUOTES`, and `LIVE_TRADING=false`.

## Snapshot rows

`intratrade_snapshots.csv` contains one row for each virtual FOLLOW/INVERT trade that remains open at a scheduled completed-bar offset: 1, 2, 3, 5, 10, 15, 20, 30, and 50. The key is `(signal_id, virtual_mode, snapshot_bar)`; `snapshot_id` is unique. A trade that closes before an offset has no row at that offset.

`snapshot_time_msc` is the end of the completed M5 bar. `feature_max_time_msc` is that same cutoff. `mark_time_msc` identifies the most recent quote observed before the cutoff. The mark uses the completed bar close and the bar's recorded spread; the quote time is retained so this bar-close valuation is auditable. `current_mfe_so_far` and `current_mae_so_far` are the virtual trade's running excursions updated only through observed quotes at or before the snapshot.

Features include identity and virtual mode, current virtual position state, Stochastic K/D levels and slopes, zone state, causal Heikin-Ashi state, tick/real volume and rolling volume summaries, OHLC price action, ATR/rolling volatility, EMA levels/slopes/alignment, recent structure counts, timestamps/session, and tick-activity Volume Profile for 30/60/120/240 minutes plus the current session. Profile features inherit the EA's `available_coverage_unverified` semantics. Missing profile/history values remain blank; they are not imputed by the exporter.

The CSV contains no outcome labels. The strict training feature whitelist must exclude all identifiers and timestamps as well as categorical fields such as `original_signal`, `virtual_mode`, and `virtual_side`. Feature construction is as-of the completed snapshot bar; `feature_max_time_msc <= snapshot_time_msc` and `mark_time_msc <= snapshot_time_msc` are mandatory.

## Future targets

`intratrade_snapshot_targets.csv` is written separately after the virtual trade closes. `END_OF_DATA` trades are censored and receive no complete targets. The table includes `exit_time_msc`, and validation requires it to be later than the matching snapshot.

- `tp_before_sl_after_snapshot` and `sl_before_tp_after_snapshot` indicate which fixed exit ended the trade after the snapshot. `TIME_EXIT` yields zero for both.
- `future_pnl_to_exit` and `continuation_score` are final directional PnL minus snapshot unrealized PnL.
- `future_max_favorable_move` and `future_max_adverse_move` are additional maximum directional excursions after the snapshot.
- `profit_erosion` is `max(0, MFE_at_snapshot - final_directional_PnL)`.
- `recovery_after_drawdown` is blank when snapshot PnL is nonnegative; otherwise it is one when post-snapshot favorable excursion could recover the snapshot loss.
- `reversal_event` is frozen before validation: one only when MFE at snapshot is at least 60 price units and either that MFE exceeds final directional PnL by at least 120 units or the fixed trade exits at SL.

Targets may use future outcomes and must never enter the feature list. No threshold may be tuned after validation is viewed.

## Split and coverage rules

Split membership is inherited from the entry `signal_id`. Build only TRAIN and DISCOVERY_VALIDATION snapshots for discovery. The exporter must stop at the last allowed validation signal and must not produce a FINAL_TEST snapshot file. The master builder writes only TRAIN and DISCOVERY_VALIDATION datasets. Unknown signal IDs fail closed rather than being treated as training data.

Each tester block needs a manifest with its exact requested period and `LIVE_TRADING=false`, `optimization=OFF`, `symbol=US30Cash`, `timeframe=M5`, and `model=Every tick based on real ticks`. Keep raw snapshots, labels, audit, logs, and manifests local; do not publish broker tick datasets or account logs.
