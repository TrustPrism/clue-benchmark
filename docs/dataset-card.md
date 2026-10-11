# Dataset card

The resource is a generator, with small example bundles, for controlled reasoning
evaluations. Its central property is checkable answerability under different
information-sharing conditions. Experiments and hypotheses are chosen by the
researcher using the generated datasets.

## Contents and labels

Each case contains suspects, finite attribute domains, trusted assignment/reliability
rules and uniquely identified evidence reports. A sampled world provides labels
without manual annotation. Unique-answer mode accepts only cases where every
compatible explanation identifies the sampled culprit. Optional ambiguous cases
publish a verified possible-answer set to evaluators.

The five bundle files are public `cases.jsonl`, ownership `partitions.jsonl`, private
`answers.jsonl`, private `certificates.jsonl`, and `manifest.json`. Public case headers
and report rows contain no answers, truth/relevance labels or coalition certificates.
`iter_cases(directory, agent_id=...)` streams the selected agent's public view.
Generation receipts and evaluator files must not be supplied to agents.

## Verified properties

Production integer and independent Boolean encodings agree on possible culprits.
Exhaustive tiny-world checks provide an additional reference. Assignment rules,
false-report assumptions, sufficient-evidence bounds, every agent coalition,
report ownership and text-to-constraint mappings are checked. Independent record
components are separately satisfiable and disconnected from target variables.
Timeouts are unresolved, never proof of ambiguity or uniqueness.

The manifest records requested/resolved controls, accepted seeds, versions, hashes,
splits, rejections and measured properties. All variants of a world use its world-based
split. Structural family holdouts are explicit. Check the final certificate: requested
clue counts, text volume and measured sufficient-clue cost are different quantities.

## Uses and limits

Intended uses include controlled single-agent or distributed-agent reasoning,
robustness to factual corruption, evidence delivery and abstention. Costs and
communication budgets can be reported without running a comprehensive topology
study or proposing a new agent algorithm.

The predicates are narrow finite constraints. Certified clue cost is not reasoning
depth or general intelligence. Two solver encodings share CP-SAT, and deterministic
English templates await independent review. Large-corpus mode adds total evidence
volume; it does not establish 50,000 necessary clues. Model difficulty and practical
usefulness require measured model results. The [initial pilot](pilot-results.md)
and [hardness study](hardness-results.md) provide small, dated reference panels;
they do not establish general model rankings.

## Release gates

Language review, independent reproduction and ownership/licenses are pending.
Measured reference panels are available; research novelty still needs a dated
comparison with relevant resources near submission time. No public redistribution
license is granted yet.
