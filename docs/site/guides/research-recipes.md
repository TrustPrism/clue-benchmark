# Four research recipes

Start with a concrete question, generate a small example, then inspect the guarantees before evaluating a model.
{.lead}

**All commands on this page run offline.** Use a new output directory for each example.

## 1. Add irrelevant evidence {#step-1-add-irrelevant-evidence}

**Question:** can more irrelevant evidence improve supported accuracy?

```sh
clue-benchmark generate-dataset \
  --preset noise-volume \
  --output runs/noise
```

This preset creates:

- One branching world with **four necessary reports**.
- **100 satisfiable, independent records** unrelated to the target answer.
- Complete evidence for one agent, with useful reports first.
- No false reports.

The original pilot suggested an improvement for Lite. The follow-up did not repeat that benefit consistently: the primary score was **10/12 at both endpoint doses**, while costs rose sharply.

[See all doses, phases and limitations →](../results/index.md#nuisance-records)

Replay the saved measurements:

```sh
clue-benchmark examples replay nuisance-followup \
  --output runs/noise-results
```

<details markdown="1">
<summary>Prepare a separate matched study without running it</summary>

Supply explicit reviewed model prices and the prior measured bank:

```sh
clue-benchmark prepare-nuisance-followup \
  --models models.json \
  --prior-bank prior/bank \
  --output runs/new-followup
```

Preparation creates candidates and maximum reservations. It **does not authorize inference**. The completed October 27 allowance is closed at an estimated **$6.96 of $10.00**, with no holds.

Recognizable records are different from adversarial prose. Changing context length and composition together does not isolate a reasoning mechanism. Any new paid study needs a separate plan and budget.

</details>

## 2. Split and share evidence {#step-2-split-and-share-evidence}

**Question:** does the receiver have enough information to answer?

```sh
clue-benchmark generate-dataset \
  --preset distributed \
  --output runs/distributed
```

The complete view is unique, while private views are ambiguous. Forwarding retains the original report identities.

The saved star-forwarding success applies to a particular protocol and fixture. It is not a universal ranking of network topologies or learned communication.

[Work through the eight-world replay →](../tutorials/distributed-evidence.md)

## 3. Introduce false reports {#step-3-introduce-false-reports}

**Question:** can an agent reason under a public **at-most-k** reliability rule?

```sh
clue-benchmark generate-dataset \
  --preset false-reports \
  --output runs/false
```

Inspect the resolved configuration:

```sh
clue-benchmark explain-config --preset false-reports
```

This preset publishes an allowance of **at most two false reports**, with **one sampled false report**. The actual corrupted identities remain evaluator-only. The answer is certified under the public rule.

A historical fixed-allowance experiment scored Lite **8/8, 7/8, 8/8** at 0/1/2 actual corruptions; Flash scored 8/8 throughout. Necessary evidence was not held fixed, so these small results do not establish a monotonic difficulty effect.

[Understand the reliability rule →](../explanations/pipeline.md#what-does-at-most-k-false-reports-mean)

## 4. Explore evidence burden {#step-4-explore-evidence-burden}

**Question:** does the amount of necessary evidence predict difficulty?

```sh
clue-benchmark generate-dataset \
  --preset hard-example \
  --output runs/hard
```

This small example has **eight suspects and eight necessary reports**. It is not the measured large hard regime.

Historical results show why that distinction matters:

- At **32 necessary reports**, Flash scored 30/30 in each of two path/tree arms; Lite scored 9/30 and 7/30. Some constructions also admit simple heuristics.
- A **fresh 48-world hard confirmation** produced 9 correct, 28 wrong and 11 abstentions under a specified output budget.
- An **adaptive six-world comparison** improved from 2/6 to 5/6 with more output allowance.

Report structure, model resources and study design all affect interpretation. Do not merge these settings into one score.

[Read the hard-case and resource results →](../results/index.md#hard-cases-and-resources)
