# Clue benchmark handoff

Updated 2026-10-04 09:59 America/Chicago. This is the entry point
for continuing this work. Live numbers below are snapshots, not final results.

## Objective and user instructions

Evaluate Gemini Flash, Gemini Flash-Lite and local Qwen on deduction and active
clue investigation. Finish the authorized first allocation, review what failed,
then improve the design before any second allocation or main study.

The latest user instruction reconfirms **$50 total Gemini API credits for the
project** and delegates splitting that amount. Both paid models have now stopped
on native output-cap violations. Preserve their **$10.138003 total commitment** and
closed failed episodes. Reallocate unused capacity to **$3 calibration, $34 revised
study, $2.861997 contingency**; the [budget plan](next-study-proposal.md) records the
revision from the initial $25/$3/$20/$2 split. The old $25 execution ceiling remains
frozen for audit, not as a spending target. Every amount includes prior calls,
probes and maximum failure holds. Never reset the ledger or treat $50 as additional
funds. Later stages still need review, offline checks and protocol freezes.

The user explicitly approved **“Apply maximum-charge holds and continue”** after
timeout and unverifiable-usage failures. Retain the entire charge bound and failed
score, then continue with fresh episodes. Never replay a closed failed request or
episode. Native incompatibility and unclassified unresolved errors still stop the
affected execution; automatic generation retries remain zero.

Continue the requested documentation cleanup conservatively. The completed
readiness plan is now in `docs/archive/`; README lists the canonical reading order
and execution notes use only the current manifest for resume commands. Historical
scientific/accounting records and checksum-bound paths remain intact. Do not expand
the project into a reporting/dashboard effort while the study remains unfinished.

## Workspace, access and security

- Work in `/Users/neevgupta/texas/clue-benchmark`, **not** the chat's default
  `/Users/neevgupta/texas/trustprism`. Do not touch unrelated user changes there.
- Branch: `codex/research-readiness`; remote private repository:
  `https://github.com/TrustPrism/clue-benchmark.git`.
- Previous execution checkpoint: `0e6df6d`, “Preserve maximum charges and continue
  first-$25 development evaluation”. Earlier: `9a3bb3a` continuation,
  `b8b2ecf` incomplete original pilot, `df6004d` native implementation.
- This checkout is outside the current chat's writable roots. Use approved
  escalated execution for writes/network and SQLite WAL-related access as needed.
  Read/check repository and ancestor instructions in a new session.
- Documentation checkpoint `b95d0d5` records the budget and cleanup. An initial
  GitHub privacy check was rejected before execution for lack of explicit saved
  credential approval. The user subsequently answered **“Verify and push”** for
  this private repository and checkpoint. The authorized GitHub API check on
  4 October confirmed `TrustPrism/clue-benchmark` is private. That approval covers
  verification and pushing this documentation checkpoint; do not request it again.
  The pre-existing completion watcher has not been modified.
- Google credentials were supplied to a hidden prompt and exist only in the paid
  process's memory/environment. Never print, persist, commit, or include them in
  handoffs. A new chat does not necessarily inherit this environment. If restart
  requires credentials, request secure local availability without pasting them.
- Original request is the attachment
  `/Users/neevgupta/.codex/attachments/5b044bae-d9d6-4fc9-91d2-8ce55244e563/Pasted text.txt`.
- No new chats, goals or recurring automations were created. A one-time completion
  watcher is running. Do not spawn extra agents unless explicitly authorized.

## Current execution: check before doing anything

Authoritative manifest: `studies/pilot-v0.3-reserved-recovery.json`.
Manifest identity:
`d50fe24b4082a8b9d66dd0b90ac6f209a70134dee14d5c36cbb05a62f4e890aa`.
Authoritative resume/accounting state:
`results/pilot-v0.3-continued/ledger.sqlite3` (ignored, with live WAL/locks).
Do not delete, replace, re-prepare or copy it inconsistently while workers run.
Exported JSON/report files can lag this ledger.

Verified processes at handoff:

- **Ended:** paid controller PID **12383**, historical tool session **75942**:
  `.venv/bin/python scripts/continue_reserved_study.py studies/pilot-v0.3-reserved-recovery.json`
