# Initial publication — October 27, 2026

The owner requested public publication with rights review still pending.
Prepare an organization-owned public research preview of the documentation and
sanitized measured summaries, with the open research/publication questions
prominent. The software remains 0.5.0rc2; no paid calls are added.

The full software/data release remains pending redistribution rights, license
scope, attribution, human reviews, private-history/archive clearance and
organization publishing configuration. No license grant or human signoff is
implied. The owner subsequently explicitly authorized making the existing
`TrustPrism/clue-benchmark` repository public, including its history. Do not
create a second repository. Ignored operational archives and credentials remain
local; do not upload them.

## Initial publication contents

- Documentation, tutorials and parameter reference describing the candidate.
- Original-study index, measured counts, phase-separated replication findings,
  uncertainty and cost, plus the sanitized evaluator outcome summaries.
- Open research questions and unresolved full-release decisions at
  `results/open-questions/`.
- Explicit pending-license and no-public-PyPI status.

## Research questions

Is the pilot's apparent noise benefit repeatable? What explains individual-world
changes and the harder-setting dip? When is robustness worth extra context cost?
Which structural difficulty controls predict errors? How stable are results
across resources, formats and model revisions? Can agents learn useful
communication? Does supported correctness improve with completion? Do independent
readers agree with the formal rule interpretation?

## Verification and scope

Build documentation strictly and verify the public export file inventory/hashes
before upload. Export the generated static site to a clean `gh-pages` branch of
the existing repository; include no operational archive, raw receipt, credential,
approval or dispatch ledger in that site. Keep
the exact public export inventory with this record. Verify the public URL without
authentication after deployment. Record actual URLs/outcomes only after success.

## Current handoff state

The source and `gh-pages` deployment branch are pushed to the existing
repository. The static deployment commit is
`857aab7` and `preview-site-manifest.json` records the 61 exported files and
their hashes (plus the self-contained manifest in the deployment branch).
The initial prerelease draft is saved at:
https://github.com/TrustPrism/clue-benchmark/releases/edit/untagged-6dbb2416e32e718a4dee

GitHub requires the owner's interactive “Confirm access” authentication before
the requested private-to-public visibility change. That is an account-security
step, not missing publication authorization. No second repository was created.
The repository was still private at verification; Pages was not enabled and
anonymous deployment verification is pending. No public URL is claimed live.

After authentication, finish the authorized visibility change, configure Pages
from `gh-pages` at the repository root, publish the saved prerelease, and verify
anonymous access to the repository, results, open questions and downloads.
Keep licenses and human reviews marked pending. The full 282-test suite, strict
MkDocs/Twine checks and offline wheel installs on Python 3.12–3.14 passed for the
cost-formatting update; no additional paid calls were made.
