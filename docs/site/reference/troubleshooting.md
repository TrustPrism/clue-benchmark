# Troubleshooting

- **Distinct values exhausted:** expand every domain/active-value set or reduce suspects; equality families require repeated assignments.
- **Family/types disagree:** restore required predicates or choose a compatible family/route. Redundant paths needs exactly n+1 reports per attribute.
- **Impossible quotas/coalition:** check shared count, replication, per-agent sums and agent limits (at most eight). A retry limit does not make impossible quotas feasible.
- **Ambiguous with a sufficient subset:** set sufficient bounds and minimum coalition to null; do not claim a unique answer.
- **Tokenizer absent:** supply a stable-identity tokenizer via Python with workers=1, or remove token constraints. Do not silently switch tokenizers.
- **Impossible word/token bounds:** raise the bound or explicitly change the requested evidence. Evidence is never truncated to fit.
- **Candidate exhaustion:** inspect saved rejection reasons and choose a new output config/directory. Incomplete is exit 2, not a complete bank.
- **Solver timeout/work exhaustion:** unresolved; use a declared larger offline budget on fresh outputs. Never disable certification.
- **Context overflow:** reject before dispatch. Do not omit evidence or shrink an answer budget after freezing a matched study.
- **Malformed tools/missing final action:** retain a protocol failure and inspect the saved finish reason separately from wrong answers.
- **Provider error/model drift/unknown usage:** stop. Preserve returned identity, safe receipt and maximum reservation. Use the documented reconciliation procedure; never edit ledger balances or assume zero cost.
- **Held funds/interruption:** resume with the same plan, sources and durable ledger. An unresolved dispatch must not replay automatically; zero retries is intentional.
- **Stale schema/source/config:** use the frozen historical source for historical plans, or prepare a new plan/output explicitly. Do not rewrite hashes to make a plan pass.
- **Existing export/report/replay output:** choose a new path. Generation alone supports identity-checked checkpoint resume.
- **Platform limitations:** native provider paths/locking are separate from offline generation. Local candidate verification is macOS/Python 3.12–3.14; Linux and Python 3.12/3.13 CI jobs are configured, not claimed as completed. Windows is not advertised as verified.