- Local Qwen PID **14518**, tool session **71563**:
  `.venv/bin/clue-benchmark run-study studies/pilot-v0.3-reserved-recovery.json --models ollama/qwen3.5:9b`
- Completion watcher PID **14590**, tool session **73678**:
  `.venv/bin/python scripts/finalize_continuation.py studies/pilot-v0.3-reserved-recovery.json --paid-pid 12383 --local-pid 14518 --plot-python /private/tmp/clue-pilot-plots/bin/python`

PIDs and tool sessions are historical pointers: verify process command/start time
before interacting; never kill a newly reused PID. Do not start duplicate workers.
Paid requests are sequential; Google and local use separate family locks.

Latest coherent ledger snapshot (2026-10-04T14:59:09.221814+00:00): **674 finished**,
1 local episode in progress, 2,575 native requests. Both Gemini models are
`accounting_stopped` after the native output-cap violations below; Qwen remains
compatible and running. Estimated settled charges $6.311107; held failed maxima
$3.826896; paid in-flight and uncertain reservations $0; total committed
**$10.138003 under the frozen $25 ceiling**. These are frozen-price estimates,
not invoice reconciliation. The paid controller has exited.

Attempted episode results across current development coverage:

- google/gemini-3.8-flash: 294 finished, 230 final submissions, 118 correct.
- google/gemini-3.5-flash-lite: 269 finished, 229 final submissions, 92 correct.
- ollama/qwen3.5:9b: 111 finished, 65 final submissions, 24 correct.

Coverage differs; these are descriptive attempted averages, not a clean model
ranking. The report has a separate declared denominator that includes unexecuted
scheduled rows as missing; always explain coverage before quoting it as accuracy.

Refresh `completion-state.json` for compact progress, or query SQLite in a coherent
read transaction. Existing local helper `/private/tmp/clue-continuation-status.py`
prints cost and per-model counters without credentials. It is temporary, not a
portable dependency. Live state is updated about every 30 seconds.

The watcher waits for specific worker identities to finish, then exports results,
runs evidence diagnostics/reporting/figures, tests, release/provenance checks,
credential scan and privacy verification, and commits/pushes owned paths. It makes
**zero model calls** and cannot spend the second allocation. It does not necessarily
wait for a separately restarted worker: if replacing a runner, inspect and replace
only the watcher with the new worker identity. Check
`/private/tmp/clue-continuation-completion.json` for final receipt (absent at handoff)
and `results/pilot-v0.3-continued/completion-state.json` for failures/progress.
The watcher has an explicit Git staging list that excludes HANDOFF.md and the
archived readiness plan. Documentation changes use a separate checkpoint; inspect
staged paths before committing and avoid racing the finalizer.

## Experiment scope and frozen settings

Original development pilot: 12 worlds (four each at 4/8/12 suspects), paired density
variants, 24 cases, seed 0. Nine conditions: complete-evidence deduction plus agent
and random investigation at 25/50/75/100% clue budgets. One repeat: 216 episodes
per model, 648 total. Continuation expands Google to 108 worlds/216 cases: 1,944
rows each. Qwen remains on original 24 cases/216 rows. Total declared rows: 4,104.
Complete initial cohort first, then rotate sizes/worlds/conditions/models. The
additional 96 worlds are exploratory development, not held-out test execution.
**All 744 test cases remain untouched by live models.** Dataset total: 960 cases.

Models: `google/gemini-3.8-flash`, `google/gemini-3.5-flash-lite`,
`ollama/qwen3.5:9b`. Native tools only, grouped clue menu, exact culprit scoring,
independent episodes; no tool emulation or model substitution. Temperature 1,
4,096 output tokens per call, 32,768 cumulative reported input+output tokens per
episode, 600 seconds, sequential tool execution, no automatic retries. Gemini
thinking medium. Qwen thinking true; top_p .95, top_k 20, presence 1.5, repeat 1.0.
Use the frozen manifest for full details rather than reconstructing from this note.

