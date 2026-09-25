# Dataset card — v0.3 private preview

## Scope

The dataset contains 960 generated cases from 480 hidden worlds. Each world has two complete, truthful clue banks with `N+4` and `N+8` clues, where `N` is the number of suspects. Every complete bank has exactly one feasible murderer, verified by CP-SAT. The complete assignment of all suspect attributes may remain ambiguous. Each bank supports both full-evidence deduction and budgeted investigation.

There are 320 cases each with 4, 8, and 12 suspects. The design crosses four versus five attributes, full versus high value reuse, and standard versus comparison versus cross-attribute proof routes. Half of worlds use the standard route, one quarter a necessary suspect-comparison chain, and one quarter a necessary cross-attribute chain. A necessary chain is a structural property, not a calibrated difficulty claim. The five-attribute/high-reuse combination is test-only.

Development contains 216 cases (108 worlds); test contains 744 cases (372 worlds). Paired banks and all variants of a world stay in one split. `data/v0.3/manifest.json` records every configuration, candidate-seed count, rejection status, dependency version, and file checksum. Each private case records both the world-sampling seed and the clue-generation seed, so `reproduce_case` can rebuild it independently of its stored hidden world.

## Generation and validation

Suspect IDs are neutral (`S01` and onward). Values come from the configured domains; each suspect samples one value per attribute, and values may repeat. High-reuse cells sample each world from a random two-value subset per attribute while retaining the full four-value public domain. All text is deterministic controlled English, not LLM-written prose.

Every clue is true in its source world. The reference solver verifies a unique feasible murderer, and independent tiny-world enumeration tests each clue type. Solver limits are bounded; unresolved checks do not certify cases. The full v0.3 structural audit completed on all 960 cases without inconclusive results. Exactly 240 cases have an individually essential cross-attribute clue, and 240 have an individually essential suspect-comparison clue by construction and revalidation. Direct-value clues alone identify the murderer in 51/960 cases, mostly among four-suspect standard-route cases. This distribution is reported rather than hidden.

Structural hashes invariant to suspect/value renaming screen worlds and clue banks across cells and splits. Exact graph-isomorphism checks classify close hash matches; conservative rejection remains in place for hash collisions or bounded-out comparisons. A separate near-structure audit flags candidates using clue-type/attribute similarity. Neither screen proves that all accepted banks require different reasoning strategies or that no semantic equivalents exist.

## Investigation interface

The public catalogue gives typed topic labels, opaque query IDs, and remaining counts. A request reveals the next clue in a deterministic shuffled topic queue. Suspect-to-suspect comparisons are grouped by attribute across all pairs. Invalid and exhausted requests consume a request slot and count as invalid actions but do not spend evidence budget. Budgets are 25%, 50%, 75%, and 100% of bank size, rounded up. Only the full bank is guaranteed sufficient.

The topic menu conveys side information. An agent can infer which categories and attributes have evidence before opening them. This is part of the task and should be held constant in comparisons. Topic choice is evaluated against random, round-robin, and a public-topic heuristic; a privileged lookahead diagnostic is optional and must be labeled separately.

## Risks, limits, and access

The task probes a narrow formal skill. Performance should not be interpreted as real-world investigative ability, safety, fairness, or general intelligence. The release has no paid model results, and the structural routes have not been calibrated against model accuracy. Wording review packets are prepared, but independent reviewer signoff is pending; they are not evidence of human validation yet. Some topic menus still have many one-clue topics, especially in four-suspect cases.

The repository and data remain private at the owner's request. Licensing is pending; no public redistribution rights have been granted. `croissant.json` is draft machine-readable metadata. Private JSONL contains answers, worlds, seeds, and configurations for the evaluator. Public JSONL contains only permitted deduction observations. Do not expose private data or evaluator logs to tested agents.
