# Independent wording and query review

A generated packet is preparation, not human validation. No independent reviews
have been collected in this phase.

## Sampling and reviewer independence

The readiness packet samples up to two cases from each of the 36 factorial cells
across development and test. Each puzzle appears with the targeted and
attribute-grouped menus. Both layouts use the same public clue bank. Every topic
has a representative actual first-response example, so reviewers can compare
the label with the evidence it reveals.

Use at least two independent human reviewers per item. Reviewers must not have
implemented the generator or produced the wording. Record a stable reviewer ID,
completion date, independence attestation, and whether external solvers or model
assistance were used. Maintainers must verify reviewer identity and independence;
the collector only checks the submitted attestations and coverage.

## Rubric

Read the public rules first. Suspects can share values; crime attributes match
the murderer; complete evidence identifies one murderer but need not identify
one full attribute assignment.

For each item:

1. Record whether every sentence has one clear logical interpretation. In
   particular, a positive cross-attribute clue says that at least one suspect
   has both values; it is not an implication about every suspect.
2. Record whether topic labels match the response examples. A crime comparison
   may compare a crime attribute with a suspect. A grouped suspect-attribute
   topic can reveal facts about different suspects on successive requests.
3. Optionally solve the puzzle and submit an exact suspect ID, with elapsed time.
   Answers are checked privately; disagreements require adjudication rather
   than being silently removed.
4. List each issue with a description and severity. Blocking issues include
   ambiguous quantifiers, misleading labels, inconsistent rules, and wording
   that changes the formal meaning. Minor issues include grammar or awkwardness
   that preserves an unambiguous meaning.

## Files and collection

~~~sh
clue-benchmark prepare-review \
  data/v0.3/private/dev.jsonl data/v0.3/private/test.jsonl \
  --output reviews/readiness-packet.json \
  --template reviews/response-template.json
~~~

The packet contains no answer, hidden world, seed, generation configuration,
necessity flag, or solver diagnostic. The template deliberately has no reviewer
identity or approved judgments.

A completed response has this shape:

~~~json
{
  "packet_id": "the exact packet checksum",
  "reviewer": {"id": "a verified reviewer ID", "human": true, "independent": true},
  "completed_at": "the actual review completion date",
  "reviews": [
    {
      "review_id": "an item ID from the packet",
      "wording_clear": true,
      "topic_expectation_clear": true,
      "answer": "S01",
      "issues": []
    }
  ]
}
~~~

This example is a schema illustration, not a completed review.

~~~sh
clue-benchmark review-check reviews/readiness-packet.json \
  reviews/reviewer-a.json reviews/reviewer-b.json \
  --cases data/v0.3/private/dev.jsonl data/v0.3/private/test.jsonl \
  --require-approved --output results/human-review.json
~~~

The collector rejects stale packet hashes, duplicate reviewer identities,
unknown/repeated items, nonhuman attestations, and missing judgments. It reports
coverage gaps, blocking issues, and answer discrepancies. Approval requires full
coverage, positive wording/topic judgments, and no blocking issues or answer
discrepancies. Approval still requires maintainers to verify the reviewers.
After wording or menu changes, generate a new packet and collect new signoff;
do not mark an old issue resolved by editing the old signed response.

Publish the sampling protocol, reviewer count, reviewed item count, issue
distribution, adjudication process, and resulting fixes. Human task-performance
claims require a separate study; this review establishes usability of the
controlled language and menu.
