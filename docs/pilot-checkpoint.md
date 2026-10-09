# Prepared pilot checkpoint — 2026-10-09

**Status: live pilot stopped before usable model results.** The human approved
the frozen pilot and supplied a local key. Its first Gemini request returned a
provider error without usage; the runner stopped and retained its $0.01213
reservation. Actual spending is unknown. The other 287 requests were not sent.
The [execution checkpoint](../benchmarks/pilot-execution-status.json) records this
failure separately from the offline controls. Administrative failure scores do
not measure model reasoning performance.

Subsequent read-only model metadata checks succeeded for both chosen IDs and
confirmed the declared context limits. The original harness did not retain the
provider's numeric error status, so the exact rejection cause is unknown. The
harness now saves safe numeric status codes in durable receipts; raw error
messages and credentials are excluded. No inference request has been retried.

The user subsequently updated the key and authorized the one-request diagnostic.
It returned **HTTP 400 without usage** and stopped. Read-only metadata access also
succeeded with the updated key. The two reservations total **$0.024266**; actual
spending remains unknown and no usable model results exist.

- Experiments: matched archive volume, false reports, and distributed evidence.
- Full local pilot: ten arms, eight worlds per arm, **80 case variants across
  24 distinct underlying worlds**. Variants are not independent observations.
- Models: Gemini 3.5 Flash-Lite and Gemini 3.8 Flash, low thinking, temperature
  zero, 4,096-token output cap, one repetition.
- Assignments: **288 requests across fourteen jobs**, paced by at least ten
  seconds per dispatched request. Minimum pacing time is 48 minutes, excluding
  inference and local work. This is not a completion-time prediction.
- Context: **zero preflight failures**. The largest input upper bound is
  **427,780 tokens**, computed conservatively from serialized bytes and tool
  headroom; it is not a tokenizer count. With the output reservation it remains
  below the declared 1,048,576-token capacity.
- Cost: conservative full-pilot maximum **$12.568273** at frozen paid rates;
  **$20 total ceiling**, divided across jobs. This is a bound, not a charge or
  expected expenditure. Other activity on the provider project is excluded.
- Original pilot software verification: **130 passing tests**, including matched controls,
  budget/context failure, mock dispatch and no-repeat resume.

## Useful findings from offline controls

- Adding 100 or 1,000 records preserves exactly four/eight required clues in
  the corresponding burden stratum. It increases volume, not necessary evidence.
- All 32 private agent views in the distributed cohort are insufficient.
- Agent 0 receives sufficient evidence in 8/8 cases with the one-round star
  and three-round chain, and in 0/8 with the one-round ring or chain.
  These outcomes depend on the stated recipient, graph, partitions and round
  budget; they are not a general superiority claim about star networks.
- The reliability-aware solver identifies the answer in all 24 false-report
  variants. Assuming every report true recovers the answer in 8/8 zero-false,
  6/8 one-false and 4/8 two-false cases. These are solver controls, not LLM
  accuracies. The model comparison will test whether models make similar errors.

Full controls and settings are in the [compact profile](../benchmarks/pilot-preflight.json),
[sample bundles](../examples/datasets/pilot/README.md), and [experiment guide](pilot.md).
The dated [comparison](resource-comparison.md) explains how the linked resources
informed the demonstrations without asserting extreme novelty.

## Frozen local inputs and next action

The full pilot is generated under ignored `runs/pilot-final/`, with hashes, accepted
seeds and preserved generation receipts; live execution has separate resumable ledgers. Its suite ID is
`31ecd2c348237221921ac5ccc3277b2e8a3927ecc03926d15a7206d0dac8506b`.
The prepared model pilot ID is
`15fcc4c9eb51fa5dd48116fff385c0dcf6ed1fca02fcb25795501133e8b3788f`.
Reproduction elsewhere generates its own hashes and requires its own approval;
do not reuse these identifiers for newly generated inputs.

