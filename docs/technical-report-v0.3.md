# Clue Benchmark v0.3: paired deduction and investigation tasks

**Private technical preview · 25 September 2026. Public licensing and human-review signoff pending. No paid model experiments.**

## Research question and contribution

Clue Benchmark asks how puzzle structure and evidence availability affect two outcomes: identifying a murderer from all evidence, and choosing which evidence topics to open under a budget. The same finite clue bank supports both tasks. This lets an experiment compare full-evidence reasoning with evidence-gathering strategy on paired worlds, with an exact suspect-ID answer and no LLM judge.

This focus differs from [SATBench](https://arxiv.org/html/2505.14615), which evaluates satisfiable versus unsatisfiable SAT-derived stories, and [ZebraLogic](https://arxiv.org/html/2502.01100), which evaluates complete logic-grid assignments and characterizes complexity with search-space size and solver conflicts. [Reasoning Gym](https://arxiv.org/html/2505.24760v2) offers a much broader library of procedural tasks with adjustable complexity. Clue Benchmark is narrower, with an interactive partial-evidence protocol. It does not yet match those projects' published model studies or establish that its structural controls predict model difficulty.

## Logical guarantee

Each suspect has one value per attribute; different suspects may share values. The crime attributes equal the murderer's attributes. Every released clue is true in the sampled world. CP-SAT confirms that exactly one suspect can be the murderer given the complete bank, though the full hidden world may remain nonunique. Inconclusive solver work is rejected. An independent exhaustive enumerator checks the solver on tiny worlds, including both new suspect-comparison clue types.

The release condition does not require every case to be difficult or to use a cross-attribute deduction. Instead, v0.3 includes three controlled proof routes. Standard cases use a mixed exclusion scaffold. Comparison cases construct and verify an individually essential suspect-to-suspect clue. Cross-attribute cases construct and verify an individually essential cross-attribute clue. These checks establish that a clue affects the logical answer; they do not measure human or model difficulty.

## Dataset design

The private suite has 480 sampled worlds and 960 cases. Every world has two clue densities, `N+4` and `N+8`, with the same answer and hidden attributes. The design crosses 4/8/12 suspects, four/five attributes, full/two-active-value reuse, and the three proof routes in a 50/25/25 world allocation. The five-attribute/high-reuse combination is held out of development. Development has 108 worlds and 216 cases; test has 372 worlds and 744 cases. All variants of a world stay in one split. The [dataset card](dataset-card-v0.3.md) and `data/v0.3/manifest.json` give the configurations and checksums.

The generator consumed 543 candidate world seeds to accept 480 worlds. The other outcomes were 51 generation failures, 10 conservative cross-cell screens, and 2 exact structural duplicates. Bounded generation logs record internal constraint and route-availability rejections. An independent regeneration produced identical checksums for all four public/private case files. The package, solver, and configuration versions are recorded with each private case, and release checks reproduce every case from its two seeds.

## Runtime profile

On macOS 26.6.2, arm64, 12 logical CPUs, Python 3.14.6, and OR-Tools 9.15.6755, a two-worker full-suite rebuild took 28.14 seconds, accepting 960 cases at 2,047 cases per minute. Median and p95 accepted-case generator calls were 9.05 and 25.77 ms. Peak parent-process RSS was 146 MB and peak individual child-process RSS was 112 MB; these are process maxima, not combined machine memory. An offline replay of 1,000 successful clue requests across 100 test cases measured p95 response latency of 0.0015 ms, excluding model latency and serialization outside the environment. The [performance artifact](../results/performance-v0.3.json) records the method. V0.2 used a different case distribution, so its historical timing is not a controlled speed comparison.

A fresh 10-seed-per-size [legacy reference run](../results/legacy-comparison-v0.3.json) accepted 8/10 four-suspect cases and none of the 8- or 12-suspect cases; the current generator accepted 10/10 at each size under the script's settings. The two engines use different selection algorithms and acceptance rules, so those figures show operational behavior on the declared seeds rather than an isolated causal speedup or matched-difficulty comparison.

## Structural audit

All 960 cases completed the private structural audit. Exactly 240 cases have an essential cross-attribute clue, and 240 have an essential suspect-comparison clue. The remaining 480 are standard-route cases. Direct-value facts alone identify the murderer in 51/960 cases: 47 among four-suspect cases, 3 among eight-suspect cases, and 1 among twelve-suspect cases. This is a reported distribution rather than a release failure.

The mean greedy irreducible-core sizes are 4.75, 9.20, and 13.52 clues for 4, 8, and 12 suspects. A greedy core is only an upper bound on the smallest sufficient subset and does not measure proof depth. Mean fractions of one-clue topics are 89.1%, 82.7%, and 76.8% by size. Topic queues therefore remain shallow, especially with four suspects. The dataset has more route diversity than v0.2, but the topic menu's strategic value must be evaluated empirically.

In a deterministic 72-case sample (one case per cell and clue density), the mean number of feasible murderers after revealing 75% of clues in stored deduction order was 2.13, 3.67, and 4.79 for 4, 8, and 12 suspects. The full bank reduced each to one. These [candidate trajectories](../results/candidate-trajectories-v0.3.json) show how evidence availability changes logical ambiguity in this sample; the stored order is not an adaptive investigation policy.

Structural hashes screen world and clue-bank renamings. Close hash matches receive exact graph-isomorphism checks, and a separate near-structure audit flags high feature similarity for review. No duplicate hashes cross splits. This does not prove that every accepted bank has a distinct solution strategy or that no two banks are semantically equivalent.

## Investigation protocol and free baselines

The agent sees typed topic labels, opaque query IDs, and remaining counts. Valid requests reveal the next clue in a deterministic shuffled topic queue and spend one evidence unit. Invalid or exhausted requests use a separate bounded request allowance and are counted as mistakes, but do not spend evidence. Budgets are 25%, 50%, 75%, and 100% of clue-bank size, rounded up. Only the complete bank is guaranteed sufficient. A single final suspect-ID submission is scored exactly.

The free policies are random answer, full-evidence reference solver, random topic selection, round-robin selection, and a heuristic using public topic metadata and revealed structured facts. Their inference has a parsing advantage over language models; they are software baselines, not LLM results. An optional privileged lookahead reads unrevealed next clues and must be reported separately. Accuracy by budget, clustered confidence intervals, evidence consumption, invalid actions, and query latency are recorded in the versioned baseline artifact.

The 744-case held-out test run produced 10,416 symbolic episodes with one seed per case/policy/budget. Reference deduction and all investigation policies at 100% evidence scored 100%, with no solver errors. At 75% evidence, random topic selection versus the public-topic heuristic scored 52.8% versus 62.9% for 4 suspects, 35.1% versus 38.7% for 8, and 17.7% versus 23.8% for 12. At 25% and 50%, the heuristic sometimes tied or lost to random. Budget-averaged heuristic advantages were 2.8, 0.7, and 1.4 percentage points by size.

The [paired, world-clustered comparison](../results/topic-choice-v0.3.json) at 75% evidence estimates heuristic-minus-random gains of 10.1 percentage points for 4 suspects (95% bootstrap interval 0.8–19.0), 3.6 for 8 (−5.6–12.9), and 6.0 for 12 (−1.2–13.3). The 75% budget was selected after inspecting development results; these held-out intervals use one verified seed per case. A three-repeat exploratory extension encountered an inconclusive solver check, so it was not used. The evidence supports a topic-choice effect in the four-suspect stratum, but remains inconclusive for the larger strata. This does not yet meet a strong claim that strategic investigation is consistently beneficial across sizes.

## Interpretation and release limits

The benchmark can test whether a system's accuracy changes with suspect count, evidence fraction, value reuse, attribute count, clue density, and relation route, and whether its topic choices outperform simple policies. The current symbolic comparisons establish software behavior and may reveal whether the topic menu offers useful choices. They do not establish that any particular puzzle is demanding for frontier models, nor that a solver-conflict proxy calibrated on ZebraLogic transfers here.

The clue language is controlled English with literal attribute/value names. A public-only wording and query-expectation packet has been prepared, but independent reviewer signoff is pending. No paid model study or human validation claim is included. The dataset and code remain private while ownership and licensing are unresolved. The next public technical release should state these limitations and defer broad AI-performance claims until model experiments are complete.
