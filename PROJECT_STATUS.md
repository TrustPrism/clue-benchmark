# Follow-up execution update — October 27, 2026

The explicitly authorized nuisance follow-up completed **98 calls** (96 scored
plus two probes) on eight underlying worlds. Receipt-based estimated total:
**$4.731671**; unresolved holds **$0**; no transport/protocol failures. Lite's
four-report counts at 0/100/1000 nuisance records were **7/8, 5/8, 7/8**: the
primary effect is zero. Eight-report Lite: **6/8, 3/8, 4/8**. Flash: 8/8 in every
panel. Four worlds per stratum, two attempts each; the earlier improvement did
not reproduce here. [Complete results and limits](docs/nuisance-followup-2026-10-27.md).

Previous preparation/status records below are retained as history. Public release,
rights clearance and independent human review remain pending; no more paid
experiments are included.

---

# Release candidate update — October 27, 2026

The private **0.5.0rc1** candidate adds installed offline presets, public exports,
case inspection, Python agent evaluation, offline historical replay, reports,
searchable docs and guarded release workflows. See [release notes](release/RELEASE_NOTES-2026-10-27.md).

The new nuisance study is prepared on eight independent worlds and 96 scored
slots plus two compatibility probes. Maximum combined commitments: **$9.838478**.
Paid calls: **zero**. Settled estimate/holds: **zero/zero**. Results are unmeasured;
exact native access, source-bound human execution approval and independent owner
release gates remain pending. No public distribution or licensing grant occurred.

The historical status below is preserved verbatim; superseded broader paid study
proposals are not current authorizations. No further paid conditions are included.

---

# Clue Benchmark: where the project stands

**Updated October 16, 2026.** This is the main plain-language project summary.
For the detailed reports and technical guides, see the [documentation index](docs/README.md).

## The short version

We have a working benchmark that generates reasoning puzzles and checks whether
the information given to an AI is enough to solve them. Several model studies
have finished, including the full Qwen run with improved settings.

The results show both easy and difficult puzzles. More importantly, the benchmark
can distinguish a wrong answer from a guess made without enough information,
and from a model that never finished answering.

**The project is ready to prepare a coordinated research study. It is not yet
ready for public release or a finished research paper.** The next study is a
proposal; it has not been run or funded. The experiments described below have
finished, and their completion monitor is paused.

## What the tool can do today

- Generate new puzzles with a known answer and check the answer automatically.
- Give an AI all the clues, only some clues, or clues shared between several agents.
- Check whether a particular set of clues is enough to identify one answer.
- Include misleading reports under an explicit rule about how many may be false.
- Add irrelevant information, vary the puzzle structure, and change how clues
  are presented or shared.
- Save the inputs, answers, resource use and evaluation records so the results
  can be checked again without paying for another model run.

These checks apply to the puzzle's stated rules. They do not prove that a model
followed a sound reasoning process just because its answer was right.

## Results gathered so far

### 1. Early studies showed why information availability matters

The initial Gemini study covered **270 planned evaluations**, with 269 returned
responses and one recorded service failure.

On eight shared puzzles, Flash solved all eight when given all the evidence.
When the clues were split into 32 private agent views, it correctly declined to
answer in every view because no individual agent had enough information.
Flash-Lite sometimes guessed instead. Some guesses in another sharing condition
were correct even though the available evidence did not establish the answer.

Adding irrelevant records increased cost, but did not consistently make the
models less accurate. Misleading reports were also largely manageable in these
small examples.

**What this tells us:** answer accuracy alone misses important differences.
Knowing when there is not enough information is a separate ability.
[Detailed early results](docs/pilot-results.md).

### 2. Larger comparisons separated stronger and weaker models

A later high-thinking Gemini study covered **360 planned evaluations across
30 underlying puzzles**, with repeated attempts and matched variations. One
request timed out; the other 359 returned responses.

Flash solved every evaluation in both 32-necessary-clue conditions. Flash-Lite
solved only 9 of 30 attempts in one condition and 7 of 30 in the other.
Other comparisons examined misleading reports and extra truthful clues.
Flash remained strong; adding reports did not always make a puzzle harder.

**What this tells us:** the tool can expose differences between models, but
the number of clues is not a universal difficulty score. Repeating one puzzle
does not turn it into several independent puzzles.
[Detailed comparison](docs/hardness-results.md).

### 3. Flash's performance changed when it had more room to think

In a small size-and-budget study, Flash initially solved **2 of 6** difficult
64-suspect puzzles. With a larger output allowance on the same six puzzles,
it solved **5 of 6**.

**What this tells us:** some apparent model failures depend on the allowed
resources. We must report the settings alongside the score.
[Budget and difficulty study](docs/flash-limits.md).

### 4. A separate hard set remained difficult for Flash

A fixed follow-up used **48 fresh hard puzzles** and a larger output allowance:

- **9 correct answers** — 18.75%.
- **28 wrong answers.**
- **11 declined answers**, despite enough information being available.

All 48 requests returned usable responses. There were no service or answer-format
failures in this study. Each puzzle had a uniquely identifiable answer under its
rules. The puzzles contained 455 reports, but that does not mean all 455 were
necessary to solve them.

