# CLI and Python reference

Find the command you need, then open the advanced evaluation details only when you need them.
{.lead}

## Find a preset

```sh
clue-benchmark presets list
clue-benchmark presets show quickstart
```

`clue-benchmark --help` lists every installed command. `clue-benchmark --version` prints the software version.

## Generate and inspect

Generate with **one** configuration source: `--preset NAME` or `--config PATH`.

```sh
clue-benchmark generate-dataset \
  --preset quickstart \
  --output runs/demo
```

| Command | Purpose |
|---|---|
| `explain-config --preset quickstart` | Show resolved values and field descriptions. |
| `profile-dataset --preset quickstart` | Profile a declared generation configuration. |
| `validate-dataset runs/demo` | Check the bundle and independent semantics. |
| `inspect-case runs/demo --agent 0` | Show one agent's public evidence. |

`--output` and `--workers` override values from the selected preset or configuration file. `explain-config` accepts the same selectors and overrides. Use `--case-id ID` to inspect a specific case.

## Export public evidence

```sh
clue-benchmark export-public runs/demo \
  --agent 0 \
  --output runs/agent.jsonl
```

Only allowlisted public case/report fields are exported. Give the agent this file, not the evaluator bundle.

## Replay a saved example

```sh
clue-benchmark examples replay nuisance-followup \
  --output runs/nuisance
```

| Example name | What it recomputes |
|---|---|
| `distributed-evidence` | Solver information controls on historical worlds. |
| `nuisance-followup` | Initial, extension and exploratory combined measured results. |
| `measured-results` | All packaged historical panels with separate study/settings identities. |

These commands make **no model calls**. The nuisance and measured-results replays accept `--figures` when the optional figures extra is installed.

## Build a readable report

```sh
clue-benchmark report runs/sample-score.json \
  --output runs/sample-report
```

Open **`runs/sample-report/index.html`**. Reports include escaped text, exact source JSON and machine-readable output. They never run inference.

## Use Python

```python
from clue_benchmark import (
    evaluate_agent,
    export_public,
    generate_dataset,
    inspect_case,
    resolve_config,
    validate_dataset,
)

config = resolve_config(
    name="quickstart",
    output="runs/python-demo",
)

generate_dataset(config)
validate_dataset("runs/python-demo")

export_public(
    "runs/python-demo",
    "runs/python-agent.jsonl",
    agent_id=0,
)

public_case = inspect_case("runs/python-demo", agent_id=0)
print(public_case["rules"])

result = evaluate_agent(
    "runs/python-demo",
    lambda view: {"kind": "abstain"},
)
```

Also available: `CommunityConfig`, `generate_case`, `partition`, `score`, `profile_dataset` and `iter_cases`. The latter streams public bundle rows.

!!! warning "A public view is not process isolation"
    `evaluate_agent` supplies copies of public fields to a trusted callable; the evaluator still owns the labels. Run untrusted code in a separate process with exported public files, then score its returned actions in the evaluator process.

## Supported final actions

Name a listed **internal suspect ID**, not its display name:

```json
{"kind": "answer", "target": "S01"}
```

Or abstain:

```json
{"kind": "abstain"}
```

Native tools are `answer(target)` and `abstain()`. Missing, malformed or extra actions count as **protocol failures**, separately from wrong answers on sufficient evidence.

## Paid evaluation: preparation and execution

Preparation and dry runs work without provider credentials. Actual execution is separately authorized.

<details markdown="1">
<summary>Prepare an evaluation plan</summary>

```sh
clue-benchmark prepare-community-evaluation runs/demo \
  --models models.json \
  --output plan.json \
  --ceiling-microdollars 1000000
```

The example ceiling is **$1.00**. Preparation freezes explicit models, prices and settings; it does not spend or authorize that amount.

Defaults:

- **Conditions:** complete, independent private views and sharing.
- **Graph:** complete; other choices are star, ring and chain.
- **Sharing:** three rounds, at most 64 reports per message.
- **Repeats:** one.
- **Input format:** `structured_text`.

`--input-view text_only` omits formal constraints. Keep those results separate from structured-text results.

