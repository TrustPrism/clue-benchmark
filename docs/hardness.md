# Advanced datasets and small experiments

The new controls make it possible to ask where a model fails **after sufficient
evidence is available**. They certify puzzle properties, not frontier-model
failure. The earlier [measured pilot](pilot-results.md) found the stronger Gemini
model solved all its settled complete-information archive cases and all false-report
cases. Independent archive volume alone did not consistently lower accuracy.
These new datasets address those limitations; model results are pending.

## What is implemented

- **Necessary-evidence ladders:** exactly 8, 16 or 32 distinct reports are needed.
  Matched equality paths and binary trees have the same world, necessary-report
  count, six additional truthful statements and 100 independent archive records.
  Extra statements use attributes outside the target tree, giving structural
  variety without introducing target shortcuts. Independently checked deletion
  worlds establish the lower bound; an actual sufficient subset establishes the
  upper bound. Across sizes, suspect count also changes: those comparisons do
  not isolate reasoning depth. Within each size, the path/tree comparison holds
  world and background facts fixed. Shortest equality distance from a unary
  anchor is measured separately; it is a graph property, not a proof-depth or
  psychological difficulty guarantee.
- **Relational false reports:** the `redundant_paths` family builds anchored
  equality paths through value groups on several attributes. The example has
  eight suspects, seven ternary attributes and sixty-three reports. Every suspect
  appears in every attribute's statements, including the culprit. Each wrong
  suspect matches two crime attributes and differs on five, so no single attribute
  identifies the culprit. All conditions
  publish the same allowance of two false reports, while actual corruption is
  zero, one or two. The original world and original sixty-three reports remain paired.
  `targeted` performs a bounded search over factual substitutions and selects
  the unique-answer instance with the smallest distance to a wrong explanation.
  It never queries a model to select difficult cases, and it can tie random
  selection on the measured distance.
- **Certified near-solutions:** the five-attribute example has forty-five
  reports and an allowance of two false reports. Wrong suspects share two crime
  attributes with the culprit. A closest wrong suspect needs
  exactly three violations, so it lies one beyond the admissible threshold.
  This is a best compatible alternative world, not merely comparison with the
  sampled world. Both encodings optimize the distance and direct predicate
  evaluation checks the witness. These examples contain zero actual false
  reports: the challenge is identifying the answer under uncertainty about
  reliability. A separate cohort tests actual factual corruptions.
- **Connected decoys:** add twelve distinct, core-entailed comparisons involving
  the same suspects and attributes. They are true relational additions, not
  provably irrelevant noise. They can create shortcuts or increase the distance
  to wrong explanations. Cost and reliability margins are recertified. The
  matched near-solution cohort admits only cases retaining margin one. Comparing
  zero/twelve decoys holds the original core fixed; comparing zero/1,000 archive
  records at twelve decoys holds all target constraints fixed.
- **Evidence placement:** choose `front`, `middle`, `end` or `interleaved` for
  useful reports within a streamed archive. The four position arms have identical
  evidence and ownership; only placement changes. Ordering never changes IDs or
  consumes extra corruption allowance. Nuisance records remain ordered and lazy;
  interleaving does not buffer the archive. Both export and model observations
  implement the setting. The independent archive structure remains recognizable.
- **Eight-agent bottleneck:** sixteen necessary reports plus six additional
  statements are split across eight agents with minimum sufficient coalition
  eight. Every proper coalition is certified insufficient. Reference plans
  include complete information, private views, star/one round, ring/three rounds,
  and chain/seven rounds, with explicit message limits and original report IDs.
  Actual final delivery is scored; topology alone does not establish sufficiency.
- **Language view:** `text_only` supplies report IDs and deterministic text,
  with public rules, domains and the display-name mapping. `structured_text`
  additionally supplies formal constraints. Labels, corrupted identities,
  reliability witnesses and necessary subsets stay private. A view comparison
  can diagnose reliance on the formal encoding, subject to independent language
  review. No new temporal or conditional clue semantics are claimed.

## Controls and limits

The five-section configuration now also accepts:

- `puzzle.family="redundant_paths"`: repeated assignments only; crime-positive,
  unary-positive and suspect-same-as must be enabled. Exactly `(suspect_count + 1) *
  number_of_attributes` core reports are required. The sampled value partitions
  vary across seeds. The family does not universally guarantee recovery after
  corruption: every final candidate is certified and unsuitable cases rejected.
  `puzzle.attribute_mismatches` specifies how many attributes distinguish each
  wrong suspect from the sampled culprit (default: all). It applies only to this
  family and must be between one and the number of attributes. It is a generation
  control, not an additional trusted rule disclosed to agents.
- `puzzle.extra_clue_scope="non_target_attributes"`: equality-tree/branching
  only, with at least two attributes. Extra core slots exclude crime statements
  and all references to the tree's target attribute. Default `all` preserves
  previous sampling behavior. Requested clue counts remain explicit.
- `evidence.connected_decoys`: a count of additional, distinct, entailed suspect
  equality/inequality statements. Counts are separate from `entailed_clues` and
  `irrelevant_records`. Unsupported clue pools fail explicitly. Certificates
  retain the original truthful basis and independently recheck entailment.
- `evidence.corruption_strategy="random"|"targeted"` and
  `corruption_search_attempts` (default twelve): targeted search supports unique
  cases. It retains the exact requested false-report count. Its evaluator receipt
  records attempted candidates and selected search index. Solver timeouts are
  unresolved, never a certified distance. Zero–two reports remain the supported
  limit; there is no source-level liar or correlated reliability model.
- `evidence.maximum_alternative_margin`: a positive maximum on the closest
  wrong culprit's minimum required violations minus the published allowance.
  A value of one requires a verified wrong explanation just outside the allowed
  region. This is a maximum-distance constraint, not a new corruption allowance.
