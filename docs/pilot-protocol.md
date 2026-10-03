# Three-model development pilot

This exploratory pilot measures reasoning and evidence gathering on 24 development
cases from 12 hidden worlds. Four worlds at each of 4, 8, and 12 suspects are selected
by Python's seeded PRNG (seed 0) from sorted world IDs. Both density variants stay
paired. Every model receives the same cases, standard prompt, and nine conditions:
complete-evidence deduction, grouped investigation at 25%, 50%, 75%, and 100%
evidence, and the fixed random-topic evidence schedules at those four budgets.
One repeat gives 216 scored episodes per model and 648 total. Native compatibility
probes are additional and are excluded from scored denominators. The existing
744-case test split and all generator/dataset records are unchanged.

The proposed capability roles do not assume a ranking. Four worlds per size are
very few independent clusters; report the curves and paired, world-clustered
bootstrap intervals as exploratory. Random controls supply evidence before the
answer, so the contrast also includes conversation and tool overhead. It is not a
pure causal estimate of evidence-selection skill. Failed/missing episodes count
incorrect and remain separately identified. An incomplete run is not a completed
model comparison.

## Frozen models, runtime, and prices

The manifest `studies/pilot-v0.3.json` records requested Google models
`google/gemini-3.8-flash` and `google/gemini-3.5-flash-lite`, along with returned
model versions for each response in the logs. The local `ollama/qwen3.5:9b`
distribution is pinned to full digest, Q4_K_M quantization, Ollama version, 32,768
context tokens, model context capacity, and hardware in
`studies/qwen3.5-9b-runtime.json`. Runtime drift prevents execution.

Temperature is 1.0, maximum output is 4,096 tokens per call, retries are zero,
episodes have a cumulative 32,768 input-plus-output token allowance and a
600-second deadline, and tool execution is sequential. The runner lowers the
output cap when necessary to stay within the episode allowance. Google uses
medium thinking with candidate and thought tokens charged as output. The local
model uses `think=true`, top_p=0.95, top_k=20, presence_penalty=1.5, and
repeat_penalty=1.0. Ollama's eval_count covers generated tokens including thinking;
it does not expose a separate thinking component. These reasoning settings are
not equivalent across model families. Google takes the maximum of its free native content token count plus tool-schema
overhead, and the previous reported input/output usage plus new tool-result
bytes. This also covers thinking history whose billable size the preflight
endpoint understates.
Ollama bounds the next input using the previous prompt_eval_count plus eval_count
and new tool-result bytes; the first prompt has a UTF-8 bound plus 2,048 overhead.
These checks can stop conservatively and are disclosed. The initial Flash run
used a larger byte bound over thinking history; six early guard failures and
two maintenance/SDK preflight failures and one billed-token allowance violation
remain in the denominator. The three source amendments preserve all requests, costs, original episode IDs, and
source-plan annotations. See the results report before interpreting comparisons.

