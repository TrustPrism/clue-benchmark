# First dataset in five minutes

Use Python 3.12 or newer. The release candidate is private: install the reviewed local wheel supplied by the maintainer. Do not upload it or infer redistribution rights from an installation example.

```sh
python -m pip install /path/to/trustprism_clue_benchmark-0.5.0rc2-py3-none-any.whl
clue-benchmark generate-dataset --preset quickstart --output runs/demo
clue-benchmark validate-dataset runs/demo
clue-benchmark export-public runs/demo --agent 0 --output runs/agent.jsonl
```

Run from any working directory. `runs/demo` is relative to that directory. Generation prints a JSON summary with `complete: true` and validation prints `status: verified`. The preset requests one single-agent case with exactly four necessary reports. It uses bounded search; exhaustion is an explicit incomplete result, never an uncertified puzzle.

Inspect the actual evidence:

```sh
clue-benchmark inspect-case runs/demo --agent 0
clue-benchmark presets list
clue-benchmark presets show quickstart
clue-benchmark explain-config --preset quickstart
```

`agent.jsonl` contains public case/report rows. It does not contain a solution, certificate, manifest, checkpoint or provider receipt. The original directory is an evaluator bundle; give your agent only the exported file.

## Submit a sample response offline

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

This deliberately conservative agent sees only public fields. Its action is valid, but abstaining with sufficient evidence is unnecessary; it will not receive a correct or supported answer score. `correct`, `supported`, `protocol_valid`, `sufficient_evidence` and `ambiguous_evidence` are separate booleans.

Read the result locally:

```sh
clue-benchmark report runs/sample-score.json --output runs/sample-report
```

Open `runs/sample-report/index.html`. It links the exact saved JSON and displays escaped text. No network request or inference occurs.

## Files and resuming

The [data dictionary](../reference/data-dictionary.md) describes the five bundle files. Matching generation checkpoints resume with the same sources/config. A changed source or config is rejected; use a new directory. Exports, reports and replays refuse an existing destination. Never edit a frozen measured run or a ledger to bypass an error.

After rights clearance and actual publication, the installation command may become `python -m pip install trustprism-clue-benchmark`. It is not a claim that this candidate is already publicly available.


Replay the final measured nuisance study without credentials:

```sh
clue-benchmark examples replay nuisance-followup --output runs/followup
```

The report separates the original eight-world phase, four-world expansion and
exploratory combined result; all 144 scored assignments and the combined $10
accounting are bundled as sanitized data.