Qwen: Ollama 0.34.0, Q4_K_M digest
`6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`,
configured context 32,768; Apple M4 Pro, 24 GiB RAM, loaded VRAM about 6.11 GiB.
Native compatibility/runtime identity passed. eval_count includes thinking without
a separate thinking component. Architecture capacity is not the configured context.

Frozen Google prices per million tokens: Flash input $.75/output $3.75;
Lite input $.30/output $2.50. Frozen validity through December 31; inspect pricing
metadata before future protocols. Local API charge zero excludes energy/hardware.

## What is completed and preserved

Native runner, durable reservations, model compatibility gates, exact scoring,
paired schedules, provenance/integrity checks, package build/wheel smoke checks,
exports, evidence feasibility diagnostics, interim report and scientific figures
are implemented. Last broader validation: **166 tests passed**, lint/format,
960-case release checks and source provenance; final watcher revalidates.
The interim generated report still mentions an earlier 151-test baseline; final
verification artifacts are authoritative. Privacy check and credential-pattern
scan passed at the last publication checkpoint.

Original incomplete pilot: 82 episodes, 213 requests; $1.052975 settled plus
$.324813 held = $1.377788 committed. Flash deduction 24/24; Lite 21/24; Qwen not
then run. Original records/source/settings remain under `results/pilot-v0.3` and
`studies/`. Original ledger immutable SHA256:
`44d730d5285dc8574080bf308589c9656517789fcbf8988f3da38e3caa3d1334`.
All original requests/episode IDs and actual/reserved charges were preserved in
the continuation copy. Episode namespace:
`e2f63908352b4c65d76d49f770fc21cf6418f7bb623b75c8f6aca5580ffc4f38`.

Fully finished original shared cohort, both Google models:

- Flash 81/216 correct (37.5%), 164 final submissions; deduction 24/24 (100%).
- Lite 77/216 correct (35.65%), 183 submissions; deduction 21/24 (87.5%).
- Agent investigation averaged Flash 18/96 correct (18.75%), Lite 22/96 (22.92%).
  Random controls averaged Flash 39/96 (40.63%), Lite 34/96 (35.42%).
- At 100% assigned allowance, Flash agent acquired identifying evidence in 12/24,
  averaging 9 clues and 7 correct; Lite 8/24, averaging 10.04 clues and 6 correct.
  Random full evidence identified the culprit in all 24, averaged 14 clues, with
  24 Flash and 21 Lite correct. Full allowance does not imply all clues acquired.

These are resource-bounded end-to-end results. Random evidence is given upfront;
agent investigation repeatedly generates/thinks and resends history. The comparison
confounds evidence selection with conversation/resource overhead. Clue counts are
recorded but are not directly rewarded; exact final answer is the primary score.

## Known issues, diagnoses and fixes already applied

- **New Flash stop:** request 2573 settled at $0.005721 with 4,638 input and
  598 output tokens (587 thinking), against a requested cap of 307. Episode
  `0951e3464ef6927643b6842e14c446571bcbea7aa31bda1cd8aa32cc12a8437c` remains
  failed as `protocol_incompatible`; Flash has 294 finished episodes. The paid
  controller exited. Do not clear this fully accounted native limit violation.
- **New Flash-Lite stop:** request 2462 settled at $0.001484 with 4,644 input
  and 36 output tokens (14 thinking), against a requested output cap of 27.
  Episode `2dbf99244fad067a2d3b03228207aed4ca60bbaf56cafe2f4fbc7ab44acc4175`
  remains failed as `protocol_incompatible`; 269 Lite episodes are finished.
  This is a fully charged native limit violation, not missing usage. Do not clear
  its `accounting_stopped` state using the incomplete-usage recovery override.
  Qwen continues locally. Retain the violations in final reporting and test small
  native caps in the separately frozen calibration stage.
- Original failure request 213: user identified HTTP 503; full $.324813 hold kept.
- Historical token overruns: 38,361 and 32,826 versus 32,768; preserved/scored.
  New Google preflight uses max(native count plus schema, previous reported input
  plus twice previous output plus new tool bytes), with 12.5% + 1,024 headroom.
  Bounds/caps persist per request. Last report showed zero new verified violations;
  unknown usage cannot prove compliance.
