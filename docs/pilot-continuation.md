# Development continuation: first $25

This phase is authorized for a **$25 cumulative Gemini ceiling**, including the
original pilot, compatibility probes, and maximum held charges for failed
requests. The project total is **$50**, reconfirmed by the user on 4 October 2026.
Both Gemini models have since stopped on output-cap violations, at $10.138003
committed including maximum holds. Local Qwen continues. The unused funds are
reallocated to $3 calibration, $34 revised study and $2.861997 contingency in the
[budget and study plan](next-study-proposal.md). The current controller cannot
allocate later stages or execute held-out test cases.

The original stopped pilot remains intact in `results/pilot-v0.3` and Git commit
`b8b2ecf`. Its manifest and source hashes refer to that historical implementation.
The continuation has a new manifest, source identity, output directory, and an
audited copy of its durable ledger. All 82 dispatched episodes and 213 requests
are preserved. Completed and failed episodes are never replayed.

## Changes supported by the initial pilot

- The user identified request 213 as HTTP 503. Its missing usage is still unknown:
  the full $0.324813 reservation remains committed. It is explicitly marked held
  under the user's continuation authorization. Future native 503 errors receive
  the same treatment and remain failed scored episodes; automatic retries stay
  zero. Successful responses without usage, unclassified failures, and unresolved
  in-flight requests still stop paid execution. Raw exception text stays out of logs.
- Google's preflight estimate understated billable conversation history. The
  revised guard uses native count plus schema overhead and prior input plus twice
  prior output plus new tool-result bytes, then adds 12.5% and 1,024 tokens of
  headroom. A regression test covers the observed 58-token overrun. Per-request
  input bounds, output caps, and remaining allowances are now saved. This is a
  conservative estimate; an actual provider limit violation still stops that model.
- The schedule first completes missing original pilot episodes, then rotates
  suspect sizes, paired worlds, evidence budgets, random controls, and Gemini
  models. This reduces the condition-coverage bias of a budget stop.
- The original four worlds per size are too few for useful uncertainty estimates.
  Remaining funds can cover more independent development worlds. Google's
  expanded primary comparison excludes the original 12 diagnostic worlds.
- Free Qwen execution has its own runner lock and accounting scope. A paid
  accounting or funding stop cannot prevent the local baseline from completing.

Thinking, temperature, output maximum, cumulative episode tokens, timeout, tools,
prompts, dataset, and local digest otherwise retain their original values. All
latencies are descriptive; hosted/local latency is not a capability ranking.

## Frozen selection and interpretation

Both Gemini models are scheduled for the 216 development cases: 108 paired worlds,
36 per suspect size, nine conditions, one repeat, or 1,944 episodes each. Qwen
completes the original 24 cases / 12 worlds / 216 episodes. There are 4,104 declared
rows, including the 82 historical episodes. The ceiling can stop paid execution
before this maximum is dispatched. Qwen/Gemini contrasts use only shared cases.

The original-pilot cohort has 648 rows across all three models. The expansion
cohort has 3,456 Gemini rows from 96 additional worlds (32 per size). Failures and
missing rows remain incorrect in primary declared denominators, with dispatch,
completion, and infrastructure error counts separately reported. Completed-answer
accuracy is a descriptive conditional measure, subject to completion selection.
World-clustered intervals retain both density variants and all related conditions.

Random controls still provide their selected clues before generation, whereas
investigation requires successive native tool calls. Thus their difference also
includes interaction/thinking overhead. It cannot isolate topic-choice quality.
A later study should match this overhead or explicitly target resource-bounded
agent performance. Evaluator-only evidence feasibility diagnostics help distinguish
ambiguity from answers that contradict revealed clues. They are never given to models.

## Reproduce execution

The authoritative frozen plan is `studies/pilot-v0.3-reserved-recovery.json`;
the authoritative resume/accounting state is
`results/pilot-v0.3-continued/ledger.sqlite3`. Verify worker identities and the
[handoff](HANDOFF.md) before starting a process; do not duplicate a live worker.
The historical plans listed below are audit records, not current resume commands.
Deleting the ledger causes continuation execution to refuse a fresh budget.
Keep it and its WAL files while running; JSON exports can lag the live ledger.

Validation and dry runs make no generation calls:

