---
name: book-to-product
description: >-
  Digest a full book (pasted text, PDF, EPUB, TXT, or Markdown) into durable
  Sheevook research plus an evidence-linked, implementation-ready backlog, and
  optionally implement the approved tasks. Runs a rigorous multi-pass method
  (intake, structural read, exhaustive batched close reading, cross-book
  synthesis, repository reconciliation, adversarial verification, opportunity
  discovery, task conversion, durable research/ integration) with multi-session
  resume. Use whenever the user wants to "digest", "ingest", "process",
  "extract insights from", "learn from", or "implement" a book; pastes a large
  body of book text; points at a book PDF/EPUB; asks to turn an author's
  framework into product work; or says "book to product" - even if they only
  ask to "summarize" the book, because for this project a summary without the
  delta analysis and backlog wastes the read.
---

# Book to Product

Extract a book's useful knowledge through repeated passes, reconcile it with
Sheevook's existing research and implementation, preserve it as durable
research under `research/`, and convert the strongest applicable findings into
evidence-linked, implementation-ready work. Optionally implement the tasks the
user approves.

You are the research lead, product strategist, staff engineer, and skeptical
reviewer at once. The task is never merely to summarize. Treat files as
external memory: record progress and findings as you go so the work can resume
across context windows and sessions without starting over.

The four required outcomes:

1. A faithful, navigable model of the book: theses, mechanisms, frameworks,
   evidence, examples, limits, assumptions, contradictions, open questions.
2. An addition to `research/` containing everything materially relevant to
   Sheevook, with precise source locations and honest confidence labels.
   Durable on disk, where the project reads it - see the tracking note in
   Step 2 for what that does and does not mean in this repo.
3. A delta analysis showing what the book confirms, refines, contradicts,
   obsoletes, or newly contributes relative to current research and code.
4. A prioritized backlog of implementable tasks, each traceable from book
   evidence to product rationale to code touchpoints and verification - and,
   when the user approves task IDs, the implementation of those tasks.

Coverage matters, but relevance is not a license to force every chapter into
the product. Record relevant ideas; explicitly discard inapplicable ones with
a short reason.

## Step 0: Check for prior and in-progress runs

Before anything else, inventory the runs that already exist:

```bash
head -n 3 docs/reports/research/books/*/CONTINUE-HERE.md 2>/dev/null
```

Three cases:

- **An unfinished run exists** (its `CONTINUE-HERE.md` does not say `COMPLETE`):
  tell the user which book(s) are in progress and ask (AskUserQuestion) whether
  to resume it or start a new book. On resume, follow the continuation protocol
  below and skip intake.
- **This book already has a COMPLETE run**: do not silently redo it. Report what
  the prior run concluded and ask whether the user wants a re-read (new edition,
  changed focus, or the repo has moved far enough that the delta is stale), a
  refresh of just the delta and backlog against today's code, or nothing.
- **Other books have COMPLETE runs**: note their slugs. They are inputs to
  Pass 0 and Pass 4 - a claim that contradicts a previously accepted claim from
  another book is a finding, not a duplicate.

## Step 1: Intake

Ask the user for what you cannot infer, in one AskUserQuestion call:

1. **Source** (skip if already given): how will the book arrive?
   - a file path (PDF, EPUB, TXT, Markdown, or a directory of chapters)
   - pasted into the chat (they paste after answering)
2. **Mode**:
   - `research-and-backlog-only` (Recommended): write research and briefs,
     touch no application code. Implementation happens only after the user
     approves specific task IDs at the end.
   - `research-then-implement`: same research phase, then after presenting the
     backlog, ask which task IDs to implement and proceed on approval.
3. **Focus**: "everything relevant to Sheevook" (default) or a narrower angle
   the user names (e.g. "just the pricing chapters").

Focus is a real scoping lever, not a preference. Under a narrow focus,
out-of-focus chapters get Pass 1 structural treatment only and are marked
`skimmed-out-of-focus` in the reading map with a one-line reason; the coverage
audit accepts that state. Never let a narrow focus silently become a full read,
and never let it drop a chapter with no record that it was considered.

