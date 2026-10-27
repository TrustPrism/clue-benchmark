# Verification evidence — October 27, 2026

Local macOS arm64 / CPython 3.14.6: **263 tests passed** in 85.82 seconds.
One upstream google-genai deprecation warning; no paid inference.

Release source, tests, scripts and the agent adapter pass Ruff lint/format checks.
Repository-wide lint also encounters 33 pre-existing style errors in the preserved,
untracked examples/plot_project_highlights.py. Unrelated figure scripts were not
reformatted or committed.

Strict MkDocs 1.6.1 build passes in a separate Python 3.13 environment. Browser
inspection verified the responsive menu, search results and Escape-key return to
the search control. Full mobile/screen-reader human review remains pending.

A noneditable wheel installed outside the checkout in a fresh Python 3.14
environment using local wheels with --no-index. Generation, independent validation,
allowlisted public export, callback scoring, eight-world solver replay, historical
count replay and --help pass. Networking was blocked in the smoke process;
provider, figure and docs extras were absent. Every packaged Python source byte
matches the checked-out release source. Wheel: 296,413 bytes; sdist: 269,492 bytes.
Candidate artifact scanning found no matching secret/local-home-path patterns.

History and every member of all six historical archives were scanned without
changing originals. Local home paths/private operational members were detected:
manual review and sanitized distribution copies remain required. Pattern scanning
is not comprehensive privacy or ownership clearance.

Follow-up dry run: 98 requests (96 scored + 2 probes), eight independent worlds,
combined child/probe ceilings 9,838,478 microdollars. Paid calls, settled estimate
and unresolved holds are all zero. Offline analysis labels all scored slots
never-dispatched and leaves effects unmeasured.

Linux/macOS Python 3.12–3.14 CI is configured; no completed matrix run is claimed.
Licensing, two independent rules readers, outside-user installation, final privacy
review and public distribution remain pending. The user explicitly approved pushing task commits to the existing private
TrustPrism release branch after automatic review requested that approval.
No public distribution is authorized by that push.

Only README.md, PROJECT_STATUS.md and examples/evaluate_public_agent.py differ
from pre-task dirty-file hashes. Their originals are preserved in the README
archive or private source/status snapshots. All other pre-existing local files
remain untouched.

Offline reproduction after installing the local wheel:

```sh
clue-benchmark examples replay distributed-evidence --output runs/replayed
clue-benchmark examples replay measured-results --output runs/recomputed
```

Add --figures to the second command with the figures extra installed. Use frozen
study sources for exact native study preflight; do not mix historical/current
source identities.
