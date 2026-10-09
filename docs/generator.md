# Generator reference

This reference describes the current `clue-community-1` dataset contracts,
verified properties and evaluation interfaces. Installation instructions and
release status are in the repository README.

## Quick start

From an installed package:

```sh
clue-benchmark generate-dataset --config examples/basic.json --output /path/to/bank
clue-benchmark validate-dataset /path/to/bank
clue-benchmark profile-dataset --config examples/large-corpus.json --output /path/to/large-bank
```

After installation, `python -m clue_benchmark` is equivalent to the console
command. Generation and validation need no network or model.
An incomplete bounded generation returns exit code 2 and preserves successful
cases and rejection receipts. Rerunning resumes; changing code, configuration,
solver version or tokenizer identity requires a new output directory.

The normal install supports offline generation. Install the `providers` extra
only for evaluation preparation/native provider execution. Actual live calls
still require a new authorization; package installation does not enable them.

## Public Python API

```python
from clue_benchmark import CommunityConfig
from clue_benchmark.community_generation import generate_case, partition, score
from clue_benchmark.community_bundle import (
    generate_dataset,
    validate_dataset,
    iter_cases,
    export_dataset,
)

config = CommunityConfig.from_dict(
    {
        "puzzle": {
            "family": "branching",
            "config": {"suspect_count": 8, "clue_count": 12},
        },
        "evidence": {"minimum_sufficient_clues": 8, "maximum_sufficient_clues": 8},
        "distribution": {"agent_count": 4, "minimum_coalition_size": 4},
        "dataset": {"count": 10, "output_directory": "/path/to/bank"},
    }
)
manifest = generate_dataset(config)
for row in iter_cases("/path/to/bank", agent_id=0):
    consume_public_record(row)  # Your agent/framework; no evaluator data supplied.
```

`generate_case(config, seed)` returns `status`, the private case, partition,
certificates and diagnostics. Rejection returns no case and never relaxes a
setting. `partition(case, config, seed)` independently generates/checks an
allocation. `score(case, response, evidence)` distinguishes sampled-answer
correctness from unique support under the observed evidence. The strict response
forms are `{"kind":"answer","target":"S01"}` and `{"kind":"abstain"}`.

`export_dataset(config, accepted_checkpoint_paths, root)` exports previously
generated private receipts; normal users should call `generate_dataset` instead.
`iter_cases` streams public header/report rows, rather than constructing a giant
array. Never hand private generator results directly to an evaluated agent.

## Configuration

Five sections are supported; unknown keys fail. Every manifest records resolved
defaults. `puzzle.config` nests the existing flat `Config` contract, preserving
retained flat puzzle commands and configuration files without migration.

- `puzzle.family`: `standard`, `pairwise`, `cross_attribute`, `equality_tree`,
  `branching`. Standard/comparison routes reuse the prior generator; equality
  tree is a path through innocents, and branching is a binary equality tree.
  Neither name claims measured reasoning depth. Constructed families require
  crime-positive, unary-positive and suspect-same-as clues. Extra clue slots use
  the enabled truthful pool and can introduce shortcuts; final cost is checked.
- `puzzle.assignment_mode`: `repeated` (default) or `distinct`. Distinct means
  all suspects have different values in each attribute, and is enforced in both
  encodings. It requires enough domain values and is incompatible with equality
  families. `pairwise`/`cross_attribute` require their corresponding legacy clue
  types; unsupported family/route combinations fail.
- `evidence.minimum_sufficient_clues`, `maximum_sufficient_clues`: optional hard
  bounds under the **final** reliability rules. The existing legacy minimum is
  also honored. Cost means original distinct reports, not text length, reasoning
  depth, agent calls or an adaptive policy optimum. An upper bound has an actual
  sufficient set; a lower bound has independently checked countermodel cuts.
  An inconclusive optimization may retain valid bounds; requested properties
  must still be proved.
- `evidence.entailed_clues`: extra distinct constraints proved entailed by the
  truthful core. Entailment is evaluated before corruption. These can shorten
  a proof, so minimum cost is recomputed after all evidence changes.
- `evidence.irrelevant_records`: fresh, independently satisfiable binary record
  components with no variables shared with the target. A structural composition
  guarantee preserves target possible-answer sets for every evidence subset.
  This is logical irrelevance, not a claim that people/models ignore the text.
- `evidence.false_reports`: 0–2 substitutions false in the sampled world.
  `corruption_allowance` defaults to the same count, must be at least that count,
  and is at most 2. The public rule is **at most k distinct reports are false**.
  Trusted rules remain unchanged. Allowed clue types apply to replacements too.
  A corruption may change a literal or invert a supported predicate.
- `evidence.answerability`: `unique` by default, `ambiguous` optionally. Unique
  requires exactly the sampled culprit; nuisance attributes may be ambiguous.
  Ambiguous requires multiple feasible culprits and
  `distribution.minimum_coalition_size=null`; minimum-clue bounds are then
  inapplicable. Inconsistent inputs are not generated as valid sampled puzzles.