Never silently cross from research into implementation. Even in
`research-then-implement`, implementation starts only after the user picks
task IDs from the finished backlog.

Infer title, author, edition, and year from the source itself; ask only when
proceeding would be unsafe or materially ambiguous. Derive `BOOK_SLUG` as
lowercase-kebab-case of the title.

## Step 2: Capture the source

Everything for a run lives in `docs/reports/research/books/<BOOK_SLUG>/`.

**If the book is a file:** do not copy or modify it. Record its absolute path
and a `sha256sum` in the reading map so a later session can tell whether it
changed. For PDFs, extract text once with `pdftotext` if installed, otherwise
read via the Read tool's `pages` parameter. Figures are not lost either way:
the Read tool renders PDF pages visually, so a page whose argument lives in a
chart or diagram can be *looked at* rather than written off - reserve
"inaccessible figure" for genuine DRM, corruption, or an image-only scan you
cannot resolve. For EPUB, convert once to text with `pandoc` if available,
otherwise unzip and strip the XHTML with a small script; write the converted
text to `source/` (see below) and read from that.

**If the book is pasted:** immediately write the pasted text verbatim to
`docs/reports/research/books/<BOOK_SLUG>/source/book.md` before doing anything
else - pasted text exists only in conversation context and will not survive
compaction or a new session. For very long pastes, ask the user to paste in
parts and append each part; after the final part, confirm with the user that
the last line you received matches the actual end of the book, because
terminal pastes truncate silently.

Hash `source/book.md` too, and rehash it at the start of every resumed session.
A converted or pasted source is more fragile than a file the user owns: an
appended part, a re-paste, or a truncated final chunk changes the line numbers
that every claim location in the ledger points at. If the hash moved between
sessions, find out why before trusting a single recorded location.

**Committing, and what "durable" actually means here.** Three different
tracking states are in play, so be precise about them:

- `source/` holds full copyrighted text and must never be committed. Ensure
  `.gitignore` contains `docs/reports/research/books/*/source/`; add it if
  missing.
- The rest of the run directory under `docs/reports/` is tracked, and is
  durable in the ordinary git sense.
- **`research/` is gitignored in this repo on purpose** (commit `e638683`,
  "untrack research notes from the repo"). Pass 8's durable integration
  therefore survives on disk, not in version control - it is not backed up by
  a push and it is invisible to anyone who clones. Write it anyway, because
  `brandContext()` and the rest of the project read it locally, but never tell
  the user their research was "committed" or "preserved in the repo", and never
  `git add research/`. If the ignore rule ever changes, this paragraph is stale;
  check `git check-ignore -v research/` rather than trusting it.

Do not commit anything yourself unless the user asks.

## Step 3: Size the run and say so out loud

Before reading anything closely, measure the source (`wc -w source/book.md`, or
the page count for a PDF) and plan the batches: **3,000-6,000 words per batch**,
addressed by line range, never overlapping. A typical business book is 60k-90k
words, which is 15-25 batches - real multi-session work.

Tell the user the shape of the run before starting it: word count, batch count,
roughly how many sessions that implies, and that the run is resumable at any
point. A user who expected a ten-minute summary should learn that here, not
four hours in. If the number surprises them, a narrower focus is the lever.

The batch plan itself is written in Pass 0, as concrete line ranges in
`00-READING-MAP.md` (rules in passes.md). Thereafter, read from `source/` by
line range only; never re-read a completed batch to "check something" - that is
what the claim ledger is for.

## Working files

Create the run directory and maintain these files incrementally - they are the
external memory that makes multi-session work possible:

```text
docs/reports/research/books/<BOOK_SLUG>/
├── source/               (pasted/converted book text - gitignored)
├── 00-READING-MAP.md
├── claims/
│   ├── INDEX.md          (batch -> file, ID range, coverage state)
│   ├── batch-01.md
│   ├── batch-NN.md       (one file per reading batch)
│   └── synthesis.md      (Pass 3 claims that belong to no single batch)
├── 02-SHEEVOOK-DELTA.md
├── 03-OPPORTUNITY-MAP.md
├── 04-IMPLEMENTATION-BACKLOG.md
├── 05-ADVERSARIAL-REVIEW.md
├── 06-FINAL-SYNTHESIS.md
└── CONTINUE-HERE.md
```

