# Clue Benchmark — private research preview

A reproducible benchmark of **deduction** and **evidence gathering** in generated mystery puzzles. Each complete puzzle has truthful clues and exactly one feasible murderer. Attribute assignments need not be unique.

**Status:** private v0.2 preview. Licensing and public publication are pending the owner's decision. No paid model experiments have been run. The included baselines are symbolic programs, not evidence about LLM performance.

## Install

Python 3.11–3.14 is covered by the CI matrix. Development was verified on macOS ARM64 with Python 3.14. Use the cross-platform lockfile for reproducible dependencies:

```sh
python -m pip install uv
uv sync --locked --extra test --extra inspect
uv run --locked clue-benchmark --help
```

A minimal install is `python -m pip install .`; it installs the generator and CLI without Inspect. The package name is `trustprism-clue-benchmark`, the Python import is `clue_benchmark`.

## Try it

```sh
clue-benchmark generate --seed 42 --suspects 4 --clues 8 --count 10 --workers 2 --output bank.json
clue-benchmark validate bank.json
clue-benchmark export bank.json --format public --output public.jsonl
clue-benchmark export bank.json --format study --output study.json
clue-benchmark evaluate bank.json --output results.json
```

The generator resumes from `bank.json` only if the configuration, seed range, requested count, generator version, and OR-Tools version match. A completed run exits 0; configuration errors, unresolved validation, or an underfilled bank exit 2. Use a different output path when changing a configuration.

```python
from clue_benchmark import Config, Environment, generate, public_puzzle

result = generate(Config(suspect_count=8, clue_count=12), seed=42)
if result["status"] != "ok":
    raise RuntimeError(result["diagnostics"])
case = result["case"]
all_evidence = public_puzzle(case)  # deduction track

env = Environment(case, budget_fraction=0.5)  # investigation track
observation = env.reset()
response = env.request_clue(observation["queries"][0]["query_id"])
remaining_by_topic = response["inventory"]
env.submit_answer("S01")
score = env.score()  # evaluator-side only
```

Agents receive serialized observations and the two allowed tools, **not the Python environment object**, private JSONL, seeds, targets, or diagnostic files. This is an evaluation protocol, not a security sandbox for arbitrary untrusted Python agents.

Investigation protocol 1.1 spends evidence budget only when a clue is revealed. Unknown or exhausted queries count as invalid requests against a separate, disclosed request limit. Every response includes current counts for all topic IDs without repeating previously revealed clues. The agent chooses topics; clues within a topic arrive in a fixed, seeded order. The primary comparison is accuracy at each evidence budget, with budget-averaged accuracy as an optional summary.

## Included research artifacts

- `data/v0.2`: 390 verified worlds: 30 development and 100 test worlds for each of 4, 8, and 12 suspects. Every bank requires indirect evidence for a unique murderer. Deduction and investigation share each world's finite bank. `data/v0.1` remains archived.
- `data/v0.2/public`: deduction inputs only. `private`: evaluator records with answers. Both remain in the private repository.
- `results/baselines-v0.2.json`: aggregate outcomes and world-clustered 95% bootstrap intervals for 9,000 episodes. Raw episode logs are regenerated locally when needed.
- `results/performance-v0.2.json`: measured comparison with the imported generator; distributions differ.
- `results/weight-sensitivity-v0.2.json`: fixed-seed audit of how alpha and beta change accepted clue types; it is not a model-difficulty study.
- [Technical report](docs/technical-report.md), [dataset card](docs/dataset-card.md), [protocol](docs/protocol.md), and [configuration](docs/configuration.md).

Reproduce the suite and free experiments:

```sh
clue-benchmark suite --workers 2 --output data/v0.2
clue-benchmark evaluate data/v0.2/private/test.jsonl --repeats 3 --summary-only --output results/baselines-v0.2.json
python scripts/profile_generation.py --seeds 10
python scripts/audit_dataset.py
python scripts/check_release.py
```

The suite writes resumable checkpoints under `data/v0.2/checkpoints/` while generating. They are ignored by Git because the versioned dataset and its manifest are the release artifacts. Omit `--summary-only` and choose a local output path if you need raw baseline episodes.

Alpha now controls the probability of using direct attribute evidence rather than a relationship exclusion for each innocent suspect. Beta affects positive relationship anchors and filler selection. Solver checks and rejection rules still change the accepted distribution. The release configuration requires at least two indirect clues and verifies that removing them destroys uniqueness; this is a structural property, not calibrated model difficulty or reasoning depth.

## Optional model evaluation

The optional adapter follows [Inspect's task and tool interfaces](https://inspect.aisi.org.uk/tutorial.html). It never selects a paid model automatically. After choosing a model and budget separately:

```python
from inspect_ai import eval
from clue_benchmark.inspect_adapter import clue_benchmark

task = clue_benchmark("data/v0.2/private/test.jsonl", track="investigation", budget_fraction=0.5)
# eval(task, model="provider/model", log_dir="model-logs")
```

The adapter uses exact `submit_answer` scoring, a 32,768-token episode cap, 4,096 maximum output tokens per call, a 120-second episode limit, and only benchmark tools. Inspect records prompts, model settings, usage, and transcripts. Free mock-model integration tests verify tool execution and answer isolation.

## Development and provenance

```sh
uv run --locked pytest -q
uv run --locked ruff check src tests scripts
uv run --locked ruff format --check src tests scripts
uv run --locked python -m build
```

`main` began as an exact imported working-tree snapshot; development is on `codex/benchmark-v1`. `PROVENANCE.json` records original file hashes, source commit, and original uncommitted status. `legacy/` retains that baseline for comparisons, including its known limitations. It is not installed with the package and must not be used to score this benchmark. The new batch API starts with the requested seed, resolving the legacy skipped-seed behavior.

The original `TrustPrism/clue-generator` repository and local directory are untouched. [LICENSING.md](LICENSING.md) describes why this preview is not a public open-source release yet.