[Google's standard API pricing](https://ai.google.dev/gemini-api/docs/pricing),
checked October 3, 2026, is frozen at $0.75/$3.75 per million input/output tokens
for Flash and $0.30/$2.50 for Flash-Lite. Thinking is billed at the output rate.
The Flash promotion ends December 31, 2026; the runner refuses the expired
snapshot. The combined ceiling is **$50 including compatibility probes**. No
provider caching, grounding, batch, flex, priority, or external tools are enabled.
Local elapsed time is descriptive; hosted versus local latency is not a model
capability ranking, and API cost excludes local energy/hardware expense.

## Reproduce preparation and the free dry run

From the private repository on `codex/research-readiness`:

```sh
uv sync --locked --extra test --extra inspect --extra metadata --extra providers
ollama pull qwen3.5:9b
uv run --locked clue-benchmark local-runtime --output studies/qwen3.5-9b-runtime.json
uv run --locked clue-benchmark prepare-pilot \
  --local-identity studies/qwen3.5-9b-runtime.json \
  --output studies/pilot-v0.3.json
uv run --locked clue-benchmark study-check studies/pilot-v0.3.json
uv run --locked clue-benchmark run-study studies/pilot-v0.3.json --dry-run
```

`local-runtime` reads runtime metadata without generation. Preparation and dry
runs neither construct generation clients nor load credentials. Re-preparing
with changed implementation, dependency lock, dataset, or runtime produces a new
content-addressed plan. Do not re-freeze an executed plan to evade a spending stop.
The existing full-study preparation, Inspect task construction, and Inspect log
export remain supported, with the original full-test selection, defaults, and
repeats. Full-study execution is outside this pilot; its model settings, runtime,
prices, and funding must be frozen separately.

## Explicit execution and resume

Supply `GOOGLE_API_KEY` through the process environment using a secure local
mechanism. Never put the value in the manifest, repository, report, prompt, or log.
Then explicitly invoke:

```sh
uv run --locked clue-benchmark run-study studies/pilot-v0.3.json
```

The runner checks Google model access/context metadata and the local identity,
then tests native clue requests and final submissions in a synthetic exchange.
It checks usage and thinking accounting and the loaded Ollama context/digest.
A non-generation input-counter check also runs before scored dispatch.
An incompatible model is stopped without substitution or tool emulation. The
Google SDK retains opaque thought signatures in conversation history, disables
automatic function calling, and permits only one HTTP attempt. Ollama uses its
native `/api/chat` tool schema.

The frozen execution directory is `results/pilot-v0.3`. Keep its
**ledger.sqlite3**, including any WAL files while running: it is the authoritative
resume and spending state, intentionally ignored by Git. `cost-ledger.json` is the
reviewable export, not a replacement for that database. A kernel file lock
prevents concurrent runners in the same directory. Each episode ID is marked
started before dispatch, so finished and interrupted episodes are never
reissued by a restart. Failed or interrupted compatibility probes are never
automatically repeated. Resume with the identical invocation and manifest.

Before each Google generation request, the runner durably reserves the maximum
charge for the model's entire input context and the permitted output, then
settles from validated input/candidate/thought usage. Unused reservation is
released only after accounted completion. An exception or missing usage retains
the conservative reservation and stops execution. A restart cannot clear it or
assume zero. Source-only amendments require a new content-addressed manifest,
unchanged cases/settings/prices/funding, preserved episode IDs, completely settled
requests, and the original successful compatibility evidence. They cannot clear
unresolved usage or retry failed compatibility probes. Historical source
annotations and pre-amendment snapshots are retained. Budget exhaustion stops before another request. Provider exception
text, HTTP bodies, headers, and tracebacks are not serialized because they may
contain credentials. The report always keeps all declared scored episodes.

## Outputs and interpretation

- `studies/pilot-v0.3.json`: frozen plan, selected cases/worlds, settings, identities,
  prices, spending limit, source/dependency/dataset hashes, and analysis.
- `results/pilot-v0.3/logs/*.json`: permitted observations, native tool calls,
  results, usage, versions, and separately labeled compatibility logs.
- `results/pilot-v0.3/cost-ledger.json`: per-request reservations, actual costs,
  unresolved costs, model compatibility states, and remaining allowance.
- `results/pilot-v0.3/results.json`: every declared episode, accuracy by size and
  budget, evidence use, invalid actions, completion, tokens, costs, latency,
  paired strategy and model contrasts, world-clustered intervals, and full-study
  cost extrapolation with coverage/limitations.
- `docs/pilot-results.md`: execution status and representative manual inspection.

The larger-study reference is 744 test cases × nine conditions × three repeats =
20,088 episodes per model. API cost extrapolation uses measured pilot episode
costs and world-clustered uncertainty. If execution is stopped or model access is
unavailable, a measured estimate may be unavailable or selectively biased; do
not manufacture a model ranking or claim that incomplete comparisons establish
benchmark discrimination. The frozen token allowance also gives conservative
API-only bounds, discussed in the results report.

Licensing and public publication remain pending. The repository, private answers,
original generator, and datasets retain their existing status.
