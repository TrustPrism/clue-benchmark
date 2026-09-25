# Configuration contract

Pass a JSON file with `--config path.json` or create `Config(**values)`. Unknown keys fail. Defaults are saved with every private case and checkpoint.

- `suspect_count=4`: integer 2–64. The released cells use 4, 8, 12.
- `domains`: 1–8 named attributes, each with 2–32 unique nonempty string values. Default weapon, location, motive, time domains have four values each. Attribute keys are sorted; list order is meaningful. Rendered literals preserve case and escaping.
- `clue_count=8`: exact required count. V0.3 density pairs use `suspects + 4` and `suspects + 8`.
- `enabled_types`: unary positive/negative, crime positive/negative, crime same-as/different-from, cross-attribute positive/negative, and suspect-to-suspect same-as/different-from. Unsupported types or values fail validation.
- `alpha=0.7`: in the standard route, probability that each innocent suspect is excluded by a direct attribute fact plus a shared crime-attribute anchor, when both direct and relationship clues are enabled. Otherwise the scaffold uses a `crime_different_from` relationship clue. `beta=0.75`: probability that each needed standard-route crime-attribute anchor uses `crime_same_as` plus a supporting unary fact, when a matching innocent is available; otherwise it uses `crime_positive`. The same weights also guide filler and replacement proposals in all routes. Comparison and cross-attribute routes use fixed proof scaffolds, so alpha does not choose their exclusions. These weights are not exact accepted-bank quotas or calibrated difficulty controls.
- `min_murderer_links=1`, `max_murderer_links=None`, `max_positive_murderer_links=None`: enforce the requested link counts.
- `min_indirect_clues=0`, `min_unique_subset_size=1`, `require_indirect_essential=False`: optional hard acceptance constraints. Sufficient-subset checks enumerate subsets and may exhaust the solver budget. An inconclusive run fails; it never waives a requirement.
- `active_values_per_attribute=None`: choose from all listed values; set to 2 or more to sample each world from a smaller random subset per attribute. The public domain remains the full listed domain.
- `reasoning_route="standard"`: construct a verified complete bank without a specified essential relation. `pairwise` or `cross_attribute` constructs one candidate chain of the named type and requires at least one clue of that type to be individually essential. These are structural treatments, not calibrated model-difficulty labels. `min_pairwise_clues=0` can separately require a count of suspect comparisons.
- `max_attempts=64`, `mutation_steps=12`, `max_solver_calls=10000`: work bounds. A mixed proof scaffold excludes each innocent suspect, and weighted clue replacement retains uniqueness. An overlong or unsupported scaffold is rejected explicitly; the generator never silently reverts to an all-direct core.
- `solver_seconds=2`, `solver_work=0.2`, `generation_seconds=30`: CP-SAT wall/deterministic limits and generation deadline. Python phases check the deadline between bounded operations; this is not a real-time process-kill SLA.

`STUDY_PRESETS` retains the historical 4-suspect easy/medium/hard parameter settings. It is a compatibility resource, not a claim that all settings will succeed within default limits. The archived historical generator is retained separately. The v0.2 pilot used `min_indirect_clues=2` and `require_indirect_essential=True`; v0.3 uses measured structural routes and does not impose that policy on every case.

Generation returns `{status, case, diagnostics}`. A failed result has `case: null` and rejection counts, elapsed seconds, attempted worlds, and solver calls. No fallback increases clue count or drops constraints.

Batch generation has an outer bound of 20 candidate seeds per requested case by default (`build_bank(..., max_candidates=...)` overrides it). Worker count affects throughput, not accepted-case ordering. Worker processes recycle after 12 jobs. Checkpoints are atomic per completed seed and consume results in seed order. An OS/process failure stops the run with its last checkpoint intact; rerun to resume.

Successful cases are reproducible with the same configuration, seed, package version, solver version, and sufficient runtime resources. Wall-time failures can vary with hardware; manifests retain the accepted seed list and failure diagnostics. Case IDs incorporate the canonical configuration and generated content. Elapsed timing is excluded from case identity.