- Failed timeouts retained full maximum under explicit authorization; fresh cases
  continue. Strict usage parser failure on request 1711, remaining output cap 197,
  retained full $.787171 maximum. Raw usage/finish metadata was not saved before
  parsing failed; do not assert whether all usage or an optional zero field was
  missing. Current hashed recovery controller implements the approved holds.
- Qwen previously stopped at 94 episodes because a 600-second timeout left an
  unresolved zero-cost reservation and triggered the local guard. Verified exact
  runtime/native identity, audited it as a $0 maximum hold, retained failed score,
  restored compatible state and resumed fresh episodes. Audit:
  `local-timeout-recovery.json`. Original local PID 7260 is obsolete. If it recurs,
  audit unresolved requests and identity before using the same authorized recovery;
  do not blanket-clear errors or retry closed cases.
- Qwen sometimes uses all 4,096 output tokens with empty visible content and no
  native final call. Repeated history consumes cumulative input allowance too.
  Several reviewed submitted answers contradict directly revealed exclusion clues.
  No hidden thinking is available, so do not claim a specific cognitive failure.
- Evidence diagnostics are evaluator-only/post-hoc: reconstruct successful reveals
  from transcripts, use structured revealed constraints and exact CP-SAT feasible
  culprits; never infer from private attributes/unrevealed clues. Unknown solver
  outcomes remain unknown. Diagnostics bind to export hash/current plan identity.
- Label imbalance: expanded four-suspect cohort constant S02 scores 17/32 (53.125%).
  Awkward “different ... value as suspect” language needs review. A cross-attribute
  category alone does not prove cross-attribute reasoning is necessary.
- Manual examples are selected Codex reviews, not independent human annotation or
  estimates of failure prevalence. Few-world/degenerate uncertainty intervals are
  limited. Do not present incomplete coverage as capability ranking.

## Next steps in order

1. Verify Qwen, ledger balance and watcher. Both Gemini runs have ended on native
   cap violations; preserve these stops. Let local Qwen progress under its unchanged
   freeze. If it stops, inspect the reason and prior authorization before recovery.
   Do not restart or clear either Gemini state to spend the remaining old ceiling.
2. When workers stop, inspect watcher receipt, final report/verification, remaining
   budget and stop reasons. “Stopped” may mean budget/accounting limits rather than
   all 4,104 rows attempted. Preserve every failure and show unexecuted coverage.
   If watcher fails, repair export/report/verification independently: these make no
   model calls. Do not label intermediate output final while a worker remains live.
3. Finalize and review first-phase results: paired world comparisons, clue-budget
   curves, acquisition sufficiency, submissions/contradictions, costs, failure types
   and uncertainty. Preserve original cohort versus expansion distinction.
4. Keep the canonical reading set current. Continue only clearly safe documentation
   consolidation; inspect staged paths and avoid concurrent finalizer publication.
5. Implement/check next-study changes offline with fixtures before paid calibration.
   Package source files are frozen for live workers: even adding a package module
   changes the implementation hash set. Do not modify them during this run.
6. Review the final first-phase report, choose compatible models, balanced development
   worlds and primary contrasts, freeze the up-to-$3 calibration stage, then freeze
   the up-to-$34 revised run using its results. Carry forward all charges/holds and
   preserve the $2.861997 contingency under the $50 total. Do not run the 744 held-out cases
   or publish externally without separately defined scope/licensing decisions.

Recommended revised-study design in `next-study-proposal.md`:

- Primary: fixed assigned clue budget, agent versus random using the same public
  menu; score remaining feasible culprits and rate of uniquely identifying evidence
  with a common evaluator. Failure to acquire assigned evidence stays in denominator.
- Fresh answer stage with separately reserved resources and identical evidence
  formatting/native submission tools. Charge both stages. Report evidence quality,
  answer accuracy, submission completion and cost separately. Conditional analyses
  are descriptive; do not replace the assigned-budget primary result.
- Separate adaptive stopping efficiency: few clues count favorably only alongside
  correctness/sufficient evidence; declare failure/censoring handling. Preserve
  end-to-end original protocol as secondary instead of pooling protocols.
