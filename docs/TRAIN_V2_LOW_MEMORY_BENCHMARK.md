# TRAIN V2 low-memory replay benchmark

**Date:** 2026-10-21  
**Branch:** `research/full-pipeline`  
**Scope:** the single preregistered `HV2_ENTRY_SPREAD_ATR_ROUTER` family, quality-v1 TRAIN only.

No feature, fold boundary, quantile, side definition, latency, baseline, support threshold, or rejection gate changed. No Discovery Validation, FINAL_TEST, or FUTURE_VALIDATION_COHORT outcome was read or scored. The router result is rejected by its frozen TRAIN gates; this is not permission to create another family or inspect a holdout.

## Resource diagnosis and fix

The host has 4,155,196 KiB of physical memory. The original prefix and latency searches used NumPy `searchsorted` against strided fields (`time_msc` / `bar_index`) in the 32-byte structured quote memmap. On a controlled real-data prefix, normal prefix lookup took 36.918 s and peaked at 1,338.8 MiB working set. It caused paging on this machine.

`LOW_MEMORY_REPLAY` now uses a compiled scalar lower-bound binary search directly against those strided mapped fields. It returns the same left insertion point as `numpy.searchsorted`, without materializing a contiguous copy. Quote data is mapped and released one source block at a time. A provenance-bound checkpoint is atomically written after each completed block and can resume only when runner, protocol, TRAIN, split, quality, and baseline hashes match. The successful run removed its checkpoint after writing the final result.

The complete low-memory run finished in 119.238 s wall time / 15.969 s process CPU with a measured process peak of **806.4 MiB**. The peak is about 532 MiB below the controlled normal-prefix run. This profiling run did not alter the replay semantics.

| Stage | 2024 block | 2025 block |
|---|---:|---:|
| Quote file size | 633,152,240 B | 749,513,968 B |
| TRAIN prefix quote records | 22,612,580 | 17,240,750 |
| TRAIN signal count | 7,071 | 4,643 |
| Trade-index read / quote matching | 0.600 s | 2.534 s |
| Prefix map / boundary search | 1.265 s | 1.245 s |
| Compact exact extrema index | 19.406 s | 63.806 s |
| Exact replay, both modes × three latencies | 14.278 s | 3.613 s |
| Block wall / CPU | 36.066 s / 8.266 s | 71.861 s / 3.797 s |

Train input load, including parquet columns, exclusions, source-block join, and causal feature preparation, took 0.941 s. All four fold calculations together took 6.634 s (2.438 s CPU); folds took 1.146, 0.523, 0.644, and 0.581 s. Summary JSON serialization took 0.0051 s. The output JSON is 58,839 B. The largest runtime hotspot was sequential quote I/O while building the extrema index, especially the 2025 file; quote matching itself used no full-field copy.

## Numerical equivalence

- On a controlled prefix of **17,240,750 real TRAIN quotes**, the low-memory and normal prefix arrays were exactly equal element-for-element. Normal lookup used 36.918 s and peaked at 1,338.8 MiB; low-memory lookup used 10.175 s in that comparison.
- On **5 real TRAIN signals**, a 63,640-quote local replay segment produced exact dictionary equality for all **30** FOLLOW/INVERT × 0/250/500 ms outcomes. Peak working set was 149.6 MiB.
- Fixture tests also compare normal and low-memory fill, SL, TP, TIME_EXIT, boundary, and prefix results. No tolerance-based comparison is used; outcomes compare exactly.

The full run validated paired source quote indices and timestamps for 23,428 baseline paths, then generated 70,284 latency/mode replay outcomes over 11,714 TRAIN signals. Four expanding purged folds were retained exactly as preregistered:

| Fold | Training signals | Evaluation signals |
|---|---:|---:|
| 1 | 3,994 | 1,985 |
| 2 | 5,985 | 1,990 |
| 3 | 7,990 | 1,988 |
| 4 | 9,988 | 1,714 |

## Frozen-gate result

Result artifact: `outputs/bar_controller/research/train_entry_spread_atr_router.json`  
Artifact SHA-256: `f18eeb27950c0d9fec01de0a49d669b604381d8c94f9356b67c1dfb5840d987`  
Runner SHA-256: `0abf63be758be06b15e0dfb84f3ce880050de48e3ec39c77b37248eaa0eeccc1`

`TRAIN_ROUTER_REJECTED`; no candidate was frozen.

- **BUY:** n=3,641; positive folds 3/4 (75%); 0/250/500 ms signs and 25/75 threshold sign pass. It fails block concentration (maximum positive share 79.7%, gate ≤50%) and session concentration (70.1%, gate ≤50%).
- **SELL:** n=4,036; positive folds 2/4 (50%, gate ≥70%); 25/75 threshold sign fails; fold concentration is 69.5%, block concentration 64.8%, and session concentration 95.9% (each gate ≤50%). Latency sign/magnitude stability passes.
- Both sides meet minimum sample support. The router drawdown proxy is −37,092.63 versus −42,263.14 for the better fixed baseline, so that gate passes; it is not account-level drawdown.
- The signal-clustered bootstrap intervals include zero for both sides: BUY [−2.85, 7.75], SELL [−0.81, 5.69].
- At primary latency 250 ms, fold mean deltas versus the selected fixed baseline (BUY / SELL) are: F1 +4.21 / +3.41, F2 −4.65 / −0.62, F3 +5.03 / +8.01, F4 +5.97 / −1.94.

The rejection is final for this preregistered family. No thresholds or rules were retuned. MFE/MAE, erosion/recovery, momentum, and volume/profile are outside this frozen entry-friction family and remain untested; no new family was created.

## Safety and verification

The output records `validation_accessed=false`, `final_test_accessed=false`, `future_cohort_accessed=false`, `demo_execution=false`, and `live_trading=false`. `FINAL_TEST=LOCKED`, `DEMO=DISABLED`, and `LIVE_TRADING=false` remain in force.

Focused verification: router equivalence and safety tests pass; TRAIN source-isolation tests pass; `compileall` and `git diff --check` pass. The separate mock/shadow adapter has no broker dependency or order method; it is disabled by default and only persists hypothetical decisions plus audit records. It hard-fails REAL/UNKNOWN account modes and uses the existing stale-data, reconnect, kill-switch, risk, and duplicate gates.
