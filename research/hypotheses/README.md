# Hypothesis registry

Each hypothesis is an immutable JSON record named `<hypothesis_id>.json`. Compute and record its SHA-256 before evaluating it. Once evaluated, edits require a new ID/version and a new hash; never overwrite the registered record. Keep observations from TRAIN separate from validation outcomes. The initial registry is empty pending review of the TRAIN-only reports.