```sh
uv run --locked clue-benchmark study-check studies/pilot-v0.3-reserved-recovery.json
uv run --locked clue-benchmark run-study studies/pilot-v0.3-reserved-recovery.json --dry-run
```

Only after verifying the corresponding worker has ended and its stop is eligible
under the frozen policy, resume fresh episodes with the existing ledger. Supply
`GOOGLE_API_KEY` securely to the paid runner (or its hidden prompt); never save it
in project files. Google requests stay sequential; local Qwen uses a separate lock.
These commands do not clear an incompatible-model state:

```sh
uv run --locked python scripts/continue_reserved_study.py studies/pilot-v0.3-reserved-recovery.json
uv run --locked clue-benchmark run-study studies/pilot-v0.3-reserved-recovery.json --models ollama/qwen3.5:9b
```

Read-only analysis of execution makes no model calls, but writes derived exports:

```sh
uv run --locked python scripts/export_native_run.py studies/pilot-v0.3-reserved-recovery.json
uv run --locked python scripts/evidence_diagnostics.py studies/pilot-v0.3-reserved-recovery.json
uv run --locked python scripts/report_continuation.py studies/pilot-v0.3-reserved-recovery.json
```

Add `--final` to reporting only after both workers have ended and their locks are
clear. A funding or compatibility stop can leave declared episodes unexecuted.

Filtered runners write provider-family snapshots. The export command takes one
consistent database read snapshot and produces aggregate `results.json` and
`cost-ledger.json`, without constructing a model client or making generation calls.
An incomplete global run returns status 2 even if a filtered local schedule has
finished. Inspect the model states and dispatch counts to distinguish this.

The preparation helpers `prepare_continuation` and `initialize_continuation` are
in `clue_benchmark.continuation`; initialization is a one-time audited migration,
not a resume operation. It cannot overwrite an existing continuation ledger.

All 744 test cases, original generator files, dataset hashes, repository privacy,
and pending licensing/publication are preserved.

## Failed-timeout recovery amendment

After a new Flash-Lite generation timeout returned no usage, the user explicitly
authorized proceeding to fresh episodes below the cap. The historical amendment
`studies/pilot-v0.3-timeout-recovery.json` used a separately hashed controller in
`scripts/continue_saved_study.py`. It retains each failed timeout's full maximum
reservation and score, then restores only compatible, accounted timeout pauses
and dispatches fresh episode IDs. It never retries a closed episode or request,
changes the native implementation, or resets costs. Unknown successful usage,
other unresolved errors, and protocol incompatibilities still stop execution.

The original continuation and pre-controller manifests remain immutable. Qwen
was already running with the preceding continuation manifest and identical native
source/settings; its original row/source identities remain preserved. The final
aggregate export uses the latest manifest and ledger binding. Family snapshots
are historical execution artifacts, not the final aggregate analysis.

A one-time local watcher, `scripts/finalize_continuation.py`, waits for the two
specific running worker processes to finish. It then exports, diagnoses, renders
scientific figures, reruns checks, verifies original costs/privacy/credential
patterns, and commits/pushes only this phase's deliverables. It makes no model
requests and cannot allocate or execute later study stages. Its status is in
`results/pilot-v0.3-continued/completion-state.json`; the final publication receipt
is `/private/tmp/clue-continuation-completion.json`. No recurring job is created.

See [the saved results](pilot-continuation-results.md) and the
[unexecuted next-study proposal](next-study-proposal.md).

## Explicit incomplete-usage override

The resumed Flash run then returned unverifiable usage on request 1711, with a
197-token remaining output cap. The user explicitly approved **“Apply
maximum-charge holds and continue.”** The current manifest is
`studies/pilot-v0.3-reserved-recovery.json`, with separately hashed controller
`scripts/continue_reserved_study.py`. The prior proposal remains non-executable
and preserved as the pre-authorization record.

The controller holds full maximum charges for failed timeouts and unverifiable
usage, preserves the failed episode and every request/score, and proceeds only
to fresh episode IDs under the cumulative $25. Actual usage and actual charges
remain unknown in the ledger; neither zeros nor invented token counts are used.
These failures are excluded from usage-complete cost extrapolation. Native
incompatibilities and other unclassified unresolved errors still stop execution.
The override is a recorded policy change, not a claim that accounting succeeded.
`usage-recovery-amendment-audit.json` and `accounting-recovery.json` retain the
migration and every subsequent recovery. Later study allocations remain unspent.
