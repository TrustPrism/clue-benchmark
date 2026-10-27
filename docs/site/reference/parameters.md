# Complete generation parameter reference

Defaults below come directly from the current dataclasses; descriptions are authored and coverage is tested. All fields affect local generation/certification only; none authorizes paid inference. Examples show JSON leaf values: place them at the named path. Bounds/compatibility and invalid combinations are stated with each description. [Evaluation/tool controls](interfaces.md) and [troubleshooting](troubleshooting.md) are separate.

## `puzzle.family`

Type: `<class 'str'>`. Resolved default / JSON example: `"standard"`.

Construction family: standard, pairwise, cross_attribute, equality_tree, branching, redundant_paths. Family-specific enabled types must remain available. A family is not a difficulty guarantee.

## `puzzle.assignment_mode`

Type: `<class 'str'>`. Resolved default / JSON example: `"repeated"`.

repeated permits shared attribute values; distinct requires at least suspect_count active values in every domain and forbids equality families.

## `puzzle.extra_clue_scope`

Type: `<class 'str'>`. Resolved default / JSON example: `"all"`.

all samples from all attributes; non_target_attributes requires branching/equality_tree and at least two attributes.

## `puzzle.attribute_mismatches`

Type: `int | None`. Resolved default / JSON example: `null`.

Optional integer 1..number of attributes; only redundant_paths. Controls how many attribute anchors differ from the culprit.

## `puzzle.config.suspect_count`

Type: `<class 'int'>`. Resolved default / JSON example: `4`.

Integer 2..64 suspects. More suspects increase encoding size and subset search; no universal accuracy prediction.

## `puzzle.config.domains`

Type: `<class 'dict'>`. Resolved default / JSON example: `{"location": ["Study", "Kitchen", "Library", "Garden"], "motive": ["Revenge", "Inheritance", "Jealousy", "Blackmail"], "time": ["20:00", "21:00", "22:00", "23:00"], "weapon": ["Rope", "Wrench", "Poison", "Knife"]}`.

Map of 1..8 nonempty attribute names to 2..32 distinct strings. Domains may contain unicode/quotes. Changing values changes the world identity. Default lists are printed in the resolved configuration.

## `puzzle.config.clue_count`

Type: `<class 'int'>`. Resolved default / JSON example: `8`.

Positive integer core reports, before evidence transformations. Must cover all configured minima. Equality constructions require at least suspect_count; redundant_paths requires (suspect_count+1)*attributes.

## `puzzle.config.enabled_types`

Type: `<class 'tuple'>`. Resolved default / JSON example: `["crime_different_from", "crime_negative", "crime_positive", "crime_same_as", "indirect_negative", "indirect_positive", "suspect_different_from", "suspect_same_as", "unary_negative", "unary_positive"]`.

Nonempty unique list of the ten supported clue predicates. Constructed families require their named predicates; see predicate reference.

## `puzzle.config.alpha`

Type: `<class 'float'>`. Resolved default / JSON example: `0.7`.

Sampling weight/control in [0,1]. Direct category weight alpha; indirect category weight 1-alpha. Construction also uses alpha when choosing available direct versus relational anchors. Rejection and availability condition these weights.

## `puzzle.config.beta`

Type: `<class 'float'>`. Resolved default / JSON example: `0.75`.

Conditional positive relationship weight in [0,1] within indirect sampling, with complement for negative relationships. Availability and rejection alter realized frequencies; not a measured difficulty slider.

## `puzzle.config.min_murderer_links`

Type: `<class 'int'>`. Resolved default / JSON example: `1`.

Nonnegative integer lower bound on murderer-link reports, at most clue_count. Hard accepted-case filter.

## `puzzle.config.max_murderer_links`

Type: `int | None`. Resolved default / JSON example: `null`.

Optional nonnegative integer upper bound, no smaller than the minimum. Impossible limits exhaust candidates.

## `puzzle.config.max_positive_murderer_links`

Type: `int | None`. Resolved default / JSON example: `null`.

Optional nonnegative cap on positive murderer links; may conflict with available family anchors.

## `puzzle.config.min_indirect_clues`

Type: `<class 'int'>`. Resolved default / JSON example: `0`.

Nonnegative minimum number of indirect reports, at most clue_count. Requires enabled indirect types.

## `puzzle.config.min_unique_subset_size`

Type: `<class 'int'>`. Resolved default / JSON example: `1`.

Positive minimum sufficient subset size, at most clue_count. Community sufficient bounds cannot undercut this legacy minimum.

## `puzzle.config.require_indirect_essential`

Type: `<class 'bool'>`. Resolved default / JSON example: `false`.

Boolean hard requirement: at least one indirect clue is essential; impossible with no indirect types.

