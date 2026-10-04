# Revised study and project budget

Status: **unexecuted study proposal**. On 4 October 2026 the user reconfirmed a
**$50 total Gemini API budget for the entire project** and delegated its split.
This includes all historical calls, compatibility probes, failed-request maximum
holds, and in-flight reservations. It is not $50 of additional credit.

## Working allocation

The paid first phase stopped on 4 October at **$10.138003 committed**: $6.311107
settled estimates plus $3.826896 maximum failure holds, with no paid requests in
flight or uncertain reservations. Both Gemini models hit native output-limit
violations; their failed episodes and model stops remain intact. Local Qwen is
still running at zero Gemini API cost, so the complete first-phase report is pending.

The original $25 execution ceiling remains frozen as an audit record. Reallocate
its unused capacity to the revised study rather than restarting the failed runs:

- **$10.138003 retained: first-phase charges and maximum holds.** This already
  includes the original pilot and compatibility probes; do not add those twice.
- **Up to $3 additional: revised-protocol calibration.** After offline checks and
  first-phase review, test native completion, small output caps, safe usage
  receipts, and separate evidence-selection/answer stages on development only.
- **Up to $34 additional: revised study.** Freeze compatible models, development
  sample size, primary contrasts, settings, and source identity after calibration.
  Use balanced complete world blocks and equal paired coverage across models
  rather than splitting dollars equally between differently priced models.
- **$2.861997 contingency.** Keep this unallocated unless a budget revision within
  the $50 total is recorded. Failed or unverifiable calls consume their stage's
  allowance at their full held maximum; contingency is not retry permission.

This supersedes the initial $25/$3/$20/$2 planning split because the paid phase
stopped early. These are ceilings, not spending targets. Carry unused funds forward
only in a recorded allocation revision. Carry the entire historical commitment
into each new stage's durable ledger; never create a fresh $50 allowance or erase
a hold. The calibration ceiling is $13.138003 cumulative. If calibration commits
K additional dollars (K <= 3), the revised-study ceiling is $10.138003+K+$34,
at most **$47.138003 cumulative**, leaving the stated contingency under $50.
Reserve worst-case costs before every call and reserve answer resources before
starting selection. The stopped first-phase controller cannot start later stages.

The budget is authorized; the revised experimental protocol is not yet frozen.
Scope this allocation to development until test scope is separately defined.
The 744 held-out test cases and public publication remain outside this plan.

## Main question and matched control

Specify two distinct estimands: the benefit of selecting evidence and success under
an end-to-end resource envelope. The current investigation/random comparison mixes
selection with conversation history, repeated thinking and native tool overhead.

For the selection comparison, let the agent acquire clues using native tools under
a declared selection allowance. Freeze a random-topic policy with the same realized
number of acquired clues and the same starting observation. Feed each resulting
clue set into a fresh answer-stage context with identical formatting, sampling,
output maximum, tools and answer allowance. Charge all selection and answer calls,
including failures. Report selection cost separately; do not equate acquisition
costs across policies merely because the answer-stage context is matched. If the
random count is matched to the agent's realized count, state that this estimates a
conditional selection contrast; it does not estimate the effect of assigning the
original maximum budget. Retain fixed-budget random controls for that estimand.

Keep the current end-to-end agent protocol as a secondary deployment metric. If
matching interaction overhead instead of using fresh answer contexts, preregister
exactly how intermediate turns and thinking allowances are matched. Never emulate
native tools or substitute a model that fails the compatibility test.

## Evidence, language and suspect labels

Balance murderer labels within suspect-size cohorts or use fixed, balanced label
permutations applied consistently to paired density variants, clue references,
answer keys and public metadata. Preserve the original worlds and original data
hashes; assign a new presentation identifier. Check permutation invariance with a
small development sample before freezing the test mapping. Include a uniform-guess
baseline and label-frequency diagnostics. The expanded four-suspect development
cohort currently permits a constant S02 answer to score 17/32 (53.125%).

Rewrite awkward controlled English such as “has a different ... value as suspect”
to clearly express the same constraint. Independently review example clues,
particularly same/different comparisons and existential cross-attribute clues.
Have several human readers solve a small development sample and flag ambiguous
interpretations. Record disagreements and corrections before the freeze. The
current Codex review is not a substitute for independent human annotation.

Determine which cases actually require cross-attribute inference using clause
ablation or dependency checks. A cross-attribute category label alone does not
establish necessity. Preserve easy controls, but report structural difficulty and
avoid presenting direct self-exclusion puzzles as complex relational reasoning.

## Native outputs and token estimands

The present 32,768-token envelope counts cumulative provider-reported input plus
output, including repeated history and thinking. A multi-turn investigator can
exhaust it with few clues. The 4,096 per-call output maximum includes thinking;
Qwen sometimes ends at that maximum without a native final call. These are
resource/protocol outcomes as well as answer failures.

Choose and state the primary resource quantity before freezing: generated tokens,
billable input-plus-output, dollar cost, latency, or a joint envelope. Preserve a
hard dollar ledger in every case. Run a small compatibility/limit development check
under the intended native thinking and output settings. If increasing an output
cap or changing thinking, version and freeze the new setting, charge the check to
the second allocation, and keep the first phase's scores intact. Do not add a
late “answer now” request without defining it as part of the new protocol and
accounting for its costs and effect on every condition.

