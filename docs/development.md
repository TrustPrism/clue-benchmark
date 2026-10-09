# Development

All package settings and direct dependencies live in `pyproject.toml`. Work from
this repository root with Python 3.12 or newer; the local test environment uses 3.14.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test,providers]'
ruff check src tests scripts examples
ruff format --check src tests scripts examples
pytest -q
python -m build
```

Tests use exhaustive references, local solver runs and mock transports. They
make no real model calls. The Google SDK fixture needs the `providers` extra;
it does not need credentials. CI runs the same checks and builds a wheel/sdist.

## Repository layout

- `src/clue_benchmark/`: current generator, encodings, exports and evaluation;
  `legacy_cli.py` supports the original flat puzzle commands.
- `tests/`: current contracts, solver semantics, generator compatibility and mock
  provider accounting; `fixtures/` holds a solver-crash regression input.
- `examples/`: presets, demonstration preparation, policy adapter and small
  generated bundles under `datasets/`.
- `examples/pilot_suite.py`: matched usefulness demonstrations, offline controls,
  frozen model plans and a separately authorized Gemini reference pilot.
- `schemas/`: current configuration, public/evaluator records and evaluation plans.
- `benchmarks/large-corpus.json`: a local scaling profile, separate from model results.
- `scripts/export_schemas.py`: regenerate structural schemas from current contracts.
- `docs/`: generator reference, dataset card and this workflow.

Use `runs/` for generated datasets, profiling output and execution ledgers. The
directory is ignored by Git. Build outputs, local environments and credentials
are also ignored. Do not add disposable copies of datasets or generated test logs
to the source repository.

## Updating contracts and examples

```sh
python scripts/export_schemas.py
clue-benchmark generate-dataset --config examples/basic.json --output runs/basic
clue-benchmark validate-dataset runs/basic
python examples/demonstrations.py --output runs/demonstrations
```

Example bundles should stay small and be regenerated deliberately after semantic
changes. Source/configuration/solver/tokenizer identity changes require a new
checkpoint directory. Frozen evaluation plans likewise reject changed inputs;
never edit a live ledger to repeat a dispatched request.

## Before public release

Finish independent language review and reproduction, resolve ownership/licenses,
and run an explicitly authorized model panel. Update the dated resource comparison
when making research claims. Publishing datasets/packages and executing paid
evaluations remain separate authorized actions.
