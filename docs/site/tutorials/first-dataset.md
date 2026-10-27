# Your first dataset

Generate a small puzzle, check it, and give an agent only the evidence it is allowed to see.
{.lead}

**You need:** Python 3.12 or newer on macOS or Linux. Installation downloads dependencies; every exercise below then runs offline. No model account or API key is required.

## 1. Install the preview {#step-1-install-the-preview}

Clone the published candidate, then enter its directory:

```sh
git clone \
  --branch v0.5.0rc2 \
  --single-branch \
  https://github.com/TrustPrism/clue-benchmark.git
cd clue-benchmark
```

Create an isolated Python environment and install the package:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

<details markdown="1">
<summary>Already have a built candidate wheel?</summary>

Install that file instead:

```sh
python -m pip install \
  /path/to/trustprism_clue_benchmark-0.5.0rc2-py3-none-any.whl
```

The package is not published to PyPI. Licensing remains pending; installation instructions do not grant redistribution rights.

</details>

## 2. Generate a puzzle {#step-2-generate-a-puzzle}

```sh
clue-benchmark generate-dataset \
  --preset quickstart \
  --output runs/demo
```

The preset asks for **one single-agent case with exactly four necessary reports**. Look for `complete: true` in the JSON summary.

`runs/demo` is relative to your current directory. You can run the installed command from anywhere.

!!! note "If generation stops early"
    Generation uses bounded search. An incomplete result means it did not find enough certified cases within that budget. It never substitutes an uncertified puzzle. See [candidate exhaustion](../reference/troubleshooting.md#when-generation-cannot-finish).

## 3. Validate it {#step-3-validate-it}

```sh
clue-benchmark validate-dataset runs/demo
```

**Expected:** `status: verified`. This checks both the bundle and the puzzle's logical meaning.

## 4. Export the agent's evidence {#step-4-export-the-agent-s-evidence}

```sh
clue-benchmark export-public runs/demo \
  --agent 0 \
  --output runs/agent.jsonl
```

Give your agent **`runs/agent.jsonl`**, not the whole `runs/demo` directory.

- The exported file contains public case and report rows.
- The original directory also contains evaluator answers and certificates.
- The export leaves out solutions, checkpoints, provider receipts and other private fields.

Inspect the public view:

```sh
clue-benchmark inspect-case runs/demo --agent 0
```

## 5. Score a sample agent {#step-5-score-a-sample-agent}

This intentionally cautious agent always abstains:

```python
from clue_benchmark import evaluate_agent

result = evaluate_agent(
    "runs/demo",
    lambda observation: {"kind": "abstain"},
    output="runs/sample-score.json",
    agent_id=0,
)

print(result["episodes"][0])
```

Its response is **valid**, but abstaining is unnecessary when the evidence identifies an answer. Valid format and successful reasoning are different scores.

[See all score meanings](../explanations/pipeline.md#what-a-score-means).

## 6. Open a readable report {#step-6-open-a-readable-report}

```sh
clue-benchmark report runs/sample-score.json \
  --output runs/sample-report
```

Open **`runs/sample-report/index.html`** in your browser. The report also links the exact saved JSON. It makes no model calls.

## Try the measured example

Replay the completed irrelevant-evidence study from saved measurements:

```sh
clue-benchmark examples replay nuisance-followup \
  --output runs/followup
```

The output separates the **initial study**, **final expansion** and **exploratory combined result**. It includes all 144 scored assignments and the closed $10.00 study accounting.

[Read what the study found →](../results/index.md)

## Explore the settings

See the available presets:

```sh
clue-benchmark presets list
```

Inspect the quickstart's resolved settings:

```sh
clue-benchmark presets show quickstart
clue-benchmark explain-config --preset quickstart
```

Start with [worked research recipes](../guides/research-recipes.md), then use the [parameter reference](../reference/parameters.md) for details.

<details markdown="1">
<summary>Existing files, checkpoints and resuming</summary>

- **Generation** can resume a matching checkpoint with the same source and configuration.
- **Exports, reports and replays** need a new destination. They refuse to overwrite an existing one.
- A changed source or configuration needs a new generation directory.
- Do not edit frozen measured runs or ledgers to bypass an error.

The [data dictionary](../reference/data-dictionary.md) describes the five bundle files.

</details>
