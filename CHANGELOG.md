# Changelog

## 0.1.1 — private protocol update

- Investigation protocol 1.1 charges evidence budget only for revealed clues, with a separate bounded request allowance for invalid or exhausted queries.
- Request responses distinguish unknown IDs from exhausted topics and include current topic counts without repeating prior clues.
- Record request counts and budget-averaged investigation accuracy; refresh symbolic baseline results under the new protocol.
- Keep dataset and generator version 0.1.0 unchanged so existing case IDs and checksums remain stable.

## 0.1.0 — private preview

- Independent repository with a checksum-recorded working-tree baseline.
- Unified bounded generator with validated configuration, controlled clue wording, and inconclusive solver handling.
- Deduction and budgeted investigation tracks, exact scoring, and optional Inspect adapter.
- Deterministic parallel generation, resumable checkpoints, structural duplicate screening, and study-shaped export.
- 390-case suite, free symbolic baselines, measured performance, tests, and reproducibility documentation.
- Public licensing and publication pending owner decision; no paid model results.
