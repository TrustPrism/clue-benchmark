# What is in a dataset?

A community bundle contains five files. Only the public export belongs in an agent's input directory.
{.lead}

## The five bundle files

| File | Purpose | Give it to the agent? |
|---|---|---|
| `cases.jsonl` | Public case headers and report rows. | Use the allowlisted public export. |
| `partitions.jsonl` | Maps original reports to owner agents. | No. |
| `answers.jsonl` | Sampled solution, possible culprits and actual corruption identities. | **No — evaluator only.** |
| `certificates.jsonl` | Answerability, subset bounds, witnesses and coalition checks. | **No — evaluator only.** |
| `manifest.json` | Configuration, hashes, versions, splits, metrics and source identity. | **No — can reveal seeds and evaluator metrics.** |

Create the agent-safe file:

```sh
clue-benchmark export-public runs/demo \
  --agent 0 \
  --output runs/agent.jsonl
```

The export uses positive field allowlists. It leaves out manifests, partitions, evaluator files, checkpoints, ledgers and receipts.

## Public case and report rows

`cases.jsonl` starts each case with a header, followed by its reports.

**Headers** describe suspect IDs, domains, display names, assignment rules, public corruption allowance, report count and presentation identity.

**Report rows** contain `kind`, `case_id`, `report_id`, deterministic `text` and the formal `constraint`.

<details markdown="1">
<summary>Evaluator files in more detail</summary>

- **Answers:** sampled solution, possible culprits, actual false-report IDs, core report IDs and nuisance count.
- **Certificates:** answerability, sufficient-subset bounds, witnesses, reliability/coalition checks and partition quotas.
- **Manifest:** schema/software/solver identities; resolved configuration and its hash; SHA-256 values for the other four files; source/checkpoint identity; world/split list; metrics; explicit release gates.
- **Partitions:** owner agent IDs and partition identity for each original report.

</details>

## What hashes do—and do not—establish

Checksums detect changes. They do **not** establish human approval, originality, logical depth or license clearance.

Keep released evaluator labels separate from agent inputs, even when sharing them for reproduction.

## Dataset scope

Cases use **synthetic worlds, deterministic templates and configured domains**. No human cases or personal records are required.

Coverage depends on the selected families, types, domains and acceptance filters. Rejection sampling changes observed frequencies. Some construction families have known shortcuts.

Splits use world hashes, with optional family transfer overrides. Paired variants share a world split.

### Appropriate uses

- Evidence-sufficiency and reliability controls.
- Abstention and supported-correctness evaluation.
- Communication delivery checks.
- Small, bounded and reproducible model demonstrations.

These scores do not establish real-world investigative skill, universal frontier-model weakness, human validation or learned collaboration.

## Saved nuisance measurements

The packaged resource `nuisance-followup.json` uses **`clue-nuisance-measurements-1`**. It contains all **144 scored slots**.

| Fields | Meaning |
|---|---|
| `phase` | Initial study or final extension. |
| `burden`, `dose`, `world_id`, `model`, `repeat` | Identify the matched assignment. |
| `answer` and outcome flags | Evaluator correctness, support, abstention, protocol and sufficiency labels. |
| Token counts and latency | Observed resources; output includes thinking where billed. |
| Integer microdollar values | Exact estimated costs. Dollar displays round to two decimals. |
| Request ID | Unique per dispatched attempt. |

The accounting header includes the two initial probes and the combined **$10.00 cap**. Scored panel costs exclude probes. Estimates are not provider invoices.

Current software is **0.5.0rc2**; the measured generation/evaluation sources remain frozen at **0.5.0rc1**. The post-result expansion is labeled, and combined summaries are exploratory.

No credentials, human authorization evidence, SQLite ledgers, raw receipt bodies or provider prose belong in these distribution copies. Public agent exports never read the evaluator measurement resource.

## Licensing and distribution

**Licensing is pending.** Proposed scopes are Apache-2.0 for code and CC BY 4.0 for data/prose; neither is granted by the candidate.

Public documentation includes sanitized outcome downloads. There is no claimed PyPI release, DOI, full hosted dataset or validated hosted Croissant distribution. Large measured archives remain separate artifacts pending screening and clearance.

[See the remaining release questions →](../results/open-questions.md#before-a-full-release)
