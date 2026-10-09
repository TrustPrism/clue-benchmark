# Pilot checkpoint — 2026-10-09

**Current state: 76 settled model results; stopped on a provider error.** The
approved 270-request recovery pilot dispatched 77 requests. Request 77 returned
HTTP 500 without usage. The harness stopped immediately, kept the reservation,
and made no retries. Another 193 original assignments remain untouched.

## Results available now

- Gemini 3.8 Flash answered all **38 settled cases correctly**.
- Gemini 3.5 Flash-Lite answered **24/38 settled cases correctly**, including one
  abstention among its other outcomes.
- These are archive-volume cases only. The false-report and distributed model
  experiments have not run.
- Added irrelevant records did not consistently reduce success in this small
  cohort. Do not turn the provider error into a claim about reasoning weakness.

The [partial results](pilot-results.md) explain coverage and limitations. The
[aggregate receipts](../benchmarks/pilot-results-partial.json) retain original
assignment denominators and separate pending assignments, provider failures,
incorrect answers and abstentions.

## Spending and preserved history

- Settled receipt-derived cost: **$3.392829**.
- HTTP 500 reservation: **$0.138501**, retained because usage is unknown.
- Three earlier diagnostic reservations: **$0.036390**, also retained.
- Settled costs plus all holds: **$3.567720** against the original **$20 ceiling**.
- Remaining authorized budget capacity: **$16.432280**; this is capacity, not
  approval of a new execution plan or a provider invoice.

All original plans, authorizations, receipts and ledgers remain unchanged under
ignored `runs/`. The [execution status](../benchmarks/pilot-execution-status.json)
keeps the earlier failures, successful schema diagnostic and accounting audit.
The schema check established successful transport but yielded no recoverable
answer score. Its reservation was not retroactively cleared.

## Concrete continuation awaiting approval

Ignored `runs/pilot-continuation/` contains nine frozen jobs with **193 requests**:

- Complete/private information and four deterministic forwarding conditions.
- Zero, one and two false reports under the same published at-most-two allowance.
- One remaining Flash archive assignment, scheduled last.

Both models and their original settings are unchanged. The conservative maximum
is **$3.554188**, under the remaining $16.432280 ceiling. Every serialized request
passes context preflight; the largest input upper bound is **427,530 tokens**,
plus the 4,096-token output reservation, below the 1,048,576-token capacity.
Pacing alone requires at least 32 minutes; inference adds time.

The [continuation review](../benchmarks/pilot-continuation-preflight.json) records
identities, scope, budgets and checks. Each request maps to an untouched original
assignment. The failed request will never be retried. The single-case archive
re-export produces a byte-identical provider payload. The offline collector
refuses to replace any dispatched receipt, including failures:

```sh
python examples/collect_pilot_results.py \
  --original runs/pilot-recovery --continuation runs/pilot-continuation \
  --output runs/pilot-combined/results.json
```

Recovery pilot ID:
`a17b1002cb710aebce1d8516e09653e391db45710b0b70bbff6e11421219728b`.
Continuation pilot ID:
`8e4d41c7c4f144e8b3834897019ff3081129d515f4aa0772bfedf350bcc9517f`.

**Fresh explicit approval is required:** the requested unknown-usage stop rule
ended the current execution. Approval of the stopped frozen plan does not
reauthorize another plan. Preparation reads no credentials and contacts no
providers. Public release still requires independent language review,
reproduction, resolved licensing and completion of the measured demonstrations.
