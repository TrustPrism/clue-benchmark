# Small experiments that demonstrate the resource

The aim is to demonstrate useful experimental controls, then measure a small
model panel. It is not to prove a new agent algorithm or complete a topology
study. Offline certificates show what information is available; model results
show whether a particular model can use it. Keep these conclusions separate.

## Demonstration 1: Required evidence versus archive volume

- Question: Does adding irrelevant information reduce success when the target
  evidence and correct answer are unchanged?
- Conditions: certified minimum evidence of 4 or 8 reports, crossed with 0,
  100, or 1,000 independent records. Complete evidence goes to one agent.
- Matching: within each burden stratum, all three variants use the same world
  and the exact same target reports. Accept or reject the entire matched group.
- Outcome: paired change in supported accuracy, plus correctness, abstention,
  protocol failures, input/output tokens, latency and cost.
- Interpretation: the distraction contrast is controlled. Comparing 4 against
  8 required reports also changes suspect count (4 versus 8), so it is a burden
  and size comparison, not an isolated causal effect of minimum evidence.
- Limit: the independent records are structurally recognizable as unrelated.
  This is a transparent archive-volume control, not realistic adversarial prose
  or 1,000 necessary clues. The 50,000-record preset remains a separate scaling
  exercise, excluded from this paid pilot.

## Demonstration 2: Reasoning despite false reports

- Question: Can models use the declared reliability rule rather than assume
  every statement is true?
- Conditions: 0, 1, or 2 actual false reports. Every condition publishes the
  same **at most two false reports** rule; agents do not receive the actual count
  or the identities of corrupted reports.
- Matching: the same four-suspect, six-attribute world and original 30-report
  core; corruption substitutes statements. All three final cases must still
  have the same certified unique answer. The accepted cohort is consequently
  conditional on surviving all requested corruptions; report rejections.
- Outcomes: paired supported accuracy and abstention, with a reliability-aware
  solver and a solver assuming all statements true as diagnostic controls.
- Limit: minimum sufficient evidence can change after corruption. Publish its
  verified bounds; do not attribute differences exclusively to deceptive text.
  These are factual false reports, not prompt injection attacks.

## Demonstration 3: Information bottlenecks and recovery

- Question: Can models solve after enough evidence reaches the decision-maker,
  and abstain when communication leaves several answers possible?
- Dataset: eight suspects, twelve reports, four agents, no shared/private
  replication. The full team is the smallest sufficient coalition.
- Conditions: complete evidence; independent private agents; deterministic
  forwarding on star/ring/chain for one round, and chain for three rounds.
  Each directed edge can carry at most 64 original reports each round.
- Matching: every condition uses the same cases and partition. Agent 0 is the
  sharing decision-maker. Forwarding sends evidence by public ID order and
  never consults evaluator labels; it is not model-generated discussion.
- Outcomes: sufficient-evidence delivery, supported/correct accuracy,
  abstention on insufficient views, protocol failures and communication cost.
  Average independent agents within each world before comparison; do not call
  this a team vote or count agents as independent samples.
- Interpretation: a model's failure with sufficient delivery is different from
  a protocol that never delivers enough information. Graph-specific outcomes
  are descriptive demonstrations, not a general ranking of network topologies.

## Generate, inspect and freeze

```sh
python examples/pilot_suite.py prepare --output runs/pilot --count 8
python examples/pilot_suite.py plan --output runs/pilot \
  --models examples/gemini-pilot-models.json --ceiling-microdollars 20000000
python examples/pilot_suite.py analyze --output runs/pilot
```

There are ten datasets and fourteen evaluation jobs. With eight worlds per arm,
two models and one repetition there are 288 assigned requests. The number of
distinct underlying worlds can be smaller than the sum across groups; all
variants are matched by world ID and keep the same split. The suite records
accepted seeds, bounded-search rejections, source identity, bundle hashes and
diagnostics. Receipts permit resuming generation with unchanged inputs.

`diagnostics.json` includes independent bundle validation, evidence bounds,
coalition sizes and solver controls. `pilot-plan.json` identifies the entire
evaluation. `pilot-results.json` says results are pending until real runs exist;
it does not substitute solver controls or fabricated responses for model data.
Small example bundles and a compact offline profile accompany the repository.
The [current partial measurements](pilot-results.md) and [execution checkpoint](pilot-checkpoint.md)
record the local run; they are separate from the reusable preparation defaults.