The original pilot remains stopped with its reservation intact. Its source is
preserved at commit `b1075ef3f59d0766fcffd3fe647f2fa7a8042187`; the diagnostics fix
changes source hashes and does not alter or reauthorize that plan.

A separate offline-prepared diagnostic under ignored `runs/gemini-diagnostic/`
uses one previously undispatched world, Gemini 3.5 Flash-Lite, the same settings,
zero retries and a $0.02 ceiling. Its conservative maximum is $0.012136;
the input bound is 6,320 tokens and passes context preflight. Its plan ID is
`e83e5d73816edfa69bafeb4bfea5d17c142fafe717a0c5f4598c810874b2917f`.
That diagnostic is now stopped and its authorization cannot fund another run.

Offline inspection found a likely Google schema compatibility issue: JSON Schema
was passed through the OpenAPI `parameters` field, including a closed-object
keyword, and abstention had an empty object schema. The adapter now uses Google's
`parameters_json_schema` field for the answer and omits parameter declarations
for the no-argument abstention. The [Google API reference](https://ai.google.dev/api/generate-content.md)
documents the separate JSON Schema field. A mock HTTP transport verifies what
the actual SDK serializes and a native abstention response. This is a proposed
compatibility fix, not a confirmed explanation of the original HTTP 400.

A corrected one-request live check was prepared under ignored
`runs/gemini-schema-diagnostic/`. It uses a third, previously undispatched world,
the same model settings and a $0.02 ceiling, with a conservative maximum of
$0.012124 and input bound of 6,278 tokens. Its plan ID is
`46351ce9a7d657464239562b07ffdd8a7e71d605f67a2beecd6f6d68528421a0`.
The user approved it. Gemini successfully returned a response identifying
`gemini-3.5-flash-lite`, with 1,369 prompt tokens, 16 candidate tokens and 1,385
total tokens. The prior parser stopped because `thoughtsTokenCount` was omitted.
The [UsageMetadata reference](https://ai.google.dev/api/generate-content.md#UsageMetadata)
defines total as prompt + thoughts + candidates, so these counters establish
zero thinking tokens. The updated parser derives zero only when that residual
is exactly zero, all three reported counters are nonnegative integers, and no
tool-use tokens are reported. Missing totals, positive residuals, invalid values
and contradictions still stop accounting. The original receipt stays unchanged
and the derived value is explicitly marked.

At the frozen rates, this response's receipt implies **$0.000451**. Its original
reservation is nevertheless retained; all three holds total **$0.036390**.
The earlier pre-accounting stop did not retain the native answer call, so this
check establishes successful transport, not answer accuracy. Future episodes
retain native calls before accounting checks. No dispatched request was repeated
and none of the frozen ledgers was altered.

## Prepared full recovery pilot

Ignored `runs/pilot-recovery/` now contains a new frozen pilot and review file.
It re-exports and independently validates the original certified cases after
excluding **every previously dispatched world from all models and variants**.
This leaves **71 case variants across 21 worlds**, with five matched worlds in
each four-clue burden arm and eight in the other arms. Selection uses dispatch
status, not model correctness. Original seed receipts, rejection records and
exclusion provenance are preserved.

The same two models, settings and fourteen jobs yield **270 requests**, with
zero context preflight failures. The conservative maximum is **$10.811723**;
the remaining ceiling is **$19.963610**, which together with the three earlier
holds preserves the user's original $20 cap. Pacing alone takes at least
45 minutes; inference adds time. No recovery requests have been made.

Recovery pilot ID:
`a17b1002cb710aebce1d8516e09653e391db45710b0b70bbff6e11421219728b`.
Suite ID:
`cb0d2e5645919558d40ed64b86812480417184610639506bab96821743ee4d15`.
New explicit approval is required because the corrected software and selected
cohort have new frozen identities. Earlier approvals do not authorize this pilot.
Current software verification: **156 passing tests**, with lint and format checks
passing. Dry preparation performs no credential reads or network calls.

Independent English review, reproduction and licensing remain release
requirements that this checkpoint does not complete.
