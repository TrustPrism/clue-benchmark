# Clue Benchmark: deduction and evidence gathering in verifiable mystery puzzles

**Dataset 0.2.0 · package 0.2.0 · investigation protocol 1.1 — private technical report, 24 September 2026. Licensing and public publication pending.**

## Abstract

Clue Benchmark provides a procedural environment for two separately scored tasks: identifying a murderer from a complete evidence bank and selecting evidence under a budget. The private preview includes 390 solver-verified worlds, a deterministic generation API, exact scoring, a local CLI, and an optional Inspect adapter. This report evaluates software correctness, generation performance, and free symbolic baselines. It contains no paid-model runs and makes no claim about LLM capability or calibrated difficulty.

## Task and guarantees

Each suspect has one value per attribute; values may repeat across suspects. Crime attributes are the murderer’s attributes. Every released clue is true in the generated world, and CP-SAT verifies exactly one feasible murderer for each complete bank. The full hidden world need not be unique. Partial investigation observations can remain ambiguous.

An agent receives exact controlled-language clues and public rules. The investigation catalogue exposes topic labels and remaining clue counts. Under protocol 1.1, only a successful clue reveal spends one evidence unit; invalid or exhausted requests use a separate bounded request allowance and are reported as mistakes. Every response supplies current topic counts. A single exact suspect-ID submission terminates the episode. Accuracy is reported separately at 25%, 50%, 75%, and 100% of bank size, with the four-budget average available as a summary. See [protocol.md](protocol.md) for the complete interface and scoring rules.

## Generation and reproducibility

The generator samples a world with a unique murderer profile, builds truthful facts, constructs a mixed exclusion scaffold, and attempts weighted clue replacements that retain uniqueness. Alpha controls whether an innocent suspect is excluded through direct attribute evidence or a crime-relationship clue. Beta controls positive relationship anchors where available and weights filler proposals. Optional constraints can require indirect evidence or exclude small sufficient subsets. All loops are bounded. Solver timeouts are inconclusive and cannot certify uniqueness.

The scaffold excludes every innocent suspect, avoiding the immediate unnamed-suspect shortcut. The v0.1 all-direct core could fill a 16-clue bank; v0.2 removes it. The release configuration requires two or more indirect-category clues and verifies that deleting all indirect clues makes the murderer ambiguous and at least one indirect clue is individually necessary. The scaffold can still yield short, explicit exclusions, and solver rejection biases the observed clue mix. Alpha and beta are structural controls, not calibrated difficulty controls or exact category quotas. Increasing suspect count need not increase model reasoning difficulty.

A fixed 40-seed sensitivity audit at 12 suspects and 16 clues, with mutation disabled, measured 0 indirect clues per bank at alpha=1/beta=0, 3.93 at alpha=0.7/beta=0, and 16 at alpha=0. At alpha=0.7, positive indirect clues rose from 0 per bank at beta=0 to 2.10 at beta=1. These measurements show that the controls affect accepted banks; they do not show that higher indirect counts make agents less accurate. Full counts are in `results/weight-sensitivity-v0.2.json`.

The package uses local seeded randomness, canonical configuration ordering, deterministic seed consumption across worker counts, and atomic checkpoints. Cases are grouped by world; graph fingerprints screen suspect/value relabelings. This conservative screening may reject non-isomorphic collisions and does not prove that all accepted cases use distinct reasoning patterns.

The v0.2 dataset has 30 development and 100 test worlds for each of 4/8/12 suspects with 8/12/16 clues. Twelve structurally matching candidates were rejected while producing 390 accepted worlds. Versions, exact configurations, seed ranges, rejection counts, and file hashes accompany the dataset. Local generation checkpoints contain detailed attempt diagnostics and can be regenerated; they are excluded from Git. The v0.1 dataset remains archived for before/after comparison.

## Validation

The tests compare every clue type and CP-SAT results against an independent small-world enumerator; cover contradiction, ambiguity, uniqueness, invalid configuration, unknown solver outcomes, checkpoint resumes, parallel reproducibility, budget exhaustion, and answer isolation; and exercise both tracks with local mock models. New tests verify that alpha and beta change accepted clue mixes and that release-policy examples cannot be solved from direct clues alone. Linux CI covers Python 3.11–3.14.

A long-run experiment exposed a reproducible OR-Tools 9.15 native crash in AddElement presolve for a partial bank containing only two crime clues. The shipped solver uses equivalent reified conditional equalities instead. The reproducer is retained as a regression fixture. All 390 v0.2 cases were verified during generation and the full-bank structural audit had no inconclusive cases.

## Baseline results

Each of 300 held-out v0.2 worlds was evaluated with three seeded repeats, for 9,000 episodes. The free baselines are random answer, exact reference deduction, random investigation plus exact inference on revealed facts, and round-robin investigation with the same inference. The symbolic baselines receive structured revealed clues, so their results do not measure language understanding. Intervals use 1,000 bootstrap resamples clustered by world.

- **4 suspects:** random-answer accuracy 24.7%; at 75% evidence, random investigation 56.0% (95% CI 50.0%–61.7%) and round-robin 48.3% (95% CI 41.3%–55.0%).
- **8 suspects:** random-answer accuracy 12.0%; at 75% evidence, random investigation 29.3% (95% CI 24.0%–34.7%) and round-robin 24.0% (95% CI 19.3%–29.0%).
- **12 suspects:** random-answer accuracy 9.0%; at 75% evidence, random investigation 16.0% (95% CI 12.3%–20.0%) and round-robin 14.0% (95% CI 10.3%–17.7%).

