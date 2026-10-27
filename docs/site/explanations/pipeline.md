# What the certificates mean

## Generation and validation pipeline

Configuration validation → seeded sampled world → truthful core → optional evidence transformations → reliability-aware certification → partitions and coalition checks → deterministic rendering → structural duplicate/split screening → streamed bundle export → public agent views → scoring and analysis.

Suspects may share motive, location, weapon or time. `assignment_mode=repeated` permits this; `distinct` forbids repeated values within an attribute and needs enough active domain values. Crime attributes match the culprit's attributes. Identifying one culprit does **not** identify a unique full assignment: Ada can be ruled out while her unmentioned weapon remains unknown.

## Reliability and interventions

A truthful clue describes the sampled world. A reported statement is what an agent receives. A sampled false report changes that statement; its identity and actual false count belong to the evaluator. The public rule permits **at most k** false reports, including zero, one, ..., k. Trusted structural rules stay trusted; an agent cannot discard the rule that crime attributes match the culprit.

Independent nuisance records introduce disjoint one-variable components. Each asserts a value in its own domain; it is satisfiable and shares no target variables. Conjoining it cannot change the target candidates. Core-entailed additions follow from the useful core; connected decoys are entailed relational additions involving target variables. Either can improve redundancy. False statements change reliability constraints. Prose padding changes presentation without adding claims. These are different interventions; extra text is not automatically harder.

## What is certified

Total report count differs from minimum sufficient subset cost. Lower and upper bounds describe the least number of original reports needed to force the answer under the reliability rule. A lower bound is not an exact minimum until it meets an upper bound. Neither count certifies proof depth, solver difficulty, strategic diversity, or model accuracy.

The production and independent Boolean encodings agree, but both use CP-SAT. Tiny exhaustive reference enumeration is engine-independent. Solver timeout or work exhaustion means **unresolved**, not uniqueness, inconsistency, or unsatisfiability. No supported workflow disables certification to force acceptance.

A private view can be ambiguous while the global view is unique. Globally ambiguous data permits several culprits even with all reports. Inconsistent evidence permits none. A correct unsupported guess differs from a supported answer; appropriate abstention on ambiguity differs from unnecessary abstention when evidence is sufficient.

Coalition checks currently cover at most eight agents and can be expensive. Reports retain their original identities when replicated/forwarded. Deterministic bounded report forwarding is a programmed protocol, not learned conversation, free-form dialogue, or a communication-emergence claim.

## Seeds, splits and duplicates

Deterministic generation screens structural fingerprints and renamings. World-hash allocation keeps paired variants in the same split; configured holdout families go to transfer. Screening detects selected structural symmetries, not every equivalent strategy or reasoning shortcut. Family holdout does not prove out-of-distribution competence.

English comes from templates, never an LLM. Internal IDs are S01, S02, ...; presentation permutes Person/Entity numbers with `naming_seed`. Default domains are weapon (Rope, Wrench, Poison, Knife), location (Study, Kitchen, Library, Garden), motive (Revenge, Inheritance, Jealousy, Blackmail), and time (20:00, 21:00, 22:00, 23:00). Customize `puzzle.config.domains` with distinct nonempty strings and inspect the resolved configuration. Quotes and unicode are JSON escaped by the formatter.