- `distribution.agent_count`: 1–8. `minimum_coalition_size=2` by default (set 1
  explicitly for single-agent data). Every coalition, including the empty set,
  is checked; all inclusion-minimal sufficient coalitions and alternative-world
  witnesses are exported privately.
- `distribution.shared_reports=0`, `private_replication=1`: shared reports go
  to every agent; private reports go to exactly the replication count, less than
  agent count except in single-agent mode. Sharing never consumes additional
  corruption allowances. Shared nuisance records are allocated first, then any
  remaining shared quota is sampled from target-component reports.
- `distribution.per_agent_quotas=null`: balanced total report incidences by
  default. An explicit list requires one exact total per agent, including shared
  reports and nuisance records. Quotas, shared count and replication must agree.
  `max_attempts=128` bounds partition search. No designated-team constraint is
  provided; users request minimum size and receive all verified teams.
  Exports report shared/private fractions and a realized overlap matrix: each
  entry counts original reports owned by both agents; diagonal entries are quotas.
- `presentation.theme`: `mystery` or `investigation`.
  `naming_seed=0`, `template=compact|expanded`, `clue_order=shuffle|canonical|reverse`.
  IDs/domains in structured evidence retain their meanings; display names have
  an explicit ID mapping. Templates are deterministic, pending independent
  language review. No LLM prose-generation calls occur.
- `presentation.minimum_words`, `maximum_words`: count joined report text and
  narrative padding, excluding public rule/header scaffolding. Minimum words
  adds non-factual archive prose; maximum words cannot truncate evidence.
  `minimum_tokens`, `maximum_tokens` require a Python tokenizer callback with a
  stable `.identity` string and workers=1. Token bounds reject unsatisfied text;
  they do not change clues or claim exact chat-input token counts. Without a
  tokenizer, token count is `null`, not an estimated number.
- `dataset.count=1`, `seed=0`, `workers=1`,
  `splits={"development":0.8,"test":0.2}`. Split allocation hashes the underlying
  world; presentation changes cannot move it. Structural family holdouts listed
  in `holdout_families` go to `transfer`. A single generation job chooses one
  family; build a suite through separate family jobs with disjoint holdouts.
- Profile measurements separate core-construction time, community-certificate
  solver time, total pipeline time, corpus storage, and necessary-evidence cost.
  Solver time excludes formatting/export and the legacy core sampler's internal
  work, which is included in core-construction time. Timings are machine-specific
  manifest metrics and do not change deterministic report-file hashes.
- `dataset.certification_seconds=60`, `max_solver_calls=20000`,
  `max_candidates_per_case=20`: bounded certification and candidate search.
  Legacy core generation retains its separate generation/work limits, checked
  within the overall elapsed certificate window. Wall-time failures can vary
  with hardware; sufficient resources and retained accepted seed lists are
  needed for reproduction.
- `dataset.large_corpus=true` is required above 1,000 nuisance records. The
  included preset produces 50,000 total records, **not 50,000 required clues**.
  Core construction, exact subset optimization and coalition enumeration have
  separate scaling limits. No automatic arbitrary-size reasoning-depth guarantee
  is provided.

## Streaming bundle and guarantees

- `cases.jsonl`: a `kind=case` header followed by `kind=report` rows, each with
  case ID, report ID, constraint and rendered text. This row format makes large
  corpora streamable. Original and replicated reports retain the same ID.
- `partitions.jsonl`: a matching row for every report, listing owners and the
  partition ID. Agent IDs are zero-based; the reference decision-maker is 0.
- `answers.jsonl`: private sampled worlds, possible culprits, false-report IDs
  and core/nuisance bookkeeping.
- `certificates.jsonl`: private production/independent agreement, witnesses,
  exact/bounded sufficient-clue costs and coalition certificates. The nuisance
  namespace can be checked one streamed component at a time.
- Independent component statements use the public predicate `record_positive`;
  no public record carries a truth/relevance classification. Their disconnection
  is derivable from the published component structure and rules.
- `manifest.json`: checksums, versions, complete defaults, accepted worlds/seeds,
  rejection accounting, split/family metadata and resource measurements.

Generation receipts live in `.community-checkpoints/`. Workers are consumed in
seed order and all launched receipts are preserved. Export files are replaced
atomically and the manifest is committed last. Validation checks file hashes,
report identities, nuisance independence, possible culprits, coalition results
and sufficient-subset bounds. Isomorphism screening conservatively rejects
within-bank duplicates; hashes alone do not prove strategic diversity.

The two logical encodings share CP-SAT. Tiny-world exhaustive enumeration is
engine-independent, but this does not constitute independent human review or
proof that every English rendering communicates the intended constraint.

