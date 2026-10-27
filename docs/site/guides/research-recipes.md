# Four worked research recipes

Each recipe keeps logical guarantees separate from observed model behavior. Use a new output directory; none of these commands invokes a model.

## Independent nuisance dose

Question: can more irrelevant evidence improve a weaker model's supported accuracy? `noise-volume` generates one four-necessary-report branching world with 100 satisfiable independent records, no false reports, single-agent complete evidence, and the useful stream in front.

```sh
clue-benchmark generate-dataset --preset noise-volume --output runs/noise
clue-benchmark examples replay measured-results --output runs/counts
```

The motivating low-thinking Lite counts were 2/5, 3/5, 5/5 at 0/100/1000 records on the same five worlds. Flash was 5/5 throughout. In the eight-report stratum Lite was 5/8, 5/8, 4/8, including one provider failure at the largest dose. This is not established noise-assisted reasoning: one attempt per condition, some identical payloads elsewhere changed answers, and input costs rose sharply.

The fixed endpoint was Lite's 1000-minus-zero change in the four-report stratum,
with two attempts averaged per world. The initial study plus one final expansion
completed twelve worlds and 144 scored calls plus two initial probes. Combined
Lite counts were **10/12, 9/12, 10/12** in the primary stratum and **9/12, 5/12,
7/12** in the eight-report stratum; Flash scored 12/12 throughout. Six worlds per
stratum give limited precision. The primary estimate is zero with a descriptive
95% world-bootstrap interval [-25, +25] points; unchanged scores are not proof of
equivalence. The combined estimate is explicitly exploratory because expansion
followed the initial result. Estimated total **$6.961763**, no holds, below $10.
See [separate phases and replay](../results/index.md#nuisance-records).

To prepare a new exact study offline, supply explicit reviewed model prices and every prior measured bank:

```sh
clue-benchmark prepare-nuisance-followup --models models.json --prior-bank prior/bank --output runs/followup
```

This command prepares candidates and maximum reservations only. It cannot authorize inference. Recognizable records differ from adversarial prose; the design changes context length and composition together and cannot identify a mechanism.

## Complete/private/shared evidence

Question: does the receiver have enough information? Use `distributed` and the [eight-world replay tutorial](../tutorials/distributed-evidence.md). The complete views are unique; private views are ambiguous, and bounded forwarding retains report identities. The observed star success is a property of this protocol and fixture, not a universal topology ranking.

## False-report robustness

```sh
clue-benchmark generate-dataset --preset false-reports --output runs/false
clue-benchmark explain-config --preset false-reports
```

Question: can an agent reason under an at-most-k rule? The preset publishes allowance two with one sampled false report; actual corrupted identities are private. Final uniqueness is certified under the published rule. The historical fixed-allowance experiment scored Lite 8/8, 7/8, 8/8 and Flash 8/8 throughout at 0/1/2 actual corruptions. Necessary evidence was not held fixed. This small result is not monotonic evidence of difficulty.

## Burden and resource limits

```sh
clue-benchmark generate-dataset --preset hard-example --output runs/hard
```

This small bounded example has eight suspects and eight necessary reports. It is not the measured large hard regime. At 32 necessary reports, historical Flash scored 30/30 in two path/tree arms while Lite scored 9/30 and 7/30, from three attempts on ten worlds per arm. Simple construction heuristics solve some families.

The fresh large confirmation scored 9/48 correct, 28 wrong and 11 abstentions with 64 suspects, 455 interacting reports and 32768 output tokens including thinking; no protocol/provider failures. The reports were not individually necessary. A prior adaptive six-world example improved from 2/6 to 5/6 with larger output allowance. Resource budgets materially affect interpretation. Do not merge these settings into one model score.
