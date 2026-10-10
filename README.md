# Clue Benchmark

Generate clue datasets with configurable puzzle structure, misleading reports,
text presentation and private information partitions. The generator certifies
whether the evidence identifies the answer and which agent coalitions have
enough information to solve it.

This is the standalone dataset-generator project. Its current software version
is **0.5.0.dev2** and its dataset schema is **clue-community-1**.

## Install and generate

Use Python 3.12 or newer; local verification uses Python 3.14.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install .
clue-benchmark generate-dataset --config examples/basic.json --output runs/basic
clue-benchmark validate-dataset runs/basic
```

Every bundle separates public rules/reports and ownership from private answers
and certificates. Give agents only the appropriate public view:

```python
from clue_benchmark import CommunityConfig, generate_dataset, iter_cases

config = CommunityConfig.from_dict(
    {
        "dataset": {"seed": 7, "output_directory": "runs/my-dataset"},
    }
)
generate_dataset(config)
for record in iter_cases("runs/my-dataset", agent_id=0):
    print(record)
```

## What is configurable

- Puzzle size, domains, clue families and repeated or distinct attribute values.
- Necessary-evidence bounds, entailed additions, independent records, zero to two
  false reports, targeted corruption, connected relational decoys, and unique-answer
  or explicitly ambiguous cases.
- One to eight agents, shared/private replication, exact report quotas, and the
  required size of the smallest sufficient coalition.
- Deterministic names, themes, wording, order and length bounds; token bounds
  require a supplied tokenizer. Evidence can appear early, late or scattered
  throughout an archive; evaluations support text-only inputs.
- Seeds, workers, splits, structural holdouts and certification budgets.

Requested settings are hard constraints. A rejected or unresolved instance does
not silently receive easier settings. Unique-answer cases certify the culprit;
they do not promise a unique complete world.

See the [generator guide](docs/generator.md), [dataset card](docs/dataset-card.md)
and [development workflow](docs/development.md). Current JSON schemas are in
`schemas/`; presets and policy examples are in `examples/`.

## Evaluate and extend

Install `.[providers]` for the evaluation harness. Supply your own model IDs,
settings, context limits and prices to prepare a frozen plan. Dry runs read no
credentials and make no network calls; live execution requires new explicit
authorization. The harness compares complete evidence, private partitions and
bounded forwarding, with a documented adapter for other communication policies.

`examples/demonstrations.py` prepares necessary-evidence/distractor and
complete/distributed-information demonstrations. `examples/large-corpus.json`
profiles 50,000 total records; that volume is separate from the certified number
of necessary clues.

Four one-case bundles in `examples/datasets/` demonstrate truthful, branching,
ambiguous and corrupted evidence. The [large-corpus profile](benchmarks/large-corpus.json)
records a local scaling check, with no model calls.

For focused usefulness demonstrations, the [small pilot](docs/pilot.md) prepares
matched archive-volume and false-report datasets plus a four-agent information
bottleneck experiment. `examples/pilot_suite.py` generates and validates these
offline, freezes a context-checked model plan under one total spending ceiling,
and computes paired world-level contrasts after separately authorized execution.
See the dated [resource comparison](docs/resource-comparison.md) for its rationale.
The [measured Gemini demonstrations](docs/pilot-results.md) contain 269 settled
responses and one preserved provider failure across all three experiments.
Results distinguish unsupported guesses, appropriate abstention and errors with
sufficient evidence. The [checkpoint](docs/pilot-checkpoint.md) records costs.

The [advanced dataset demonstrations](docs/hardness.md) add certified 8/16/32-report
burdens, relational false reports, near-solutions, connected decoys, evidence
placement and an eight-agent bottleneck. `examples/hardness_suite.py` prepares
matched cohorts and frozen experiment plans offline. Small certified examples
and an offline verification report are included; new model measurements are
pending. Existing pilot results and authorizations remain separate.

The original `generate`, `validate` and `export` commands and flat `Config` API
remain available for puzzle-generation compatibility. Retired experiment runners
are not part of the current interface.

## Release status

The software is locally tested. Public release still requires independent language
review, independent reproduction and resolved licensing.
No frontier-model weakness or research novelty is established by software tests.
See [licensing status](LICENSING.md).
