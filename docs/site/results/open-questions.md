# Open questions for the initial preview

This is an early research preview of Clue Benchmark 0.5.0rc2. The measured
results are preliminary; the software candidate, redistribution licenses and
human reviews remain pending. The owner requested an initial public preview
with those questions visible. This does not grant an open-source or dataset
license or claim a PyPI release.

## Questions the experiments leave open

1. **Does irrelevant evidence ever help consistently?** The original five-world
   Lite improvement did not repeat in the expanded follow-up. The primary
   endpoint change was zero, with a descriptive interval of [-25, +25] percentage
   points on six worlds. A larger, separately preregistered sample would be
   needed to distinguish a repeatable benefit from sampling and response variation.
2. **Why did individual worlds improve or worsen?** Four primary worlds stayed
   unchanged, one improved and one worsened. These outcomes do not identify a
   reasoning mechanism. Content, order and context length need separate controls
   before attributing changes to distraction or useful extra computation.
3. **Is the harder-setting dip repeatable?** Lite's 9/12 → 5/12 → 7/12 pattern
   at 0/100/1,000 irrelevant records is small and non-monotonic. Does it recur on
   fresh worlds, and how much is ordinary response variation?
4. **When does robustness become worth its cost?** In the four-report setting,
   cost rose about 56× for Lite and 77× for Flash at 1,000 records without higher
   endpoint accuracy. Does that tradeoff change with useful redundancy, related
   distractors, other models or a different resource allowance?
5. **What makes a certified puzzle difficult for an agent?** Minimum necessary
   evidence measures information burden, not proof depth or model difficulty.
   Which structural properties predict errors after controlling for simple
   construction heuristics, input length and output budget?
6. **How stable are results across resource settings and model versions?** The
   adaptive six-world budget comparison and fresh 48-world hard confirmation
   answer different questions. Fresh matched comparisons are needed before
   generalizing across thinking/output allowances, formats or model revisions.
7. **Can agents learn to communicate the right evidence?** Current star
   forwarding is programmed. It demonstrates delivery sufficiency, not learned
   collaboration or efficient communication policies.
8. **Do supported correctness and completion improve together?** Qwen's matched
   returned slots showed more completed actions without higher supported
   correctness. Future work should retain lucky guesses, appropriate abstentions,
   wrong answers and protocol failures as separate outcomes.
9. **Do independent people interpret the rules as intended?** Two independent
   template/rule reviews and an outside installation/replay run remain pending.
   Automated solver checks do not substitute for these reviews.

These are proposed research questions, not registered experiments or authorized
spending. The October 27 allowance is closed at an estimated **$6.96**, with
no holds and no further paid calls. Any future study requires a separate plan
and budget.

## Questions before a full software and data release

- **Rights and licenses:** Does TrustPrism have redistribution rights for all
  imported code, contributor work, generated assets and saved provider outcomes?
  Are Apache-2.0 for code and CC BY 4.0 for data/prose the final approved scopes?
- **Attribution and maintenance:** Who are the confirmed maintainers and citation
  authors, and which notices or exclusions are required?
- **Human validation:** Who will complete the two rule reviews and outside
  installation/reproduction review, and how will disagreements be recorded?
- **Historical archive boundary:** Which additional reproduction archives may
  be distributed after manual privacy review? The owner authorized public
  visibility of the existing repository and its history. The documentation
  deployment excludes credentials, authorizations, ledgers and raw provider
  prose; ignored operational archives remain local and are not uploaded.
- **Distribution:** Which organization-owned PyPI and dataset accounts will host
  approved artifacts? Are protected environments, trusted publishing and final
  hosted dataset/Croissant checks configured?
- **Final acceptance:** Which exact source revision and artifact hashes will
  the owner approve for the complete release? Public preview availability does
  not clear these gates.

## What is available now?

Read the [results and original-study index](index.md), including phase-separated
follow-up measurements, limitations and sanitized assignment downloads. Read
the [tutorial](../tutorials/first-dataset.md), [parameter reference](../reference/parameters.md)
and [release checklist](../maintainers/release.md). Package installation commands
describe the candidate workflow; no public PyPI release is claimed.
