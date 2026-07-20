# The passes

Complete the work in these passes, in order. Each pass has a distinct failure
mode it exists to prevent; skipping one reintroduces that failure.

## Evidence and intellectual-honesty rules (bind every pass)

1. **Never invent a citation, page, quote, result, or implementation fact.**
   If pagination is unavailable or unstable, cite chapter/section plus the
   source file location. Mark OCR uncertainty.
2. **Separate four things and never collapse them into one sentence:**
   what the author claims; what evidence the book presents; your inference for
   Sheevook; a product decision or proposal.
3. **The book is primary evidence for the author's argument, not necessarily
   for the truth of the argument.** Grade empirical support independently. A
   famous framework or prestigious author receives no exemption.
4. **Date-sensitive claims accrue verification debt.** Platform rules, laws,
   API capabilities, model behavior/pricing, benchmarks, market conditions,
   and current best practices must be checked against current authoritative
   sources before entering code, prompts, constants, or user-facing copy. If
   live research is unavailable, mark them `VERIFY-LIVE` and block the
   corresponding implementation task.
5. Prefer original research, official documentation, statutes/regulators, and
   first-party platform sources for verification. Label secondary and
   anecdotal evidence as such.
6. Distinguish causal evidence from correlation, case study, expert judgment,
   metaphor, and speculation. Capture population and context limits.
7. Search for disconfirming evidence and alternative explanations.
8. Preserve meaningful disagreement with existing research. Do not smooth
   contradictions into vague consensus.
9. Paraphrase by default. Short quotations only when exact wording is uniquely
   important, always with a source location. Never reproduce substantial
   portions of the book.
10. Never infer that absence from the book proves absence in the field.
11. Keep an uncertainty ledger: `high`, `medium`, `low`, or `unverified`
    confidence, with low-confidence recommendations explained.

## Pass 0: Intake, integrity, and baseline

SKILL.md's Steps 0-3 are the pre-flight for this pass: by the time you get here
the source is captured, hashed, and measured, and the mode and focus are known.
Do not redo that work - carry the results in and spend Pass 0 on what the
pre-flight did not cover, which is the inventory, the project baseline, and the
files. If a pre-flight step was skipped (a resumed run, a source handed over
mid-conversation), complete it here rather than assuming it happened.

1. Confirm the source can be read. Identify title, author, edition,
   publication year, format, pagination scheme, table of contents,
   appendices, notes, bibliography, figures, and index where present.
2. Record extraction limitations honestly: missing pages, scan/OCR errors,
   inaccessible figures, DRM, duplicate pages, uncertain edition, or (for a
   paste) possible truncation. Do not conceal gaps.
3. Hash or otherwise identify the source (`sha256sum`) so a later run can tell
   whether it changed. Do not modify the book.
4. Read the project baseline named in SKILL.md and locate the research docs
   and code modules overlapping the book's topics.
5. Read `06-FINAL-SYNTHESIS.md` from any COMPLETE prior book run whose topics
   overlap this one. You need to know what the project already accepted from
   another author before you can tell whether this book confirms it, sharpens
   it, or contradicts it.
6. Write `00-READING-MAP.md` with: bibliographic identity and source location;
   source-integrity notes; chapter/section inventory; initial
   topic-to-Sheevook mapping; the batch plan as concrete line ranges; and a
   coverage checklist with every chapter initially `not started`.
7. Initialize `claims/INDEX.md` and `CONTINUE-HERE.md`.

**Batch plan.** Target 3,000-6,000 words per batch. Break at chapter or section
boundaries rather than mid-argument, even where that means an undersized batch -
a mechanism split across two batches is a mechanism you will record twice and
understand once. Number batches sequentially; `batch-NN.md` in `claims/` matches
the batch number exactly.

Address batches in whatever unit the source actually has. Text extracted to
`source/book.md` has line ranges; a PDF read through the Read tool's `pages`
parameter has page ranges and no lines at all. Pick one unit per run, say which
in the reading map, and use it consistently in every `Location` field - a ledger
whose locations mix units is a ledger nobody can check a claim against later.

If the source is incomplete, continue with the readable material and clearly
scope all conclusions. Ask for another copy only if the missing material makes
the requested result materially unreliable.

## Pass 1: Structural reading

Read the preface/introduction, table of contents, conclusion, chapter
openings and endings, figures/tables, appendices, notes, and index as
available. Build a provisional model of:

- the central thesis and intended audience;
- the problem the book claims to solve;
- the argument structure and dependencies between chapters;
- named frameworks and definitions;
- recurring mechanisms, examples, and prescriptions;
- the evidence base and likely weak points;
- terms that require exact interpretation;
- likely overlap with Sheevook's research and architecture.

Update the reading map. This pass is orientation, not a substitute for close
reading.

