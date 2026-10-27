# Bundle data dictionary and dataset card

Every community bundle contains five files. `cases.jsonl` streams one public case header followed by report rows (`kind`, `case_id`, `report_id`, deterministic `text`, formal `constraint`). Headers include suspect IDs/domains, display names, assignment rule, public corruption allowance, report count and presentation identity. `partitions.jsonl` maps each original report ID to its owner agent IDs and partition identity.

`answers.jsonl` is evaluator-only: sampled solution, possible culprits, actual false report IDs, core report IDs and nuisance count. `certificates.jsonl` is evaluator-only: answerability, sufficient-subset bounds, witnesses, reliability/coalition checks and partition quotas. `manifest.json` identifies schema/software/solver, resolved config/config hash, SHA-256 for the other four files, source/checkpoint identity, world/split list, metrics and explicit release gates. The manifest is not an agent input: it can expose evaluator metrics and seeds.

Checksums detect changes, not human approval, originality, logical depth, or license clearance. Public export uses positive case/report/constraint field allowlists and does not copy the manifest, partitions, evaluator files, checkpoints, ledgers or receipts. Anyone releasing labels for reproduction must keep them out of agent input directories.

## Scope and provenance

Synthetic worlds, deterministic templates and configured domains; no human cases or personal records are required. Coverage depends on selected families, types, domains and acceptance filters. Rejection sampling changes observed frequencies. Known shortcuts exist in construction families; certified information cost is not a certified hardness scale. Splits use world hashes with optional family transfer overrides; paired variants share a world split.

Appropriate uses include evidence sufficiency controls, reliability reasoning, abstention, communication delivery and bounded reproducible demonstrations. Do not infer real-world investigative skill, universal frontier-model weakness, human validation, or learned collaboration from these scores.

Code license proposal: Apache-2.0. Dataset/prose proposal: CC BY 4.0. **Neither is granted by this candidate; ownership clearance is pending.** No hosted dataset URLs, Croissant distribution URLs, DOI or public upload is claimed. Large measured archives remain separate private artifacts until screened and cleared. The wheel contains only tiny example data and sanitized assignment outcomes for offline reanalysis.