## `puzzle.config.min_pairwise_clues`

Type: `<class 'int'>`. Resolved default / JSON example: `0`.

Nonnegative required suspect-comparison count, at most clue_count. May reject unsupported families.

## `puzzle.config.active_values_per_attribute`

Type: `int | None`. Resolved default / JSON example: `null`.

Optional integer 2..smallest domain size. Distinct assignment also requires at least suspect_count active values.

## `puzzle.config.reasoning_route`

Type: `<class 'str'>`. Resolved default / JSON example: `"standard"`.

standard, pairwise or cross_attribute legacy construction route. Keep standard for equality constructions; family and route must agree.

## `puzzle.config.max_attempts`

Type: `<class 'int'>`. Resolved default / JSON example: `64`.

Positive bounded legacy construction attempts per candidate; increasing it costs solver time and does not relax semantic filters.

## `puzzle.config.mutation_steps`

Type: `<class 'int'>`. Resolved default / JSON example: `12`.

Nonnegative legacy search mutation steps. Zero skips mutation; it does not skip certification.

## `puzzle.config.max_solver_calls`

Type: `<class 'int'>`. Resolved default / JSON example: `10000`.

Positive maximum legacy solver calls. Exhaustion means unresolved, never a proof.

## `puzzle.config.solver_seconds`

Type: `<class 'float'>`. Resolved default / JSON example: `2.0`.

Positive per-solve wall-time seconds in legacy construction. Timeouts mean unresolved.

## `puzzle.config.solver_work`

Type: `<class 'float'>`. Resolved default / JSON example: `0.2`.

Positive CP-SAT deterministic work bound. Engine-specific effort units; unrelated to model reasoning depth.

## `puzzle.config.generation_seconds`

Type: `<class 'float'>`. Resolved default / JSON example: `30.0`.

Positive total legacy generation wall-time seconds. Independent of community certification_seconds.

## `evidence.minimum_sufficient_clues`

Type: `int | None`. Resolved default / JSON example: `null`.

Optional nonnegative certified lower bound in reports. Must not exceed maximum or undercut legacy minimum; ambiguous cases forbid it.

## `evidence.maximum_sufficient_clues`

Type: `int | None`. Resolved default / JSON example: `null`.

Optional nonnegative certified upper bound in reports; ambiguous cases forbid a sufficient subset.

## `evidence.entailed_clues`

Type: `<class 'int'>`. Resolved default / JSON example: `0`.

Nonnegative count of extra core-entailed reports. Can improve redundancy and model performance; increases text and certification cost.

## `evidence.connected_decoys`

Type: `<class 'int'>`. Resolved default / JSON example: `0`.

Nonnegative count of extra relational entailed reports connected to target variables. Different from independent nuisance.

## `evidence.irrelevant_records`

Type: `<class 'int'>`. Resolved default / JSON example: `0`.

Nonnegative count of satisfiable independent one-variable components, appended by default. Above 1000 requires large_corpus=true. Increases export and model input cost.

## `evidence.false_reports`

Type: `<class 'int'>`. Resolved default / JSON example: `0`.

Integer 0..2 actual sampled corruptions; private evaluator information. Cannot exceed corruption_allowance.

## `evidence.corruption_allowance`

Type: `int | None`. Resolved default / JSON example: `0`.

Optional integer 0..2 public at-most-k rule; resolves to false_reports when omitted. At most is not exactly k.

## `evidence.answerability`

Type: `<class 'str'>`. Resolved default / JSON example: `"unique"`.

unique or ambiguous after all reports and the reliability rule. Ambiguous requires null sufficient bounds and null minimum coalition size.

## `evidence.corruption_strategy`

Type: `<class 'str'>`. Resolved default / JSON example: `"random"`.

random or targeted. Targeted false reports require unique answerability and may increase solver search.

## `evidence.corruption_search_attempts`

Type: `<class 'int'>`. Resolved default / JSON example: `12`.

Positive targeted-search attempt cap. Exhaustion retains rejection evidence; never implies success.

## `evidence.maximum_alternative_margin`

Type: `int | None`. Resolved default / JSON example: `null`.

Optional positive maximum alternative reliability margin; requires unique answerability. Extra solver profiling cost.

## `distribution.agent_count`

Type: `<class 'int'>`. Resolved default / JSON example: `2`.

Integer 1..8. Explicitly use one for single-agent work; default two. Coalition enumeration grows exponentially.

## `distribution.shared_reports`

Type: `<class 'int'>`. Resolved default / JSON example: `0`.

Nonnegative count visible to every agent, no larger than total report count.

## `distribution.private_replication`

Type: `<class 'int'>`. Resolved default / JSON example: `1`.