## Pass 2: Exhaustive close reading in batches

Read every substantive chapter, appendix, figure, table, endnote, and
relevant bibliography entry, in the batches planned in the reading map,
checkpointing after each batch. Record claims in `claims/batch-NN.md` using
the record format in templates.md, with stable IDs (`BK-001`, ...) issued from
the counter in `CONTINUE-HERE.md`.

Under a narrow focus, out-of-focus chapters are read at Pass 1 depth only and
marked `skimmed-out-of-focus` in the reading map with a one-line reason. Still
record anything that lands squarely on Sheevook - a focus scopes what you go
looking for, not what you are allowed to notice.

For each batch:

1. Extract claims and mechanisms, not just topics.
2. Capture operational detail: inputs, decisions, sequence, thresholds,
   failure modes, expected outputs. This is what makes a claim implementable
   later; a topic label is not.
3. Capture negative knowledge: what not to do, boundary conditions, cases
   where the method fails.
4. Note dependencies on data Sheevook does not have or cannot honestly infer.
5. Record candidate product implications without prioritizing them yet.
6. Mark the exact coverage range complete in `00-READING-MAP.md` and add the
   batch's row to `claims/INDEX.md` (file, line range, ID range, state).
7. Update `CONTINUE-HERE.md`, including the claim-ID counter, before starting
   the next batch.

Do not declare a chapter complete from its summary alone. Do not re-read a
completed batch's source lines - if you need what was in it, read its claim
file. The ledger only works as external memory if you actually rely on it.

## Pass 3: Second-pass synthesis across the whole book

Revisit the claim ledger after the first complete read - all of it, every batch
file in one sitting if context allows. This pass is the one that cannot be done
piecemeal: seeing that chapter 2's "activation loop" and chapter 11's
"onboarding ladder" are the same mechanism requires both in view at once. If the
ledger is too large for one pass, work through it in halves and then do a
dedicated reconciliation across the halves - do not skip the reconciliation,
which is where the cross-chapter findings actually live.

Look across chapters for:

- concepts repeated under different names;
- dependencies and causal chains;
- tensions or internal contradictions;
- frameworks that only work together;
- hidden assumptions about company size, channel, geography, maturity, data
  volume, budget, or organizational structure;
- examples that do not actually support the general claim made from them;
- ideas easy to encode deterministically versus ideas requiring human
  judgment (Sheevook strongly prefers the former);
- missing topics that limit applicability to Sheevook.

Consolidate duplicates without losing source locations - mark them
`Duplicate of: BK-###` in place rather than deleting, so every ID a later file
cites still resolves.

Claims that only become visible in this pass get fresh IDs from the counter and
go in `claims/synthesis.md`, not in a batch file - they belong to the book as a
whole rather than to any one range, and backdating them into a batch would
falsify that batch's ID range and hide the fact that the cross-chapter read is
what found them. Give each one a `Location` listing every section it draws on.
Add `synthesis.md` to `claims/INDEX.md` as its own row.

Write a concise conceptual model of the book into the reading map.

## Pass 4: Reconcile with Sheevook

For every relevant claim, compare against the actual repository - search both
research and code before concluding anything is missing. Write
`02-SHEEVOOK-DELTA.md` using the delta table and delta classes in
templates.md.

Delegate the searching, per the delegation rule in SKILL.md: batch claims by
domain area and give each area to an `Explore` subagent that returns finished
delta rows with real file paths. Keep the classification decision yourself -
a subagent can tell you what the code does, but whether that counts as
`CONFIRMS` or `REFINES` depends on the whole book model, which only you hold.

Reconcile against prior book runs too, not just the repo. Where this book meets
a claim another book already contributed, say which: agreement between two
independent authors raises confidence, and disagreement is a finding worth
surfacing on its own rather than quietly resolving in favor of the newer read.

Check especially for implications to: product positioning and scope; brand,
audience, journey, campaign, content, and sales strategy; content creation,
rewriting, tailoring, stress-test lenses, and approval; scheduling,
publishing, community, media, and integrations; attribution, analytics,
learning loops, economics, and data sufficiency; onboarding, workflows,
accessibility, error states, and calm/dense design; privacy, security, legal
compliance, claims safety, and AI disclosure; deterministic engines, AI
prompt context, model gating/caching, and costs; schema/domain types,
repository boundaries, project scoping, tests, and docs; differentiation,
pricing/packaging, operational reliability, and maintainability.

Do not call something missing until repository search supports that
conclusion. Do not propose rebuilding an existing capability under a
different name.

## Pass 5: Adversarial and live-verification pass

Write `05-ADVERSARIAL-REVIEW.md` before prioritizing opportunities. For the
most consequential claims and every proposed behavior change:

