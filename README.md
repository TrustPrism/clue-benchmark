# Clue Benchmark — private research preview

A reproducible benchmark of **deduction** and **evidence gathering** in generated mystery puzzles. Each complete puzzle has truthful clues and exactly one feasible murderer. Attribute assignments need not be unique.

**Status:** private v0.3 preview. Licensing and public publication are pending the owner's decision. No paid model experiments have been run. The included baselines are symbolic programs, not evidence about LLM performance. V0.3 measures structural properties rather than requiring every case to contain an essential cross-attribute clue; see the [revised design](docs/v0.3-design.md).

## Install

Python 3.11–3.14 is covered by the CI matrix. Development was verified on macOS ARM64 with Python 3.14. Use the cross-platform lockfile for reproducible dependencies:

```sh
python -m pip install uv
uv sync --locked --extra test --extra inspect --extra metadata
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
clue-benchmark audit bank.json --output audit.json
clue-benchmark duplicate-audit bank.json --output duplicates.json
clue-benchmark review-packet bank.json --output review.json
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

Investigation protocol 2.0 spends evidence budget only when a clue is revealed. Unknown or exhausted queries count as invalid requests against a separate, disclosed request limit. Every response includes current counts for all topic IDs without repeating previously revealed clues. The agent chooses typed topics; clues within a topic arrive in a fixed, seeded order. Topic labels distinguish crime values, crime comparisons, suspect attributes, suspect comparisons, and cross-attribute relationships. The primary comparison is accuracy at each evidence budget, with budget-averaged accuracy as an optional summary.

## Included research artifacts

- `data/v0.3`: paired factorial private suite targeting 480 worlds and 960 cases. It varies suspect count, four/five attributes, value reuse, clue density, and standard/comparison/cross-attribute proof routes. A five-attribute/high-reuse combination is held out of development. Deduction and investigation share each case's finite bank.
- `data/v0.2`: archived 390-world pilot requiring indirect evidence. `data/v0.1` remains archived.
- `data/v0.3/public`: deduction inputs only. `private`: evaluator records with answers. Both remain in the private repository.
- `results/structure-v0.3.json`: bounded structural diagnostics for all 960 cases; `results/duplicates-v0.3-test.json`: close-bank audit; `results/wording-review-packet-v0.3.json`: public-only review packet with signoff pending.
- `results/candidate-trajectories-v0.3.json`: feasible-murderer counts across stored clue order for a deterministic 72-case sample.
- `results/baselines-v0.3-dev.json` and `results/baselines-v0.3-test.json`: free symbolic policies at each evidence budget. The test file contains no paid model outcomes.
- `results/topic-choice-v0.3.json`: paired, world-clustered 75%-budget policy gap; `results/performance-v0.3.json`: full-suite runtime and memory profile.
- `results/legacy-comparison-v0.3.json`: fresh small-seed generator comparison; algorithms and accepted distributions differ.
- [V0.3 technical report](docs/technical-report-v0.3.md), [dataset card](docs/dataset-card-v0.3.md), [protocol](docs/protocol.md), and [design rationale](docs/v0.3-design.md).
- `results/baselines-v0.2.json`: aggregate outcomes and world-clustered 95% bootstrap intervals for 9,000 episodes. Raw episode logs are regenerated locally when needed.
- `results/performance-v0.2.json`: measured comparison with the imported generator; distributions differ.
- `results/weight-sensitivity-v0.2.json`: fixed-seed audit of how alpha and beta change accepted clue types; it is not a model-difficulty study.
- The v0.2 [technical report](docs/technical-report.md) and [dataset card](docs/dataset-card.md) remain archived for comparison; [configuration](docs/configuration.md) documents current controls.

Reproduce the suite and free experiments:

```sh
clue-benchmark suite-v03 --workers 2 --output data/v0.3
clue-benchmark evaluate data/v0.3/private/test.jsonl --repeats 3 --summary-only --output results/baselines-v0.3.json
clue-benchmark audit data/v0.3/private/dev.jsonl data/v0.3/private/test.jsonl --output results/structure-v0.3.json
clue-benchmark duplicate-audit data/v0.3/private/test.jsonl --output results/duplicates-v0.3-test.json
clue-benchmark review-packet data/v0.3/private/dev.jsonl --output results/wording-review-packet-v0.3.json
python scripts/compare_topics.py data/v0.3/private/test.jsonl --output results/topic-choice-v0.3.json --repeats 1
python scripts/candidate_trajectories.py data/v0.3/private/dev.jsonl data/v0.3/private/test.jsonl --output results/candidate-trajectories-v0.3.json
python scripts/profile_v03.py --output-root /tmp/clue-v03-profile --report results/performance-v0.3.json --workers 2
python scripts/profile_generation.py --seeds 10 --output results/legacy-comparison-v0.3.json
python scripts/profile_generation.py --seeds 10
python scripts/audit_dataset.py
python scripts/check_release.py
```

The suite writes resumable checkpoints under `data/v0.3/checkpoints/` while generating. They are ignored by Git because the versioned dataset and its manifest are the release artifacts. Omit `--summary-only` and choose a local output path if you need raw baseline episodes.

Machine-readable JSON reports are compact to keep Git diffs small. Use `python -m json.tool results/performance-v0.3.json` to inspect one in a readable layout.

Alpha controls the probability of using direct attribute evidence rather than a relationship exclusion for each innocent suspect. Beta affects positive relationship anchors and filler selection. Solver checks and rejection rules still change the accepted distribution. The v0.3 suite reports how often cross-attribute clues are actually necessary, instead of filtering to force that property.

## Optional model evaluation

The optional adapter follows [Inspect's task and tool interfaces](https://inspect.aisi.org.uk/tutorial.html). It never selects a paid model automatically. After choosing a model and budget separately:

```python
from inspect_ai import eval
from clue_benchmark.inspect_adapter import clue_benchmark

