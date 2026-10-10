# Certified advanced inspection datasets

The nineteen matched arms each contain two cases. `relational-32/` contains a
separate one-case stress point. These are small inspection examples; the larger
offline preparation used ten cases per matched arm. Model measurements for these
new datasets are pending.

Give agents only public records from `cases.jsonl`, filtered through ownership in
`partitions.jsonl` when testing private views. `answers.jsonl`,
`certificates.jsonl`, `manifest.json` and `suite.json` are evaluator information.
They contain labels, known worlds, bounds, witnesses and experiment metadata.

The main `suite.json` lists matched arms and their underlying worlds. The separate
231-report stress point can be generated and validated through its preset.
All variants of a world share a split. The examples retain full independent
certificate witnesses, including alternative worlds for insufficient coalitions;
numeric manifest profiles omit duplicate proof cuts.

See [the advanced guide](../../../docs/hardness.md) for controls, experiment
commands, certification limits, reference models and authorization requirements.
