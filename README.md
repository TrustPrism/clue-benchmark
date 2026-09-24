# Clue Generator

`clue-generator` is a Python package for generating logic-based mystery puzzles. It samples a hidden world, builds a pool of truthful clues, and uses a CP-SAT solver to keep the selected clue set uniquely solvable.

## What it does

The generator works with a small cast of suspects and several attribute domains such as weapon, location, motive, and time. From those inputs it:

1. Samples a random world state and chooses a murderer.
2. Builds a pool of direct and indirect clues from that world.
3. Selects a clue subset with hardness controls.
4. Verifies that the final clue set still has a unique solution.

The package also includes a simple CLI mystery game that prints the clues and asks the player to identify the murderer.

## Project Layout

- `main.py` - benchmark/demo entry point that generates a puzzle and launches the CLI game.
- `run_task_playable.py` - batch generator for study-ready puzzle banks with difficulty tiers.
- `puzzle_generator.py` - orchestration layer for world sampling, clue generation, hardness selection, and uniqueness checks.
- `world_sampler.py` - creates random suspect attribute assignments.
- `clue_generator.py` - builds the raw clue pool.
- `hardness_controller.py` - selects clues using alpha/beta-based hardness sampling.
- `csp_solver.py` - CP-SAT model that checks feasibility and uniqueness.
- `clue_formatter.py` - converts structured clues into readable text.
- `solvability_policy.py` - helper logic used by the batch generator.

## Requirements

Install the Python dependency listed in `requirements.txt`:

- `ortools`

## Setup

From the `clue-generator` directory:

```bash
python -m pip install -r requirements.txt
```

If you are using a virtual environment, activate it first.

## Run the demo game

The default demo measures generation time, prints the result, and then starts the interactive CLI game:

```bash
python main.py
```

## Generate a clue bank

`run_task_playable.py` produces a JSON file containing multiple generated puzzle states and diagnostics.

```bash
python run_task_playable.py
```

Optional flags:

- `--suspects 3|4` - choose the suspect count.
- `--output-prefix NAME` - change the output file prefix.

Example:

```bash
python run_task_playable.py --suspects 4 --output-prefix generated_puzzle_states_study
```

## How the clue pipeline works

The main generation path in `PuzzleGenerator.generate()` is:

1. Sample a world with `WorldSampler`.
2. Build a clue pool with `ClueGenerator`.
3. Create a solver with `MysteryCSPSolver`.
4. Choose clues with `HardnessController`.
5. Reject the clue set if it does not yield a unique murderer.

The solver encodes each clue as a CP-SAT constraint, which lets the generator test whether a candidate clue set is still consistent and uniquely solvable.

## Output shape

A generated puzzle is a dictionary with:

- `suspects`
- `domains`
- `clues`
- `solution`
- `metadata`

`solution` stores both the murderer and the full hidden world state.

## Manual Unity import format

The study generator preserves the structured solver clues and adds a
`records` list for each bank. Each record contains:

- `case_id`, `clue_id`, and `clue_fact_id`;
- `bank_tier` (`easy`, `medium`, or `hard`);
- `clue_complexity`, which is the intrinsic complexity assigned to that clue;
- `clue_type`, the solver encoding type;
- `solver_fields`, the structured source of truth for the clue;
- `formatted_text`, the player-facing text;
- murderer-link, indirectness, and uniqueness-necessity flags.

`bank_tier` and `clue_complexity` are intentionally separate. A clue selected
for the hard bank can have a different intrinsic complexity; the bank tier is
the player-facing request category, not an information-value claim.

IDs are deterministic for the same seed and generator version. Identical
logical facts share a `clue_fact_id`; a bank presentation receives its own
`clue_id`. Exact duplicates are removed from the clue pool when practical.
Cross-bank repeats are allowed and recorded in diagnostics so generation does
not become unnecessarily slow or brittle.

The solver proves only a `unique_murderer`: exactly one suspect remains
feasible. It does not prove that every hidden-world attribute is unique.
Validation also checks that every selected clue is true for the generated
world and does not exclude the true murderer.

## Validation and generation

Run the validation tests from this directory:

```bash
python -m unittest discover -s tests -v
```

Generate the normal study output with parallel workers and resumable
checkpoints:

```bash
python run_task_playable.py --target-states 25 --workers 8
```

For a larger bank, change `--target-states`; the generator continues until
that many banks pass all easy/medium/hard criteria and writes a checkpoint
after each batch:

```bash
python run_task_playable.py --target-states 1000 --workers 8 \
  --output-prefix generated_puzzle_states_1000
```

Diagnostics include generator and OR-Tools versions, seed, duration, attempts,
counts by bank/type/complexity, duplicate statistics, murderer-link and
indirect-clue counts, minimum unique subset size, and per-bank validation
status.

## Notes

- The demo uses a fixed set of suspects and domains in `main.py`.
- Puzzle generation can recurse if a selected clue set is not unique, so some runs may take longer than others.
- `run_task_playable.py` writes a JSON file named `<output-prefix>.json` in the current directory.
