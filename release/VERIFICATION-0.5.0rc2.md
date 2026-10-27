# 0.5.0rc2 production verification — October 27, 2026

The private candidate has **282 passing local tests** (86.98 seconds), plus Ruff
lint/format checks for all 68 tracked Python files. One upstream Google SDK
deprecation warning is unrelated to inference; CI uses provider mocks only.

Fresh noneditable installed-wheel smoke tests passed outside the checkout on
macOS arm64 with Python **3.12.13, 3.13.12 and 3.14.6**. Networking was blocked;
provider/figure/docs extras were absent. Checks covered generation, validation,
public export, callback scoring, distributed-evidence replay, historical gallery
and the final 144-slot nuisance replay. Every shipped source/resource byte
matches the reviewed working tree. Wheel: 317,586 bytes; source archive: 290,723
bytes. Twine checks both metadata/readmes successfully. Strict MkDocs passes.

The final nuisance archive replay passed with networking blocked: all initial,
extension and combined panels, paired contrasts and accounting matched. All 146
paid requests are uniquely settled, with an estimate of **$6.961763**, no holds,
and a combined $10 cap. No further paid calls are authorized by this allowance.
The combined primary estimate is zero, with a descriptive interval [-25,+25]
percentage points on six underlying worlds; it is not an equivalence claim.

Pattern scanning found no credentials/private-key/local-home-path matches in the
candidate wheel/sdist. All members of eight historical archives were scanned;
original private operational/history findings remain documented for manual
review, not erased. Authorizations, keys and dispatch ledgers are never included
in the new distribution copies. Original measured sources remain frozen at
0.5.0rc1; production source is 0.5.0rc2, schema remains clue-community-1.

Offline installation from the source archive also passed with the pinned build backend and runtime wheels only (no network access). Hosted Linux and macOS 3.12–3.14 and docs checks all passed on commit `35173b84f05d9f34812102235075b330e188f0eb` in private draft PR #2. The current PR is authoritative for subsequent status.
Current action references use verified immutable v7 checkout/setup-python SHAs
with Node 24; feature branches run the matrix through PRs with superseded PR runs
cancelled. Hosted outcomes must be read from the actual check run before claiming
all remote platforms passed.

After the README/original-results navigation update, strict MkDocs and Twine
checks passed again. The rebuilt private wheel contains the updated README;
offline installed-wheel smoke tests were repeated on Python 3.12–3.14. Package
code and saved measurements are unchanged; previous full-suite results apply to
that unchanged code. This documentation update makes no additional paid calls.

Code is prepared for production review, not publicly published. Remaining owner
gates are rights/license clearance, independent template/rule readers, outside-
user installation review, manual privacy review and organization publishing
approval. No license grant, human signoff, public upload or merge is fabricated.
