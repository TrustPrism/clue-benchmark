# Research readiness results — 2 October 2026

Software 0.3.1 leaves the 480-world, 960-case v0.3 bank unchanged. The baseline
snapshot is preserved on codex/benchmark-v1; readiness development is on
codex/research-readiness. This report contains free symbolic diagnostics and
software verification, not model-performance results or human signoff.

## Investigation diagnostics

The development comparison used all 216 cases from 108 worlds, two topic menus,
four request policies, all four evidence budgets, and three seeded repeats:
20,736 episodes. There were zero inconclusive solver episodes. Every policy
reached 100% accuracy with the full bank. The artifact is
results/investigation-readiness-dev.json.

The mean proportion of one-clue topics fell from 89.3% to 75.4% for four
suspects, 82.9% to 64.2% for eight, and 75.2% to 51.1% for twelve when unary
suspect facts were grouped by attribute. This made queues deeper, but it did not
consistently improve the policies' accuracy.

At 75% evidence the public-topic heuristic outperformed random topic selection
by 19.0, 15.7, and 5.1 percentage points for 4/8/12 suspects with the targeted
menu. The respective descriptive paired world-cluster intervals were
10.2–27.3, 6.0–26.4, and −2.3–12.5 points. With the grouped menu the gains were
19.0, 6.5, and 6.0 points, with intervals 9.3–28.2, −2.3–15.7, and −2.3–15.3.
The four-budget average gains were 6.8/4.2/2.1 points for targeted and
5.1/0.5/1.5 points for grouped.

These are exploratory development results. All budgets and comparisons are
reported; the 75% slice is a descriptive example, not a new selected primary
hypothesis. The earlier held-out v0.3 results remain unchanged and inconclusive
for a general topic-choice claim across larger sizes. The targeted menu remains
the API compatibility default. Attribute grouping is experimental, not a proven
policy-performance improvement.

A separate shortcut audit chooses among suspects with the fewest named unary
topic capacities, using only public menu labels and counts. Its expected
accuracy on tie breaking was 44.4%, 28.9%, and 18.3% for 4/8/12 suspects, versus
chance levels of 25%, 12.5%, and 8.3%. The world-cluster intervals were
34.0–54.3%, 22.8–36.1%, and 13.7–23.6%. This is generator-correlated public side
information, not a secret-field leak. Grouped menus contain no named unary
suspect topics and this strategy is exactly at chance. The prepared study
therefore defaults to grouping. This audit does not rule out other shortcuts,
including patterns in the revealed clue text.

The extra random_clue policy chooses a topic with probability proportional to
its remaining capacity and reveals that queue's next clue. It uses no hidden
content. This controls for the small-topic preference of uniform random topic
selection; it does not directly request an arbitrary hidden clue. For example,
at 75% evidence on eight-suspect targeted menus, random topic accuracy was 25.5%
and capacity-weighted random accuracy was 38.0%, compared with heuristic 41.2%.
The definition of the random baseline therefore matters.

The separate privileged diagnostic examined four prefixes of nine deterministic
development worlds under both menus: 72 decision points. The immediate number
of feasible murderers differed across the available next clues at 56 points.
All 72 checks completed. This demonstrates opportunities for unequal immediate
information on this sample. It does not show that an agent can recognize them
from public information, nor establish an optimal strategy or proof depth.

The largest per-stratum p95 environment request latency was 0.0088 ms, below the
10 ms local target. This excludes model/API latency, JSON serialization outside
the environment, and reference-inference time. Profiling a small reference run
found repeated model construction and feasible-candidate checks dominate the
offline symbolic work. Evidence replay itself makes no solver calls.

## Model-study preparation

The study plan binds case files, code, lockfile, literal prompts, declared
conditions, dependency versions, token/time limits, and analysis to a checksum.
It currently has no selected model and makes no provider calls. It declares
full-evidence deduction, four investigation budgets, and a fixed random-evidence
control, using the grouped menu. Optional prompt and legacy-menu conditions must
be selected before freezing a new plan.

The task builder checks for drift and yields Inspect tasks. Native log export
keeps missing logs, provider failures, invalid submissions, and missing answers
in the denominator and reports them separately. Summaries include token and
latency coverage, cell accuracy, and paired strategy intervals clustered by
world. Mock integration checks exercise this flow with no paid provider.

The random-evidence control supplies a subset upfront, so comparison with an
interactive agent also includes conversation and tool-use overhead. It helps
separate skills but is not an isolated causal estimate of selection quality.

## Independent review and publication

The public-only packet contains 72 sampled cases from all 36 cells and two
menus, for 144 review items. It includes actual topic-response examples, a rubric,
and a blank response template. No reviews have been collected. Approval requires
at least two independent human attestations per item, full coverage, and no
blocking issues or answer discrepancies. Packet, presentation, and response
hashes prevent silently reusing stale signoff.

The draft Croissant context and extraction rules were corrected. The official
validator accepts the local metadata; the official loader reads all 216 public
development and 744 public test records. Required responsible-use fields are
present, including social impact and the distinction between established formal
correctness and unestablished model construct validity.

The code and data remain private with licensing pending. Local metadata
validation does not grant a license or establish hosted accessibility. The
readiness report leaves ownership/licensing, independent signoff, public
hosting, and final hosted metadata validation pending.

## Verification

The original 93 tests passed before preserving/pushing the baseline. The readiness
suite passes 117 tests, including provider failures, missing logs, source/dataset
drift, unsupported provider tools, menu budgets, and public-data isolation.
An isolated wheel install outside the checkout passes generation, validation,
reference scoring, CLI smoke checks, and solver-free replay with both menus.
All 960 cases reproduce with matching public/private hashes. The original
generator's files, Git status, HEAD, and remote remain unchanged.

These checks establish a working private package and a prepared research
workflow. Actual model experiments and independent human observations are still
needed to support claims about AI reasoning or investigation ability.
