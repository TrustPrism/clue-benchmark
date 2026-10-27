# Preliminary measured results

These are separate historical studies with different thinking budgets, input shapes, adaptive/fresh status and denominators. No pooled leaderboard is supported. Recompute from sanitized per-assignment records without credentials:

The [initial-preview open questions](open-questions.md) separate unanswered
research questions from pending full-release decisions.

```sh
clue-benchmark examples replay measured-results --output runs/measured
```

With the optional figures extra installed, add `--figures` to reproduce the paired accuracy/cost SVG. The command writes `results.json` and an accessible local HTML report with study-specific tables, source hashes and assigned counts.

## What is interesting about the follow-up?

The pilot's apparent benefit from irrelevant evidence **did not repeat consistently**. Lite's four-report endpoint accuracy was unchanged on average, but that average hid one improving world and one worsening world, with four unchanged. The eight-report dip at 100 extra records and partial recovery at 1,000 is a possible distraction signal, not an established dose-response pattern. Flash stayed at the ceiling in this narrow setting. The most consistent tradeoff was cost: roughly 56× for Lite and 77× for Flash at 1,000 extra records, without higher aggregate endpoint accuracy.

These results make a useful replication and robustness example. They do not prove that irrelevant evidence never helps or hurts. The small sample and post-result expansion require exploratory interpretation; the [full phase results below](#follow-up-and-final-expansion) retain uncertainty and all conditions.

## Where to find the original results

The earlier studies have not been replaced by the new follow-up. Their sanitized outcomes are included in both the installed offline gallery and this documentation:

- [Original nuisance pilot](#original-pilot) and [information availability](#information-availability): [pilot assignments](../assets/pilot.json).
- [Certified evidence burden](#certified-burden): [hardness assignments](../assets/hardness.json).
- [Fresh hard cases](#hard-cases-and-resources): [48-world assignments](../assets/flash-hard-scale.json); the [adaptive output-budget assignments](../assets/flash-limits.json) are a separate study.
- [Qwen completion and correctness](#completion-versus-supported-correctness): [screening outcomes](../assets/qwen-sampled-screening.json).
- [Initial October 27 follow-up](#follow-up-and-final-expansion): [original 96-call analysis](../assets/nuisance-followup-results.json) and [original reproduction index](../assets/nuisance-followup-reproduction.json).
- [Final expansion and exploratory combined result](#follow-up-and-final-expansion): [separate phase summaries](../assets/nuisance-extended-results.json), [144 assignments with phase identities](../assets/nuisance-extended-measurements.json) and [combined reproduction index](../assets/nuisance-extended-reproduction.json).

The [historical source/checksum index](../assets/index.json) records original source locations and hashes. The original documents, frozen study sources and operational archives remain preserved in the private checkout; distribution copies omit credentials and operational records. Full raw archives are not publicly deployed. Saved evaluator outcomes must never enter agent prompts.

![Historical four-report paired accuracy and cost](../assets/paired-accuracy-and-cost.svg)

The same five worlds appear at all doses, with one attempt each. Additional context cost more. This small positive Lite observation is a hypothesis, not a general claim that weaker agents benefit from noise.

## Information availability

Eight worlds: Flash 8/8 complete answers, 32/32 appropriate abstentions on ambiguous private views, and 8/8 answers when one-round star forwarding delivered the needed evidence. Lite made two lucky correct ring guesses with insufficient evidence. Forwarding was programmed. The [offline tutorial](../tutorials/distributed-evidence.md) reproduces solver controls separately from these model counts.

## Nuisance records

### Original pilot

Four necessary reports: Lite 2/5, 3/5, 5/5 at 0/100/1000 records; Flash 5/5 at every dose. Eight necessary reports: Lite 5/8, 5/8, 4/8, with a provider error included at the last dose. That last count is not four observed reasoning errors. One repetition; 8/32 preplanned identical-payload pairs elsewhere changed answers, all Lite. [Sanitized assignment records](../assets/pilot.json).

### Follow-up and final expansion

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
stratum, mean estimated cost per scored call rose from less than $0.01 to $0.07
for Lite (about 56×), and less than $0.01 to $0.17 for Flash (about 77×), while
zero- and 1000-record aggregate scores stayed unchanged. This is a useful bounded
cost/robustness example, not a general law about reasoning.

![Initial, extension and exploratory combined accuracy](../assets/extended-nuisance-accuracy.svg)

![Scored-call cost across phases](../assets/extended-nuisance-cost.svg)

The combined receipt-based estimate is **$6.96**, including **$4.73**
initially and **$2.23** for the final expansion. The initial total includes
**$0.24** for the two probes. No unresolved holds; no transport or protocol
failures. This is not a provider invoice. The total commitment preflight was
**$9.40** against the single **$10.00** allowance; no further paid calls are planned.

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

Fresh confirmation: 9/48 correct, 28 wrong, 11 abstentions, no provider/protocol errors, 48 independent worlds, 64 suspects, 455 interacting reports, 32768 output tokens including thinking. The 455 reports were not individually necessary. Estimated $7.23 belongs to a closed historical allowance. [Fresh records](../assets/flash-hard-scale.json).

An earlier adaptive same-six-world comparison rose from 2/6 to 5/6 with more output allowance. Preserve adaptive status and resource differences. [Adaptive records](../assets/flash-limits.json).

## Completion versus supported correctness

Sampled Qwen: 67/72 valid final actions, 22 supported correct, 15 wrong with sufficient evidence, 11 appropriate abstentions, 19 unsupported answers including two lucky correct guesses, and five output-limit protocol failures. Three receipts were reused; 72 slots were not 72 fresh calls or independent worlds. On 29 matched returned slots completion rose 13/29 to 25/29 while supported correctness changed 13/29 to 12/29. More completed outputs did not imply better reasoning. [Sanitized indexed outcomes](../assets/qwen-sampled-screening.json) permit count replay; full raw provider replay remains private/pending rights and sanitization review.

## Provenance and limits

[Source/checksum/sanitization index](../assets/index.json) records original source paths and SHA-256 values plus hashes of the distribution copies. Only selected evaluator outcome fields are retained; no raw receipt, approval, checkpoint or model prose is shipped. These summaries are evaluator data and must not be placed in agent prompts. Hashes are integrity evidence, not ownership clearance.

The original documents and frozen sources remain preserved. The owner authorized public visibility of the existing repository and its history; ignored operational archives remain local and are not uploaded. Licensing, outside reproduction and human template review remain pending. No inference occurs when reading or replaying these records.
