# Research readiness implementation plan

Baseline: `96f42d20814fcd35a6fa491c1fc97ef2ec1edfd0`, verified and pushed on
`codex/benchmark-v1`. Work proceeds on `codex/research-readiness`.
The repository remains private and licensing remains pending. The owner has
requested study preparation with no paid model calls.

## 1. Reliable release verification

- Run current v0.3 integrity and reproduction checks in CI, replacing the stale
  v0.2 validation target.
- Test an installed wheel outside the source checkout, including generation,
  validation, deduction, investigation, and private-data isolation.
- Keep dataset version 0.3.0 immutable; version software changes separately.

## 2. A frozen, executable model-study specification

- Record dataset, prompt, protocol, software, model identifiers, settings,
  budgets, repeats, and analysis choices in a content-addressed study plan.
- Verify a plan before execution and reject drift, duplicate IDs, split overlap,
  and incomplete model declarations.
- Provide Inspect tasks and export world-clustered summaries, evidence use,
  invalid actions, missing answers, latency, model failures, and token usage.
- Make execution explicit. Preparation and mock integration checks make zero
  model-provider calls. Actual model results remain pending.

## 3. Investigation validity, measured without enforcing positive results

- Preserve the existing targeted topic menu as the default.
- Add an experimental attribute-grouped menu for paired comparison on identical
  clue banks. It reduces one-clue queues without changing clues or answer rules.
- Compare random, round-robin, and public-topic policies at all four budgets,
  using repeated seeds and paired intervals clustered by world.
- Record inconclusive solver checks; do not discard failed episodes.
- Add a bounded diagnostic of alternative next-clue effects. Hidden-clue
  lookahead is explicitly privileged and is not an optimal-policy bound.
- Use development data for these exploratory design diagnostics. Freeze the
  selected protocol before confirmatory model evaluation. If construction or
  protocol is tuned after test inspection, regenerate an untouched final test.

## 4. Independent human review that can actually be completed

- Prepare public-only examples with topic labels and representative responses.
- Define a rubric for wording, rules, query expectations, and issue severity.
- Collect identifiable reviewer attestations bound to the exact packet hash.
- Validate coverage and report pending, incomplete, or unresolved reviews.
  Automated checks cannot supply independent human signoff.

## 5. Publication checks and explicit remaining gates

- Add missing responsible-use metadata and check hashes, fields, and hosting.
- Produce a machine-readable readiness report separating a working private
  package, public-release requirements, and evidence for AI-performance claims.
- Keep ownership, licensing, human signoff, public hosting, and actual model
  experiments pending until real evidence or an owner decision exists.
- Document bounded claims against SATBench and ZebraLogic and current NeurIPS
  Evaluations & Datasets requirements. No claim of superiority or calibrated
  model difficulty follows from solver checks alone.

## Acceptance checks

- Existing and new tests, lint, formatting, locked dependency resolution, build,
  clean-wheel smoke test, all 960 case reproduction checks, and source isolation.
- Mock study runs exercise both tracks and both menu layouts with no leakage.
- Development investigation results include all budgets and explicit failures.
- Study and review artifacts are reproducible and cannot silently accept drift.
- New branch is committed and pushed after the checks pass.

## Completion record

Implementation and measured outcomes will be recorded here after verification.
External decisions and observations remain pending; they are not satisfied by
creating a plan or a review packet.