Integer 1..max(1,agent_count-1) owners per non-shared report; repeated presentation retains original report identity.

## `distribution.per_agent_quotas`

Type: `list[int] | None`. Resolved default / JSON example: `null`.

Optional exact nonnegative report counts, one per agent. Must be feasible with sharing and replication; impossible quotas reject candidates.

## `distribution.minimum_coalition_size`

Type: `int | None`. Resolved default / JSON example: `2`.

Optional integer 1..agent_count. Hard certified minimum team size; null for globally ambiguous data.

## `distribution.max_attempts`

Type: `<class 'int'>`. Resolved default / JSON example: `128`.

Positive bounded partition-search retries; more retries cost certification time, not a relaxed quota.

## `presentation.theme`

Type: `<class 'str'>`. Resolved default / JSON example: `"mystery"`.

mystery or investigation. Uses Person/Entity labels, deterministic wording and no LLM.

## `presentation.naming_seed`

Type: `<class 'int'>`. Resolved default / JSON example: `0`.

Integer seed for label permutation, independent of the sampled world; labels are not real people.

## `presentation.template`

Type: `<class 'str'>`. Resolved default / JSON example: `"compact"`.

compact or expanded deterministic report wording. Expanded adds a fixed sentence to each report.

## `presentation.clue_order`

Type: `<class 'str'>`. Resolved default / JSON example: `"shuffle"`.

shuffle, canonical or reverse. Shuffle uses a deterministic seed; canonical sorts report hashes.

## `presentation.evidence_placement`

Type: `<class 'str'>`. Resolved default / JSON example: `"front"`.

front, middle, end or interleaved position of core reports within the independent nuisance stream.

## `presentation.minimum_words`

Type: `int | None`. Resolved default / JSON example: `null`.

Optional nonnegative minimum whitespace word count. Adds explicitly nonfactual template padding when necessary.

## `presentation.maximum_words`

Type: `int | None`. Resolved default / JSON example: `null`.

Optional nonnegative maximum whitespace word count. Evidence is never truncated; impossible bounds reject.

## `presentation.minimum_tokens`

Type: `int | None`. Resolved default / JSON example: `null`.

Optional nonnegative lower token bound. Requires Python tokenizer with stable identity and workers=1; not provider chat billing.

## `presentation.maximum_tokens`

Type: `int | None`. Resolved default / JSON example: `null`.

Optional nonnegative upper token bound; same tokenizer constraints. Overflow rejects instead of shortening reports.

## `dataset.count`

Type: `<class 'int'>`. Resolved default / JSON example: `1`.

Positive accepted-world target. Candidate exhaustion writes incomplete status and CLI exits 2.

## `dataset.seed`

Type: `<class 'int'>`. Resolved default / JSON example: `0`.

Nonnegative first candidate seed; candidates increase in deterministic order. Resume reuses recorded candidate receipts.

## `dataset.workers`

Type: `<class 'int'>`. Resolved default / JSON example: `1`.

Positive process count. Does not change config fingerprint or accepted seed order. Custom tokenizer requires one worker.

## `dataset.splits`

Type: `<class 'dict'>`. Resolved default / JSON example: `{"development": 0.8, "test": 0.2}`.

development/test/transfer proportions, finite nonnegative values summing to one. Hash-based allocation keeps paired worlds together.

## `dataset.holdout_families`

Type: `list[str]`. Resolved default / JSON example: `[]`.

List of valid families forced to transfer split; family holdout is not a proof of strategy diversity.

## `dataset.output_directory`

Type: `<class 'str'>`. Resolved default / JSON example: `"community-output"`.

Nonempty local directory. Existing matching checkpoints resume; source/config drift rejects. Keep frozen measured runs separate.

## `dataset.certification_seconds`

Type: `<class 'float'>`. Resolved default / JSON example: `60`.

Positive community certification wall-time seconds per candidate. Includes coalition checks; unresolved timeouts reject.

## `dataset.max_solver_calls`

Type: `<class 'int'>`. Resolved default / JSON example: `20000`.

Positive community certification call budget. Separate from nested legacy generation controls.

## `dataset.max_candidates_per_case`

Type: `<class 'int'>`. Resolved default / JSON example: `20`.

Positive candidate multiplier; total attempted candidates bounded by count times this value.

## `dataset.large_corpus`

Type: `<class 'bool'>`. Resolved default / JSON example: `false`.

Boolean explicit opt-in for more than 1000 independent records. Does not authorize inference or raise any monetary cap.

## `schema_version`

Type: `<class 'str'>`. Resolved default / JSON example: `"clue-community-1"`.

Exact wire contract clue-community-1. Separate from software and presentation identity; stale schemas are rejected.
