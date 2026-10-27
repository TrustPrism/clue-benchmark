# Preliminary measured results

These are separate historical studies with different thinking budgets, input shapes, adaptive/fresh status and denominators. No pooled leaderboard is supported. Recompute from sanitized per-assignment records without credentials:

```sh
clue-benchmark examples replay measured-results --output runs/measured
```

With the optional figures extra installed, add `--figures` to reproduce the paired accuracy/cost SVG. The command writes `results.json` and an accessible local HTML report with study-specific tables, source hashes and assigned counts.

![Historical four-report paired accuracy and cost](../assets/paired-accuracy-and-cost.svg)

The same five worlds appear at all doses, with one attempt each. Additional context cost more. This small positive Lite observation is a hypothesis, not a general claim that weaker agents benefit from noise.

## Information availability

Eight worlds: Flash 8/8 complete answers, 32/32 appropriate abstentions on ambiguous private views, and 8/8 answers when one-round star forwarding delivered the needed evidence. Lite made two lucky correct ring guesses with insufficient evidence. Forwarding was programmed. The [offline tutorial](../tutorials/distributed-evidence.md) reproduces solver controls separately from these model counts.

## Nuisance records

Four necessary reports: Lite 2/5, 3/5, 5/5 at 0/100/1000 records; Flash 5/5 at every dose. Eight necessary reports: Lite 5/8, 5/8, 4/8, with a provider error included at the last dose. That last count is not four observed reasoning errors. One repetition; 8/32 preplanned identical-payload pairs elsewhere changed answers, all Lite. [Sanitized assignment records](../assets/pilot.json).

The initial follow-up and one final, outcome-independent expansion are both
completed. The expansion used all four remaining worlds from the original
screened seed prefix, with no model outcomes used in selection. Combined:
**12 underlying worlds, six per stratum, 144 scored calls plus two initial probes**.
The expansion decision followed the initial result, so report phases separately
and treat combined estimates as exploratory.

At 0/100/1000 independent records:

- Initial four-report Lite: **7/8, 5/8, 7/8**; extension: **3/4, 4/4, 3/4**;
  combined: **10/12, 9/12, 10/12**.
- Initial eight-report Lite: **6/8, 3/8, 4/8**; extension: **3/4, 2/4, 3/4**;
  combined: **9/12, 5/12, 7/12**.
- Flash: every scored response correct in both phases and every dose; **12/12
  per combined panel**. This ceiling score is specific to these cases/settings.

Each combined denominator twelve means two attempts on six worlds, not twelve
independent worlds. The primary 1000-minus-zero Lite estimate remains **0 points**:
four worlds unchanged, one gains 0.5 and one loses 0.5. Descriptive 95% world
bootstrap interval **[-25, +25] points**, exact sign-flip p=1.0. Equal observed
accuracy does not establish equivalence or prove no effect. Necessary evidence,
context length and composition do not isolate a general reasoning mechanism.
The earlier aggregate improvement did not reproduce here. In the four-report
stratum, mean estimated cost per scored call rose from $0.001269 to $0.070781
for Lite (about 56×), and $0.002258 to $0.174906 for Flash (about 77×), while
zero- and 1000-record aggregate scores stayed unchanged. This is a useful bounded
cost/robustness example, not a general law about reasoning.

![Initial, extension and exploratory combined accuracy](../assets/extended-nuisance-accuracy.svg)

![Scored-call cost across phases](../assets/extended-nuisance-cost.svg)

The combined receipt-based estimate is **$6.961763**, including **$4.731671**
initially and **$2.230092** for the final expansion. The initial total includes
**$0.244634** for the two probes. No unresolved holds; no transport or protocol
failures. This is not a provider invoice. The total commitment preflight was
**$9.400427** against the single **$10** allowance; no further paid calls are planned.

Replay from an installed wheel, without a repository, key or provider:

```sh
clue-benchmark examples replay nuisance-followup --output runs/nuisance
```

Add `--figures` with the figures extra. The output contains initial.json,
extension.json, analysis.json and an accessible local HTML report with separate
phase tables. The general `examples replay measured-results` gallery also includes
these 144 saved assignments, preserving study/settings identities.

[Combined analysis](../assets/nuisance-extended-results.json) and
[all sanitized assignments](../assets/nuisance-extended-measurements.json), and
[source/archive checksum index](../assets/nuisance-extended-reproduction.json) retain
nulls, wrong answers and abstentions. Approvals, credentials, dispatch ledgers,
provider prose and raw receipts are excluded. These are evaluator outcomes and
must not be added to agent prompts. Initial study source archives remain immutable;
the expansion and production code have distinct version/source identities.

## Certified burden

Flash 30/30 in each 32-report path/tree arm; Lite 9/30 and 7/30. These are three attempts on ten worlds per arm. A simple heuristic solves some constructions. Necessary-report cost is not proof depth or model difficulty. High thinking differs from the motivating low-thinking pilot. [Sanitized records](../assets/hardness.json).

## Hard cases and resources

Fresh confirmation: 9/48 correct, 28 wrong, 11 abstentions, no provider/protocol errors, 48 independent worlds, 64 suspects, 455 interacting reports, 32768 output tokens including thinking. The 455 reports were not individually necessary. Estimated $7.231002 belongs to a closed historical allowance. [Fresh records](../assets/flash-hard-scale.json).

An earlier adaptive same-six-world comparison rose from 2/6 to 5/6 with more output allowance. Preserve adaptive status and resource differences. [Adaptive records](../assets/flash-limits.json).

## Completion versus supported correctness

Sampled Qwen: 67/72 valid final actions, 22 supported correct, 15 wrong with sufficient evidence, 11 appropriate abstentions, 19 unsupported answers including two lucky correct guesses, and five output-limit protocol failures. Three receipts were reused; 72 slots were not 72 fresh calls or independent worlds. On 29 matched returned slots completion rose 13/29 to 25/29 while supported correctness changed 13/29 to 12/29. More completed outputs did not imply better reasoning. [Sanitized indexed outcomes](../assets/qwen-sampled-screening.json) permit count replay; full raw provider replay remains private/pending rights and sanitization review.

## Provenance and limits

[Source/checksum/sanitization index](../assets/index.json) records original source paths and SHA-256 values plus hashes of the distribution copies. Only selected evaluator outcome fields are retained; no raw receipt, approval, checkpoint or model prose is shipped. These summaries are evaluator data and must not be placed in agent prompts. Hashes are integrity evidence, not ownership clearance.

The original documents and immutable source/data archives remain preserved in the private repository. Licensing, outside reproduction and human template review remain pending. No inference occurs when reading or replaying these records.