The claim ledger is **split per batch, not one growing table**. A single
300-row markdown table is the wrong data structure here: appending to it means
matching unique text near the end of a long file, re-reading it costs the whole
table to see the last ten rows, and one bad edit corrupts every claim. Per-batch
files append cleanly, are cheap to read selectively, and localize damage.
`claims/INDEX.md` is the only thing you need to read to know what exists.

Also create or update the appropriate durable domain research document under
`research/` (usually `research/strategy/<topic>.md`; a new well-named file
only when no existing document is a natural home). Do not dump a raw chapter
summary into `research/` - integrate a decision-useful synthesis with
citations, limitations, counterarguments, and Sheevook implications, and add
it to `research/README.md`'s index where the structure calls for it.

Do not edit `TODOS.md` automatically. Proposed work goes in the book-specific
backlog so the user decides what enters the canonical queue. If an existing
task already covers a finding, cross-reference it instead of duplicating it.

The claim record format, index and delta tables, both task templates, delta
classes, priority meanings, and the CONTINUE-HERE template are in
[references/templates.md](references/templates.md). Read it before writing any
working file so IDs and fields stay uniform across sessions and books.

## Step 4: Run the passes

The full method is in [references/passes.md](references/passes.md). Read it in
full before starting Pass 0, and re-read the relevant section when entering
each pass. Do not skip from reading to feature ideas - the passes exist
because single-read extraction reliably misses mechanisms, cross-chapter
structure, and contradictions.

| Pass | What it produces |
|---|---|
| 0 | Intake, source integrity, project baseline, `00-READING-MAP.md` |
| 1 | Structural read: thesis, argument structure, overlap map |
| 2 | Exhaustive close reading in batches into `claims/batch-NN.md` |
| 3 | Second pass across the whole book: consolidation, tensions, hidden assumptions |
| 4 | Reconciliation with the actual repository into `02-SHEEVOOK-DELTA.md` |
| 5 | Adversarial + live-verification review into `05-ADVERSARIAL-REVIEW.md` |
| 6 | Opportunity discovery into `03-OPPORTUNITY-MAP.md` |
| 7 | Implementation-ready tasks into `04-IMPLEMENTATION-BACKLOG.md` |
| 8 | Durable `research/` integration and `06-FINAL-SYNTHESIS.md` |

The evidence and intellectual-honesty rules at the top of passes.md bind every
pass: never invent a citation or fact, keep author-claim / evidence /
inference / proposal separate, grade evidence independently of the author's
prestige, mark date-sensitive claims `VERIFY-LIVE` until checked against
current authoritative sources, and keep an uncertainty ledger.

## What to delegate, and what never to

Your own context is reserved for one thing: the accumulating model of the book.
Everything that would flood it with file dumps belongs in a subagent that
returns conclusions.

**Delegate.** Pass 4's repository reconciliation is dozens of "does the repo
already do this?" questions, each of which reads several files to answer. Batch
the claims by domain area (analytics, tailoring, publishing, AI/prompting,
scoping/security, UI/design, ...) and give each area to an `Explore` subagent
with the specific claims, the delta vocabulary from templates.md, and an
instruction to return finished delta rows with real file paths - not summaries
of what it read. Do the same for Pass 5's live verification: one subagent per
`VERIFY-LIVE` cluster, returning URL, publisher, date, and exactly what the
source supports. Run independent subagents concurrently in one message.

**Never delegate.** The close reading itself (Pass 2), the cross-book synthesis
(Pass 3), and the final judgment calls in Passes 5-8. Reading is where the
book's model is built, and it is built by one context accumulating it: a
subagent handed chapter 9 has not read chapters 1-8 and cannot see that the
author has quietly renamed a mechanism, contradicted an earlier caveat, or
built chapter 9 entirely on an assumption chapter 3 disclaimed. Splitting the
read across agents produces a per-chapter summary set, which is precisely the
artifact this skill exists to be better than.

