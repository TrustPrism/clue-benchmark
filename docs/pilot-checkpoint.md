# Prepared pilot checkpoint — 2026-10-09

**Status: offline prepared; model results pending.** No credentials were read and
no Gemini requests were sent. The selected models and prices were checked against
provider documentation; API access and account-specific quotas remain unchecked.

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
- Software verification: **130 passing tests**, including matched controls,
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

To collect model results, the authorizing human must approve this concrete
pilot and provide a local credential source. A key by itself does not authorize
dispatch. Independent English review, reproduction and licensing remain release
requirements that this software checkpoint does not complete.
