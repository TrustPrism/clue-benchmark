# Completed pilot checkpoint — 2026-10-09

**All 270 original assignments were dispatched: 269 settled responses and one
preserved provider failure.** The approved 193-request continuation completed
without new errors, retries or model substitutions. No further model calls are
scheduled.

## Delivered measurements

- Matched archive-volume cases with certified four/eight-report evidence burden.
- Zero, one and two false reports under a fixed at-most-two reliability rule.
- Complete/private information and bounded star/ring/chain forwarding.
- Correctness, evidence-supported correctness, abstention, delivery, calls,
  tokens, latency and cost; world-level descriptive paired contrasts.
- [Results and four figures](pilot-results.md), [aggregate data](../benchmarks/pilot-results.json),
  and [per-assignment evaluator outcomes](../benchmarks/pilot-episodes.jsonl).

The clearest finding is that certification distinguishes an unsupported correct
guess from an answer justified by sufficient evidence. The selected false-report
cases were largely easy for these models; added archive volume did not reliably
reduce accuracy. The results do not establish a frontier-model weakness.

## Spending and preserved failures

- Receipt-based estimated cost at frozen rates: **$4.006113**.
- Recovery-phase HTTP 500 reservation: **$0.138501**, retained.
- Three earlier diagnostic reservations: **$0.036390**, also retained.
- Estimated costs plus holds: **$4.181004**, within the original **$20 ceiling**.
- Remaining budget capacity: **$15.818996**; no further execution is authorized
  by this completed plan. These figures are not a provider invoice.

Original plans, approvals, receipts and ledgers remain unchanged under ignored
`runs/`. The [execution status](../benchmarks/pilot-execution-status.json) preserves
all earlier attempts. The [continuation review](../benchmarks/pilot-continuation-preflight.json)
records the 193 mapped assignments and successful execution. Every continuation
assignment was untouched in the stopped recovery; its failed request was not
retried. Some preplanned demonstrations intentionally reuse identical complete
inputs, which are identified separately in the measured report.

Recovery pilot ID:
`a17b1002cb710aebce1d8516e09653e391db45710b0b70bbff6e11421219728b`.
Continuation pilot ID:
`8e4d41c7c4f144e8b3834897019ff3081129d515f4aa0772bfedf350bcc9517f`.

The offline collector preserves dispatched failures and combines continuation
results under original assignment denominators:

```sh
python examples/collect_pilot_results.py \
  --original runs/pilot-recovery --continuation runs/pilot-continuation \
  --output runs/pilot-combined/collection.json
```

Current software verification: **161 passing tests**, including continuation
merge checks. Public release still requires independent language review,
independent reproduction and resolved licensing. The repository remains private;
publication and further paid evaluations require separate authorization.