task = clue_benchmark("data/v0.3/private/test.jsonl", track="investigation", budget_fraction=0.5)
# eval(task, model="provider/model", log_dir="model-logs")
```

The adapter uses exact `submit_answer` scoring, a 32,768-token episode cap, 4,096 maximum output tokens per call, a 120-second episode limit, and only benchmark tools. Inspect records prompts, model settings, usage, and transcripts. Free mock-model integration tests verify tool execution and answer isolation.

## Development and provenance

Software 0.3.1 prepares the next research phase without making paid model calls.
The unchanged v0.3 dataset remains the private pilot. The existing targeted menu
is still the API compatibility default. Prepared studies default to an experimental
menu grouping suspect facts by attribute (protocol 2.1-experimental), because
named-topic counts in the legacy menu predict answers above chance without clues.
Grouping removes that particular hint; other shortcuts still need study. See the
[implementation plan](docs/research-readiness-plan.md),
[model study protocol](docs/research-study.md), and
[independent human review workflow](docs/human-review.md), and
[measured readiness results](docs/readiness-results.md).

~~~sh
clue-benchmark compare-investigation data/v0.3/private/dev.jsonl --repeats 3 --summary-only --output results/investigation-readiness-dev.json
clue-benchmark prepare-study --dev data/v0.3/private/dev.jsonl --test data/v0.3/private/test.jsonl --output studies/readiness-v0.3.json
clue-benchmark study-check studies/readiness-v0.3.json
clue-benchmark prepare-review data/v0.3/private/dev.jsonl data/v0.3/private/test.jsonl --output reviews/readiness-packet.json --template reviews/response-template.json
clue-benchmark review-check reviews/readiness-packet.json --output results/human-review-readiness.json
clue-benchmark readiness data/v0.3 --review-report results/human-review-readiness.json --output results/release-readiness.json
mlcroissant validate --jsonld data/v0.3/croissant.json
~~~

The readiness command reports outstanding gates. Add --public to fail while any
public-release gate remains pending. Local Croissant validation and record
loading do not establish that future hosted URLs are accessible or that a
redistribution license has been granted. Investigation diagnostics inspect all
budgets on development data; a positive policy effect is a result to measure,
not a condition used to remove unfavorable cases.

```sh
uv run --locked pytest -q
uv run --locked ruff check src tests scripts
uv run --locked ruff format --check src tests scripts
uv run --locked python -m build
```

`main` began as an exact imported working-tree snapshot; the verified v0.3 preview is on `codex/benchmark-v1`, with readiness work on `codex/research-readiness`. `PROVENANCE.json` records original file hashes, source commit, and original uncommitted status. `legacy/` retains that baseline for comparisons, including its known limitations. It is not installed with the package and must not be used to score this benchmark. The new batch API starts with the requested seed, resolving the legacy skipped-seed behavior.

The original `TrustPrism/clue-generator` repository and local directory are untouched. [LICENSING.md](LICENSING.md) describes why this preview is not a public open-source release yet.