Each model record supplies `id`, `vendor`, `model`, `settings`, `context_tokens`, `input_microdollars_per_million_tokens` and `output_microdollars_per_million_tokens`.

An optional `identity` is an exact expected returned model string; `tokenizer_identity` is descriptive. Vendor-specific settings are validated. Billed output allowances include thinking where applicable.

One dollar equals **1,000,000 microdollars**. Serialized-byte bounds include tool overhead. Context overflow is rejected, never truncated.

</details>

<details markdown="1">
<summary>Dry-run, execution and durable budget controls</summary>

```sh
clue-benchmark run-community-evaluation plan.json \
  --dataset runs/demo \
  --output runs/evaluation \
  --dry-run
```

Actual execution needs `--execute --authorization human.json` with a human, plan-bound contract. The command never creates approval.

- Request timeout: **600 seconds**.
- Automatic retries: **zero**.
- Persistent SQLite reservations survive interruptions and concurrent launches.
- Settled usage plus unresolved maximum reservations must fit the plan cap.
- Unknown usage or identity/resource breaches stop execution and retain a conservative hold.

Do not edit ledger balances or assume unresolved calls were free. The completed $10.00 follow-up used one shared allowance across child plans and probes; a separate cap per arm was not allowed.

</details>

## Files, errors and concurrent runs

- **Success summaries:** JSON on stdout.
- **Invalid or incomplete work:** exit status 2 with an actionable error on stderr.
- **Exports, reports and replays:** refuse an existing destination.
- **Generation:** resumes only a matching source/config checkpoint. Complete matching datasets return without being regenerated or rewritten.
- **Frozen evaluations:** reject source/config drift.

<details markdown="1">
<summary>Atomic writes and concurrency guarantees in 0.5.0rc2</summary>

Generation and native evaluation take exclusive per-directory locks on Linux and macOS. Simultaneous writers receive a short error.

A request that loses an atomic budget reservation is never dispatched. Ledger identity creation is serialized. Unknown usage still stops execution and holds the maximum.

JSON writes use unique temporary files and atomic publication. Public exports and new evaluator outputs do not overwrite existing files. An occupied evaluator output is rejected before calling the agent.

Reports validate their source before creating output, escape text, retain exact JSON, and keep phase tables keyboard-scrollable.

</details>

## Advanced reproduction and legacy commands

<details markdown="1">
<summary>Prepare, run or analyze the original follow-up protocol</summary>

`prepare-nuisance-followup` prepares matched inputs and maximum costs offline. It grants no execution permit.

```sh
clue-benchmark run-nuisance-followup runs/followup
```

This preflights the original frozen study offline. Explicit execution requires `--execute --authorization human.json`. It serializes the study, checks child ceilings, and stops later jobs after unknown usage or a failed compatibility probe. Fixed child ledgers prevent replay on resume.

The original manifest binds 96 scored slots plus at most two probes. The final expansion is recorded separately; the closed allowance cannot be reused.

```sh
clue-benchmark analyze-nuisance-followup runs/followup \
  --output runs/followup-analysis
```

Analysis preserves never-dispatched slots. Incomplete panel accuracy and paired effects remain null until completion. Completed analyses use world-level attempt means, descriptive cluster bootstrap, exact sign-flip analysis and between-model differences. No model is called.

</details>

<details markdown="1">
<summary>Unpack an explicit reproduction archive</summary>

```sh
clue-benchmark unpack-archive study.tar.gz \
  --sha256 PUBLISHED_HASH \
  --output runs/unpacked
```

Use the actual published hash, not the placeholder above. The command verifies it before extraction and rejects links, traversal and duplicate paths.

The default uncompressed limit is one billion bytes; override with `--maximum-bytes`. Full study archives are separate from the public sanitized outcome downloads and remain pending review where not released.

</details>

<details markdown="1">
<summary>Legacy v0.3 interfaces</summary>

Flat `generate`, `validate`, `export`, the legacy `Config` API and v0.3 archives retain their original shapes. They are separate from community bundles.

Old investigation/request-clue interfaces are historical. Current conditions are complete evidence, independent private views and bounded forwarding.

</details>
