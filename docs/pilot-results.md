# Exploratory pilot execution report

Execution is in progress on development data only. The frozen current manifest
is `studies/pilot-v0.3.json`; the ledger preserves every dispatched episode and
all charges across the three disclosed source amendments. Final results will be
recorded after the runner completes or reaches a stop condition. The 744-case
model test split remains untouched.

The initial Flash deduction condition completed 24/24 correctly. Six early
investigation episodes stopped on an overly conservative byte estimate; two
other episodes retain a maintenance or SDK preflight failure. One further
investigation episode reported 38,361 billed tokens, exceeding the intended
32,768-token allowance because native countTokens understated retained thinking
history. Its full usage/cost was captured and its score remains incorrect.
The corrected runner uses both native content counts and the previous request's
reported input/output plus new tool-result bounds. No prior episode was replayed,
no cost was removed, and the $50 combined ceiling was never reset.

These engineering failures and mixed source revisions prevent a clean model
ranking. The pilot is exploratory; the report will keep every declared episode
in the denominator and disclose completion and measurement coverage. A newly
frozen study is needed for a confirmatory comparison.

The native compatibility probes are additional, separately logged exchanges.
The local runtime is Apple M4 Pro, 24 GiB memory, Ollama 0.34.0, Qwen3.5-9B
Q4_K_M, 32,768 context tokens, digest
`6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`.
Hosted/local latency is descriptive and is not a capability ranking.

Automated verification passed 143 tests, formatting/lint, package build,
installed-wheel smoke checks, and the 960-case dataset integrity check.
The repository remains private, with licensing/publication pending.
