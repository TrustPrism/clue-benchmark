# Clue Benchmark: deduction and evidence gathering in verifiable mystery puzzles

**Dataset 0.1.0 · package 0.1.1 · investigation protocol 1.1 — private technical report, 24 September 2026. Licensing and public publication pending.**

## Abstract

Clue Benchmark provides a procedural environment for two separately scored tasks: identifying a murderer from a complete evidence bank and selecting evidence under a budget. The private preview includes 390 solver-verified worlds, a deterministic generation API, exact scoring, a local CLI, and an optional Inspect adapter. This report evaluates software correctness, generation performance, and free symbolic baselines. It contains no paid-model runs and makes no claim about LLM capability or calibrated difficulty.

## Task and guarantees

Each suspect has one value per attribute; values may repeat across suspects. Crime attributes are the murderer’s attributes. Every released clue is true in the generated world, and CP-SAT verifies exactly one feasible murderer for each complete bank. The full hidden world need not be unique. Partial investigation observations can remain ambiguous.

An agent receives exact controlled-language clues and public rules. The investigation catalogue exposes topic labels and remaining clue counts. Under protocol 1.1, only a successful clue reveal spends one evidence unit; invalid or exhausted requests use a separate bounded request allowance and are reported as mistakes. Every response supplies current topic counts. A single exact suspect-ID submission terminates the episode. Accuracy is reported separately at 25%, 50%, 75%, and 100% of bank size, with the four-budget average available as a summary. See [protocol.md](protocol.md) for the complete interface and scoring rules.

## Generation and reproducibility

The generator samples a world with a unique murderer profile, builds truthful facts, constructs an elimination core when feasible, and attempts weighted clue replacements that retain uniqueness. Optional constraints can require indirect evidence or exclude small sufficient subsets. All loops are bounded. Solver timeouts are inconclusive and cannot certify uniqueness.

The core includes a fact about every suspect before replacement to avoid an immediate unnamed-suspect shortcut. This does not establish absence of other shortcuts. At 12 suspects and 16 clues, the core often fills every slot, leaving alpha/beta to influence only the 12 attempted replacements. Solver rejection further biases accepted clue distributions; nominal alpha/beta proposal weights are not accepted-bank proportions or calibrated difficulty controls. Increasing suspect count need not increase model reasoning difficulty.

The package uses local seeded randomness, canonical configuration ordering, deterministic seed consumption across worker counts, and atomic checkpoints. Cases are grouped by world; graph fingerprints screen suspect/value relabelings. This conservative screening may reject non-isomorphic collisions and does not prove that all accepted cases use distinct reasoning patterns.

The dataset has 30 development and 100 test worlds for each of 4/8/12 suspects with 8/12/16 clues. Eight structurally matching candidates were rejected while producing 390 accepted worlds. Rebuilding all cases after the final solver correction reproduced private and public JSONL byte-for-byte. Versions, exact configurations, seed ranges, rejection counts, and file hashes accompany the dataset. Local generation checkpoints contain detailed attempt diagnostics and can be regenerated; they are excluded from Git.

## Validation

The original 76 automated tests passed on Python 3.13 and 3.14 locally; 78 tests passed on Python 3.14 after the protocol 1.1 investigation-interface changes. Tests compare every clue type and CP-SAT results against an independent small-world enumerator; cover contradiction, ambiguity, uniqueness, invalid configuration, unknown solver outcomes, checkpoint resumes, parallel reproducibility, budget exhaustion, and answer isolation; and exercise both tracks with local mock models. The six archived baseline tests also pass. Linux CI covers Python 3.11–3.14.

A long-run experiment exposed a reproducible OR-Tools 9.15 native crash in AddElement presolve for a partial bank containing only two crime clues. The shipped solver uses equivalent reified conditional equalities instead. The reproducer is retained as a regression fixture. All 390 release cases were reverified and the complete 9,000-episode evaluation then finished without solver errors.

## Baseline results

Each of 300 held-out worlds was evaluated with three seeded repeats. The free baselines are random answer, exact reference deduction, random investigation plus exact inference on revealed facts, and round-robin investigation with the same inference. The symbolic baselines receive structured revealed clues, so their results do not measure language understanding. Intervals use 1,000 bootstrap resamples clustered by world.

- **4 suspects:** random-answer accuracy 25.7%; at 75% evidence, random investigation 49.7% (95% CI 44.3%–55.3%) and round-robin 52.0% (95% CI 45.3%–58.7%).
- **8 suspects:** random-answer accuracy 9.3%; at 75% evidence, random investigation 31.3% (95% CI 26.0%–37.0%) and round-robin 24.7% (95% CI 19.3%–29.7%).
- **12 suspects:** random-answer accuracy 7.7%; at 75% evidence, random investigation 20.0% (95% CI 15.3%–25.0%) and round-robin 19.7% (95% CI 15.3%–24.0%).

