# Resource comparison and experiment rationale

Checked **2026-10-09**. This is a scoped comparison of the linked primary
descriptions, not an exhaustive novelty search or reproduction of their results.
Repository descriptions and reported performance can change. No source code,
datasets or prose were imported from these resources.

## What the reference resources already provide

- [MuSR](https://arxiv.org/abs/2310.16049) evaluates multistep soft reasoning in
  natural-language narratives using a synthetic-to-natural generation process.
  Its abstract describes evaluation across models and prompting methods, with
  human-solvable tasks. Our narrow finite constraints are a different scope;
  generating mysteries or difficult text is not by itself a contribution.
  **Design lesson (our inference):** state the capability precisely and measure
  it under several conditions. Inspected: paper abstract and metadata.
- [Temporal Clue](https://github.com/bradhilton/temporal-clue) generates
  Clue-inspired deduction puzzles with temporal/spatial relationships using
  OR-Tools CP-SAT. It asks culprit and additional world-attribute questions.
  **Design lesson (our inference):** reusable generation and explicit task rules
  matter. We focus on culprit answerability under information distribution,
  rather than claiming a new temporal puzzle generator. Inspected: README.
- [ZebraLogic](https://huggingface.co/blog/yuchenlin/zebra-logic) describes
  programmatically generated logic grids with unique full assignments, evaluation
  by puzzle and cell accuracy, and performance breakdowns across sizes and
  difficulty strata. The linked 2024 numbers are historical, not evidence about
  today's Gemini models. **Design lesson (our inference):** separate size strata
  and report more than a single aggregate score. Our culprit guarantee is weaker
  than full-world uniqueness; our distribution certificates serve a different
  evaluation question. Inspected: original author blog.
- [EnigmaForge](https://github.com/robottwo/enigmaforge) currently describes
  mechanically verified generation, alternative surface forms, distractors,
  bounded investigation and scoring beyond final-answer similarity. Its README
  documents limitations and an earlier grader failure involving story copying.
  These overlap with several features we have; neither verification, distractors,
  adjustable size nor reproducible generation alone establishes novelty.
  **Design lesson (our inference):** include simple controls, preserve negative
  results and use answer semantics rather than prose similarity. The descriptions
  reviewed do not document our particular combination of all-coalition
  answerability certificates and at-most-k false-report sufficient subsets.
  This is a scoped observation, not a claim that the whole repository lacks
  related machinery. Inspected: current README, including limits/guarantees.

## Examples from the accepted NeurIPS 2025 D&B proceedings

The supplied [OpenReview listing](https://openreview.net/group?id=NeurIPS.cc/2025/Datasets_and_Benchmarks_Track#tab-accept-oral)
rendered only a loading shell in the research tool. The following examples were
verified through official proceedings as accepted D&B papers; their oral status
was not verified. We use their experimental arguments, not their scale as a target.

- [BLINK-Twice](https://proceedings.neurips.cc/paper_files/paper/2025/hash/2b76873e897f3de3069b2f360c65e0c2-Abstract-Datasets_and_Benchmarks_Track.html)
  describes visual challenges, adversarial image pairs and reasoning annotations,
  evaluated across foundation and reasoning models. **Design lesson (our
  inference):** matched conditions and diagnostic outcomes can expose a specific
  failure mechanism. Our matched noise/corruption variants and sufficient-delivery
  measures follow that experimental principle; they do not reproduce its tasks.
- [NaturalReasoning](https://proceedings.neurips.cc/paper_files/paper/2025/hash/60b22138917015fcba7165670e6f453c-Abstract-Datasets_and_Benchmarks_Track.html)
  describes diverse generated questions with reference answers and demonstrates
  utility through knowledge-distillation and self-training experiments.
  **Design lesson (our inference):** demonstrate a concrete use enabled by the
  resource. Here that use is diagnosing which information conditions permit a
  model to answer, not reproducing training experiments. Inspected: abstract.

The [2025 call](https://neurips.cc/Conferences/2025/CallForDatasetsBenchmarks)
explicitly includes generators and research tools, and stresses accessible,
executable, documented resources. We treat this as evidence that a reusable
generator with demonstrated utility is a coherent resource-paper direction;
it is not a prediction of acceptance or a plan to submit to NeurIPS.

## Our useful scope

- Main feature: request information-sharing conditions, then certify which
  agent coalitions identify the culprit under the published reliability rule.
- Evidence manipulation: distinguish necessary-report bounds, total records,
  false reports and text length; recompute guarantees after changes.
- Evaluation diagnostic: distinguish unsupported correct guesses, insufficient
  delivery, and failures even when the available evidence is sufficient.
- Community value: ship fresh generation, reusable example experiments, strict
  evaluator separation and measured reference results once obtained.

The small pilot in [pilot.md](pilot.md) tests these controls directly. It makes
no claim that our dataset is hardest, uniquely realistic, or the first to provide
any individual feature. Model tests and this comparison cannot replace language
review, independent reproduction or licensing. Update this dated comparison near
any paper submission or public release, especially the rapidly changing repositories.