Verify what comes back. A subagent that reports "no existing implementation" has
made a claim you are about to put in front of the user - spot-check the ones
that turn into P0 or P1 tasks against the actual files.

## Project constraints the book cannot overrule

Read `CLAUDE.md`, `DESIGN.md`, `research/README.md`, and (where present)
`VISION.md`, `TODOS.md`, `COMPLETED.md`,
`research/marketing-map/98-synthesis.md`, and
`research/marketing-map/99-gap-ledger.md` during Pass 0, plus the research
docs and code modules closest to the book's topic. Build the project map from
what exists now - trust executable code over stale status summaries. Use
`rg`/targeted reads; never ingest `.next/` or `node_modules/`.

The book can challenge the project, but it cannot automatically overrule the
repo's doctrine (deterministic-first AI with gates and caches, outcome-over-
engagement ranking, honest refusal of unsupported analysis, human approval
before publish, multi-project scoping, portable SQL behind the repository
layer, canonical platform files, AI disclosure duties). If the book exposes a
reason to revise a doctrine, present an explicit doctrine-change proposal with
evidence, risks, affected files, and migration cost - never an incidental task.

## Multi-session continuation

Assume the work exceeds one context window. `CONTINUE-HERE.md` is mandatory
from Pass 0 on, overwritten at every stable checkpoint (template in
templates.md). On any resumed run: read `CONTINUE-HERE.md` first, verify the
source identity/hash, resume at the exact next action without restarting
finished passes, and recheck repository facts that may have changed.

**The ID counters in `CONTINUE-HERE.md` are authoritative.** Issue the next
claim, opportunity, and task IDs from them directly; do not go trawling ledger
tails to reconstruct where you were. That makes the counters load-bearing, so
they must be updated in the same checkpoint that writes the IDs they count -
never write claims and update the counter later.

If approaching a context or time limit, stop cleanly only after updating all
working files and the continuation state - never claim completion because the
session is ending.

## Implementation phase

Applies only to task IDs the user explicitly approves after seeing the
backlog.

**A task with `Status: blocked` does not become implementable because the user
picked it.** The block means a date-sensitive fact behind it was never verified,
and shipping it writes an unchecked claim into code, a prompt, a constant, or
user-facing copy - the specific harm the whole verification rule exists to
prevent. If the user approves a blocked task, say what is unverified and offer
to verify it now; implement only if that check clears. Approval is not
evidence.

For each approved, unblocked task:

1. Reread the current code before editing; the repo may have moved since the
   research was written.
2. Use existing patterns; make the smallest coherent change satisfying the task.
3. Update mirrored research and code together.
4. Add focused regression tests; run relevant tests and lint, and the full
   `pnpm test` + `pnpm build` before calling a meaningful feature complete;
   run `pnpm verify:postgres` after SQL/schema changes when possible.
5. Report failures honestly. Never weaken tests or doctrine to pass a check.
6. Do not commit, deploy, publish externally, or perform destructive
   operations unless separately authorized.

## Finishing

Before declaring the research phase done, run every audit in
[references/audits.md](references/audits.md) (book coverage, relevance,
repository, evidence, task quality), verify the stopping conditions listed
there, record the audit results in `06-FINAL-SYNTHESIS.md`, and set
`CONTINUE-HERE.md` to `COMPLETE`.

Close with the concise final report format in audits.md, then - in either mode -
end with a decision, not homework. Do not hand the user a wall of thirty task
IDs and ask them to pick; you have already computed a dependency-aware sequence
and a recommended first slice, so put that to work. Ask (AskUserQuestion):

1. the recommended first slice, named and one-line justified (recommended);
2. quick wins only (the XS/S tasks, listed by ID);
3. let them pick specific task IDs;
4. stop here - research and backlog only.

Offer only unblocked tasks in options 1 and 2. If blocked tasks exist, say so in
one line above the question rather than folding them into a choice.

In `research-and-backlog-only` mode, a choice to implement means confirming the
mode change first. The backlog is a durable artifact either way: nothing is
lost by stopping, and the user can approve task IDs in any later session.
