# Clue Benchmark 0.5.0rc2

**Private release candidate. Ownership clearance and independent review are pending.**

Clue Benchmark is a configurable Python generator and evaluation tool for certified information availability, reliability, and evidence distribution. It creates deterministic synthetic mysteries with explicit logical rules, certifies which answers the evidence supports, and separates public agent inputs from evaluator answers.

Start with [your first dataset](tutorials/first-dataset.md), then try [distributed evidence](tutorials/distributed-evidence.md). See [research recipes](guides/research-recipes.md), [concepts](explanations/pipeline.md), [all parameters](reference/parameters.md), [tools and Python API](reference/interfaces.md), and the [preliminary results gallery](results/index.md).

No model service, account, key or repository clone is needed for the installed offline workflow. Paid model evaluation is separately authorized and never runs in the tutorials.

## A miniature public puzzle

Ada, Ben and Cy each have one badge value: red or blue. Repeated values are allowed. The responsible person's badge is red. Ada's badge is blue. Ben's badge equals Ada's. These three truthful reports identify Cy; they do not determine every other attribute of the world. If Ben's report is missing, Ben and Cy are both possible, so abstaining is supported and a lucky Cy guess is not supported correctness.

This is a teaching example, not a model measurement. See [predicate semantics](reference/predicates.md) for the formal rules used by the generator.

## Version identities

Software: **0.5.0rc2**. Dataset schema: **clue-community-1**. Legacy flat data: **0.3.0**. Presentation IDs, study IDs, returned model identities and source hashes describe different things; never substitute one for another.

[Download a real public-only quickstart case](assets/quickstart-public.jsonl).
The [bundle dictionary](reference/data-dictionary.md) explains how to keep evaluator labels separate.
