# TRAIN / Discovery Validation isolation incident audit

**Audit date:** 2026-10-18
**Repository:** `l6i2/stochastic-gpt-lab`
**Branch / audited HEAD:** `research/full-pipeline` / `949faf833a95c0cdcbab44ec5c14456a7319fc7f`

## Determination

```text
DISCOVERY_VALIDATION_CONTAMINATION=POTENTIAL
ISOLATION_INCIDENT=CANNOT_CLOSE
DISCOVERY_VALIDATION_STATUS=POTENTIALLY_CONTAMINATED
FUTURE_DISCOVERY_VALIDATION_USE=BLOCKED_PENDING_REMEDIATION
```

This is an evidence limitation, not a finding that Validation definitely
affected the results. The R2/R3/R4 reports state that the score calculations
used frozen TRAIN membership, and their manifests record
`validation_accessed=false`. Their published metrics are TRAIN-fold metrics.
However, the exact runner source for R2 and R3 was not preserved in Git, so the
manifest assertions alone do not independently prove the complete data flow or
exclude an unrecorded human or automated influence. Under the requested proof
standard, the incident cannot be closed as clean.

## Evidence examined

| Evidence | Observation | Audit implication |
|---|---|---|
| R2 replay manifest | SHA-256 `d7cdc561030f1e8479c2af1b9d60b27447333b738ce0b159d5c5116387cdde25`; runner SHA `a5617f5c0c14cc1fd8257b7a52c479b62a3fb7cef2fdabd8ee2ac0ad9f0cb15d` | Records 11,714 TRAIN signals, 1,810,478 snapshots, frozen hypotheses, and `validation_accessed=false`; original runner bytes are unavailable for independent source comparison. |
| R2 walk-forward report | SHA-256 `4c49cfbb0d003afbb58b8ddf9640f07045ddf5ddb1dbabfd2867856187fc1cf6` | Contains four purged TRAIN folds, no selected Validation hypothesis, and `validation_accessed=false`. |
| R3 replay manifest | SHA-256 `b17d7d153232fa09d6f89dcf4dd158abb0bfb640c7178fcc3f988cfe585c58ed`; runner SHA `5a0f229db628054f7064dbb8183bcbf7c6847c6874bea66df75314e27791acd1` | Records TRAIN-only scope and `validation_accessed=false`; original runner bytes are unavailable for independent source comparison. |
| R3 walk-forward report | SHA-256 `918d942ff6978be0b3fe12929504b10756627c3b1089d24544759191605b609b` | Contains purged TRAIN-fold metrics and no Validation score. |
| R4 replay manifest | SHA-256 `2813027a2909013f8c99d10c0d60f00227915e1ba5f1b9b3c5572908f6c20062`; runner SHA `a63eb86bc2a1a453b434a3fceb959bd592d0a4e69b2df6f077a1a7c270068769` | Runner SHA matches the committed `python/explore_train_intratrade_round2.py` at audited HEAD. That code obtains frozen TRAIN IDs and filters event rows before retaining them. |
| R4 walk-forward report | SHA-256 `2e18eeb6724d138473f0df988589e9f1846c5dbe2b4a147ec709c1468b97c4ca` | Contains four purged TRAIN-fold metrics and no Validation score. |
| Historical round summary | `docs/INTRATRADE_TRAIN_ROUNDS_REPORT.md` | Explicitly disclosed that early runners read the combined event source before restricting calculations to TRAIN IDs. It does not preserve the missing R2/R3 runner source. |
| Outputs / preregistrations | Round reports, frozen hypothesis hashes, and the R2/R3/R4 protocols | Show 16 hypotheses and gates were documented; all 16 failed TRAIN. No Discovery Validation evaluation or candidate is recorded. |

The R2 and R3 runner hashes are not present as source blobs in the audited
commit history. Hashes identify bytes but cannot recover or explain them. The
combined `stochastic_events.csv` contains TRAIN and Discovery Validation rows;
early runner documentation says it was read before filtering. That physical
read is known. Whether any unpreserved code path used a Validation value outside
the reported TRAIN membership cannot now be independently reconstructed.

## Influence by decision channel

| Channel | What the preserved evidence shows | Conclusion |
|---|---|---|
| Metrics | Published R2–R4 scores are four-fold TRAIN walk-forward results. Manifests say Validation was not accessed. | No Validation metric is present in the reported results; exact R2/R3 source flow remains unverified. |
| Selection / ranking | No hypothesis survived TRAIN; selected-for-Validation is null; no candidate exists. | No recorded Validation-based selection; absence of source prevents a complete negative proof. |
| Thresholds / definitions | Protocols and SHA-256 hypothesis records freeze the definitions before each replay. | No evidence of Validation-derived threshold changes; exact R2/R3 execution source is missing. |
| Models / rules | R2–R4 were fixed replay rules; no Validation model training is reported. | No Validation-trained model or promoted rule is recorded. |
| Human / automated decisions | Reports show no candidate and no Validation evaluation. Historical execution logs/source for every human-visible decision are not preserved alongside R2/R3 runner bytes. | No influence is evidenced, but a complete negative proof is unavailable. |

Because the user explicitly required sufficient evidence before declaring
clean isolation, this audit does not equate “not recorded” with “did not
happen.” Do not score, rank, train on, or otherwise use the existing
Discovery Validation split until a prospective remediation is approved and
documented. Do not move its boundary to obtain a favorable result.

## New preventive control

TRAIN event loaders now call `assert_train_only_source_path` before I/O. It
rejects paths under or named `validation`, `discovery_validation`, or
`final_test`. The control is wired into the R2/R3/R4 replay and walk-forward
read paths. Tests prove the guard rejects such paths before `pandas.read_csv`
is invoked, while a shared combined source remains usable only through exact
frozen TRAIN-ID filtering. This prevents opening a separately materialized
Validation file; it does not claim that parsing a combined source never reads
Validation bytes from disk.

## Remediation gate

The existing split is blocked for future research pending an independent
decision on a scientifically valid replacement evaluation design. A safe
candidate design is a newly collected, strictly forward-time cohort with a
preregistered protocol and an untouched future evaluation interval. It must
not reassign old rows or redraw boundaries based on observed outcomes. No new
hypothesis round is authorized by this audit.