1. State the strongest objection or competing framework.
2. Inspect the book's cited evidence where available.
3. Identify evidence quality, sample/context limitations, and causal gaps.
4. Check whether the recommendation conflicts with Sheevook's observed
   product evidence, existing research, or non-negotiable doctrine.
5. Verify current/time-sensitive facts against authoritative sources when
   tools allow (WebSearch/WebFetch). Record URL, publisher,
   publication/update date, access date, and exactly what it supports.
6. Decide: `keep`, `narrow`, `defer`, `reject`, or
   `blocked-pending-verification`.

Never use web research to make a stale book appear current. Preserve both the
book-era claim and the present-day correction - the difference is itself a
finding.

**When verification is unavailable** - no web tools in the session, a source
behind a paywall, a platform that does not document the behavior - the decision
is `blocked-pending-verification`. Never `keep`. A date-sensitive claim that
could not be checked is not thereby fine; it is unchecked, and the task it
feeds carries the block until someone checks it. Record what you tried, so the
next session does not repeat a dead end. This is the rule most likely to be
rationalized away late in a long run, when the backlog looks nearly done and
one blocked task is all that stands between here and finished.

## Pass 6: Opportunity discovery

Translate only surviving findings into `03-OPPORTUNITY-MAP.md` (table in
templates.md, stable IDs `OPP-001`, ...). Explore more than obvious new
features:

- improving existing algorithms, guardrails, fallbacks, and validation;
- adding or refining deterministic strategy/context layers;
- better user decisions, explanations, warnings, and refusal states;
- closing quality gaps in generated/tailored output;
- improving measurement honesty and feedback quality;
- reducing friction, failure, latency, token cost, or maintenance cost;
- strengthening tests, observability, documentation, and research/code drift
  detection;
- removing behavior the evidence suggests is harmful;
- experiments where evidence is uncertain but testable;
- deliberate non-features where restraint is the product improvement.

Evaluate fit against the core loop, target user, product principles, data
availability, offline/no-key behavior, and both database engines. Reject
ideas that create unsupported analysis, fake automation, or complexity
disproportionate to user value.

## Pass 7: Convert opportunities into implementation-ready tasks

Write `04-IMPLEMENTATION-BACKLOG.md` using the task templates in templates.md.
Prefer the smallest independently valuable vertical slices; epics only when
necessary.

Match the template to the task's size: XS/S tasks use the short form, M/L/XL
use the full form. A one-line copy fix does not need a rollout plan or a
migration-impact section, and forcing it to have one produces a paragraph of
"n/a" that teaches the reader to skim - which is expensive later, when a real
migration risk is sitting in that field on a different task. If a short-form
task turns out to need three of the full form's fields, that is evidence it was
not actually XS; resize it.

Acceptance criteria must be observable and testable, never "works well" or
"improve UX". Include error, empty, loading, permission, no-provider,
multi-project, and SQLite/Postgres cases where relevant. Name existing
interfaces and patterns to reuse.

Do not fabricate numeric impact estimates. If reach, confidence, or effort is
unknown, say so - explicit qualitative reasoning beats fake RICE precision.

Organize into: quick wins; core-loop improvements; larger capabilities/epics;
experiments and measurement plans; research/documentation/test debt; rejected
or deferred proposals with reasons. Add a dependency-aware recommended
sequence and identify the best first slice. Cross-reference existing
`TODOS.md` items and completed work to avoid duplicates.

## Pass 8: Durable synthesis and research integration

Update the appropriate file(s) under `research/` and write
`06-FINAL-SYNTHESIS.md` containing:

1. bibliographic note and scope limitations;
2. the book's central model in no more than 15 bullets;
3. the highest-value lessons for Sheevook;
4. what was genuinely new versus already known;
5. contradictions and how they were resolved or preserved, including
   disagreements with claims accepted from prior book runs;
6. claims rejected, stale, or blocked on verification, each with what would
   unblock it;
7. changes made to durable research, summarized well enough to stand alone -
   because `research/` is untracked, this section is the only version-controlled
   record that the work happened, and the only way to reconstruct it if the
   local `research/` tree is ever lost;
8. prioritized task summary with IDs and dependencies;
9. the recommended first implementation slice;
10. remaining gaps and the next research questions.

Add the durable research document to `research/README.md`'s index where its
structure calls for it. Link, do not duplicate, existing research.

`research/` is gitignored in this repo by deliberate choice (see SKILL.md), so
verify your write actually landed - a file written into an ignored tree gets no
git feedback at all, and a silent failure here loses the most valuable output
of the whole run. Read the file back after writing it, and say plainly in the
final report that this document lives on disk only.

Ensure every material proposal traces backward:

```text
TASK -> OPP -> BK claim -> precise book location
                     \-> current verification source when required
```

and forward:

```text
research finding -> affected product behavior/files -> acceptance tests
```
