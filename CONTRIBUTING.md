# Contributing

This is a private release candidate; redistribution and licensing are pending.
Discuss intended changes through a repository issue before broad redesigns.

Create a Python >=3.12 environment and install `.[test,providers,figures]`.
Run `ruff check src tests scripts examples`, `ruff format --check src tests scripts examples`, and `pytest -q`.
For docs, install the docs extra and run `mkdocs build --strict`; macOS Python
3.14 may need a separate Python 3.13 docs environment if watchdog lacks a wheel.

New semantics need independently encoded solver checks and tiny exhaustive
examples, public/evaluator fixtures, authored parameter entries, and English
predicate examples. Keep public inputs free of answers, certificates and private
truth labels. Preserve deterministic seed/worker/resume behavior. Do not change
historical data or hashes to make a test pass.

Provider tests use mocks only. No CI step may read a provider credential, invoke
paid inference, retry dispatched assignments or edit durable budget ledgers.
Review task-related diffs only; preserve pre-existing local edits. Release
requires the owner gates in docs/site/maintainers/release.md.