Dry runs make no credential reads or network calls. Preflight checks every
serialized provider request, including rules, structured constraints and tool
overhead, using a conservative byte-based token bound. Oversize requests stop
planning; evidence is never silently truncated. The model receives both text
and structured constraints, so this pilot does not isolate natural-language
comprehension. Token counts reported after execution are provider receipts.

The **single $20 ceiling** is divided across the fourteen plans. Their ceilings
sum to $20, with immutable per-job ledgers and no retries. Planning rejects a
conservative maximum above the total limit rather than silently shrinking the
experiment. Usage uncertainty stops the whole pilot and retains reservations.
Pacing waits ten seconds before each dispatched request; this is a conservative
schedule, not a guarantee about the user's project-specific quota. A provider
rate-limit failure stops execution. Confirm project RPM/TPM/RPD in AI Studio
before a live run. Other processes using the same project are outside this
pilot's accounting.

## Selected Gemini settings and approval

The user authorized selecting Gemini models and a total $20 ceiling. The preset
compares stable `gemini-3.5-flash-lite` and `gemini-3.8-flash`, both at low thinking,
temperature zero and a 4,096-token output cap. Provider documentation checked
2026-10-09 lists a 1,048,576-token input limit and a 65,536-token output limit for
both models. The declared context bound conservatively reserves output as well.
See [Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite),
[Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash) and
[thinking levels](https://ai.google.dev/gemini-api/docs/thinking).

The frozen standard paid rates per million input/output tokens are $0.30/$2.50
for Flash-Lite and $0.75/$3.75 for Flash, including thinking in output. Flash's
listed rates change on 2027-01-01; recheck rates and prepare a new plan for a
later run. No caching, search, batch or other paid tools are requested.
Sources: [pricing](https://ai.google.dev/gemini-api/docs/pricing) and
[project limits](https://ai.google.dev/gemini-api/docs/rate-limits).
API access to the selected models is not verified until execution; missing access
is a retained failure and never triggers automatic model substitution.
Both IDs returned responses in the dated local pilot; access elsewhere still
depends on the supplied project and credentials.

Actual execution still requires fresh approval of the concrete pilot ID. Supply
an authorization JSON with exactly these fields, filling values from the plan:

```json
{
  "schema_version": "clue-pilot-authorization-1",
  "pilot_id": "exact pilot_id from pilot-plan.json",
  "approved_by": "authorizing human",
  "approved_at": "approval timestamp",
  "spending_ceiling_microdollars": 20000000,
  "max_requests": 288
}
```

Keep the authorization in ignored `runs/`. Keep the API key out of chat, datasets
and Git; the native runner reads `GEMINI_API_KEY` from its environment only during
authorized dispatch. Run:

```sh
python examples/pilot_suite.py run --output runs/pilot \
  --authorization runs/pilot/authorization.json
python examples/pilot_suite.py analyze --output runs/pilot
```

Planning never writes approvals. The runner derives each existing harness
authorization only from the supplied pilot-bound approval, after checking all
plans and their total ceiling. Reuse the same output directory when resuming;
already dispatched requests are never repeated. New runs require new approval.

## Reporting without overclaiming

- Keep all assigned failures and unattempted assignments in the report.
- Report supported and sampled-answer accuracy separately, alongside abstention
  and delivery. A lucky correct answer to an ambiguous view is unsupported.
- Compute contrasts within matched worlds; average repetitions/agents first.
  Use descriptive paired world-bootstrap intervals. Eight worlds per arm is
  exploratory and cannot establish a robust leaderboard or broad model weakness.
- Inspect failures without changing the frozen pilot. Use a separately seeded
  cohort if those findings guide new controls or harder settings.
- If both models perform well, report that positive result: the settings provide
  calibration cases. If performance falls, localize whether corruption, volume,
  evidence delivery or inference causes the drop. Do not promise a drop in advance.
- Publication still requires independent English review, independent reproduction,
  resolved ownership/licenses, and measured results. See the dated
  [resource comparison](resource-comparison.md).