Reference deduction and both investigation policies at full evidence achieved 100% accuracy at all sizes. The smaller-budget curves are not strictly monotone in finite random trials; all per-budget aggregate results and four-budget averages are in `results/baselines-v0.2.json`. Raw episodes can be regenerated with the evaluation command. There were zero unresolved solver outcomes. These are protocol sanity checks and symbolic baselines, not model-comparison results.

## Performance

Measurements ran on macOS-26.6.2-arm64-arm-64bit-Mach-O (arm64), Python 3.14.6, with 12 logical CPUs. CP-SAT uses one search worker per solve. The generation microbenchmark uses 10 seeds per size and matched suspect/clue counts, weights, and attempt bounds. The v0.2 engine also enforces its release indirect-evidence policy; the archived engine has no equivalent. Both successful and rejected attempts are recorded.

- **4 suspects:** 10/10 generated; median 40.4 ms, p95 82.2 ms, 1,198 accepted cases/minute of measured generation time.
- **8 suspects:** 10/10 generated; median 50.0 ms, p95 69.2 ms, 1,149 accepted cases/minute.
- **12 suspects:** 10/10 generated; median 65.9 ms, p95 90.6 ms, 896 accepted cases/minute.

The imported generator accepted 8/10 four-suspect cases with a successful-run median of 1.78 seconds; it accepted none of the eight- or twelve-suspect attempts within the matched attempt limit. **The generation algorithms, constraints, and accepted distributions differ, so this is not a difficulty-matched speedup claim.** The 10-seed measurements are small, include warm-process effects, and were collected on a working desktop. The complete v0.2 suite of 390 cases generated in about 20 seconds with four workers, excluding the subsequent audit and evaluation.

The largest per-cell p95 clue-response latency in the protocol 1.1 v0.2 symbolic run was 0.0183 ms, below the 10 ms target. This times an in-process clue request only, excluding model latency, rendering, network transport, and serialization at an external boundary. The profiling process peak resident memory was 104.7 MiB; this excludes legacy subprocess memory. Full measurements are in `results/performance-v0.2.json`.

## Sampling audit and limitations

- **4 suspects:** 0/130 banks were solvable from direct-category evidence alone; mean necessary-clue count 4.12; 0 inconclusive full-bank diagnostic audits.
- **8 suspects:** 0/130 banks were solvable from direct-category evidence alone; mean necessary-clue count 9.02; 0 inconclusive full-bank diagnostic audits.
- **12 suspects:** 0/130 banks were solvable from direct-category evidence alone; mean necessary-clue count 13.49; 0 inconclusive full-bank diagnostic audits.

The first ten development worlds per size were also searched for sufficient subsets of up to three clues, with a ten-second per-case cap. Raw audit statuses are reported rather than treating an inconclusive search as a lower bound. A sufficient-subset size is not reasoning depth. The v0.1 direct-only counts were 115, 123, and 123 respectively; the new release policy removes that shortcut, but direct `crime_different_from` exclusions can still make cases easy. Model calibration is needed to establish actual difficulty.

Other limitations include a narrow murder-themed formal domain, known templates, public topic metadata, a small held-out sample, and possible training contamination after publication. Fresh procedural seeds mitigate direct memorization but do not prove contamination resistance. The data does not establish real-world investigative competence, safety, fairness, or general intelligence.

## Related work and publication requirements

[Reasoning Gym](https://arxiv.org/abs/2505.24760) already provides configurable verifiable reasoning environments. [ZebraLogic](https://arxiv.org/abs/2502.01100) generates truthful candidate clues and checks uniqueness while selecting them; this motivated retaining solver verification after clue replacement. [SATBench](https://doi.org/10.48550/arXiv.2505.14615) uses formal instance generation and validation, reinforcing the distinction between a structural generation parameter and measured model difficulty. This project therefore positions itself around paired deduction and evidence-selection protocols, rather than claiming procedural generation or solvability verification as new. No exhaustive novelty claim is made.

[Inspect](https://inspect.aisi.org.uk/tutorial.html) supplies the optional execution/logging adapter. [Current NeurIPS evaluation guidance](https://neurips.cc/Conferences/2026/CallForEvaluationsDatasets) emphasizes what an evaluation measures and the limits of its claims. [Dataset hosting guidance](https://neurips.cc/Conferences/2026/EvaluationsDatasetsHosting) specifies documentation and machine-readable metadata for dataset contributions. The 2026 submission deadline has passed; recheck requirements for a future venue.

## Release status

The code, dataset, summarized results, and this report are prepared for private review. Licensing remains pending at the owner’s request. No public repository switch, package-registry upload, or public dataset hosting has occurred. Draft Croissant metadata must be finalized with approved licensing before a public release. A separately funded model study is needed before making claims about AI-system performance.

Reproduce the experiments with the commands in the repository README. `scripts/check_release.py` verifies dataset checksums, all case proofs, split separation, public exports, the 9,000-episode baseline summary, and the clue-latency target. `scripts/verify_source.py` checks that the original generator files, Git status, commit, and remote remain untouched.
