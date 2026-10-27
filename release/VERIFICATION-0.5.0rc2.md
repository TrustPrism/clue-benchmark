# 0.5.0rc2 production verification — October 27, 2026

The private candidate has **282 passing local tests** (86.98 seconds), plus Ruff
lint/format checks for all 68 tracked Python files. One upstream Google SDK
deprecation warning is unrelated to inference; CI uses provider mocks only.

Fresh noneditable installed-wheel smoke tests passed outside the checkout on
macOS arm64 with Python **3.12.13, 3.13.12 and 3.14.6**. Networking was blocked;
provider/figure/docs extras were absent. Checks covered generation, validation,
public export, callback scoring, distributed-evidence replay, historical gallery
and the final 144-slot nuisance replay. Every shipped source/resource byte
matches the reviewed working tree. Wheel: 316,527 bytes; source archive: 288,561
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

Hosted Linux/macOS 3.12–3.14 CI and docs are being verified in private draft PR #2.
Current action references use verified immutable v7 checkout/setup-python SHAs
with Node 24; feature branches run the matrix through PRs with superseded PR runs
cancelled. Hosted outcomes must be read from the actual check run before claiming
all remote platforms passed.

Code is prepared for production review, not publicly published. Remaining owner
gates are rights/license clearance, independent template/rule readers, outside-
user installation review, manual privacy review and organization publishing
approval. No license grant, human signoff, public upload or merge is fabricated.
