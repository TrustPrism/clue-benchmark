# Clue Benchmark

**A research preview for reasoning with evidence.** Generate synthetic logic puzzles, certify what each agent can infer, and score a correct answer separately from a supported one.

[Read the website](https://trustprism.github.io/clue-benchmark/) · [Measured results](https://trustprism.github.io/clue-benchmark/results/) · [Open questions](https://trustprism.github.io/clue-benchmark/results/open-questions/) · [Initial prerelease](https://github.com/TrustPrism/clue-benchmark/releases/tag/v0.5.0rc2)

## Start offline

Use **Python 3.12 or newer**. From the checked-out preview source:

```sh
python -m pip install .
```

Generate one case:

```sh
clue-benchmark generate-dataset \
  --preset quickstart \
  --output runs/demo
```

Check it and export only the agent's evidence:

```sh
clue-benchmark validate-dataset runs/demo

clue-benchmark export-public runs/demo \
  --agent 0 \
  --output runs/agent.jsonl
```

After installation these commands run without a key, network or paid model calls. Give the agent **`runs/agent.jsonl`**, not the evaluator bundle.

[Follow the complete tutorial →](docs/site/tutorials/first-dataset.md)

## What makes this useful?

![Build a world, certify what the evidence supports, then score an agent while keeping the answer key separate.](docs/site/assets/evidence-flow.svg)

- **Evidence sufficiency:** distinguish one identifiable answer from several possibilities.
- **Reliability:** reason under a public at-most-k false-report rule.
- **Distribution:** compare complete, private and forwarded evidence.
- **Separate outcomes:** keep correctness, support, abstention and protocol failures distinct.

A tiny example: Ada has a blue badge; Ben's badge matches Ada's; the responsible person's badge is red. Cy is the only possible responsible person. Remove Ben's report and both Ben and Cy become possible. Guessing Cy can then be correct without being supported.

## What did the latest experiment find?

**The pilot's apparent benefit from irrelevant evidence did not repeat consistently.**

In the expanded follow-up, Lite's four-report scores were **10/12, 9/12, 10/12** with 0, 100 and 1,000 extra records. Four worlds stayed unchanged between the endpoints, one improved and one worsened. Flash scored **12/12 throughout** in both burden settings.

Costs rose roughly **56× for Lite and 77× for Flash** in the four-report setting without higher aggregate endpoint accuracy.

The combined result is exploratory: six worlds per setting, two attempts each, with a primary interval of **−25 to +25 percentage points**. An unchanged score is not proof of no effect.

All **144 scored calls and two probes** completed without provider/protocol failures. Estimated spend: **$6.96 of the single $10.00 cap**, with no unresolved holds. The allowance is closed.

[Read every condition, separate phases and costs →](docs/site/results/index.md)

## Where are the original results?

The [original-study index](docs/site/results/index.md#where-to-find-the-original-results) preserves the earlier evidence:

- Original nuisance pilot and distributed-evidence controls.
- Certified evidence-burden comparisons.
- Fresh hard cases and a separate adaptive output-budget example.
- Qwen completion versus supported correctness.
- Initial follow-up, final expansion and exploratory combined result.

They use different settings and denominators. They are not a pooled leaderboard.

Replay the saved follow-up:

```sh
clue-benchmark examples replay nuisance-followup \
  --output runs/nuisance
```

Or replay all packaged historical panels:

```sh
clue-benchmark examples replay measured-results \
  --output runs/results
```

## Learn more

- [Research recipes](docs/site/guides/research-recipes.md).
- [Pipeline and guarantees](docs/site/explanations/pipeline.md).
- [Parameter reference](docs/site/reference/parameters.md).
- [CLI and Python API](docs/site/reference/interfaces.md).
- [Data dictionary](docs/site/reference/data-dictionary.md).

Build the searchable site with `mkdocs build --strict` after installing the docs extra.

## Preview status

Software **0.5.0rc2**; dataset schema **clue-community-1**. No PyPI release is claimed.

**Licensing, ownership clearance and independent reviews remain pending.** Public availability does not grant an open-source or dataset redistribution license. See [licensing](LICENSING.md), [provenance](PROVENANCE.md) and [release reviews](docs/site/maintainers/release.md).

For contributions, see [CONTRIBUTING](CONTRIBUTING.md). The [preserved earlier README](docs/archive/readme-before-release-2026-10-27.md) retains the historical interface context; legacy flat v0.3 data remains supported separately.
