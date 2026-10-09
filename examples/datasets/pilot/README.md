# Inspectable pilot samples

- Ten dataset arms, each with three independently validated cases: **30 case
  variants across 9 distinct underlying worlds**. Variants are paired within
  each experiment; some burden/distribution cases share a world across groups.
- Six archive-volume arms: four/eight necessary clues, each with zero, 100 or
  1,000 irrelevant records. Within each size, target evidence is identical.
- Three false-report arms: zero/one/two substitutions under the same published
  allowance of at most two. Each accepted case retains its unique answer.
- One four-agent dataset: all four agents are required for a sufficient team.
- `suite.json` records matching and hashes; `diagnostics.json` contains offline
  solver controls. These are **not model results**.
- Give agents only selected views through `iter_cases(..., agent_id=...)`.
  Answers, certificates and diagnostics are evaluator material.

These bundles are small inspection examples, not the eight-world model pilot.
See [the experiment guide](../../../docs/pilot.md) for generation, frozen plans,
the single $20 ceiling, and separate authorization for model execution.
Manifest output-directory fields record original generation locations; bundle
validation uses relative paths and their unchanged checksums after copying.
Certification bounds in false-report cases are deliberately labeled bounded,
not exact optima.