- `presentation.evidence_placement`: `front` (compatible default), `middle`,
  `end`, `interleaved`. `clue_order` still controls order among target-component
  reports. Independent record components retain their own deterministic order.
- Evaluation `input_view="text_only"|"structured_text"`; the CLI uses
  `--input-view`. The default remains `structured_text` for compatibility.

Sampled worlds, truth status, graph measurements, distance profiles and sufficient
subsets are evaluator information. Give an agent the public evidence view only,
not the manifest, answers, suite measurements or certificate files. Added decoys
may change sufficient-clue cost; a bounded certificate is not an exact optimum.
Wall-time budgets can affect accepted seeds and retained bound tightness. Preserve
accepted seeds and receipts, and give reproduction enough certification resources.

## Reproduce and inspect

From the repository root after installation:

```sh
python examples/hardness_suite.py prepare --output runs/hardness --count 10
python examples/hardness_suite.py prepare --output runs/hardness-small --count 2
clue-benchmark generate-dataset --config examples/advanced/targeted-false-2.json --output runs/targeted
clue-benchmark validate-dataset runs/targeted
```

`--groups` can restrict preparation to `reasoning-8`, `reasoning-16`,
`reasoning-32`, `false-reports`, `near-solutions`, `archive-position`, or
`distributed`. Default seed is 107. Generation preserves atomic candidate
receipts, bounded search reasons and conservative isomorphism screening. Resume
requires identical source/configuration/script identities. It never fills a
cohort with repeated isomorphic puzzles just to achieve the requested count.
All variants of an underlying world share their split. The default suite includes
nineteen arms, ten worlds per arm; matched arms are not independent samples.

The committed small bundles in `examples/datasets/advanced/` are inspection
examples. The compact [offline certification report](../benchmarks/hardness-preflight.json)
records the larger prepared cohorts, accepted seeds, hashes, solver controls,
cost bounds, margins and rejection counts. It contains no model-performance
measurements. The 50,000-record streaming test checks export/validation scaling,
not 50,000 necessary clues or successful model ingestion.

`examples/advanced/relational-32.json` supplies a larger relational stress point:
32 suspects, seven attributes, 231 reports and two targeted factual corruptions.
Its separately checked one-case bundle and
[profile](../benchmarks/hardness-relational-32.json) retain verified cost bounds;
they do not claim that all 231 reports are necessary or that a model failed.
The relational constructions mention every suspect on every attribute and mix
shared crime values, removing the simple "only unmentioned suspect" shortcut.
Single-attribute equality scaffolds remain useful burden controls and may admit
construction-specific heuristics; certification alone does not establish hardness.

## Prepare a model experiment without dispatching it

The new example model file uses the previously measured Gemini model IDs with
**high thinking and an 8,192-token output cap**, rather than the pilot's low
thinking/4,096 cap. Google documents high thinking for both models in its
[thinking reference](https://ai.google.dev/gemini-api/docs/thinking).
Context capacities and full-token prices are the dated pilot values; verify them
before approving execution. These two models are reference points, not an
exhaustive panel of today's strongest models. Researchers can supply others.

```sh
python examples/hardness_suite.py plan \
  --datasets runs/hardness --models examples/gemini-hardness-models.json \
  --arms equality_tree-32 branching-32 relational-random-false-2 relational-targeted-false-2 near-decoys-0-noise-0 near-decoys-12-noise-0 \
  --repeats 3 --input-views text_only --output runs/hardness-plans
```

Planning performs no credential reads or model calls. Zero is the default
spending ceiling; such plans are deliberately unfunded. Supplying an explicit
ceiling prepares funded plans only when **all** contexts fit and the sum of
conservative request reservations is within it. Otherwise every job remains at
zero spending capacity. The script reports the complete bound, does not reduce
repetitions or trim evidence, and refuses to overwrite a different frozen plan.
Use a new output directory to change the experiment.

The six selected arms give three focused comparisons, ten paired worlds per
comparison and three repetitions: path/tree structure, random/targeted two-report
corruption, and connected decoys. Adding `structured_text` enables a view contrast.
Optional archive-position and distributed arms extend the investigation. Each
job's approved maximum is bounded so all jobs together respect the suite ceiling.
Actual live execution still uses the existing separately authorized harness;
this script exposes no dispatch command and creates no authorizations.

Run outputs can be combined offline:

```sh
python examples/hardness_suite.py analyze \
  --datasets runs/hardness --plans runs/hardness-plans \
  --runs runs/hardness-model-results --output runs/hardness-results.json
```

Place each harness `results.json` under its named job directory. Analysis checks
plan and request identities, preserves all assigned failures, separates missing
jobs, and reports world-clustered correctness, supported correctness, abstention,
protocol failures, tokens and cost through the harness metrics. Original per-request
harness outputs retain evidence-delivery flags and measured latency separately.
The small cohort supports descriptive comparisons; bootstrap intervals are not a
claim of statistical significance. Inspect development and test worlds separately
and keep any model-guided search on development data. A public frontier-failure
claim additionally needs reviewed language, adequate reasoning budgets, verified
context fit, held-out replication and a broader model panel.

## Research position

[ZebraLogic](https://arxiv.org/abs/2502.01100) measures logical complexity and
reports declining model accuracy as complexity grows. [EnigmaForge](https://github.com/robottwo/enigmaforge)
already describes configurable structure, distractors and mechanically verified
generation. These motivate controlled difficulty comparisons; adjustable size or
confusing prose alone is not our novelty claim. Our scope is reliability-aware
answerability and certified information distribution. This comparison was checked
2026-10-09 and should be refreshed before a resource paper or public release.
