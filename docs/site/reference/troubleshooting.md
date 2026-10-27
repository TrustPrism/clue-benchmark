# Troubleshooting

Start with the message you received. An incomplete or unresolved result is reported explicitly; it is never silently treated as a certified puzzle.
{.lead}

## When generation cannot finish

### Candidate exhaustion

Inspect the saved rejection reasons. Use a fresh output directory with a revised configuration. Increasing a retry limit cannot make contradictory requirements feasible.

An incomplete bank uses **exit status 2**.

### Solver timeout or work exhaustion

The result is **unresolved**. Use a declared larger offline budget on fresh outputs if appropriate. Do not disable certification or count the timeout as a proof.

### Distinct values exhausted

Expand the domains or active-value set, or reduce the number of suspects. Equality construction families require repeated assignments.

### Family and enabled types disagree

Restore the required predicates or choose a compatible family and route. `redundant_paths` needs exactly `suspect_count + 1` reports per attribute.

### Impossible quotas or coalition requirements

Check the shared count, replication factor and per-agent quotas. Coalition checks support **at most eight agents**. More retries do not fix impossible quotas.

### Ambiguity conflicts with a sufficient subset

For globally ambiguous cases, set the sufficient bounds and minimum coalition size to `null`. Do not claim a unique answer.

## When outputs already exist

**Exports, reports and replays** need a fresh destination:

```sh
clue-benchmark examples replay nuisance-followup \
  --output runs/nuisance-new
```

**Generation** can resume a checkpoint only when the source and configuration match. Complete matching datasets return without being rewritten.

For a stale schema, source or configuration, use the frozen historical source for its historical plan—or prepare a new plan and output. Do not rewrite hashes to make an old plan pass.

## When size bounds cannot be met

### Tokenizer is absent

Supply a tokenizer with a stable identity through Python and use `workers=1`, or remove token constraints. Do not silently substitute another tokenizer.

### Word or token bounds are impossible

Raise the bound or explicitly change the requested evidence. The generator never truncates evidence to fit.

### Model context would overflow

Reject the request before dispatch. Do not omit evidence or shrink an answer allowance after freezing a matched study.

## When a model run fails

!!! warning "Keep failure types separate"
    A wrong answer, malformed final action, provider failure and unresolved budget hold are different outcomes.

### Malformed tool call or missing final action

Retain a protocol failure. Inspect the saved finish reason separately from reasoning errors.

### Provider error, model drift or unknown usage

Stop and preserve the returned identity, safe receipt and maximum reservation. Reconcile from documented evidence; do not edit ledger balances or assume zero cost.

### Held funds after an interruption

Resume only with the same plan, sources and durable ledger. An unresolved dispatch must not replay automatically. **Zero automatic retries is intentional.**

## Supported platforms

- **Python:** 3.12–3.14 checked on Linux and macOS in hosted CI.
- **Local installation:** clean offline candidate-wheel checks on macOS Python 3.12–3.14; source-archive installation also checked.
- **Windows:** not advertised as verified.

Generation and saved-data replay are distinct from optional native provider paths. Check [PR #2](https://github.com/TrustPrism/clue-benchmark/pull/2) for checks on the current revision.
