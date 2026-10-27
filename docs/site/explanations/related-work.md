# Related implementations

Source checks recorded on **October 27, 2026**. These narrow inspections guide positioning; they are not head-to-head evaluations or claims of superiority.
{.lead}

**What was checked:** selected source files. **What was not checked:** complete test suites or another project's model results. Main-branch links can change; the inspected file hashes are retained below.

## Temporal Clue

The code constructs a temporal/spatial mystery prompt with suspects, weapons,
rooms, times, motives, questions and a solution export. Its CP-SAT model enforces:

- Categorical assignments.
- Movement adjacency.
- Weapon movement with suspects.
- Crime room/time relationships.

These are confirmed features in the inspected files.
No broad assertion about absent capabilities follows from inspecting two files;
we did not run its generation tests or reproduce its evaluations.

<details markdown="1">
<summary>Inspected source files and hashes</summary>

Inspected [puzzle.py](https://github.com/bradhilton/temporal-clue/blob/main/temporal_clue/puzzle.py),
blob `bcaa67ff012c0528860c04874dba591a8c544571`, and
[model.py](https://github.com/bradhilton/temporal-clue/blob/main/temporal_clue/model.py),
blob `4668d89c0dbc63249a3bbf9870011f20a8b9487b`.

</details>

## EnigmaForge

The generator samples a ground truth, adds consistent relational constraints,
strengthens toward uniqueness, and minimizes surviving constraints. Verification code includes:

- SAT/oracle model-set and uniqueness checks.
- Ablation and distractor safety.
- Template realization and round-trip checks.

 These overlap with verified
puzzle generation and controlled evidence; those features alone are not novelty
claims. We did not establish coverage or correctness by executing this source,
nor verify its model-performance claims.

<details markdown="1">
<summary>Inspected source files and hashes</summary>

Inspected [generator.py](https://github.com/robottwo/enigmaforge/blob/main/enigmaforge/generator.py),
blob `b1d1145d6ff5cf44d01813ae92be5cd952e344a1`, and
[verify.py](https://github.com/robottwo/enigmaforge/blob/main/enigmaforge/verify.py),
blob `9c69c6dfeb72a2c8b8d856c00fb04cf0af198766`.

</details>

## Positioning and publication patterns

Clue Benchmark focuses on configurable certified information availability,
public reliability rules, private/coalition evidence and supported correctness.
It does not claim novelty for mysteries, distractors, graphs or verified puzzles
in isolation. [Reasoning Gym](https://github.com/open-thought/reasoning-gym) and
[lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) are useful
onboarding/interface references; [Inspect](https://inspect.aisi.org.uk/eval-logs.html)
illustrates readable saved records. No adapter compatibility is advertised.

The static docs separate tutorials, practical guides, explanations and reference
following [Diataxis](https://diataxis.fr/), with [MkDocs](https://www.mkdocs.org/) search.
