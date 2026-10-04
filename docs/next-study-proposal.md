# Proposal for the reserved second $25

Status: **unexecuted proposal**, to revise after reviewing the first-$25 continuation.
This document neither allocates the remaining funds nor authorizes test execution.
The first allocation is cumulative, including historical and held charges. Keep the
744 test cases untouched until a separate protocol and model selection are frozen.

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

Before spending the reserved allocation: review the final first-phase report and
native logs, select the intended comparison and participating compatible models,
set a cumulative ceiling that carries forward all charges and held reservations,
freeze a new manifest/source/presentation identity, verify the dollar ledger and
native-limit controls, and record the selected balanced development worlds. Test
execution and publication require their own explicit scope and licensing decision.
No script in this proposal starts those actions automatically.

## Additional issue observed during continuation

The resumed Flash run returned a response that the current strict usage parser
could not verify, on a request whose remaining output cap was 197 tokens. Its
entire $0.787171 maximum remains reserved; no billing usage is invented. The raw
numeric usage metadata and finish reason were not retained before the parser
raised, so this run cannot determine whether the provider omitted all usage or
whether a zero/optional component triggered the guard. Do not infer either cause.

Before the next freeze, retain a safe diagnostic receipt containing numeric usage
counters, finish reason, requested caps and returned model identity on parser
failure, without credentials, headers, URLs or hidden reasoning. Test empty
visible-output and thinking-only responses at small output caps. Accept a missing
component as zero only when documented semantics and complete returned totals
prove the arithmetic; otherwise keep usage unknown and its full cost bound held.
Separate this infrastructure failure from a wrong or truncated submitted answer.
