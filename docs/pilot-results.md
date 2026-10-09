# Partial Gemini demonstration — 2026-10-09

**The benchmark already distinguishes these two models on certified, complete
information.** Gemini 3.8 Flash solved all 38 settled cases; Gemini 3.5 Flash-Lite
solved 24/38. This is a small exploratory result, not a general ranking or a
frontier-model weakness claim.

## What was measured

- Necessary evidence: four or eight reports, verified exactly for these cores.
- Archive volume: zero, 100 or 1,000 independently satisfiable nuisance records.
- Matching: the same underlying world and exact target reports within each
  burden stratum. Five paired worlds in the four-clue stratum; eight in the
  eight-clue stratum. One repetition per model and case.
- Models: `gemini-3.5-flash-lite` and `gemini-3.8-flash`, low thinking,
  temperature zero, 4,096-token output cap. Prompts include deterministic text,
  structured constraints and native answer/abstention tools.

## Completed comparisons

- **Four necessary clues:** Flash-Lite achieved **2/5, 3/5 and 5/5** with zero,
  100 and 1,000 nuisance records respectively. Flash achieved **5/5** in each.
- **Eight necessary clues:** both zero and 100 nuisance records yielded
  **5/8 for Flash-Lite** and **8/8 for Flash**. Flash-Lite abstained once in the
  zero-nuisance condition despite sufficient evidence.
- Correct answers in these completed groups were also evidence-supported: the
  visible evidence uniquely identifies the culprit. This does not validate a
  model's reasoning trace.
- Added volume did **not** consistently reduce accuracy. The experiment remains
  useful because it separates volume from necessary evidence and measures cost,
  even when the expected performance decline does not occur.

## Incomplete large-archive comparison

- With eight necessary clues and 1,000 nuisance records, Flash-Lite solved
  **4/7 settled cases**; its eighth request returned HTTP 500 without usage.
- Flash solved **7/7 settled cases**; its eighth assignment was not sent.
- Keeping all eight original assignments gives **4/8 and 7/8** observed assigned
  successes, respectively. These are partial coverage scores. The unsent Flash
  assignment is not an observed incorrect answer, and the Lite provider error
  is not evidence of a reasoning failure.
- No settled request overflowed the declared context or violated the native
  answer protocol. The largest observed input was approximately 231,000 tokens;
  these are provider-reported counts, not counts of necessary clues.

## What remains to demonstrate

- Robustness to zero, one or two factual false reports under a fixed reliability
  rule. Solver controls certify all cases; there are no model results yet.
- Complete versus private information, and recovery after sufficient reports
  reach a decision-maker. Coalition certificates separate unavailable answers
  from failures to reason with available evidence; model jobs remain pending.
- Deterministic forwarding on star/ring/chain graphs with fixed rounds measures
  information delivery. It does not test learned communication or establish a
  general topology ranking.

The [aggregate data](../benchmarks/pilot-results-partial.json) supplies counts,
usage, frozen model settings, receipt hashes and paired contrasts for completed
comparisons. World IDs are the sampling units; variants and private-agent calls
are not independent samples. Small cohorts and one repetition limit inference.
Increasing necessary evidence from four to eight also increases suspect count,
so that comparison does not isolate reasoning depth.

The [checkpoint](pilot-checkpoint.md) records costs, the preserved provider
failure and the concrete continuation. The [experiment guide](pilot.md) explains
how to generate fresh datasets and prepare independently authorized evaluations.