- Calibrate native thinking/output limits; choose explicit primary resource quantity
  (generated tokens, cumulative billed tokens, dollars, latency/joint envelope).
  Keep hard dollar reservations regardless. A larger output cap alone is not a fix.
- Safe parser-failure receipt: numeric counters, finish reason, requested caps and
  returned model identity; no credentials/headers/URLs/hidden reasoning. Accept
  absent components as zero only if documented semantics and totals prove it.
- Version balanced culprit-label permutations/clearer clue grammar consistently
  across paired presentations, retaining original world hashes. Independent human
  interpretation checks; structural/ablation tests for necessary cross-attribute
  inference. More balanced independent worlds before many repeats; cluster
  uncertainty by world. Preregister consistent service-error policy and all charges.

## Keep documentation and implementation lighter

The user requests cleanup of unused/stale docs. Do this after inspecting references
and frozen identity/checksum dependencies. Do not delete history to make it tidy.

Keep the active reading set small: `README.md` for entry/setup, this handoff for
state/resume, `pilot-continuation.md` for execution/accounting, the single generated
`pilot-continuation-results.md` for findings, and `next-study-proposal.md` for the
unexecuted revision. Keep necessary dataset/protocol/API documentation for users.
Prefer updating these over adding another status/progress/planning document.

Review overlap among readiness/design plans, old technical reports, pilot results,
configuration and release notes. Merge reusable content into canonical docs; move
superseded narrative working notes into a clearly labeled archive only when no
frozen manifest, source verification, packaging or live finalizer references the
path. Update links and list the canonical reading order. Delete genuinely unused
duplicate drafts after confirming content is preserved in Git and no live/frozen
references depend on them. Avoid maintaining multiple independently edited reports.

**Protect** original results, frozen manifests/amendments, source snapshots,
pricing/runtime records, request/episode logs, recovery audits, immutable hashes,
verification receipts and the SQLite ledger/WAL. A proposed-but-non-executable
manifest can be an audit artifact; do not assume it is disposable from its name.
Do not change frozen files just to reformat them. Do not reorganize files read by
active workers/watcher. Keep mutable progress ignored; leave figures/generated
exports reproducible, and consolidate rather than duplicate new notebooks/charts.
Defer extra dashboards, sweeping refactors and broad documentation rewrites until
the main study is complete. Correctness, accounting and the next protocol take priority.

## Useful entry points and verification

From the benchmark root, these analysis operations make zero generation calls:

```sh
.venv/bin/python scripts/export_native_run.py studies/pilot-v0.3-reserved-recovery.json
.venv/bin/python scripts/evidence_diagnostics.py studies/pilot-v0.3-reserved-recovery.json
.venv/bin/python scripts/report_continuation.py studies/pilot-v0.3-reserved-recovery.json
```

Use report `--final` only after checking execution has ended. Scientific plotting:
`scripts/plot_continuation.py` with `/private/tmp/clue-pilot-plots/bin/python`
(separate matplotlib environment; frozen runner dependencies unchanged).
`study-check` validates the frozen plan; `scripts/check_release.py` and
`scripts/verify_source.py` cover release integrity/provenance. Check actual command
arguments in scripts rather than guessing flags. Tests are in `tests/`.

Core analysis paths: `results.json`, `cost-ledger.json`, `analysis-summary.json`,
`evidence-diagnostics.json`, `evidence-feasibility-cache.json`, `manual-review.json`,
`accounting-recovery.json`, `local-timeout-recovery.json`, and scientific PNG/SVG
figures beneath `results/pilot-v0.3-continued/`. Family exports can have older plan
metadata; aggregate exports/current ledger are canonical, while rows preserve their
execution identities. `docs/pilot-continuation-results.md` snapshot at handoff is
14:37:30 UTC and predates live counts above.

Temporary helpers (verify availability; do not rely on them for portability):
`/private/tmp/clue-continuation-status.py`, `clue-private-github-check.py`,
`clue-pilot-secret-check.py`, separate plotting environment, completion receipt.
An absent temporary helper does not invalidate preserved results. Recreate safely
from repository code as needed; never dump environment or Git credential output.
