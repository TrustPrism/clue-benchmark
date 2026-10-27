# CLI, Python and native tools

## Current commands

`clue-benchmark --help` is the installed command inventory. `--version` prints the software identity. All offline commands work without provider/figure/docs extras.

- `presets list` lists purpose; `presets show NAME` includes resolved values.
- `generate-dataset` and `profile-dataset` accept exactly one of `--preset NAME` or `--config PATH`. Explicit `--output` and `--workers` override either source.
- `explain-config` accepts the same config selectors and overrides; it returns resolved values with authored field descriptions.
- `validate-dataset DIRECTORY` checks the five-file bundle and independent semantics.
- `export-public DIRECTORY --agent 0 --output FILE` writes allowlisted public case/report JSONL only.
- `inspect-case DIRECTORY [--case-id ID] [--agent 0]` returns public evidence for one case.
- `examples replay distributed-evidence --output DIRECTORY` recomputes solver information controls.
- `examples replay nuisance-followup --output DIRECTORY` recomputes the initial, final expansion and exploratory combined study; optional `--figures` writes plots.
- `examples replay measured-results --output DIRECTORY` recomputes all packaged historical panels, preserving study/model/arm/condition denominators.
- `report SOURCE.json --output DIRECTORY` writes local HTML, exact source JSON and a machine-readable report. It never runs inference.
- `prepare-nuisance-followup` prepares offline matched inputs and full-study costs; it grants no execution permit.

Invalid inputs and incomplete work use status 2 with actionable stderr errors. Normal command summaries are JSON on stdout. Exports/reports/replays refuse overwrites. Generation resumes only matching source/config checkpoints. A frozen evaluation plan rejects drift.

## Python public API

```python
from clue_benchmark import (
    resolve_config, generate_dataset, validate_dataset,
    iter_cases, export_public, inspect_case, evaluate_agent,
)
config = resolve_config(name="quickstart", output="runs/python-demo")
generate_dataset(config)
validate_dataset("runs/python-demo")
export_public("runs/python-demo", "runs/python-agent.jsonl", agent_id=0)
print(inspect_case("runs/python-demo", agent_id=0)["rules"])
result = evaluate_agent("runs/python-demo", lambda view: {"kind": "abstain"})
```

`CommunityConfig`, `generate_case`, `partition`, `score` and `profile_dataset` remain available. `iter_cases` streams public bundle rows. `evaluate_agent` supplies copies of public fields to a trusted callable; it owns the evaluator labels. This is an API boundary, not process isolation. Run untrusted code separately with only exported public files, then score its returned actions in the evaluator process.

## Native actions and evaluation

The supported final actions are `answer(target)` and `abstain()`. `target` must be a listed internal suspect ID, not the display name. Python response dictionaries are `{"kind":"answer","target":"S01"}` or exactly `{"kind":"abstain"}`. Missing, malformed or extra actions are protocol failures, separately reported from wrong supported-context answers.

`prepare-community-evaluation DIRECTORY --models models.json --output plan.json --ceiling-microdollars INTEGER` freezes explicit models, prices and settings. Conditions: complete, independent private views, sharing. Graphs: star, ring, chain, complete. Defaults: all three conditions, complete graph, three rounds, 64 reports/message, one repeat, structured_text input. CLI `--input-view text_only` omits formal constraints; do not pool with structured_text results.

Each model supplies id, vendor, model, settings, context_tokens, input/output_microdollars_per_million_tokens; optional identity is an exact expected returned string, tokenizer_identity is descriptive. Vendor-specific settings are validated. Output allowances include thinking when the provider bills it. One dollar is 1,000,000 microdollars. Conservative serialized-byte bounds include tool overhead. Overflow is rejected, never truncated.

`run-community-evaluation plan.json --dataset DIRECTORY --output RUN --dry-run` serializes/preflights without credentials or network. `--execute --authorization human.json` requires the human plan-bound contract; the command never creates approval. Request timeouts are 600 seconds, retries zero. Persistent SQLite reservations survive interruption and concurrent launches. Settled usage plus unresolved maxima must fit the plan cap. Unknown usage or identity/resource breaches stop and hold funds. Never release holds by guessing or edit the ledger. The new $10.00 study additionally requires one shared allocation across every child plan and probe; a cap per arm is forbidden.

## Legacy appendix

Flat `generate`, `validate`, `export`, the legacy `Config` API and v0.3 archives retain their original shapes. They are not aliases for community bundles. Old investigation/request-clue interfaces are historical; current modes are complete, independent private views and bounded report forwarding.

`run-nuisance-followup DIRECTORY` preflights every frozen scored/probe plan offline.
Its explicit `--execute --authorization human.json` mode serializes the entire study,
checks the sum of child ceilings, and stops all later jobs on unknown usage or a
failed native compatibility probe. Fixed child ledgers prevent replay on resume.
Human approval binds `manifest_id`, the $10.00 cap and exact total request count;
the current candidate permits 96 scored slots plus at most two compatibility calls.
No authorization is generated by preparation.

`analyze-nuisance-followup DIRECTORY --output NEW_DIRECTORY` writes per-call JSONL
and a machine-readable analysis. It preserves never-dispatched slots and leaves
completed-panel accuracy and paired effects null while execution is incomplete.
Completed studies use world-level two-attempt means, descriptive cluster bootstrap,
exact sign-flip analysis and between-model differences. No paid model is called.

`unpack-archive FILE.tar.gz --sha256 PUBLISHED_HASH --output NEW_DIRECTORY` handles
explicit local reproduction downloads. It verifies the checksum before extraction,
rejects links/traversal/duplicate paths, and enforces a declared uncompressed byte
limit (`--maximum-bytes`, default one billion). No hosted URLs or download service
are claimed until the owner clears and publishes the artifacts.


## Output safety in 0.5.0rc2

Completed matching datasets are returned without solver work or file rewrites.
Generation and native evaluation take an exclusive per-directory lock on Linux
and macOS; simultaneous writers receive a short error. A request whose atomic
reservation was lost to another launcher is never dispatched. Ledger identity
creation is serialized. Unknown usage still stops and holds the maximum.

JSON files use unique temporary files and atomic publication. Public exports and
new evaluator outputs use atomic no-clobber publication. An occupied evaluator
output is rejected before invoking an agent callback. Reports validate source
shape before creating output, escape arbitrary text and retain exact source JSON;
phase-separated result tables are keyboard-scrollable.
