# Evaluation protocol v1.1

## Rules and task

There is exactly one murderer. Each suspect has exactly one value for each listed attribute. Values can be shared; no all-different assumption applies. Crime attributes equal the murderer's attributes. All evidence is truthful. The task is to identify the murderer; the rest of the world may remain ambiguous.

Positive relational clues are existential conjunctions. Negative relational clues prohibit any suspect from having both specified properties. Controlled English quotes attribute/value literals exactly. Unknown clue types fail validation.

## Deduction

Supply `public_puzzle(case)` with all clue text, domains, suspects, and rules. The Inspect adapter permits only `submit_answer(suspect_id)`. Exact correct ID scores 1; incorrect, malformed, or missing submission scores 0. A free-text guess is not a valid tool submission.

## Investigation

Begin with rules, suspects, domains, and a query catalogue, but no clue contents. Topic labels and remaining counts are deliberately public information and part of the task. Unary clues are grouped by suspect and attribute, crime clues by attribute, and relational clues by attribute pair. Opaque query IDs are shuffled deterministically, independently of the winning answer label. The agent chooses a topic, not a particular clue within it.

Every clue belongs to exactly one queue. Queue order follows the deterministically shuffled bank; repeated valid requests reveal successive clues. Only a successful clue reveal spends one evidence unit. Every response includes the current remaining counts for all topic IDs, the remaining evidence budget, and the remaining request slots; it does not repeat previously revealed clues. Unknown IDs return `unknown_query_id`; an empty listed topic returns `topic_exhausted`. Both count as invalid actions and consume a request slot, but not evidence budget. The maximum request count is `budget + max(2, budget)`, disclosed to the agent. This prevents unlimited free retries. When evidence or request capacity is exhausted, further requests return an error and reveal nothing; the agent can still submit its answer. Calls after a final answer are rejected. Reset starts a new episode with the same bank.

Budgets are ceil(K × fraction) for fractions .25, .5, .75, 1. A final submission is allowed after consuming the last unit. Submission is terminal and returns only acceptance, not correctness. Only the complete bank is guaranteed to identify the murderer. Agents should not be told that a partial observation is uniquely solvable.

## Scoring and reporting

Report the two tracks separately and stratify by suspect count and evidence budget. Exact accuracy at each budget is the primary measure. The mean of the four investigation accuracies at 25%, 50%, 75%, and 100% is an optional single-number summary of the budget-accuracy curve, always accompanied by the four component values. It is not combined with request cost or latency. Secondary measures include clues revealed, total requests, invalid actions, wall time, query latency, and model token usage when available. A failed request affects request counts and limits, not evidence spent.

The free baselines are uniform random answer, exact reference deduction, random topic selection with reference inference on revealed facts, and round-robin topic selection with the same inference. Investigation baselines stop when their revealed facts prove uniqueness; at budget exhaustion they guess uniformly among feasible suspects. Symbolic baselines receive structured versions of revealed clues. This parsing advantage must be stated in comparisons with language models. They do not use the hidden world to select an answer.

The included symbolic results use three seeded repeats and 1,000 bootstrap resamples by world. Variants/repeats of one world are one cluster. Intervals concern the procedural sample, not general human reasoning ability. Report solver errors separately; never silently omit failed episodes. Numeric latencies exclude model API time unless explicitly stated. Record protocol version 1.1 with every new run; earlier protocol 1.0 results used a different failed-request cost rule and are not directly comparable.

## Isolation and reproducibility

Only the evaluator loads private cases. The model sees a serialized public allowlist and the benchmark's two tools. Full evaluator objects, answers, seeds, structured private clues, and necessity annotations are never sent as tool responses. Inspect scoring targets stay evaluator-side and appear only in private logs.

Do not run unrestricted agent code in the evaluator process. The package is not a hardened sandbox. With external agent systems, declare tool access and report results separately; they are outside the v1.1 protocol.

Keep generator configuration and prompts fixed before test evaluation. Track all variants of a world together. Preserve both seed and configuration manifests privately for regeneration. Public procedural generators and released examples can still be contaminated or memorized; fresh seeds are a mitigation, not proof against leakage.