## Model evaluation without taking over users' experiments

The harness supports explicit Google, OpenAI, Anthropic and local Ollama model
configurations using the existing native payload/receipt translators. Direct transport calls remain hard-gated before credential access.
The new path requires a separate manifest-bound dispatch permit and durable
reservation before credentials or transport are used.

Model JSON must include `id`, `vendor`, exact requested `model`, provider-specific
`settings` including `max_output_tokens`, `context_tokens`, and explicit integer
`input_microdollars_per_million_tokens` and `output_microdollars_per_million_tokens`.
Optional `identity` is an exact expected returned-model string; a mismatch stops
execution. Ollama's `settings.context_tokens` must match declared capacity.
Only settings actually supported by the native translator are accepted.

```sh
clue-benchmark prepare-community-evaluation /path/to/bank --models /path/to/models.json --ceiling-microdollars 1000000 --output /path/to/plan.json
clue-benchmark run-community-evaluation /path/to/plan.json --dataset /path/to/bank --output /path/to/run --dry-run
```

A million microdollars is one dollar. Preparing and dry-running plans perform
zero credential reads and zero network calls. Context preflight uses a
conservative serialized UTF-8-byte bound plus tool-envelope headroom; provider
usage is subsequently checked. This is not a tokenizer-measured context count.
Input, output, thinking and cache accounting preserve the existing translator's
limits; unimplemented cache-price decomposition fails closed.

Default conditions are complete evidence in one call, separate calls to each
independent agent, and raw-report sharing followed by one decision-maker call.
Independent results average agents within each world; they are not a vote-based
team result. Star/ring/chain/complete graphs use synchronous rounds and bounded
report payloads. Useful and nuisance records compete under the same public ID
ordering. `forward_evidence` also accepts bounded user-supplied discussion text;
it does not spend model tokens to invent that discussion. Graph policies can be
replaced through the Python interface without giving agents evaluator files.

For an alternative forwarding policy, pass its stable version string as
`forwarding_policy_identity` to `prepare_evaluation` and the callable as
`forwarding_policy` to `run_evaluation`. Set `callable.identity` to that version.
The callback receives `(public_header, report_iterator, ownership_iterator,
limits)` and returns `{"evidence": [[report_id, ...], ...], "messages": [...]}`.
Messages contain `round`, `sender`, `recipient`, `report_ids`, and optional
`discussion`. The harness checks graph edges, round/message bounds, original IDs,
and synchronous evidence availability before passing any content to models.
Callbacks never receive answers or certificates. Custom adapters are responsible
for their own buffering; the built-in policy remains bounded for large corpora.
Adapter code must be versioned by the researcher; the manifest identity is not
a source-code audit. See `examples/policy_adapter.py`.

To enable an actual run, a human must supply a new authorization JSON with:

```json
{
  "schema_version": "clue-community-authorization-1",
  "plan_id": "the exact newly prepared plan ID",
  "approved_by": "the authorizing human",
  "approved_at": "the approval timestamp",
  "spending_ceiling_microdollars": 1000000,
  "max_requests": 10000
}
```

The ceiling and request limit must match the plan. This is a local authorization
contract, not a cryptographic identity service. The CLI does not manufacture
approval. Run with `--execute --authorization /path/to/authorization.json` only
after approval. Credentials or old ceilings alone do not suffice.

Zero retries are allowed. SQLite reservations precede dispatch; unknown usage,
timeouts and interrupted requests retain their maximum cost and block later
calls. Resume never repeats dispatched requests. Preflight failures and all
administratively unattempted assignments remain explicit. Resource/identity
breaches stop execution. Summaries separate correctness, support, failures,
abstention, communication, token usage, observed latency and held costs. World
bootstrap intervals are descriptive and uninformative with one world; examples
are engineering demonstrations, not powered scientific comparisons.

## Demonstrations and release gates

`examples/demonstrations.py --output /path/to/demos` prepares four
datasets crossing 4/8 required clues and 0/100 nuisance records.
The cores contain four additional truthful records to vary structure; the
certified minimum remains exactly 4 or 8. This permits duplicate screening to
retain multiple cases rather than counting renamed copies of one fixed tree.
Add user model
JSON and an explicit ceiling to prepare unexecuted evaluation plans. The script
has no live-execution option. Basic, branching, ambiguous, corrupted and large
presets are also included.
`communication-policies.json` gives explicit star/ring/chain/complete schedules
for four-agent cases; use `--graph`, `--rounds`, and `--message-reports` during
evaluation preparation. Model identifiers and prices must come from the user;
the examples contain no chosen model panel or fabricated results.

The package can be built and installed for offline use now. Public release still
requires resolved ownership/licenses, independent language review, another
person reproducing the workflow, and a frozen model-panel evaluation. Export
manifests keep these gates pending and never claim frontier-model performance.
Novelty claims require a dated comparison with current resources.