Reference deduction and both investigation policies at full evidence achieved 100% accuracy at all sizes. The smaller-budget curves are not strictly monotone in finite random trials; all per-budget aggregate results and four-budget averages are in `results/baselines.json`. Raw episodes can be regenerated with the evaluation command. There were zero unresolved solver outcomes. These are protocol sanity checks and symbolic baselines, not model-comparison results.

## Performance

Measurements ran on macOS-26.6.2-arm64-arm-64bit-Mach-O (arm64), Python 3.14.6, with 12 logical CPUs. CP-SAT uses one search worker per solve. The generation microbenchmark uses 10 seeds per size and matched suspect/clue counts, weights, and attempt bounds, with no minimum-subset requirement. Both successful and rejected attempts are recorded.

- **4 suspects:** 10/10 generated; median 16.4 ms, p95 33.2 ms, 3267 accepted cases/minute of measured generation time.
- **8 suspects:** 10/10 generated; median 22.7 ms, p95 26.2 ms, 2882 accepted cases/minute of measured generation time.
- **12 suspects:** 10/10 generated; median 19.6 ms, p95 24.3 ms, 3013 accepted cases/minute of measured generation time.

The imported generator accepted 8/10 four-suspect cases with a successful-run median of 1.43 seconds; it accepted none of the eight- or twelve-suspect attempts within the matched attempt limit. **The generation algorithms and accepted distributions differ, so this is not a difficulty-matched speedup claim.** The 10-seed measurements are small, include warm-process effects, and were collected on a working desktop.

The largest per-cell p95 clue-response latency in the protocol 1.1 symbolic run was 0.0103 ms, below the 10 ms target. This times an in-process clue request only, excluding model latency, rendering, network transport, and serialization at an external boundary. The profiling process peak resident memory was 106.1 MiB; this excludes legacy subprocess memory. Historical bank timings are not used as a fresh baseline.

## Sampling audit and limitations

- **4 suspects:** 115/130 banks were solvable from direct-category evidence alone; mean necessary-clue count 4.83; 0 inconclusive full-bank diagnostic audits.
- **8 suspects:** 123/130 banks were solvable from direct-category evidence alone; mean necessary-clue count 10.27; 0 inconclusive full-bank diagnostic audits.
- **12 suspects:** 123/130 banks were solvable from direct-category evidence alone; mean necessary-clue count 14.65; 0 inconclusive full-bank diagnostic audits.

The first ten development worlds per size were also searched for sufficient subsets of up to three clues, with a ten-second per-case cap. Raw audit statuses are reported rather than treating an inconclusive search as a lower bound. A sufficient-subset size is not reasoning depth. Many default cases need no indirect clues, especially at larger sizes; stronger optional constraints need separate feasibility and model calibration experiments.

Other limitations include a narrow murder-themed formal domain, known templates, public topic metadata, a small held-out sample, and possible training contamination after publication. Fresh procedural seeds mitigate direct memorization but do not prove contamination resistance. The data does not establish real-world investigative competence, safety, fairness, or general intelligence.

## Related work and publication requirements

[Reasoning Gym](https://arxiv.org/abs/2505.24760) already provides configurable verifiable reasoning environments. [ZebraLogic](https://arxiv.org/abs/2502.01100) studies logical reasoning with generated puzzles, and [SATBench](https://doi.org/10.48550/arXiv.2505.14615) derives puzzles from satisfiability instances. This project therefore positions itself around paired deduction and evidence-selection protocols, rather than claiming procedural generation or solvability verification as new. No exhaustive novelty claim is made.

[Inspect](https://inspect.aisi.org.uk/tutorial.html) supplies the optional execution/logging adapter. [Current NeurIPS evaluation guidance](https://neurips.cc/Conferences/2026/CallForEvaluationsDatasets) emphasizes what an evaluation measures and the limits of its claims. [Dataset hosting guidance](https://neurips.cc/Conferences/2026/EvaluationsDatasetsHosting) specifies documentation and machine-readable metadata for dataset contributions. The 2026 submission deadline has passed; recheck requirements for a future venue.

## Release status

The code, dataset, summarized results, and this report are prepared for private review. Licensing remains pending at the owner’s request. No public repository switch, package-registry upload, or public dataset hosting has occurred. Draft Croissant metadata must be finalized with approved licensing before a public release. A separately funded model study is needed before making claims about AI-system performance.

Reproduce the experiments with the commands in the repository README. `scripts/check_release.py` verifies dataset checksums, all case proofs, split separation, public exports, the 9,000-episode baseline summary, and the clue-latency target. `scripts/verify_source.py` checks that the original generator files, Git status, commit, and remote remain untouched.