Report requested budget, realized acquired clues, evaluator-only identifying
evidence, feasible wrong answers, contradictory answers, missing final calls,
invalid calls, token stops and infrastructure failures. Unknown solver outcomes
remain unknown. Thinking that is unreported cannot support a cognitive-process
claim. Conditional success after identifying evidence is descriptive and selected.

## Design, stopping and uncertainty

Use more independent worlds before many repeats. Balance suspect size, density,
policy, evidence budget and model in the execution schedule. Pair density variants
and model/policy observations within worlds. Allocate a small repeat subset if the
budget permits, to assess sampling variability. Estimate precision and cost using
this phase's condition-specific coverage rather than a single global mean.

Freeze primary contrasts and their failure denominators. Count failed and missing
attempts as incorrect in the declared primary result and always show coverage.
Distinguish funding stops from actual task attempts. A post-hoc whole-world subset
is useful as a diagnostic but must not silently replace the declared estimand.
Bootstrap complete world clusters; report few-cluster and degenerate-interval
limitations. Avoid a capability ranking if native compatibility or resource
failure patterns dominate. Do not select worlds based on observed model success.

Preregister a service-error policy. Zero automatic retries preserves the current
one-attempt protocol; HTTP 503 failures can retain maximum cost reservations and
failed scores while permitting new independent episodes. If retries are introduced,
apply the same explicit policy to both models, count all calls and charges, and
report both attempt-level and episode-level failure rates. Missing usage must never
be treated as zero cost. Fully accounted non-generation preflight failures should
be distinguished from generation calls with unknown charges in the recovery audit.

## Freeze gates

Before starting calibration: review the final first-phase report and
native logs, select the intended comparison and participating compatible models,
set a cumulative ceiling that carries forward all charges and held reservations,
freeze a calibration manifest/source/presentation identity, verify the dollar
ledger and native-limit controls, and record the selected balanced development
worlds. After calibration, freeze a separate main-run manifest before spending
its allocation; do not silently change settings within either stage. Test
execution and publication require their own explicit scope and licensing decision.
No script in this proposal starts those actions automatically.

## Additional issue observed during continuation

The resumed Flash run returned a response that the current strict usage parser
could not verify, on a request whose remaining output cap was 197 tokens. Its
entire $0.787171 maximum remains reserved; no billing usage is invented. The raw
numeric usage metadata and finish reason were not retained before the parser
raised, so this run cannot determine whether the provider omitted all usage or
whether a zero/optional component triggered the guard. Do not infer either cause.

Both Gemini models subsequently stopped on output-cap violations. Flash-Lite
request 2462: the ledger records 36 output
tokens (including 14 thinking tokens) against a requested output cap of 27. The
charge settled at $0.001484, but the episode remains a protocol failure and the
model stays stopped. Flash request 2573 reported 598 output tokens (587 thinking)
against a cap of 307 and settled at $0.005721; it also remains a failed episode.
Both stops are separate from missing usage. Calibration must test
small native output caps and preregister how to end a stage when too little output
allowance remains; do not waive these violations or resume either model in the
frozen first phase.

Before the next freeze, retain a safe diagnostic receipt containing numeric usage
counters, finish reason, requested caps and returned model identity on parser
failure, without credentials, headers, URLs or hidden reasoning. Test empty
visible-output and thinking-only responses at small output caps. Accept a missing
component as zero only when documented semantics and complete returned totals
prove the arithmetic; otherwise keep usage unknown and its full cost bound held.
Separate this infrastructure failure from a wrong or truncated submitted answer.

## Recommended primary protocol

Make fixed-budget evidence quality the primary selection comparison. At each
preregistered clue allowance, the model selects clues through native tools and the
random control acquires the same assigned number from the same public menu.
The environment ends selection at the allowance. Record failure to reach it as an
acquisition failure; preserve those failures in the assigned-budget denominator.
Use the exact constraint evaluator to report remaining feasible culprits and the
fraction of assigned episodes that acquire evidence identifying a unique culprit.
Do not give a primary reward for individual clues: useful combinations can contain
clues with little marginal effect in isolation.

Then give each acquired evidence set to a fresh answer context with a separately
reserved allowance and identical answer formatting and native submission tools.
Reserve this stage before beginning selection. Report answer accuracy, native
submission completion, selection cost and answer cost separately. The evaluator's
evidence-quality score provides a common reference across selectors even when the
models differ as answerers. Failed acquisition is not dropped from the primary
result; any answer-stage analysis on successful acquisition is explicitly secondary.

Keep adaptive stopping as a separate efficiency comparison. Measure clues used,
correctness and whether the acquired evidence identifies the culprit together;
report unsuccessful episodes as failures or censored observations under a declared
rule. Few clues alone earn no reward. Retain the original end-to-end protocol as
another secondary comparison rather than pooling these protocols into one score.

Implement and validate the phase boundaries, dollar reservations, safe usage
receipts, label permutations and evidence evaluator with fixtures and offline
checks first. After reviewing the final first-phase report, use a small, explicitly
budgeted development preflight to calibrate thinking/output settings and native
completion. Freeze the new protocol before the main second-phase run. This remains
an unexecuted recommendation and does not change the active first-$25 experiment.
