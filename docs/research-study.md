# Model study protocol

This document describes the prepared full study. Model measurements are confined
to the separate [development pilot](pilot-protocol.md), whose
[results](pilot-results.md) record execution status. The v0.3 cases remain unchanged. Software 0.3.1 adds study preparation,
explicit menu conditions, and failure-inclusive result export.

## Questions and comparisons

The primary questions are whether a system identifies the murderer with complete
evidence, and how its accuracy changes under four evidence budgets. Compare
agent-selected topics with a fixed random topic schedule on the same case bank.
The fixed schedule supplies the selected evidence before the model answers,
exposes only submit_answer, and makes no solver calls to select clues.

This control separates a partial-evidence reasoning task from interactive
selection, but the difference also includes conversation and tool-use overhead.
It is not a pure causal measure of topic-choice quality. Symbolic policies, which
have exact inference on structured revealed clues, provide a complementary check
on the evidence menu itself.

Report accuracy by suspect count and all four budgets. The declared primary
strategy contrast averages the four budgets and uses paired differences clustered
by hidden world. Report factorial-cell slices, the held-out attribute/reuse
combination, evidence consumed, invalid actions, missing answers, provider
failures, latency, and available tokens. Repeats and the two clue-density variants
of one world stay in one statistical cluster.

The standard prompt is fixed in the plan. An optional deliberate prompt asks the
system to check the logical consequences before answering; selecting it adds a
declared prompt condition. A complete study should use multiple model families
and capability levels, with immutable model versions where providers offer them.
Full-study models remain unselected; the pilot selects three explicitly named models separately.

## Preparation and freezing

~~~sh
clue-benchmark prepare-study \
  --dev data/v0.3/private/dev.jsonl \
  --test data/v0.3/private/test.jsonl \
  --output studies/readiness-v0.3.json
clue-benchmark study-check studies/readiness-v0.3.json
~~~

The prepared file records case-file hashes, package implementation hashes,
dependency-lock hash, runtime dependency versions, literal prompts, generation
settings, protocol, repeats, and analysis. With no model argument its status is
awaiting-model-selection. Preparation does not invoke a provider. One prompt,
the grouped menu, three repeats, and all declared controls imply 20,088 episodes
per selected model on the 744-case test set; pilot costs on development examples
should be estimated before choosing the final study budget.

Selecting explicit models and rebuilding the plan freezes a new plan ID:

~~~sh
clue-benchmark prepare-study \
  --dev data/v0.3/private/dev.jsonl \
  --test data/v0.3/private/test.jsonl \
  --model provider/immutable-model-version \
  --output studies/approved-model-study.json
~~~

This command still makes no model calls. The prepared study defaults to the
attribute-grouped menu, protocol 2.1-experimental. A development audit found that
the legacy targeted menu's named-topic counts predict the murderer above chance
without reading evidence. Grouping removes that particular suspect-count hint;
it does not establish the absence of every shortcut or improved model accuracy.
The Environment and adapter APIs retain targeted protocol 2.0 for compatibility.
Add --topic-mode targeted for a declared legacy comparison, or
--prompt-style deliberate for a declared prompt condition. Scores from different
menus remain separate conditions.

Do not tune the generator or query policy on model test results. Structural and
symbolic test results have already been inspected during v0.3 development.
Disclose that history. If the menu or construction is redesigned in response to
test outcomes, generate and freeze a new untouched final test version. Fresh
seeds mitigate memorization but do not prove the absence of contamination.

## Execution after model and budget authorization

Study task construction checks the frozen plan and yields Inspect tasks without
provider calls:

~~~python
import json
from clue_benchmark.study import study_tasks

plan = json.load(open("studies/approved-model-study.json"))
tasks = study_tasks(plan, root=".")
for model, task in tasks:
    # After a separate approved budget, pass task and model to inspect_ai.eval.
    # Use epochs=1: repeats are already explicit tasks in the plan.
    pass
~~~

The full study remains preparation-only. The separate development pilot adds
`prepare-pilot` and `run-study`, with native provider checks and a frozen $50 ceiling.
A full study needs its own approved spending budget before real execution.
Provider retries default to zero and are frozen as a generation setting; changing
that policy requires a new plan and its cost estimate.
Inspect records native logs, model identifiers, settings, messages, usage, and
errors. Logs include evaluator targets and must not be handed to the agent.
Only request_clue and submit_answer are exposed in the agent-selection condition.

## Results and failure handling

~~~sh
clue-benchmark study-export studies/approved-model-study.json \
  model-logs/*.eval --output results/model-study.json
~~~

The exporter checks plan identity, model identifiers, actual logged generation
settings, episode limits, prompts, protocol, conditions, repeats, and
duplicate samples. Every declared case remains in the denominator: missing logs,
missing answers, and failed samples score incorrect and are counted separately.
Available token counts and latency are aggregated with their coverage counts;
missing measurements are not represented as zero token usage or zero latency.
Cell and paired strategy summaries use world-clustered bootstrap intervals.
Individual budget/slice intervals are descriptive; do not select a favorable
budget after test inspection and present it as a preplanned primary result.

Error analysis should inspect a stratified sample of incorrect and correct
episodes. Label unsupported exclusions, missed relationships, contradictory
attribute assumptions, query misunderstandings, invalid tools, and missing
submissions. Exact answer scoring cannot prove that a correct answer followed a
valid reasoning trace; any trace study needs its own review protocol.

## What this can support

SATBench combines solver consistency with sampled human validation and model
error analysis; ZebraLogic reports model behavior against structural complexity
measures. The corresponding missing evidence here is human interpretation and
measured model behavior, not a required minimum number of complex clues.
Correctness, structure, and empirical model difficulty are separate claims.

Sources: [SATBench](https://aclanthology.org/2025.emnlp-main.1716/),
[ZebraLogic](https://arxiv.org/abs/2502.01100),
[NeurIPS 2026 reviewing guidance](https://neurips.cc/Conferences/2026/EvaluationsDatasetsReviewerGuidelines).
Venue requirements must be rechecked for a future submission.
