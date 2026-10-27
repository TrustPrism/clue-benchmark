# Clue Benchmark — 0.5.0rc2 private candidate

A configurable Python generator and evaluation tool for **certified information availability, reliability, and evidence distribution**. Generate synthetic clue puzzles, certify what each agent can infer, export only public evidence, and score correctness separately from evidential support and abstention.

A tiny public puzzle: Ada, Ben and Cy have red/blue badges; the responsible person has red, Ada has blue, and Ben has Ada's badge value. Cy is responsible. Remove Ben's report and both Ben and Cy remain possible: a lucky Cy answer is no longer supported. Repeated values are allowed; one culprit need not imply one complete world.

Ownership clearance and independent review are pending. Install the reviewed private wheel with `python -m pip install /path/to/trustprism_clue_benchmark-0.5.0rc2-py3-none-any.whl` (Python >=3.12). No public package upload is claimed.

```sh
clue-benchmark generate-dataset --preset quickstart --output runs/demo
clue-benchmark validate-dataset runs/demo
clue-benchmark export-public runs/demo --agent 0 --output runs/agent.jsonl
```

No clone, API key or inference is needed. Discover configurations with `clue-benchmark presets list` and `clue-benchmark explain-config --preset quickstart`. Replay the eight-world information controls with `clue-benchmark examples replay distributed-evidence --output runs/replayed`, or recompute historical assignment counts with `clue-benchmark examples replay measured-results --output runs/results`.

Preliminary examples: Flash answered 8/8 complete views and abstained on 32/32 ambiguous private views. Lite's four-report nuisance-dose counts were 2/5, 3/5, 5/5 on the same five worlds, but the eight-report stratum did not improve and one provider error remains in the denominator. A separate fresh hard regime yielded 9/48 correct under its stated resource budget. These are different small studies, not a pooled leaderboard. The follow-up plus one final expansion completed 144 scored calls and two probes
under the single $10 cap (receipt-based estimate $6.961763). Lite's combined
four-report counts were 10/12, 9/12, 10/12 at 0/100/1000 records: no aggregate
primary improvement. Six worlds per stratum, two attempts each; the combined
estimate is exploratory. [Full results](docs/site/results/index.md) retain both
phases, all conditions and costs. Replay the included data with
`clue-benchmark examples replay nuisance-followup --output runs/nuisance`.

Start with [the five-minute tutorial](docs/site/tutorials/first-dataset.md), [distributed evidence](docs/site/tutorials/distributed-evidence.md), [research recipes](docs/site/guides/research-recipes.md), [concepts](docs/site/explanations/pipeline.md), [parameter reference](docs/site/reference/parameters.md), [CLI/Python/tools](docs/site/reference/interfaces.md), [results and limitations](docs/site/results/index.md), or [dataset card](docs/site/reference/data-dictionary.md). Build searchable docs with `mkdocs build --strict` after installing the docs extra.

Contributors: [CONTRIBUTING](CONTRIBUTING.md), [release gates](docs/site/maintainers/release.md), [licensing pending](LICENSING.md), [provenance](PROVENANCE.md). Historical status and the preserved prior README remain in [the archive](docs/archive/readme-before-release-2026-10-27.md); flat v0.3 interfaces remain supported separately.
