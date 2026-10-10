# Advanced presets

These configurations generate datasets offline. Their requested guarantees must
be certified; no preset promises a model failure.

- `reasoning-32.json`: exactly 32 necessary reports, plus six non-target
  statements and 100 archive records. The suite pairs it with a branching tree.
- `targeted-false-2.json`: eight suspects, seven attributes, 63 relational
  reports and two factual corruptions. A wrong explanation lies one violation
  beyond the published two-false-report allowance.
- `near-decoys-12.json`: 45 original reports, twelve true connected comparisons,
  no actual corruption, and an allowance of two false reports. Wrong suspects
  remain just outside that allowance.
- `archive-interleaved.json`: eight necessary reports scattered through 1,000
  independent archive records, with six additional non-target statements.
- `distributed-eight.json`: eight private agents; every proper coalition is
  insufficient. The complete team identifies the answer.
- `relational-32.json`: a one-case stress point with 32 suspects and 231 reports,
  including two factual corruptions. Cost bounds are reported; 231 necessary
  reports are not promised.

Use `clue-benchmark generate-dataset --config <preset> --output <new-directory>`.
Change counts, seeds or budgets explicitly and use a new output directory.
For matched experiments and limitations, see [the guide](../../docs/hardness.md).
