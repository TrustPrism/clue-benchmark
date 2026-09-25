# Dataset card — v0.1 private preview

## Purpose and contents

Synthetic mystery puzzles for exact deduction and budgeted evidence gathering. The dataset contains 390 independently verified worlds: 90 development and 300 test cases, evenly divided across 4, 8, and 12 suspects. Corresponding banks contain 8, 12, and 16 clues. Each case supports both tracks.

Every complete bank identifies one murderer under the published rules. Full world assignments are not guaranteed unique. Reduced evidence budgets can be insufficient. Four named attributes have four values each; suspects use neutral identifiers S01–S12.

## Provenance and collection

Generated locally with the code in this repository and OR-Tools 9.15.6755. Seeds start at 140000, 180000, and 220000 respectively and advance in order. The first 30 accepted worlds per size form development; the next 100 form test. `data/v0.1/manifest.json` records exact configurations, counts, versions, and SHA-256 values. The private case files retain accepted seeds; local generation checkpoints retain detailed rejection diagnostics and are excluded from Git.

The source generator's uncommitted working-tree improvements were copied into an independent Git repository; `PROVENANCE.json` records imported hashes. No human study data, participant identifiers, or scraped text are included. Template language is generated deterministically, not by an LLM.

## Validation and duplicate screening

All clues are checked against their generated world; CP-SAT proves exactly one feasible murderer. Small-world tests compare CP-SAT with an independent exhaustive enumerator. Unknown/timeout outcomes never certify uniqueness.

Eight-round Weisfeiler–Lehman graph fingerprints screen both world structure and clue structure, invariant to suspect names and value relabeling while retaining attribute labels. Matching fingerprints are rejected conservatively, including possible collisions between non-isomorphic graphs. This is structural screening, not an exact canonical-isomorphism implementation or a guarantee of entirely distinct reasoning patterns. No matching fingerprints cross development/test splits.

## Sampling bias and limitations

The generator constructs an elimination core when possible, fills remaining slots, and attempts weighted uniqueness-preserving replacements. Rejection and core construction bias the accepted distribution. This is a deliberate speed/variety tradeoff; compare observed clue-type distributions, not nominal sampling weights alone.

Many v1 cases may be solved using direct evidence. Default cells do not require indirect evidence to be essential or impose a minimum sufficient-subset size. Neither puzzle size nor sufficient-subset size establishes reasoning depth. Model difficulty and saturation are uncalibrated until model experiments are performed. Query topic names and counts convey side information by design.

The murder theme is fictional and the benchmark measures a narrow formal skill. It should not be used to assess real-world investigative competence, safety, fairness, or general intelligence. No demographic representativeness claim is made.

## Access and licensing

Repository and artifacts remain private at the owner's request. Licensing is pending; no public redistribution rights have been granted. `croissant.json` is draft machine-readable metadata, not a publication-ready licensed dataset registration. Resolve ownership and licensing before public hosting.

Private JSONL contains solutions for the evaluator. Public JSONL contains deduction observations without answers or generation seeds. Do not hand private files or evaluator logs to tested agents.