**What this tells us:** we have a demonstrated hard regime for Flash under the
tested settings. It does not establish that every strong model would struggle,
or that more resources or additional tools would not help.
[48-puzzle results](docs/flash-hard-scale.md).

### 5. The latest Flash screening supplied useful easy controls

The recent screening assigned Flash 72 evaluations. It returned **71 responses**:
41 correct answers supported by sufficient evidence, 29 appropriate decisions
not to answer, and one declined answer where the evidence was sufficient.
The remaining request was interrupted by the user and was not retried.

Flash solved all six examples in each of the 4-, 8- and 16-necessary-clue groups.
A simple clue-following program also solves the prepared burden constructions.

**What this tells us:** these are useful controls, but requiring more clues does
not necessarily require deeper reasoning. The benchmark needs both easy controls
and separately demonstrated hard conditions.
[Screening results](docs/publication-screening-results.md).

### 6. Qwen now finishes more answers, but still makes substantial mistakes

Qwen's first configuration frequently ran out of output space before submitting
an answer. A nine-call diagnostic tested recommended sampling, a larger allowance,
and disabling thinking. That led to a complete follow-up using recommended
sampling with an 8,192-token allowance.

The follow-up has **72 results**: 69 new local calls and three matching pilot
responses carried forward. Every planned evaluation is accounted for:

- **22 correct answers supported by enough evidence.**
- **11 appropriate decisions not to answer.**
- **15 wrong answers despite enough evidence.**
- **19 answers made without enough evidence**, including two lucky correct guesses.
- **5 responses cut off at the output limit**, without a usable answer.

Overall, **67 of 72** evaluations produced a valid answer or abstention. On the
29 evaluations with returned responses under both old and new settings, answer
submission improved from 13 to 25, while supported correct answers changed from
13 to 12.

The three-case diagnostic found no benefit from raising the sampled output
allowance from 8K to 32K on those cases. That does not rule out a benefit on other
puzzles. Disabling thinking did not consistently fix completion or accuracy.

**What this tells us:** improved settings fixed much of the missing-answer
problem, but did not make Qwen reliably correct. We can now see more of its
actual answering and uncertainty-handling failures.
[Full Qwen results](docs/qwen-sampled-screening-results.md) ·
[Settings diagnostic](docs/qwen-diagnostic-results.md).

## What the combined evidence supports

The strongest research direction is a benchmark that helps explain **why** an AI
failed: it lacked enough information, answered incorrectly despite having enough,
guessed without support, or failed to finish.

The evidence also supports keeping a range of easy and hard cases. It does not
support one overall score across all our studies, a universal ranking of models,
or treating clue count as a measure of reasoning depth. The studies used different
models, settings and puzzle families, and several were used to choose later settings.

Sharing in these experiments follows programmed rules. We have not demonstrated
that a team of AI agents can learn to communicate effectively from these results.
[Full combined assessment](docs/combined-benchmark-assessment-2026-10-16.md).

## What is complete, and what remains

**Complete:** the working generator and evaluator; the studies summarized above;
the Qwen configuration diagnostic and full follow-up; automated validation;
saved-result replay checks; and a paper-informed study proposal.

**Still needed:** a check against the closest benchmark implementations,
independent review of the puzzle wording, an outside reproduction of the workflow,
and one coordinated final study on fresh puzzles. Ownership, licensing and
permission for public distribution also remain unresolved. The project stays private.

Local checks have passed, but they are not the same as someone outside the project
independently reproducing the work.

## The proposed next study

The recommended design uses **150 fresh puzzles** and three model families:

1. **60 puzzles about information sharing:** compare complete information,
   private information, and limited versus more complete delivery.
2. **60 puzzles about misleading reports:** compare matched versions with zero
   and two false reports under the same public reliability rule.
3. **30 puzzles with no unique answer:** test whether models appropriately decline.

Existing experiments help choose the settings, but will not be relabeled as
fresh final-test data. Identical model requests would be reused transparently
rather than paid for twice.

The planning scenario is approximately **$68–$75 in API charges**, using earlier
frozen prices. A smaller 60-puzzle alternative is approximately **$27–$30**, with
less precise conclusions. These are not current quotes or approved budgets;
exact inputs, model access and prices must be checked before any new run.

The immediate next step is to finish that offline preparation and validation,
then review the exact study and cost before execution.
[Concrete study plan](docs/publication-study-protocol-2026-10-16.md) ·
[How related papers organize their benchmarks](docs/benchmark-paper-structure-review-2026-10-16.md).

## Spending on the most recent work

The latest paid Flash screening recorded approximately **$1.01**, with another
**$0.035 reserved** for the interrupted request. The Qwen diagnostic and follow-up
used local inference and had **no API charges**, although they used computer time.
Earlier studies have separate spending records in their detailed reports.
Recorded usage estimates are not provider invoices.

## Where to start reading

Use this file for current status, the [documentation index](docs/README.md) for
navigation, and the [study proposal](docs/publication-study-protocol-2026-10-16.md)
for the next research step. Older planning notes and superseded summaries are in
the [archive](docs/archive/README.md). Detailed completed-study reports remain
available so their results and limitations can still be checked.
