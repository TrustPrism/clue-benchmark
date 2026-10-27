# Complete, private and forwarded evidence

```sh
clue-benchmark examples replay distributed-evidence --output runs/replayed
```

This bundled eight-world historical fixture is small enough to ship with the wheel. The command validates its checksums and independently recomputes which answers each view permits. It writes `replay.json`, the five-file evaluator bundle, and `report/index.html`.

For all eight complete views the solver finds a unique answer. The 32 private views remain ambiguous. One round of programmed star forwarding brings enough reports to the hub in all eight worlds. This is an **offline solver control**, not new model inference and not learned communication.

The historical low-thinking Flash measurements were 8/8 complete answers, 32/32 appropriate private abstentions, and 8/8 answers at the star hub. In the ambiguous ring condition Lite made two correct unsupported guesses. [Replay measured counts](../results/index.md) separately; those observations do not become new experiments when recomputed.

Generate a fresh small example with `clue-benchmark generate-dataset --preset distributed --output runs/fresh-distributed`. Each private view receives a certified partition, retaining original report identities. More received reports do not guarantee sufficient evidence: which reports arrive matters.
