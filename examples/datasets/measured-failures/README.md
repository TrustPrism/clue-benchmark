# Measured failure examples

Four certified, one-case bundles illustrate actual outcomes from the October
10–11 Gemini hardness study. They were selected **after measurement, exclusively
from development worlds**. They are inspection examples, not a held-out estimate
of accuracy or a promise that another run will fail.

- `equality_tree-32`, seed 109: Flash-Lite answered incorrectly on 3/3 attempts.
- `branching-32`, seed 109: the same underlying world; Flash-Lite answered
  incorrectly on 3/3 attempts. Both cases require exactly 32 reports and contain
  six additional truthful statements plus 100 independent records.
- `relational-random-false-2`, seed 110: Flash answered once correctly and
  abstained twice. All three views identify a unique culprit under the published
  allowance of two false reports; exactly two reports were corrupted.
- `relational-targeted-false-2`, seed 114: Flash answered twice correctly and
  abstained once under the same allowance. The closest wrong explanation is
  exactly one violation beyond the allowed region.

Models used high thinking, temperature zero, deterministic text-only report
views and an 8,192-token output limit including thinking. Finite budgets and
observed variation matter; these are not unlimited-reasoning results.

Each directory contains the standard five-file bundle, an exact public
`observation.json`, and private evaluator `observed-outcomes.json`.
**Give a model only `observation.json`**, using the original native answer/abstain
tools for a matching evaluation. Answers, certificates, manifests, outcome
files and this gallery's selection metadata are evaluator information.
The observation contains neither actual corruption counts nor corrupted report
identities. Structured reports in `cases.jsonl` were not supplied in these calls.

```sh
clue-benchmark validate-dataset examples/datasets/measured-failures/relational-random-false-2
```

See [the study report](../../../docs/hardness-results.md) for the complete cohort,
assigned denominators, provider failures, usage and comparison limits. The
original measured bundles and plans remain frozen separately.
