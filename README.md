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

## What the experiments found

**The original observation that irrelevant evidence helped Lite did not repeat consistently.** In the original pilot, Lite scored 2/5, 3/5 and 5/5 with 0, 100 and 1,000 extra records on the same five four-report worlds. In the follow-up plus final expansion, those counts were **10/12, 9/12 and 10/12**. Each denominator twelve represents two attempts on six worlds. Four worlds stayed unchanged between the endpoint doses, one improved and one worsened: an unchanged average hid changes on individual worlds.

In the eight-report setting, Lite scored **9/12, 5/12 and 7/12**. The dip and partial recovery suggest a possible distraction effect, but this small, irregular pattern does not establish one. Flash scored **12/12 at every dose in both settings**. At 1,000 extra records, average call cost in the four-report setting rose about **56× for Lite and 77× for Flash**, without improving aggregate endpoint accuracy.

The combined primary change was zero, with a descriptive 95% world-bootstrap interval of **[-25, +25] percentage points**. This does not establish equivalence or prove no effect. The final expansion followed the initial result, so the combined findings are exploratory. All **144 scored calls plus two compatibility probes** completed without provider/protocol failures; the receipt-based estimate was **$6.961763 of the single $10 cap**, with no unresolved holds. The allowance is closed.

[Full results, separate phases and costs](docs/site/results/index.md#nuisance-records) remain available. Replay these saved measurements without a key or paid calls:

```sh
clue-benchmark examples replay nuisance-followup --output runs/nuisance
```

## Where are the original results?

The [results gallery and source index](docs/site/results/index.md#where-to-find-the-original-results) preserve the earlier studies alongside the follow-up. They use different settings and denominators and must not be pooled into a leaderboard.

- [Original pilot: irrelevant evidence](docs/site/results/index.md#original-pilot): Lite's 2/5 → 5/5 observation, the eight-report negative/control result and its provider error; [saved pilot assignments](docs/site/assets/pilot.json).
- [Information availability and distributed evidence](docs/site/results/index.md#information-availability): Flash 8/8 complete answers, 32/32 appropriate abstentions and 8/8 after programmed star forwarding; also in the pilot assignments.
- [Certified evidence burden](docs/site/results/index.md#certified-burden): Flash 30/30 in each 32-report arm, Lite 9/30 and 7/30; [saved assignments](docs/site/assets/hardness.json).
- [Hard cases and output resources](docs/site/results/index.md#hard-cases-and-resources): fresh Flash confirmation 9/48 correct, separately from the adaptive six-world 2/6 → 5/6 comparison; [fresh assignments](docs/site/assets/flash-hard-scale.json), [adaptive assignments](docs/site/assets/flash-limits.json).
- [Qwen completion versus supported correctness](docs/site/results/index.md#completion-versus-supported-correctness): 67/72 valid final actions, 22 supported correct and five output-limit failures; [saved outcomes](docs/site/assets/qwen-sampled-screening.json).
- [Initial October 27 follow-up and final expansion](docs/site/results/index.md#follow-up-and-final-expansion): the initial 96 scored calls remain separate from the 48-call extension; [initial analysis](docs/site/assets/nuisance-followup-results.json), [phase-separated combined analysis](docs/site/assets/nuisance-extended-results.json), [all 144 saved assignments](docs/site/assets/nuisance-extended-measurements.json).

Recompute all included historical counts with `clue-benchmark examples replay measured-results --output runs/results`. The [source/checksum index](docs/site/assets/index.json) identifies original sources and sanitized copies. Full operational archives remain private pending privacy and rights review.

Start with [the five-minute tutorial](docs/site/tutorials/first-dataset.md), [distributed evidence](docs/site/tutorials/distributed-evidence.md), [research recipes](docs/site/guides/research-recipes.md), [concepts](docs/site/explanations/pipeline.md), [parameter reference](docs/site/reference/parameters.md), [CLI/Python/tools](docs/site/reference/interfaces.md), [results and limitations](docs/site/results/index.md), or [dataset card](docs/site/reference/data-dictionary.md). Build searchable docs with `mkdocs build --strict` after installing the docs extra.

Contributors: [CONTRIBUTING](CONTRIBUTING.md), [release gates](docs/site/maintainers/release.md), [licensing pending](LICENSING.md), [provenance](PROVENANCE.md). Historical status and the preserved prior README remain in [the archive](docs/archive/readme-before-release-2026-10-27.md); flat v0.3 interfaces remain supported separately.
