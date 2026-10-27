# Related implementation checks — October 27, 2026

These narrow source inspections guide positioning, not claims of superiority or
reproductions of another project's model results. File blob hashes identify the
actual inspected contents; main-branch links may later change.

## Temporal Clue

Inspected [puzzle.py](https://github.com/bradhilton/temporal-clue/blob/main/temporal_clue/puzzle.py),
blob `bcaa67ff012c0528860c04874dba591a8c544571`, and
[model.py](https://github.com/bradhilton/temporal-clue/blob/main/temporal_clue/model.py),
blob `4668d89c0dbc63249a3bbf9870011f20a8b9487b`.

The code constructs a temporal/spatial mystery prompt with suspects, weapons,
rooms, times, motives, questions and a solution export. Its CP-SAT model enforces
categorical assignments, movement adjacency, weapon movement with suspects, and
crime room/time relationships. These are confirmed implementation features.
No broad assertion about absent capabilities follows from inspecting two files;
we did not run its generation tests or reproduce its evaluations.

## EnigmaForge

Inspected [generator.py](https://github.com/robottwo/enigmaforge/blob/main/enigmaforge/generator.py),
blob `b1d1145d6ff5cf44d01813ae92be5cd952e344a1`, and
[verify.py](https://github.com/robottwo/enigmaforge/blob/main/enigmaforge/verify.py),
blob `9c69c6dfeb72a2c8b8d856c00fb04cf0af198766`.

The generator samples a ground truth, adds consistent relational constraints,
strengthens toward uniqueness, and minimizes surviving constraints. Verification
code includes SAT/oracle model-set checks, uniqueness, ablation, distractor
safety, and template realization/round-trip checks. These overlap with verified
puzzle generation and controlled evidence; those features alone are not novelty
claims. We did not establish coverage or correctness by executing this source,
nor verify its model-performance claims.

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
